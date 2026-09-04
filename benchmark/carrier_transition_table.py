# -*- coding: utf-8 -*-
"""
carrier_transition_table.py — **R23① 반송파 전이표**: 3.5 GHz 판정을 5.8 GHz 에 어디까지 인용하나
================================================================================

■ 묻는 것 하나
지금까지의 모든 판(격자 밴드 R16 · 스위치 요인 R13 · 예산 사다리 R17 · 방위 R12 …)은 **3.5 GHz
한 자리**에서 잰 것이다. 반송파를 5.8 GHz 로 옮기면 그중 무엇을 **계산만으로** 옮겨 적을 수 있고
무엇을 **다시 재야** 하나. 전자를 «닫힌다», 후자를 «안 닫힌다» 라고 부른다.

  · **닫힌다**  = 값이 λ(또는 f)의 멱으로 정해진다 → 여기서 숫자를 내고 끝. GPU 0.
  · **안 닫힌다** = 위상 간섭·이산화·표본 집합이 통째로 갈아엎어진다 → R23② 로 다시 재야 한다.

■ ⛔GPU 를 안 쓴다
`sionna.rt`·`mitsuba`·`drones`(→materials→sionna.rt) 를 **임포트하지 않는다.** 기체 제원은
`src/drones.py` 를 **ast 로 읽고**, 나머지는 이미 있는 원장에서 읽는다.

■ 왜 격자는 λ/12 를 유지하나
격자 간격은 코드가 `λ/div` 로 잡는다(`elevation_sweep_md.py`). div 를 12 로 두면 5.8 GHz 판도
**같은 λ/12 규약**이라 R16 이 잰 격자 밴드(AC 3.86 dB · 리듬 몫 21.8 %p · 날개끝 밖 몫 12.55 %p)를
⛔R29 — 리듬 몫의 **크기는 인용하지 않는다**(창 반폭 hw 2/8/32 Hz 로 같은 데이터가 9.9/63.4/90.0 %). «λ/12 한정» 꼬리표로는 부족하다 — 격자보다 분석 손잡이가 더 크게 흔든다. 순서만 읽는다.

그대로 판정 문턱으로 쓸 수 있다. div 를 손대면 밴드를 다시 재야 한다.

    PYTHONPATH=src:benchmark python benchmark/carrier_transition_table.py
"""
from __future__ import annotations

import ast
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = f"{ROOT}/outputs/carrier_transition_table.json"

C_CODE = 2.998e8          # ⚠코드가 실제로 쓰는 광속 상수(elevation_sweep_md · rcs_sbr 하류 규약)
C_SI = 299792458.0
EPS0 = 8.8541878128e-12
FC0, FC1 = 3.5e9, 5.8e9   # 기준 반송파 · 옮길 반송파
DIV = 12                  # ⭐λ/12 유지
R_M = 15.0                # R23② 가 쓰는 거리
N_POSES = 8192            # R23② 가 쓰는 자세 수

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json", encoding="utf-8"))["_meta"]
PRF = float(TJ["prf_hz"])

# ── 기체 제원 — drones.py 를 **읽기만** 한다(임포트하면 sionna.rt 가 딸려 온다) ──────
def drone_specs(keys=("matrice4e", "mini5pro")) -> dict:
    tree = ast.parse(open(f"{ROOT}/src/drones.py", encoding="utf-8").read())
    node = next(n.value for n in ast.walk(tree)
                if isinstance(n, (ast.Assign, ast.AnnAssign))
                and ((isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "DRONES")
                     or (isinstance(n, ast.Assign)
                         and any(getattr(t, "id", "") == "DRONES" for t in n.targets))))
    out = {}
    for k, v in zip(node.keys, node.values):
        if k.value in keys:
            out[k.value] = {kw.arg: ast.literal_eval(kw.value) for kw in v.keywords
                            if kw.arg in ("prop_dia_mm", "prop_blades", "num_rotors",
                                          "hover_rpm", "name")}
    return out


SPECS = drone_specs()
# 메쉬 크기 D — 두 규약이 저장소에 함께 산다. 둘 다 싣고 어느 쪽인지 밝힌다.
D_DIAG3D = {"matrice4e": 0.7764}                       # audit_po_trust.json::nearfield_verdict
R16 = json.load(open(f"{ROOT}/outputs/report16_rung_mesh_full.json", encoding="utf-8"))
D_EXTENT = {k: float(v["extent_m"]) for k, v in R16["nearfield_diagnosis"]["rows"].items()}


def lam(fc):
    return C_CODE / fc


def gamma_bulk_metal(fc):
    """ITU 'metal' 은 (εr, σ) = (1.0, 1e7) 로 **주파수에 안 걸린다**(sionna/rt/radio_materials/itu.py:41).
    남는 주파수 의존은 εc = εr − jσ/(ωε0) 하나뿐이다."""
    ec = 1.0 - 1j * 1e7 / (2 * np.pi * fc * EPS0)
    return float(abs((1 - np.sqrt(ec)) / (1 + np.sqrt(ec))))


def f_tip(fc, key, el_deg):
    s = SPECS[key]
    R = s["prop_dia_mm"] / 2000.0
    f_rev = float(s["hover_rpm"]) / 60.0
    return 2.0 * (2 * np.pi * f_rev * R) / lam(fc) * np.cos(np.radians(el_deg))


def f_flash(key):
    s = SPECS[key]
    return float(s["prop_blades"]) * float(s["hover_rpm"]) / 60.0


def grid_side(fc, D):
    """얼린 격자 한 변의 칸 수 — rcs_sbr.grid_ref_from 의 식(Rout = Rmax·1.15 + 3d, n = ⌈2Rout/d⌉).
    ⚠Rmax 는 메쉬가 있어야 정확하다. 여기서는 D/2 로 잡은 **어림**이다(비율만 인용할 것)."""
    d = lam(fc) / DIV
    Rout = (D / 2.0) * 1.15 + 3 * d
    return int(np.ceil(2 * Rout / d)), d


rows: list[dict] = []


def add(group, item, v0, v1, rule, closes, note, fmt="{:.4g}"):
    r = dict(group=group, item=item, at_3p5=v0, at_5p8=v1, rule=rule,
             closes=closes, note_ko=note)
    # ⚠dB 항은 비를 안 싣는다 — dB 끼리 나누면 뜻이 없다(차이가 뜻이다).
    if isinstance(v0, (int, float)) and isinstance(v1, (int, float)) and v0 and "dB" not in item:
        r["ratio_5p8_over_3p5"] = round(float(v1) / float(v0), 6)
    rows.append(r)


# ═══ A. 닫힌다 — 파장의 멱으로 정해진다 ═══════════════════════════════════════
l0, l1 = lam(FC0), lam(FC1)
add("A_닫힘", "파장 λ [m]", l0, l1, "∝ 1/f", True,
    "모든 λ 항의 뿌리. 5.8/3.5 = 1.6571 배 주파수 → 파장은 0.6034 배.")
add("A_닫힘", "파수 k = 2π/λ [rad/m]", 2 * np.pi / l0, 2 * np.pi / l1, "∝ f", True,
    "우리 커널의 위상 exp(+j2k p·û) 가 그만큼 빨리 감긴다.")
add("A_닫힘", "격자 간격 d = λ/12 [mm]", l0 / DIV * 1e3, l1 / DIV * 1e3, "∝ 1/f", True,
    "⭐div 를 12 로 두면 규약이 유지된다 — 코드가 λ/div 로 잡으므로 저절로 따라 줄어든다. "
    "그래야 R16 격자 밴드를 판정 문턱으로 그대로 쓸 수 있다.")

for key in ("matrice4e", "mini5pro"):
    D = D_EXTENT[key]
    n0, _ = grid_side(FC0, D)
    n1, _ = grid_side(FC1, D)
    add("A_닫힘", f"격자 한 변 칸 수 n ({key}, 어림)", n0, n1, "∝ f", True,
        f"Rmax 를 D/2 = {D/2:.4f} m 로 잡은 어림이다. 셀 수는 n² 라 "
        f"{n0**2:,} → {n1**2:,} (×{(n1/n0)**2:.2f}) — 우리 커널의 계산량이 그만큼 는다.")

for key in ("matrice4e", "mini5pro"):
    ffl = f_flash(key)
    add("A_닫힘", f"플래시 박자 f_flash [{key}, Hz]", ffl, ffl, "불변", True,
        "날개 수 × 회전수라 반송파와 **무관**하다. 분류의 «기하 특징» 축이 여기 붙어 있다.")
    for el in (0.0, -30.0, -60.0):
        t0, t1 = f_tip(FC0, key, el), f_tip(FC1, key, el)
        add("A_닫힘", f"날개끝 상한 f_tip [{key}, el {el:+.0f}°, Hz]", t0, t1, "∝ f", True,
            f"2·(2π f_rev R)/λ·cos(el). 대역 0.35~1.0 f_tip 도 같은 비로 늘어난다 "
            f"(R23② 의 «λ 비로 늘린 대역»).")
    add("A_닫힘", f"빗살 이빨 수 (0.35~1.0 f_tip, {key}, el 0°)",
        (1 - 0.35) * f_tip(FC0, key, 0) / ffl, (1 - 0.35) * f_tip(FC1, key, 0) / ffl,
        "∝ f", True, "대역이 넓어진 만큼 f_flash 배수가 더 들어온다 — 고조파 판별에 유리하다.")

add("A_닫힘", "요구 표본율 PRF ≥ 2·f_tip(0°) [matrice4e, Hz]",
    2 * f_tip(FC0, "matrice4e", 0), 2 * f_tip(FC1, "matrice4e", 0), "∝ f", True,
    f"⭐지금 판의 PRF 는 {PRF:.0f} Hz 라 여유가 "
    f"{PRF/(2*f_tip(FC0,'matrice4e',0)):.2f}× → {PRF/(2*f_tip(FC1,'matrice4e',0)):.2f}× 로 줄 뿐 "
    "**여전히 충분하다** — R23② 큐는 PRF 를 안 건드려도 된다.")
add("A_닫힘", "비모호 속도 v_max = λ·PRF/4 [m/s]", l0 * PRF / 4, l1 * PRF / 4, "∝ 1/f", True,
    "모노스태틱 규약. 드론 속도(≤ 30 m/s)에 견줘 여전히 아득하다.")
add("A_닫힘", f"속도 분해능 Δv = λ/(2T), T = {N_POSES}/PRF [m/s]",
    l0 / (2 * N_POSES / PRF), l1 / (2 * N_POSES / PRF), "∝ 1/f", True,
    "드웰 T 가 같으면 5.8 GHz 가 **더 곱게** 갈린다.")
add("A_닫힘", "박자 FFT 분해능 PRF/n [Hz]", PRF / N_POSES, PRF / N_POSES, "불변", True,
    "슬로타임 격자의 몫이라 반송파와 무관하다. 대역만 넓어지므로 **대역 안 빈 수가 ×1.657** 로 는다.")

for key, D, src in (("matrice4e", D_DIAG3D["matrice4e"], "3D 대각(audit_po_trust)"),
                    ("matrice4e", D_EXTENT["matrice4e"], "extent(report16)"),
                    ("mini5pro", D_EXTENT["mini5pro"], "extent(report16)")):
    b0, b1 = 2 * D * D / l0, 2 * D * D / l1
    add("A_닫힘", f"원거리장 경계 2D²/λ [{key}, D={D:.4f} m · {src}, m]", b0, b1, "∝ f", True,
        f"⭐⭐R23② 는 R = {R_M:g} m 다 → 3.5 GHz 에서는 경계 "
        f"{'밖(원거리장)' if R_M > b0 else '안(근거리장)'}, 5.8 GHz 에서는 "
        f"{'밖(원거리장)' if R_M > b1 else '안(근거리장)'}.")

Dq = D_DIAG3D["matrice4e"]
add("A_닫힘", f"2차 위상 오차 kD²/(4R) [matrice4e, R={R_M:g} m, rad]",
    (2 * np.pi / l0) * Dq**2 / (4 * R_M), (2 * np.pi / l1) * Dq**2 / (4 * R_M), "∝ f", True,
    "우리 커널은 range_m 구면파로 이 항을 **넣는다**(rcs_sbr:1090). 커져도 모형 밖으로 안 샌다.")
add("A_닫힘", f"조명 각도 산포 atan((D/2)/R) [matrice4e, R={R_M:g} m, °]",
    np.degrees(np.arctan((Dq / 2) / R_M)), np.degrees(np.arctan((Dq / 2) / R_M)), "불변", True,
    "순수 기하라 반송파와 무관하다. ⚠우리 커널이 **안 넣는** 항이라는 사실도 그대로다.")
add("A_닫힘", "광선 예산 규칙 (R/3)²×1M", 1_000_000 * (R_M / 3) ** 2,
    1_000_000 * (R_M / 3) ** 2, "불변", True,
    "기하 표집이라 반송파와 무관하다 — R23② 는 --spp 4e9 를 그대로 쓴다.")
add("A_닫힘", "거리 분해능 ΔR = c/(2B) [B=100 MHz, m]", C_SI / (2 * 1e8), C_SI / (2 * 1e8),
    "불변", True,
    "⚠**대역폭의 몫이지 반송파의 몫이 아니다.** 5.8 GHz 에서 값이 달라진다면 그건 그 대역에서 "
    "쓸 수 있는 B 가 달라서지 반송파 때문이 아니다 — 두 이유를 섞어 적지 말 것. "
    "바이스태틱은 같은 B 에서 ΔR_b = c/B 로 두 배 거칠다.")
add("A_닫힘", "프롭 전기적 크기 ka = 2πR_p/λ [matrice4e]",
    2 * np.pi * (SPECS['matrice4e']['prop_dia_mm'] / 2000) / l0,
    2 * np.pi * (SPECS['matrice4e']['prop_dia_mm'] / 2000) / l1, "∝ f", True,
    "둘 다 ka ≫ 1 이라 광학영역이다 — 5.8 GHz 가 더 깊이 들어간다(PO 에 **유리한** 방향).")
add("A_닫힘", "우리 커널 재질 |Γ| — metal [dB]",
    20 * np.log10(gamma_bulk_metal(FC0)), 20 * np.log10(gamma_bulk_metal(FC1)), "거의 불변", True,
    f"⭐우리 커널이 쓰는 |Γ| 중 **주파수에 걸리는 것은 metal 하나**이고 그 차이가 "
    f"{20*np.log10(gamma_bulk_metal(FC1)/gamma_bulk_metal(FC0)):+.5f} dB 다. 나머지(plastic 0.28 · "
    "prop_plastic 0.25 · carbon 0.90 · camera 0.85 · pcb 0.80)는 MATERIALS 의 상수 "
    "override 라 반송파와 무관하다 ⇒ **우리 커널 쪽 재질 축은 닫힌다.**")
add("A_닫힘", "PTD 격자 권고 λ/20 대비 우리 격자 λ/12", DIV, DIV, "불변", True,
    "권고 미달(12 < 20)이라는 **판정 자체가 반송파와 무관**하다 — d 도 λ 도 같은 비로 줄기 때문. "
    "ptd=True 를 인용할 때의 격자 단서는 5.8 GHz 에서도 글자 그대로 유효하다.")
add("A_닫힘", "τ(float32) 위상 잡음 2πf·δτ [R=15 m, rad]",
    2 * np.pi * FC0 * (2 * R_M / C_SI) * 6e-8, 2 * np.pi * FC1 * (2 * R_M / C_SI) * 6e-8,
    "∝ f", True,
    "PathSolver 의 τ 가 float32 라 상대오차 ~6e−8 이 위상으로 번역된다. 둘 다 1e−3 rad 아래라 "
    "무해하지만 **반송파에 비례해 는다** — 더 먼 거리·더 높은 반송파에서는 다시 재야 한다.")

# ═══ B. 안 닫힌다 — 다시 재야 한다 ═══════════════════════════════════════════
A_flat = 0.05      # 평판 어림 면적 [m²] — 상한 감각용
add("B_안닫힘", "σ 절대 레벨 (level_db)", None, None, "λ 멱으로 못 준다", False,
    f"평판 극한이라면 σ = 4πA²/λ² 라 {20*np.log10(l0/l1):+.2f} dB 만큼 오를 «상한 감각» 은 있다. "
    "그러나 우리 표적은 곡면·다면체·부품 간섭이라 그 극한을 안 따른다 — R16 이 격자만 바꿔도 "
    "레벨이 밴드(AC 3.86 dB) 폭으로 흔들리는 것을 보였다. ⇒ **R23② 로 재는 대상 1 번.**")
add("B_안닫힘", "로브·널의 위치", None, None, "각폭만 ∝ λ/D", False,
    "간섭 무늬의 **폭**은 λ/D 로 좁아진다고 말할 수 있지만 **어디에 생기는가**는 위상 합이라 "
    "예측 불가다. 널 깊이는 이미 격자(31.89 dB)·조명(10.26 dB) 두 축에서 흔들린다"
    "(audit_po_trust::nearfield_verdict).")
add("B_안닫힘", "가림(occlusion)", None, None, "기하는 같고 표본은 갈아엎어진다", False,
    "그림자를 만드는 기하는 그대로다. 그런데 우리 커널은 λ/12 격자 위의 점에서 가림을 판정하므로 "
    "**비추는 점 집합이 통째로 바뀐다**(격자가 1.657 배 촘촘해진다). R16 이 λ/12↔λ/24 에서 "
    "판정 순서가 뒤집히는 칸을 이미 6 개 찾았다 — 같은 종류의 변화다.")
add("B_안닫힘", "PO 문턱 (few-λ marginal 판정)", None, None, "방향만 안다", False,
    "곡률 반경·판 크기가 λ 대비 커지므로 PO 는 **덜 marginal** 해진다(개선 방향). 그러나 프롭 두께"
    "(1~3 mm)는 3.5 GHz 에서 0.012~0.035 λ, 5.8 GHz 에서 0.019~0.058 λ 로 여전히 얇아 박막 |Γ| "
    "대표값(0.25)의 근거가 바뀌지 않는다 ⇒ «좋아진다» 를 수치로 주장하려면 다시 재야 한다.")
add("B_안닫힘", "PathSolver 재질 (슬래브 계수)", None, None, "두께/λ 로 자리가 바뀐다", False,
    f"Sionna 는 지정 두께의 **슬래브**로 반사·투과를 푼다. 커스텀 재질(plastic·carbon·prop_plastic)은 "
    f"DEFAULT_THICKNESS = 0.1 m 라 전기적 두께가 "
    f"{0.1*np.sqrt(2.7)/l0:.2f} λ → {0.1*np.sqrt(2.7)/l1:.2f} λ 로 옮겨가 간섭 자리가 달라진다. "
    "⚠이 항은 R2(셸 두께 정정)의 오염과 얽혀 있다 — 5.8 GHz 팔도 같은 단서를 달고 나온다.")
add("B_안닫힘", "판정의 **순서**(팔 사이 우열)·분류 성적", None, None, "—", False,
    "R16 이 λ/24 에서 순서가 뒤집히는 칸을 봤으므로 반송파에서도 뒤집힐 수 있다. "
    "R23② 의 사전등록은 **순서 보존을 부차**로 두고 밴드 안/밖만 헤드라인으로 삼는다.")

# ═══ 출력 ════════════════════════════════════════════════════════════════════
meta = dict(
    generator="benchmark/carrier_transition_table.py",
    question_ko="3.5 GHz 에서 잰 판정을 5.8 GHz 에 어디까지 그대로 인용해도 되나",
    fc_ref_hz=FC0, fc_new_hz=FC1, f_ratio=FC1 / FC0, lambda_ratio=FC0 / FC1,
    grid_div=DIV, range_m=R_M, prf_hz=PRF, n_poses=N_POSES,
    c_used_by_code=C_CODE,
    grid_rule_ko="⛔R29 — 리듬 몫의 **크기는 인용하지 않는다**(창 반폭 hw 2/8/32 Hz 로 같은 데이터가 9.9/63.4/90.0 %). «λ/12 한정» 꼬리표로는 부족하다 — 격자보다 분석 손잡이가 더 크게 흔든다. 순서만 읽는다."
                 "⭐격자는 λ/12 를 유지한다 — 그래야 R16 격자 밴드(AC 3.86 dB · 리듬 몫 21.8 %p · "
                 "날개끝 밖 몫 12.55 %p)를 5.8 GHz 판정 문턱으로 그대로 쓸 수 있다. "
                 "div 를 손대면 밴드를 다시 재야 한다.",
    headline_ko="⭐닫히는 것은 **시간·주파수 축의 눈금**(f_tip·대역·표본율·속도축·원거리장 경계)이고, "
                "안 닫히는 것은 **세기와 무늬**(σ 절대레벨·로브 위치·가림이 만드는 복소합·PO 문턱)다. "
                "전자는 여기서 끝났고, 후자가 R23② 가 GPU 를 사는 이유다.",
    caveat_farfield_ko="⚠원거리장 경계는 D 를 무엇으로 잡느냐로 갈린다. 3D 대각(0.7764 m) 기준이면 "
                       "5.8 GHz 에서 23.32 m 라 **R = 15 m 가 근거리장으로 넘어간다**. "
                       "report16 이 쓰는 수평 extent(0.5947 m) 기준이면 13.68 m 라 아슬하게 밖이다. "
                       "⇒ 5.8 GHz 리포트에는 «근거리장 단서» 를 다시 붙이고 어느 D 인지 명시할 것.",
    caveat_bandwidth_ko="⚠ΔR 은 대역폭 B 의 몫이지 반송파의 몫이 아니다. 5.8 GHz 에서 값이 달라 보이면 "
                        "그 대역에서 쓸 수 있는 B 가 달라서다 — 두 이유를 한 문장에 섞지 말 것.",
    sources_ko=["src/drones.py (ast 로 읽음)", "outputs/report07_three_engines.json::_meta",
                "outputs/report16_rung_mesh_full.json::nearfield_diagnosis",
                "outputs/audit_po_trust.json::nearfield_verdict",
                "src/materials.py::MATERIALS", "sionna/rt/radio_materials/itu.py:41",
                "sionna/rt/constants.py::DEFAULT_THICKNESS"],
    drones=SPECS)
json.dump(dict(_meta=meta, rows=rows), open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"\n═══ 반송파 전이표 · {FC0/1e9:g} GHz → {FC1/1e9:g} GHz "
      f"(f ×{FC1/FC0:.4f} · λ ×{FC0/FC1:.4f}) ═══\n")
print(f"{'닫힘':^4} {'항목':<52} {'3.5 GHz':>12} {'5.8 GHz':>12} {'비':>7}  규칙")
print("─" * 118)
for r in rows:
    v0, v1 = r["at_3p5"], r["at_5p8"]
    s0 = f"{v0:12.4g}" if isinstance(v0, (int, float)) else f"{'—':>12}"
    s1 = f"{v1:12.4g}" if isinstance(v1, (int, float)) else f"{'—':>12}"
    rt_ = f"{r['ratio_5p8_over_3p5']:7.4f}" if "ratio_5p8_over_3p5" in r else f"{'—':>7}"
    print(f"{'✅' if r['closes'] else '⛔':^4} {r['item']:<52} {s0} {s1} {rt_}  {r['rule']}")
print("\n" + meta["headline_ko"])
print("\n" + meta["caveat_farfield_ko"])
print(f"\n✅ {OUT}")
