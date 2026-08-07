# -*- coding: utf-8 -*-
"""
build_report00_microdoppler.py — 리포트 00 §4a 의 근거와 그림을 만든다
=========================================================================
질문 하나에 답한다: **결정표(§4)가 실제 사례에서 맞는가.**

§4 는 «표적 항이 비율에서 소거되는가» 로 실험을 왼쪽/오른쪽 칸에 나눈다.
마이크로도플러는 그 표를 시험하기에 좋은 사례다 — 절대 세기는 필요 없고
«도는 것이 있는가» 만 보면 되므로 오른쪽 칸에 앉아야 한다.

여기서 세 가지를 나란히 놓는다. 셋 다 **로터 위상을 같은 각도로 돌리고
매번 다시 계산**한 것이고, 거리·자세·재질·주파수가 전부 같다.

  ① Sionna PathSolver     — 씬을 매 위상마다 다시 추적
  ② 우리 SBR+PO 커널      — 같은 위상 스텝, 같은 메쉬
  ③ 같은 부피의 구        — 같은 속도로 돌린다. ⭐ 어느 방향에서 봐도 같은
                            모양이라 **변조를 만들 수가 없다**. 널(null) 대조.

읽는 법: ①②가 닮았으면 «Sionna 가 도는 기하의 위상을 따라간다» 는 뜻이고,
③이 검게 남으면 «지금 보는 무늬가 계산 잡음이 아니다» 는 뜻이다. 둘 다 필요하다.

⚠ 이 파일은 **읽기만** 한다 — outputs/report15_verdict.json 과 report15_probe.json
   을 읽어 요약과 그림만 새로 쓴다. 계산을 다시 하지 않는다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/build_report00_microdoppler.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import matplotlib                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402

from report15_verdict import spectrogram             # noqa: E402  (기존 모듈 재사용)

VERDICT = os.path.join(_ROOT, "outputs", "report15_verdict.json")
PROBE = os.path.join(_ROOT, "outputs", "report15_probe.json")
OUT_JSON = os.path.join(_ROOT, "outputs", "report00_microdoppler.json")
FIGDIR = os.path.join(_ROOT, "outputs", "figures")

N_REV = 6                         # 스펙트로그램에 담는 회전 수
DEG = "\u00b0"
PM = "\u00b1"
RANGE = "3"                       # 대표 거리 [m] — mini2 는 원거리장, matrice4e 는 그 아래
ASPECT = "nose"
DRONES = [("mini2", "DJI Mini 2"), ("matrice4e", "DJI Matrice 4E")]


def _wave(cell):
    """분석 dict → 복소 위상파형. PO 칸은 진폭만 있으므로 실수로 돌려준다."""
    if not cell or cell.get("empty"):
        return None
    a = np.asarray(cell["wave_amp_db"], float)
    p = cell.get("wave_phase_deg")
    if p is None:
        return (10 ** (a / 20.0)).astype(complex)
    return 10 ** (a / 20.0) * np.exp(1j * np.radians(np.asarray(p, float)))


def collect(J, P):  # noqa: C901
    """세 팔의 변조 깊이 + 거울반사 인구조사를 한 dict 로."""
    S, PO, NU, PH = J["sionna"], J["po"], J["nulls_vs_range"], J["physics"]
    #  원거리장 경계는 probe 쪽 physics 에만 있다 — 판정 파일과 키가 다르다.
    FF = {a["drone"]: a for a in
          [P["airframes"][k]["headline"] for k, _ in DRONES]}
    arms, rows = {}, []
    for key, name in DRONES:
        ph = PH[key]
        ff_m = float(FF[key]["farfield_m"])
        c_s = S[key].get(f"{RANGE}/{ASPECT}/prod/prop")
        c_p = PO[key].get(f"matched/{RANGE}/{ASPECT}/prop")
        c_n = ((NU.get("arms") or {}).get(f"sphere_{key}_plastic") or {}) \
            .get("by", {}).get(f"{RANGE}/all")
        arms[key] = {"sionna": c_s, "po": c_p, "sphere": c_n}
        rows.append({
            "drone": key, "name": name,
            "f_tip_hz": float(ph["f_tip_hz"]),
            "farfield_m": ff_m,
            "in_farfield_at_3m": ff_m < float(RANGE),
            "ptp_sionna_db": _f(c_s, "modulation_ptp_db"),
            "ptp_po_db": _f(c_p, "modulation_ptp_db"),
            "ptp_sphere_db": _f(c_n, "modulation_ptp_db"),
        })
        r = rows[-1]
        # ⭐ 구가 왜 널인지: 「작다」가 아니라 「만들 수 없다」임을 배수로 적는다.
        if r["ptp_sphere_db"] and r["ptp_sphere_db"] > 0:
            r["sionna_over_sphere"] = r["ptp_sionna_db"] / r["ptp_sphere_db"]
            r["po_over_sphere"] = r["ptp_po_db"] / r["ptp_sphere_db"]

    # 거울반사 인구조사 — 프로펠러에서 정반사가 몇 번 잡혔나
    bf = P.get("blade_flash") or {}
    census = {"plate_control": bf.get("plate_control")}
    tot_cells = tot_spec = tot_prop = 0
    for key, _ in DRONES:
        a = (bf.get("airframes") or {}).get(key) or {}
        n_cells = len(a.get("az_deg", [])) * len(a.get("el_deg", [])) * len(a.get("phases_deg", []))
        census[key] = {k: a.get(k) for k in
                       ("n_cells_with_specular", "n_cells_with_prop_specular",
                        "frac_cells_with_specular", "source_of_specular")}
        census[key]["n_cells"] = n_cells
        tot_cells += n_cells
        tot_spec += int(a.get("n_cells_with_specular") or 0)
        tot_prop += int(a.get("n_cells_with_prop_specular") or 0)
    census["total"] = {"n_cells": tot_cells, "n_with_specular": tot_spec,
                       "n_with_prop_specular": tot_prop}
    return arms, rows, census


def _f(c, k):
    try:
        return float(c[k])
    except Exception:
        return None


def figure(J, arms, rows, stem):
    """그림 — 3열(Sionna · PO · 구) × 2행(기체). 게재 규격(paper_kit)으로 그린다.

    ⭐ 두 축을 **정규화**해서 여섯 판이 문자 그대로 같은 자리를 쓴다:
      · 가로 = 로터 회전수(회) — 기체마다 rpm 이 달라 ms 로 두면 판이 안 맞는다.
      · 세로 = 도플러 ÷ 날개끝 도플러 — 그러면 운동학 예측선이 **모든 판에서 정확히 ±1** 이다.
    이렇게 해야 «닮았다/조용하다» 를 눈으로 바로 비교할 수 있다.
    """
    from paper_kit import paper_style, save_figure

    PH = J["physics"]
    panels, peaks = {}, []
    for i, (key, _) in enumerate(DRONES):
        ff = float(PH[key]["f_flash_hz"])
        ftip = float(PH[key]["f_tip_hz"])
        for j, arm in enumerate(("sionna", "po", "sphere")):
            z = _wave(arms[key][arm])
            if z is None:
                panels[(i, j)] = None
                continue
            zp = z - z.mean()
            t, f, Sd = spectrogram(zp, ff, n_rev=N_REV)
            # 각 판의 정지(DC) 성분 기준 dB — 널 판과 신호 판이 직접 비교된다
            Sd = 20 * np.log10(np.maximum(np.abs(Sd), 1e-14) / max(np.abs(z.mean()), 1e-14))
            f_rev = ff / 2.0                      # 2엽 → 플래시율의 절반이 회전율
            panels[(i, j)] = (np.asarray(t) * f_rev, np.asarray(f) / ftip, Sd)
            peaks.append(float(np.nanmax(Sd)))
    vmax = float(np.nanmax(peaks))
    vmin = vmax - 60.0
    #  ⚠ 스펙트로그램 창이 끝까지 안 차므로 축 상한을 **자료 실제 끝**으로 잡는다.
    #     N_REV 로 두면 판마다 오른쪽에 흰 여백이 남는다.
    x_hi = float(min(np.nanmax(d[0]) for d in panels.values() if d is not None))

    cols = ("Sionna PathSolver", "Our SBR + PO kernel", "Equal-volume sphere")
    subs = ("re-traced each step", "same steps, same mesh", "spun, same speed (null)")
    ptp_keys = ("ptp_sionna_db", "ptp_po_db", "ptp_sphere_db")

    with paper_style(width="double", base_pt=9.0, aspect=0.60) as st:
        fig = plt.figure()
        gs = fig.add_gridspec(2, 3, left=0.135, right=0.885, bottom=0.135, top=0.845,
                              wspace=0.07, hspace=0.14)
        pm = None
        for i, (key, name) in enumerate(DRONES):
            for j in range(3):
                ax = fig.add_subplot(gs[i, j])
                d = panels[(i, j)]
                if d is None:
                    ax.set_facecolor("#0b0b0b")
                    ax.text(.5, .5, "no paths", color="w", ha="center", va="center",
                            transform=ax.transAxes)
                else:
                    x, y, Sd = d
                    pm = ax.pcolormesh(x, y, Sd, cmap="magma", vmin=vmin, vmax=vmax,
                                       shading="auto", rasterized=True)
                #  운동학 예측 = 정규화 축에서 정확히 ±1
                for s in (+1, -1):
                    ax.axhline(s, color="#00e676", ls=(0, (4, 3)), lw=1.0)
                ax.set_xlim(0, x_hi)
                ax.set_ylim(-1.75, 1.75)
                ax.set_xticks([t for t in range(0, N_REV + 1) if t <= x_hi])
                ax.set_yticks([-1, 0, 1])
                #  ⭐ 판마다 변조 깊이를 뱃지로 — 그림만 보고도 표와 연결된다
                v = rows[i][ptp_keys[j]]
                ax.text(0.975, 0.955, f"{v:.2f} dB", transform=ax.transAxes,
                        ha="right", va="top", color="w", fontsize=st.rc["legend.fontsize"],
                        bbox=dict(fc="#000000aa", ec="none", pad=1.6))
                if i == 0:
                    ax.set_title(f"{cols[j]}\n{subs[j]}", pad=4.0, linespacing=1.25)
                if i == 1 and j == 1:          # 가로 축 제목은 가운데 한 번만
                    ax.set_xlabel("rotor revolutions")
                if j == 0:
                    #  행 이름만 축에 붙이고, 세로 축 제목은 그림 전체에 한 번만 단다.
                    ax.text(-0.19, 0.5, name, transform=ax.transAxes, rotation=90,
                            ha="center", va="center", fontweight="bold")
                else:
                    ax.set_yticklabels([])
                if i == 0:
                    ax.set_xticklabels([])
                ax.tick_params(length=2.5)
        fig.text(0.038, 0.49, "Doppler / blade-tip Doppler", rotation=90,
                 ha="center", va="center")
        cax = fig.add_axes([0.897, 0.135, 0.016, 0.710])
        cb = fig.colorbar(pm, cax=cax)
        cb.set_label("modulation depth  [dB re each panel's own static return]")
        cb.ax.tick_params(length=2.5)
        fig.suptitle(f"Rotor stepped and the scene recomputed at every step "
                     f"(R = {RANGE} m, az 0{DEG} / el 15{DEG})",
                     y=0.975)
        fig.text(0.485, 0.022,
                 "Green dashed = blade-tip Doppler from the kinematics alone, so it sits at "
                 f"{PM}1 in every panel.  Both axes are normalised, so all six panels share one frame.",
                 ha="center", fontsize=st.rc["legend.fontsize"], color="#333333")

    save_figure(fig, stem, caption=(
        "Micro-Doppler of the same rotor computed two ways and against a null. "
        "The rotor phase is stepped and the whole scene recomputed at every step; "
        "range, aspect, materials and frequency are identical across the three arms. "
        "Axes are normalised to rotor revolutions and to the kinematic blade-tip Doppler, "
        "so the six panels share one frame."), close=True)


def main():
    J = json.load(open(VERDICT, encoding="utf-8"))
    P = json.load(open(PROBE, encoding="utf-8"))
    arms, rows, census = collect(J, P)

    os.makedirs(FIGDIR, exist_ok=True)
    stem = os.path.join(FIGDIR, "report00_f5")
    figure(J, arms, rows, stem)

    out = {
        "_meta": {
            "generator": "benchmark/build_report00_microdoppler.py",
            "reads": ["outputs/report15_verdict.json", "outputs/report15_probe.json"],
            "what": "리포트 00 §4a — 결정표를 마이크로도플러 사례로 시험한 근거와 그림",
            "range_m": float(RANGE), "aspect": ASPECT,
            "protocol": "세 팔 모두 같은 로터 위상 스텝·같은 거리·같은 자세·같은 재질·같은 주파수",
        },
        "rows": rows,
        "specular_census": census,
        "reading_ko": (
            "① 과 ② 의 무늬가 닮았다는 것은 Sionna 가 **도는 기하의 왕복 위상**을 따라간다는 뜻이다. "
            "③ 이 검게 남는 것은 지금 보는 무늬가 계산 잡음이 아니라는 뜻이다 — "
            "구는 어느 방향에서 봐도 같은 모양이라 돌려도 변조를 만들 수가 없다."),
        "caveats_ko": [
            "⚠ 프로펠러에서 나온 거울반사(정반사) 경로는 0 개다. 지금 보이는 무늬는 전부 "
            "흩어져 되돌아오는 반사에서 나오고, 그 값은 광선을 다시 쏠 때마다 흔들린다.",
            "⚠ matrice4e 는 이 거리에서 원거리장에 못 미친다. 계산은 유효하지만 "
            "이 값을 RCS 로 환산해 인용하면 안 된다.",
            "⚠ 가림(동체 뒤 블레이드)은 다음 라운드 몫이다. 세 팔이 같은 조건이라 비교는 성립하고, "
            "절대값 인용은 가림을 넣은 뒤로 미룬다.",
            "⚠ 네 로터를 같은 위상으로 돌렸다. 실제 기체는 로터마다 위상이 흩어진다.",
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print(f"wrote {OUT_JSON}")
    print(f"wrote {stem}.png / .pdf")
    for r in rows:
        print(f"  {r['name']:16s} Sionna {r['ptp_sionna_db']:6.2f} · "
              f"PO {r['ptp_po_db']:6.2f} · 구 {r['ptp_sphere_db']:5.2f} dB")
    c = census["total"]
    print(f"  거울반사 인구조사: {c['n_cells']} 칸 중 정반사 {c['n_with_specular']} 칸, "
          f"그중 프로펠러 {c['n_with_prop_specular']} 칸")


if __name__ == "__main__":
    main()
