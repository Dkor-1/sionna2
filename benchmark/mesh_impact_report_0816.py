# -*- coding: utf-8 -*-
"""
mesh_impact_report_0816.py — outputs/mesh_impact_0816.json → 사람이 읽는 표
============================================================================
값을 만들지 않는다. 드라이버가 잰 숫자를 **표로만** 옮긴다(전사 실수 방지).

  python benchmark/mesh_impact_report_0816.py            # 콘솔
  python benchmark/mesh_impact_report_0816.py --md       # 마크다운(§⑩ 붙여넣기용)
"""
from __future__ import annotations

import argparse
import json

SRC = "/workspace/sionna/outputs/mesh_impact_0816.json"
NAME = {"caps": "③ 로프트 끝단 캡", "env": "⑥ phantom4 외형 강제 해제",
        "gimbal": "① mavic4pro 짐벌", "b4": "④ matrice4e 뒷다리",
        "b7": "⑦ matrice4e 모터 벨 z"}
ORDER = ["caps", "env", "gimbal", "b4", "b7"]
FLEET = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4",
         "m350rtk", "x500v2", "s1000plus", "typhoonh480"]


def shape_note(gd):
    """형상이 실제로 얼마나 움직였나 — 한 줄."""
    if gd.get("sha_drone_same"):
        return "0 (메쉬 비트동일)"
    bits = []
    b = gd["d_drone_bbox_mm"]
    if any(abs(x) > 5e-4 for x in b):
        bits.append("드론 bbox Δ(%+.3f, %+.3f, %+.3f)" % tuple(b))
    if abs(gd["d_wheelbase_mm"]) > 5e-4:
        bits.append("축간거리 %+.3f" % gd["d_wheelbase_mm"])
    fz = [round(a - b_, 9) for a, b_ in zip(gd["fit_scale_after"], gd["fit_scale_before"])]
    if any(abs(x) > 1e-8 for x in fz):
        bits.append("sz %.6f→%.6f" % (gd["fit_scale_before"][2], gd["fit_scale_after"][2]))
    mv = []
    for g, e in sorted(gd["groups"].items()):
        if isinstance(e, dict) and not e["sha_same"]:
            dz = e["d_z_mm"]
            mv.append("%s(Δz %+.2f/%+.2f)" % (g, dz[0], dz[1]) if any(abs(v) > 5e-3 for v in dz)
                      else g)
    if mv:
        bits.append("바뀐 그룹: " + " ".join(mv))
    if gd.get("d_n_tri"):
        bits.append("삼각형 %+d" % gd["d_n_tri"])
    return " · ".join(bits) if bits else "지문만 바뀜(좌표 변화 < 0.5 µm)"


def sig_cell(s, el):
    e = s[el]
    return (e["d_az_mean_db"], e["d_worst_db"], e["pattern"]["rms_db"], e["pattern"]["corr"],
            e["before"]["az_mean_dbsm"], e["after"]["az_mean_dbsm"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    d = json.load(open(SRC))
    L = []
    P = L.append

    P("## 수리별 영향 (단계 하나씩, 앞 단계 대비)")
    P("")
    P("| 기체 | 수리 | 형상 Δ | Δσ 방위평균 el0 / el15 [dB] | Δσ 최악방위 el0 / el15 [dB] | 패턴 RMS el0 / el15 [dB] |")
    P("|---|---|---|---|---|---|")
    for rep in ORDER:
        blk = d["per_repair"][rep]
        for k in FLEET:
            e = blk["keys"][k]
            if e["geom"].get("sha_drone_same") and not e["expected_to_change"]:
                continue                     # 안 바뀐 기체는 아래 «비트동일» 표에서 한꺼번에
            g = e["geom"]
            if "sigma" in e:
                c0, c15 = sig_cell(e["sigma"], "el0"), sig_cell(e["sigma"], "el15")
                s1 = "%+.3f / %+.3f" % (c0[0], c15[0])
                s2 = "%+.3f / %+.3f" % (c0[1], c15[1])
                s3 = "%.3f / %.3f" % (c0[2], c15[2])
            else:
                s1 = s2 = s3 = "—"
            P("| %s | %s | %s | %s | %s | %s |" % (k, NAME[rep], shape_note(g), s1, s2, s3))
    P("")

    P("## 누적 (수리 0건 → 전부 적용)")
    P("")
    P("| 기체 | σ 전 el0 [dBsm] | σ 후 el0 | 누적 Δ el0 | 누적 Δ el15 | 최악방위 Δ el0 / el15 | 패턴 RMS el0 |")
    P("|---|---|---|---|---|---|---|")
    for k in FLEET:
        e = d["cumulative"][k]
        if "sigma" not in e:
            P("| %s | — | — | — | — | — | — |" % k)
            continue
        s0, s15 = e["sigma"]["el0"], e["sigma"]["el15"]
        P("| %s | %.3f | %.3f | **%+.3f** | **%+.3f** | %+.3f / %+.3f | %.3f |" % (
            k, s0["before"]["az_mean_dbsm"], s0["after"]["az_mean_dbsm"], s0["d_az_mean_db"],
            s15["d_az_mean_db"], s0["d_worst_db"], s15["d_worst_db"], s0["pattern"]["rms_db"]))
    P("")
    P("### 상쇄하나 더하나 — «그 수리 하나만» 넣은 세계와 비교 (el 0°, 방위평균)")
    P("")
    P("| 기체 | 수리 하나만 넣었을 때 [dB] | 단독 합 | 누적(전부) | 상호작용 |")
    P("|---|---|---|---|---|")
    for k in FLEET:
        e = d["cumulative"][k]
        if "sigma" not in e:
            continue
        s0 = e["sigma"]["el0"]
        terms = " · ".join("%s %+.3f" % (NAME[r].split()[0] + NAME[r].split()[1][:0] or r, v)
                           if False else "%s %+.3f" % (r, v)
                           for r, v in s0["isolated_terms_db"].items())
        P("| %s | %s | %+.3f | %+.3f | **%+.3f** |" % (
            k, terms or "—", s0["isolated_sum_db"], s0["d_az_mean_db"], s0["interaction_db"]))
    P("")

    P("## 마이크로도플러 축 — 움직이는 성분이 0 인가")
    P("")
    P("| 기체 | 프롭 메쉬 지문 | 로터 1개 회전에코 | 프롭 4개 합성에코 | 프롭에코 변동분 RMS Δ [dB] | 전체에코 변동분 RMS Δ [dB] |")
    P("|---|---|---|---|---|---|")
    for k, m in d["micro_doppler"].items():
        c = m["cumulative"]
        same = len({tuple(v) for v in m["prop_sha"].values()}) == 1
        po = max(c["md_prop_only"]["d_ac_rms_db"].values())
        fu = max(c["md_full"]["d_ac_rms_db"].values())
        P("| %s | %s | %s | %s | %.4f | %.4f |" % (
            k, "불변 ✅" if same else "⛔바뀜",
            "비트동일 ✅" if c["md_single_rotor"]["bit_identical"] else "바뀜",
            "비트동일 ✅" if c["md_prop_only"]["bit_identical"] else "바뀜",
            po, fu))
    P("")
    P("(회전에코 = 로터 위상 36 단계 σ, fc 3.5 GHz, el 0°·30° × az 0/45/90/180°. "
      "«변동분» = 위상축 평균을 뺀 나머지 = 마이크로도플러를 만드는 바로 그 성분. "
      "표의 값은 el·az 조합 중 **최댓값**.)")
    P("")
    for k, m in d["micro_doppler"].items():
        c = m["cumulative"]
        if not c["md_prop_only"]["bit_identical"]:
            P("* %s 프롭 합성에코가 바뀐 자리: " % k +
              ", ".join("%s %.3f dB" % (lb, v) for lb, v in
                        sorted(c["md_prop_only"]["d_ac_rms_db"].items(),
                               key=lambda x: -x[1])[:4]))
    P("")

    P("## 비트동일 — 안 건드린 기체")
    P("")
    P("| 기체 | 지문 T0 | 지문 T5 | T0=T5 | 바뀐 단계 |")
    P("|---|---|---|---|---|")
    for k in FLEET:
        b = d["bit_identity"][k]
        P("| %s | `%s` | `%s` | %s | %s |" % (
            k, b["sha_by_stage"]["T0"], b["sha_by_stage"]["T5"],
            "✅ 같음" if b["identical_T0_T5"] else "바뀜(의도)",
            ", ".join(b["changed_at"]) or "—"))
    P("")
    P("판정: " + d["bit_identity"]["_verdict"])
    out = "\n".join(L)
    print(out)


if __name__ == "__main__":
    main()
