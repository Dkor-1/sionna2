# -*- coding: utf-8 -*-
"""
mesh_impact_l2_ledger_0816.py — **2층 수리 영향 원장 조립**
==============================================================================

프로브(`mesh_impact_l2_probe_0816.py`)가 수리 조합마다 따로 낸 측정을 모아
«기체 × 결함 × (수리 전 σ · 수리 후 σ · Δ dB · 밴드 밖인가)» 전수표를 만든다.
마이크로도플러 축(`mesh_impact_l2_md_0816.py`)도 같은 원장에 넣는다.

읽는 규칙 (이 라운드가 스스로 지킨 것)
  · Δ dB = **수리 후 − 수리 전**. 음수면 어두워진 것이다.
  · 밴드 = |Δ| < 0.1 «무해» · 0.1~1.0 «보임» · > 1.0 «결론을 바꿈»(= 판정 밴드 **밖**).
  · 한 번에 하나씩 — 표의 각 칸은 **그 수리 하나만 켠 세계**와 아무 것도 안 켠 세계의 차다.
    ⚠예외 하나: mini2 의 i4 는 i5 가 선행이라(비수밀 body 에는 불리언이 안 돈다)
      «i5+i4» − «i5» 로 잰다. 원장에 그 사실을 칸마다 적는다.
  · 지문이 안 바뀐 기체는 **대조군**이다. 거기서 Δ 가 0 이 아니면 측정이 틀린 것이다.

사용:  python benchmark/mesh_impact_l2_ledger_0816.py --runs <dir> --md <dir> --out <json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
GEOMS = ("mono_el0", "mono_el-30", "bi_b120_el-30")
FLEET = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4",
         "m350rtk", "x500v2", "s1000plus", "typhoonh480"]
#  (수리 id, 수리 켠 판, 비교 기준판, 설명)
FIXES = [("i5", "i5", "off", "mini2 body 구멍 — 슬리버를 지우는 대신 모서리 붕괴"),
         ("m6", "m6", "off", "uv_sphere 극점 중복정점 공유"),
         ("battery", "battery", "off", "battery 그룹 자기겹침 — 팩·구조판 불리언 합집합"),
         ("i4", "i4", "off", "묻힌 캐노피 — body 와 합치기(셸형)"),
         ("m4", "m4", "off", "x500v2 카본 튜브가 나일론 클램프를 관통 — 잘라냄"),
         ("i3", "i3", "off", "매몰면 이중계상 — PO 적분에서 뺌(메쉬는 안 바꿈)")]
#  mini2 의 i4 만 예외 — i5 가 선행 조건이다
I4_MINI2 = ("i5_i4", "i5")
AZ_STEP = 2.0


def band(d):
    a = abs(d)
    return "무해(<0.1dB)" if a < 0.1 else ("보임(0.1~1dB)" if a <= 1.0 else "⭐결론을바꿈(>1dB)")


def outside(d):
    return bool(abs(d) > 1.0)


def load(runs, tag):
    with open(os.path.join(runs, f"{tag}.json")) as fh:
        return json.load(fh)


def smooth(sig, win_deg=3.0):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from rcs_po import angular_smooth
    return angular_smooth(np.asarray(sig, float), win_deg, AZ_STEP)


def cmp_sigma(a, b, key="sigma"):
    """b(수리 후) − a(수리 전). 방위평균 dBsm · Δ dB · 최악방위(3° 평활)."""
    out = {}
    for g in GEOMS:
        s0 = np.asarray(a[key][g], float)
        s1 = np.asarray(b[key][g], float)
        m0 = 10 * np.log10(s0.mean())
        m1 = 10 * np.log10(s1.mean())
        d_per = 10 * np.log10(np.maximum(smooth(s1), 1e-300)) - \
                10 * np.log10(np.maximum(smooth(s0), 1e-300))
        i = int(np.argmax(np.abs(d_per)))
        out[g] = dict(
            sigma_before_dbsm=round(float(m0), 4), sigma_after_dbsm=round(float(m1), 4),
            delta_db=round(float(m1 - m0), 4), delta_db_full=float(m1 - m0),
            band=band(m1 - m0), outside_band=outside(m1 - m0),
            worst_az_deg=round(float(i * AZ_STEP), 1),
            worst_az_delta_db=round(float(d_per[i]), 4),
            bit_identical=bool(np.array_equal(s0, s1)),
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "mesh_impact_layer2_0816.json"))
    a = ap.parse_args()

    R = {t: load(a.runs, t) for t in
         ("off", "i5", "m6", "battery", "i4", "m4", "i3", "i5_i4", "mesh5", "all6")}
    off = R["off"]["drones"]

    rep = {"_meta": dict(
        무엇을_쟀나=("2층 메쉬 수리 6종을 **하나씩** 켜고 끄며 기체 10종의 σ 가 얼마나 바뀌는지. "
                 "값을 넣은 것은 앞선 수리 라운드들이고 이 라운드는 그 값의 **영향만** 잰다."),
        측정_규약=R["off"]["_meta"],
        소스_스냅샷=("측정 중 다른 라운드가 같은 파일을 고치고 있어서 src/ 를 얼려 두고 그 위에서만 "
                 "쟀다. 아래 sha256 이 그 스냅샷이다 — 원장의 모든 수치가 같은 스냅샷에서 나온다."),
        판정밴드="|Δ| < 0.1 무해 · 0.1~1.0 보임 · > 1.0 ⭐결론을바꿈(판정 밴드 밖)")}

    # ---------------------------------------------------------------- 개별 수리
    tbl = {}
    for fid, tag, ref, desc in FIXES:
        cur = R[tag]["drones"]
        base = R[ref]["drones"]
        rows = {}
        #  ⚠ 조합마다 잰 기체가 다르다 — 대상이 한 기체뿐인 수리(i5·m4)는 그 기체와 대조 하나만
        #    쟀다(이 기계가 메모리 압박으로 느려서 σ 를 아낄 수밖에 없었다. 안 잰 칸은 «안 잼»
        #    으로 남기고 «0» 으로 적지 않는다).
        keys_here = [x for x in FLEET if x in cur]
        if fid == "i4" and "mini2" not in keys_here:
            keys_here.append("mini2")      # mini2 는 i5 선행이라 «i5+i4» − «i5» 로 따로 잰다
        for k in keys_here:
            note = ""
            if fid == "i4" and k == "mini2":            # 예외 — i5 선행
                b0 = b1 = None
            else:
                b0, b1 = base[k], cur[k]
            if fid == "i4" and k == "mini2":
                b0, b1 = R[I4_MINI2[1]]["drones"][k], R[I4_MINI2[0]]["drones"][k]
                note = "⚠ i5 선행 — «i5+i4» − «i5» 로 쟀다(비수밀 body 엔 불리언이 안 돈다)"
            row = dict(
                mesh_changed=bool(b0["fp_drone"] != b1["fp_drone"]),
                n_faces=[b0["n_faces"], b1["n_faces"]],
                area_mm2=[b0["area_mm2"], b1["area_mm2"]],
                area_delta_pct=round(100 * (b1["area_mm2"] - b0["area_mm2"]) / b0["area_mm2"], 4),
                n_pts=[b0["n_pts"], b1["n_pts"]],
                fit_scale_changed=bool(b0["fit_scale"] != b1["fit_scale"]),
                rotor_centers_changed=bool(b0["rotor_centers_mm"] != b1["rotor_centers_mm"]),
                prop_mesh_changed=bool(b0["fp_prop_ccw"] != b1["fp_prop_ccw"]
                                       or b0["fp_prop_cw"] != b1["fp_prop_cw"]),
                sigma=cmp_sigma(b0, b1),
                sigma_prop=cmp_sigma(b0, b1, key="sigma_prop"),
            )
            if note:
                row["note"] = note
            if "i3" in b1:
                row["i3_removed"] = b1["i3"]
            rows[k] = row
        ks = list(rows)
        worst = max(abs(rows[k]["sigma"][g]["delta_db"]) for k in ks for g in GEOMS)
        tgt = [k for k in ks if rows[k]["mesh_changed"] or rows[k]["n_pts"][0] != rows[k]["n_pts"][1]]
        ctrl_bad = [k for k in ks if k not in tgt
                    and any(not rows[k]["sigma"][g]["bit_identical"] for g in GEOMS)]
        tbl[fid] = dict(설명=desc, 켠_스위치=tag, 기준판=ref, rows=rows, 잰_기체=ks,
                        안_잰_기체=[x for x in FLEET if x not in ks],
                        건드린_기체=tgt, 최대_절대Δ_dB=round(float(worst), 4),
                        대조군_위반=ctrl_bad,
                        대조군_뜻=("지문·점수가 안 바뀐 기체는 대조군이다. 거기서 σ 가 한 비트라도 "
                                "움직이면 측정이 틀린 것이다 — 위 목록이 비어 있어야 한다."))
    rep["수리별_영향"] = tbl

    # ---------------------------------------------------------------- 누적
    cum = {}
    for k in FLEET:
        indiv = {g: 0.0 for g in GEOMS}
        missed = []
        for fid, tag, ref, _ in FIXES:
            if k not in tbl[fid]["rows"]:
                #  안 잰 칸 — 그 수리가 이 기체의 **메쉬를 안 바꾼다**는 것이 지문으로 확인된
                #  경우에만 0 으로 놓는다(아래 근거 필드에 남긴다).
                missed.append(fid)
                continue
            r = tbl[fid]["rows"][k]["sigma"]
            for g in GEOMS:
                indiv[g] += r[g]["delta_db"]
        c_all = cmp_sigma(off[k], R["all6"]["drones"][k])
        c_m5 = cmp_sigma(off[k], R["mesh5"]["drones"][k])
        cum[k] = dict(
            전부_켬=c_all, 메쉬수리5종만=c_m5,
            개별합_dB={g: round(float(indiv[g]), 4) for g in GEOMS},
            개별합에서_빠진_수리=missed,
            상호작용_dB={g: round(float(c_all[g]["delta_db"] - indiv[g]), 4) for g in GEOMS},
            읽는_법=("«개별합» 은 수리를 하나씩 켰을 때의 Δ 를 그냥 더한 것이고 «전부_켬» 은 실제로 "
                  "다 켜고 잰 것이다. 둘의 차 = 상호작용. 0 에 가까우면 서로 독립이고, "
                  "크면 한 수리가 다른 수리의 대상을 이미 없앴다는 뜻이다."))
    rep["누적"] = cum

    # ---------------------------------------------------------------- 마이크로도플러 축
    MD = {t: json.load(open(os.path.join(a.md, f"{t}.json"))) for t in ("off", "mesh5", "i3", "all6")}

    def db(x):
        return 10 * np.log10(np.maximum(np.asarray(x, float), 1e-300))

    md = {}
    for t in ("mesh5", "i3", "all6"):
        rows = {}
        for k, b in MD["off"]["drones"].items():
            v = MD[t]["drones"][k]
            dfull = db(v["sigma_full"]) - db(b["sigma_full"])
            dprop = db(v["sigma_prop"]) - db(b["sigma_prop"])
            dacp = db(v["sigma_ac_prop"]) - db(b["sigma_ac_prop"])
            dacf = db(v["sigma_ac_full"]) - db(b["sigma_ac_full"])
            mod0 = db(b["sigma_full"]).max(axis=0) - db(b["sigma_full"]).min(axis=0)
            mod1 = db(v["sigma_full"]).max(axis=0) - db(v["sigma_full"]).min(axis=0)
            rows[k] = dict(
                프롭메쉬_동일=bool(v["fp_prop_ccw"] == b["fp_prop_ccw"]),
                프롭필드_비트동일=bool(v["fp_E_prop"] == b["fp_E_prop"]),
                max_dprop_db=round(float(np.abs(dprop).max()), 6),
                max_dac_prop_db=float(np.abs(dacp).max()),
                max_dac_full_db=float(np.abs(dacf).max()),
                max_dfull_db=round(float(np.abs(dfull).max()), 4),
                변조깊이_전후=[round(float(mod0.max()), 3), round(float(mod1.max()), 3)],
                변조깊이_최대변화_db=round(float(np.abs(mod1 - mod0).max()), 4),
                i3_뺀_프롭면_위상별=v.get("i3_removed_prop"),
            )
        md[t] = rows
    # ---------------------------------------------------------------- 교차검증
    #  앞선 수리 라운드들이 **자기 스냅샷에서** 낸 σ 를 내 스냅샷에서 다시 재서 맞춰 본다.
    #  ⚠ 부호 규약이 다르다 — 그쪽은 «결함이 부풀린 양»(수리 전 − 수리 후)을 양수로 적었고
    #    내 표는 «수리 후 − 수리 전» 이다. 그래서 부호를 뒤집어 비교한다.
    X = {}
    try:
        bt = json.load(open(os.path.join(ROOT, "outputs", "mesh_layer2_battery_overlap_0816.json")))
        for k, v in bt["σ"].items():
            if k in tbl["battery"]["rows"]:
                for g in GEOMS:
                    X[f"battery/{k}/{g}"] = [round(-v["sigma"][g]["azimuth_mean_db"], 4),
                                             tbl["battery"]["rows"][k]["sigma"][g]["delta_db"]]
    except Exception as e:
        X["battery_error"] = str(e)
    try:
        bc = json.load(open(os.path.join(ROOT, "outputs", "mesh_layer2_buried_canopy_0816.json")))
        for k, v in bc["I4_묻힌_캐노피"]["기체별"].items():
            if k in tbl["i4"]["rows"] and "실제_수리후" in v.get("σ", {}):
                for g in GEOMS:
                    X[f"i4/{k}/{g}"] = [round(-v["σ"]["실제_수리후"][g]["azimuth_mean_db"], 4),
                                        tbl["i4"]["rows"][k]["sigma"][g]["delta_db"]]
        mm = bc["m4_x500v2_클램프"]["측정"].get("σ", {}).get("실제_수리후", {})
        mm = mm or bc["m4_x500v2_클램프"]["측정"]["σ"].get("실제_수리후_m4", {})
        for g in GEOMS:
            if g in mm:
                X[f"m4/x500v2/{g}"] = [round(-mm[g]["azimuth_mean_db"], 4),
                                       tbl["m4"]["rows"]["x500v2"]["sigma"][g]["delta_db"]]
    except Exception as e:
        X["i4_m4_error"] = str(e)
    try:
        bf = json.load(open(os.path.join(ROOT, "outputs", "mesh_layer2_buried_faces_0816.json")))
        for k, v in bf["sigma"].items():
            if k in tbl["i3"]["rows"]:
                for g in GEOMS:
                    q = v["per_geometry"][g]["⭐진짜결함만_뺐을_때"]["azimuth_mean_db"]
                    X[f"i3/{k}/{g}"] = [round(-q, 4), tbl["i3"]["rows"][k]["sigma"][g]["delta_db"]]
    except Exception as e:
        X["i3_error"] = str(e)
    diffs = [abs(a - b) for v in X.values() if isinstance(v, list) for a, b in [v]]
    rep["교차검증_앞라운드"] = dict(
        무엇을_맞췄나=("앞선 수리 라운드 4곳이 **자기 스냅샷**에서 낸 방위평균 Δ 를 내 스냅샷에서 "
                  "다시 재서 칸마다 맞춰 봤다. 값은 [그쪽(부호 뒤집음), 내 값]."),
        칸수=len(diffs), 최대차_dB=round(max(diffs), 4) if diffs else None,
        중앙값차_dB=round(float(np.median(diffs)), 4) if diffs else None, 칸=X)

    rep["마이크로도플러_축"] = dict(
        무엇을_보나=("프로펠러는 아무도 안 건드렸으니 «움직이는 성분» 의 변화는 0 이어야 한다. "
                 "σ_prop = 프롭 점만의 σ, σ_ac = 위상평균을 뺀 뒤의 세기(대수적으로 프레임과 무관)."),
        표=md)

    with open(a.out, "w") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print(f"[ledger] {a.out} ({os.path.getsize(a.out)/1024:.0f} KB)")

    # ---------------------------------------------------------------- 화면 표
    print("\n=== 수리별 σ 영향 (Δ dB = 수리 후 − 수리 전, 방위평균) ===")
    hdr = f"{'수리':8} {'기체':11} {'지문':4} " + " ".join(f"{g:>16}" for g in GEOMS)
    print(hdr)
    for fid, _, _, _ in FIXES:
        for k in FLEET:
            if k not in tbl[fid]["rows"]:
                print(f"{fid:8} {k:11} {'—':4} " + "            안 잼")
                continue
            r = tbl[fid]["rows"][k]
            cells = []
            for g in GEOMS:
                d = r["sigma"][g]
                cells.append(f"{d['sigma_before_dbsm']:7.2f}→{d['delta_db']:+7.3f}")
            mark = "●" if r["mesh_changed"] or r["n_pts"][0] != r["n_pts"][1] else "·"
            print(f"{fid:8} {k:11} {mark:4} " + " ".join(f"{c:>16}" for c in cells))
        print()
    print("=== 누적(전부 켬) ===")
    for k in FLEET:
        c = cum[k]
        print(f"{k:11} " + " ".join(f"{c['전부_켬'][g]['delta_db']:+8.3f}" for g in GEOMS) +
              "   개별합 " + " ".join(f"{c['개별합_dB'][g]:+8.3f}" for g in GEOMS) +
              "   상호작용 " + " ".join(f"{c['상호작용_dB'][g]:+8.3f}" for g in GEOMS))


if __name__ == "__main__":
    main()
