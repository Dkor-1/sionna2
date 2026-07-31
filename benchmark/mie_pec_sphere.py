# -*- coding: utf-8 -*-
"""
mie_pec_sphere.py — PEC 구의 **두 기준해(reference solution)**: 정확한 Mie + 해석적 PO
=====================================================================
■■ 이 파일의 지위: **기준해이지 엔진이 아니다** (2026-07-30 사용자 지시로 명시)
---------------------------------------------------------------------------
저장소 방침이 바뀌었다 — **순수 PO 를 "엔진" 으로 쓴 결과는 전부 제거**한다. 표적 σ 는
반드시 **SBR+PO**(Mitsuba 광선으로 first-hit 을 찾아 **가림을 포함**한 PO 면적분) 또는
선행연구가 쓴 방식으로만 낸다.

**그런데 이 파일의 `po_sphere_norm` 은 그 금지 대상이 아니다.** 여기 있는 두 함수는 우리가
무엇을 계산하는 도구가 아니라, **커널을 채점하는 자**다:

    · `mie_pec_backscatter_norm` — 완전도체 구의 **정확해**(Maxwell 엄밀해).
    · `po_sphere_norm`           — 완전도체 구의 **PO 근사 해석해**(닫힌형).

왜 둘 다 필요한가:

    (커널 − Mie)  =  (커널 − 해석 PO)        +  (해석 PO − Mie)
                      ↑ 우리 **수치오차**          ↑ PO 근사를 쓴 **대가**(모델 고유, 못 줄임)

우리 커널이 SBR+**PO** 이므로 격자를 아무리 조여도 수렴하는 목적지는 Mie 가 아니라 **해석 PO** 다.
따라서 **수치 수렴을 볼 때의 과녁은 해석 PO** 이고, Mie 잔차는 "PO 를 쓴 대가" 를 재는 **별도의 자**다.
기준을 하나로 두면 둘이 뒤섞여, 물리모델의 고유 간극이 우리 오차로 오기입된다.
(실증: kr=3 에서 우리 커널은 해석 PO 와 **0.04 dB**, Mie 와는 **3.19 dB** — 그 3.2 dB 는
 PO/Mie 간극 3.23 dB 그 자체다. `outputs/sbr_kr_sweep.json`)

**리포트 표기 규약**: 이 두 값은 언제나 **"기준해(reference solution)"** 로 명시하고, 우리 결과와
같은 줄에 놓지 않는다. "우리가 PO 로 계산했다" 로 읽히면 안 된다.
=====================================================================
왜 필요한가: 우리 SBR+PO 검증은 지금까지 **구 반경 하나(r=0.5 m)** 뿐이라 **kr 단일점**이다
(`outputs/report2_waveform_rcs.json` sbr_validation 의 구는 r 하나). 그런데
`docs/PRIOR_WORK_COMPARISON.md` 는 Sagitta(arXiv:2604.09243)의 **kr 스윕 검증**을
"adopt" 라고 선언해 놓고 **실행한 적이 없다**. 게다가 같은 문서가 스스로 이렇게 적고 있다:

    "SBR+PO 정확도 — Sagitta 대비 산포 6배 나쁨, 유효구간 하단 가장자리.
     div≥8 σ/exact 선형 std 15.5%, div≥16 8.6% vs Sagitta 2.5%.
     kr=36.7 은 Sagitta 유효 하한 kr=30 의 1.22배"

즉 우리는 "이 방법이 유효하다고 공표된 구간의 **가장 시끄러운 가장자리**" 에서 한 점만 재고
있었다. 이 모듈은 그 스윕의 **기준해**를 제공한다.

정확해 (PEC 구, 후방산란)
---------------------------------------------------------------------------
    σ_b / (π a²) = (1/(ka)²) · | Σ_{n=1}^∞ (−1)ⁿ (2n+1) (a_n − b_n) |²

    a_n = j_n(ka) / h_n^(2)(ka)                       (TM / 전기형)
    b_n = [ka·j_n(ka)]′ / [ka·h_n^(2)(ka)]′           (TE / 자기형)

    h_n^(2)(x) = j_n(x) − i·y_n(x)          (e^{+iωt} 규약)
    [x·f_n(x)]′ = f_n(x) + x·f_n′(x),  f_n′ 은 구면베셀 도함수

⚠ **왜 PO/GO 가 아니라 Mie 여야 하나**: 우리가 지금 쓰는 기준은 광학극한 σ = πr² 인데,
  그건 ka → ∞ 의 **점근값**이라 ka 가 작아지면 참값이 아니다. Mie 는 전 영역에서 정확하다.
  (Rayleigh 극한 ka≪1 에서 σ/(πa²) = 9(ka)⁴ 로, πr² 과 임의로 크게 어긋난다.)

⚠ **그런데 Mie 하나만으로도 부족하다** — 해석적 PO 기준해를 나란히 둔다
---------------------------------------------------------------------------
우리 커널은 SBR+**PO** 다. 격자를 아무리 촘촘히 해도 수렴하는 목적지는 정확해(Mie)가
아니라 **PO 근사 자체의 해석해**다. 둘의 차이는 우리 수치오차가 아니라 GO+PO 라는
물리모델이 원래 가진 간극이다. 기준을 Mie 하나로 두면 이 간극이 통째로 우리 오차로
장부에 잘못 적힌다. `po_sphere_norm` 이 그 두 번째 기준해다(유도와 근거는 함수 docstring).

⚠ **여기 없는 기준해** (2026-07-30, 찾는 사람이 헤매지 않도록 명시)
  이 파일은 **구** 전용이다. SBR 커널이 쓰는 나머지 두 해석 과녁은 형상이 구가 아니라
  `src/rcs_sbr.py` 에 함께 있다 — 정면입사 평판 4πA²/λ²(`validate()` [2] 안에 인라인)와
  직각 이면반사체 8πa²b²/λ²(`dihedral_exact_sigma`, `validate()` [3]). 셋 다 한 번에 도는
  집계·기록은 `benchmark/verify_sbr_defect_fixes.py` → `outputs/sbr_defect_fixes.json`.
  (평판·이면반사체는 닫힌형 한 줄이라 Mie 처럼 별도 구현·자기검증이 필요 없다.)

자기검증 (이 파일 실행 시 자동)
  · Rayleigh 극한  ka≪1  →  σ/(πa²) → 9(ka)⁴
  · 광학 극한      ka≫1  →  σ/(πa²) → 1
  · 첫 공진 과녁   ka≈1 부근의 오버슛. ⚠ **최초 판에서 내가 이 값을 ~1.6 이라 잘못 적어
                    게이트가 FAIL 했다** — 실제 계산은 **3.655 @ ka=1.03**. 코드가 아니라
                    기대값이 틀린 것이었다(Rayleigh 가 상대오차 4.6e−04, 광학이 1.000 으로
                    맞는데 커널이 틀릴 수는 없다). PEC 구 후방산란 정규화 곡선의 첫 첨두는
                    교과서적으로 **ka≈1 에서 3.6~3.7** 이다. 기대값을 고쳤다.
  · 해석 PO ↔ 수치적분  닫힌형이 PO 적분의 직접 수치구적과 일치하는지(대수 검증)
  · G = σ_PO/σ_Mie      kr 대역별 평균·산포와 PO 리플 주기

실행: cd sionna2 && ~/.venvs/py312/bin/python benchmark/mie_pec_sphere.py
"""
from __future__ import annotations

import numpy as np
from scipy.special import roots_legendre, spherical_jn, spherical_yn

# 서베이가 측정해 둔 G = σ_PO/σ_Mie 산포(%). 게이트 기대값이자 재현 대상.
SURVEY_G_STD_PCT = {"30-100": 1.613, "30-1000": 0.981}


def _sph_h2(n, x, derivative=False):
    """제2종 구면 한켈 h_n^(2)(x) = j_n − i·y_n  (e^{+iωt} 규약)."""
    return spherical_jn(n, x, derivative=derivative) - 1j * spherical_yn(n, x, derivative=derivative)


def mie_pec_backscatter_norm(ka, n_max=None):
    """PEC 구의 **정규화 후방산란 RCS** σ_b/(πa²). ka 는 스칼라 또는 배열."""
    ka = np.atleast_1d(np.asarray(ka, float))
    out = np.empty_like(ka)
    for i, x in enumerate(ka):
        # Wiscombe 규칙: 항 수는 x + 4x^(1/3) + 2 로 충분하고, 여유를 더 준다.
        N = int(n_max or max(8, np.ceil(x + 4.0 * x ** (1.0 / 3.0) + 10)))
        n = np.arange(1, N + 1)
        jn = spherical_jn(n, x)
        jnp = spherical_jn(n, x, derivative=True)
        h2 = _sph_h2(n, x)
        h2p = _sph_h2(n, x, derivative=True)
        # [x f_n(x)]' = f_n + x f_n'
        xjn_p = jn + x * jnp
        xh2_p = h2 + x * h2p
        a_n = jn / h2
        b_n = xjn_p / xh2_p
        s = np.sum(((-1.0) ** n) * (2 * n + 1) * (a_n - b_n))
        out[i] = (np.abs(s) ** 2) / (x ** 2)
    return out if out.size > 1 else float(out[0])


def mie_pec_sigma_m2(radius_m, fc_hz):
    """PEC 구의 후방산란 RCS σ [m²] (절대값)."""
    lam = 299792458.0 / float(fc_hz)
    ka = 2 * np.pi * np.asarray(radius_m, float) / lam
    return mie_pec_backscatter_norm(ka) * np.pi * np.asarray(radius_m, float) ** 2


def po_sphere_norm(kr):
    """PEC 구의 **해석적 물리광학(PO) 후방산란** σ_PO/(πr²). kr 은 스칼라 또는 배열.

        σ_PO/(π r²) = 1 − sin(2kr)/(kr) + (1 − cos(2kr)) / (2 (kr)²)

    유도(한 줄): 입사 방향을 ẑ 로 두고 조명 반구만 적분한다. t = cosθ ∈ [−1, 0] 에 대해
        I(kr) = ∫_{−1}^{0} (−t) · e^{j·2kr·t} dt ,      σ/(πr²) = (2kr)² · |I(kr)|²
    이고 이 적분은 닫힌형으로 풀려 위 식이 된다. 같은 적분을 수치구적으로 다시 푸는 독립
    경로를 `_po_quadrature_norm` 에 두었고, 자기검증 ④ 가 둘의 일치를 매 실행 확인한다
    (서베이는 4e−12 일치를 보고했고, 이 파일의 구적 설정에서는 ~1e−12 수준으로 재현된다).

    ⚠ 이 함수가 왜 Mie 옆에 반드시 같이 있어야 하는가 (이 라운드의 핵심)
    ---------------------------------------------------------------------------
    우리 커널은 SBR+PO 다. 메쉬를 아무리 잘게 쪼개고 광선을 아무리 많이 쏴도 그 커널이
    수렴하는 값은 **정확해(Mie)가 아니라 이 해석적 PO** 다. 즉

        (커널 − Mie)  =  (커널 − 해석 PO)          +  (해석 PO − Mie)
                          ↑ 우리가 줄일 수 있는 수치오차   ↑ GO+PO 모델의 고유 간극(줄 수 없음)

    이다. 기준을 Mie(또는 πr²) 하나로 두면 오른쪽 두 번째 항이 통째로 우리 수치오차로
    장부에 잘못 적힌다.

    ⚠ **정정(2026-07-29, 적대검증)** — 이 자리에 원래 *"'SBR+PO 산포가 Sagitta 대비 6배
      나쁘다' 는 헤드라인이 바로 그 잘못된 장부에서 나왔다"* 고 적혀 있었다. **틀렸다.**
      그 헤드라인(`docs/PRIOR_WORK_COMPARISON.md` K13)의 15.5% 는 **kr 을 고정(36.677)한 채
      광선격자 밀도축(div≥8)에서 잰 산포**다. 기준해를 바꾸는 것은 모든 표본에 **같은 상수**
      (1/1.02481 = 0.97579)를 곱하는 일이라 산포는 거의 그대로다 — 실측 15.5% → 15.12%,
      즉 Sagitta 2.5% 대비 6.2배 → **6.0배**. Mie 기준으로는 오히려 15.66% 로 나빠진다.
      **기준 선택은 그 6배 격차의 약 3% 만 설명한다.**
      진짜 원인은 K13 자신이 한 줄 옆에 이미 적어둔 **축 불일치**다 — 우리는 단일 입사에서
      div 스윕 산포를, Sagitta 는 **입사방향 평균 후 kr 스윕** 산포를 본다. 서로 다른 양이다.

      그럼 기준 정정이 무의미한가? 아니다. **산포**에는 거의 영향이 없지만 **절대 편차**에는
      크게 작용한다. 실측(`outputs/rcs_anchor.json` 의 구 교정, r=0.178 m·5G):
      πr² 기준 −0.0697 dB 인 편차가 Mie 기준으로는 **−0.3748 dB** 로 5배가 된다
      (ka=13 에서는 광학 점근 자체가 +0.305 dB 틀리기 때문이며, 그 오차가 우리 편차를
      상쇄해 **실제보다 좋아 보이게** 만들고 있었다). 즉 기준 정정은 *"우리 σ 가 얼마나
      맞나"* 를 고치고, 축 정정은 *"우리 산포가 Sagitta 대비 어떤가"* 를 고친다.

    부호가 반대라는 점이 결정적이다. 우리가 검증에 쓰는 구(r=0.5 m, 5G 3.5 GHz →
    kr = 36.6773)에서 두 기준해는 πr² 을 **사이에 두고 양쪽에** 있다:

        Mie      σ/(πr²) = 0.98968  →  πr² 보다 **0.0451 dB 낮음**
        해석 PO  σ/(πr²) = 1.02481  →  πr² 보다 **0.1065 dB 높음**   (둘 사이 0.152 dB)

    따라서 같은 커널 출력을 놓고도 기준을 Mie 로 잡느냐 PO 로 잡느냐에 따라 오차의
    **부호가 뒤집힌다**. 어느 쪽이 옳은가는 취향이 아니다. 커널이 PO 이므로 수치 수렴을
    보는 자리에서는 해석 PO 가 옳은 과녁이고, Mie 는 "PO 근사를 쓰는 대가" 를 재는
    별도의 자다. 두 값 모두 이 파일 실행 시 표로 출력된다(리포트에는 손으로 적지 말고
    outputs/*.json 경유로 주입할 것).

    kr 대역별 G = σ_PO/σ_Mie (log 등간격 kr, 자기검증 ⑤ 가 매 실행 재측정)
        kr ∈ [30, 100]    평균 ≈ 1.0005, 표준편차 ≈ 1.61 %
        kr ∈ [30, 1000]   평균 ≈ 1.0002, 표준편차 ≈ 0.98 %
    두 값 모두 서베이 보고치(1.613 %, 0.981 %)와 마지막 자리에서만 다르다(격자·ddof 규약
    차이).
    ⚠ **정정(2026-07-29)** — 원래 *"kr 을 1000 까지 키워도 이 간극이 0 으로 사라지지 않는다"*
      고 적었으나 **틀렸다**. 국소 간극은 1/kr 로 **줄어든다** — 실측 대역별 표준편차
      [30,100] 1.611 % · [30,1000] 0.980 % · **[300,1000] 0.143 % · [900,1000] 0.075 %**,
      평균 G → 1.000003. [30,1000] 이 1% 근처로 남는 것은 **저 kr 쪽이 분산을 지배**하기
      때문이지 리플이 계속 살아 있어서가 아니다.
    PO 리플 주기는 sin(2kr) 때문에 kr 축에서 π 이며(측정 ≈ 3.142, 서베이 3.14227), 1/kr
    포락선이 첨두를 살짝 밀어 π 보다 아주 조금 크게 측정된다.

    ⚠ 적용 한계: 여기서의 PO 는 모서리 회절 보정(PTD)이 없는 순수 PO 다. 구에는 모서리가
    없으므로 PO−Mie 잔차는 곧 PO 근사 자체의 오차(주로 그림자면 크리핑파 누락)다.
    """
    kr = np.atleast_1d(np.asarray(kr, float))
    u = 2.0 * kr
    out = 1.0 - np.sin(u) / kr + (1.0 - np.cos(u)) / (2.0 * kr ** 2)
    return out if out.size > 1 else float(out[0])


def po_sphere_sigma_m2(radius_m, fc_hz):
    """PEC 구의 해석적 PO 후방산란 RCS σ [m²] (절대값)."""
    lam = 299792458.0 / float(fc_hz)
    kr = 2 * np.pi * np.asarray(radius_m, float) / lam
    return po_sphere_norm(kr) * np.pi * np.asarray(radius_m, float) ** 2


def sphere_reference_set(radius_m, fc_hz):
    """PEC 구 검증의 **기준해 3종을 한 dict 으로** — 모든 생산자가 공유하는 단일 출처.

    반환 키
        kr                              2πr/λ
        go_sigma_m2 / go_dbsm           **광학 점근** πr² — ⚠ 참값이 아니다(ka→∞ 극한값)
        po_sigma_m2 / po_dbsm           **해석적 PO** — SBR+PO 커널이 수렴해야 하는 과녁
        mie_sigma_m2 / mie_dbsm         **정확 Mie** — 물리적 참값
        po_minus_go_db / mie_minus_go_db / po_minus_mie_db

    왜 세 개를 같이 주는가: `po_sphere_norm` docstring 의 분해식대로
        (커널 − Mie) = (커널 − 해석PO) + (해석PO − Mie)
    이므로 **잔차를 하나의 자로만 적으면 장부가 틀린다**. 커널의 수치오차를 보는 자리에서는
    `po_*` 가, "PO 근사를 쓴 대가" 까지 포함한 절대 정확도를 보는 자리에서는 `mie_*` 가 과녁이고,
    `go_*` 는 **라벨된 점근값**으로만 싣는다(과녁으로 쓰지 말 것).

    ⚠ 왜 πr² 을 과녁으로 쓰면 안 되는지, 측정값으로:
      · r=0.5 m·3.5 GHz(kr=36.68) — πr² 은 두 기준해 **사이**에 있다. 해석 PO 가 +0.107 dB
        위, 정확 Mie 가 −0.045 dB 아래(둘 사이 0.152 dB). 생산 커널의 구 잔차(≈0.09 dB @λ/16)
        보다 **과녁 선택의 폭이 더 크다** → 어느 자를 골랐는지가 숫자를 지배한다.
      · r=0.178 m·3.5 GHz(ka=13.06) — 광학 점근 자체가 Mie 대비 +0.305 dB 틀려서,
        πr² 기준 −0.070 dB 로 보이던 편차가 Mie 기준 −0.375 dB(5배)가 된다.

    ⚠ 평판(4πA²/λ²)에는 이 정정이 **적용되지 않는다** — 정면입사 평판에서 그 식은 점근값이
      아니라 **PO 의 정확한 답**이다. 잘못 조준된 것은 구뿐이다.
    """
    lam = 299792458.0 / float(fc_hz)
    r = float(radius_m)
    kr = 2.0 * np.pi * r / lam
    go = np.pi * r ** 2
    po = float(po_sphere_norm(kr)) * go
    mie = float(mie_pec_backscatter_norm(kr)) * go
    go_db, po_db, mie_db = (float(10.0 * np.log10(v)) for v in (go, po, mie))
    return dict(radius_m=r, fc_hz=float(fc_hz), kr=float(kr),
                go_sigma_m2=float(go), po_sigma_m2=po, mie_sigma_m2=mie,
                go_dbsm=go_db, po_dbsm=po_db, mie_dbsm=mie_db,
                po_minus_go_db=po_db - go_db, mie_minus_go_db=mie_db - go_db,
                po_minus_mie_db=po_db - mie_db,
                note=("go_*=광학 점근 πr²(참값 아님) · po_*=해석적 PO(SBR+PO 커널의 과녁) · "
                      "mie_*=정확 Mie(절대 정확도의 자)"))


def _po_quadrature_norm(kr, n_nodes=2000):
    """PO 적분을 **직접 수치구적**으로 푼 σ/(πr²). `po_sphere_norm` 닫힌형의 독립 검증용.

    조명 반구 t = cosθ ∈ [−1, 0] 위에서 I = ∫(−t)·e^{j·2kr·t} dt 를 Gauss–Legendre 로
    적분하고 σ/(πr²) = (2kr)²|I|² 를 쓴다. 닫힌형과 유도 경로가 겹치지 않으므로 대수
    실수(부호·계수)를 잡아낸다. n_nodes 는 kr≈100(진동 ~32주기)까지 기계정밀도로 충분하다.
    """
    x, w = roots_legendre(int(n_nodes))
    t = -0.5 * (x + 1.0)                       # [−1,1] → [−1,0]
    u = 2.0 * float(kr)
    integral = 0.5 * np.sum(w * (-t) * np.exp(1j * u * t))
    return float(np.abs(u * integral) ** 2)


def selfcheck(verbose=True):
    """알려진 극한으로 구현을 검증한다. 반환 dict(모든 게이트 통과 시 ok=True)."""
    res = {}
    # ① Rayleigh: ka<<1 → 9(ka)^4
    ka_r = np.array([0.01, 0.02, 0.05])
    got = mie_pec_backscatter_norm(ka_r)
    want = 9.0 * ka_r ** 4
    rel = np.abs(got / want - 1.0)
    res["rayleigh"] = dict(ka=ka_r.tolist(), got=got.tolist(), want=want.tolist(),
                           max_rel_err=float(rel.max()), ok=bool(rel.max() < 0.02))
    # ② 광학: ka>>1 → 1
    ka_o = np.array([100.0, 300.0, 1000.0])
    go = mie_pec_backscatter_norm(ka_o)
    res["optical"] = dict(ka=ka_o.tolist(), got=go.tolist(),
                          max_dev=float(np.abs(go - 1.0).max()), ok=bool(np.abs(go - 1.0).max() < 0.15))
    # ③ 첫 공진 오버슛: ka~1 근처 최대가 1.2~2.2
    ka_g = np.linspace(0.5, 2.5, 401)
    gg = mie_pec_backscatter_norm(ka_g)
    pk = float(gg.max()); pk_ka = float(ka_g[int(np.argmax(gg))])
    res["resonance"] = dict(peak=pk, at_ka=pk_ka, ok=bool(3.0 < pk < 4.2 and 0.8 < pk_ka < 1.3))
    # ④ 해석 PO 닫힌형 ↔ PO 적분 직접 수치구적 (대수 검증)
    kr_q = np.array([0.5, 1.0, 5.0, 36.6773, 100.0])
    po_c = np.atleast_1d(po_sphere_norm(kr_q))
    po_q = np.array([_po_quadrature_norm(v) for v in kr_q])
    rel_q = np.abs(po_c / po_q - 1.0)
    res["po_quadrature"] = dict(kr=kr_q.tolist(), closed=po_c.tolist(), quad=po_q.tolist(),
                                max_rel_err=float(rel_q.max()), ok=bool(rel_q.max() < 1e-9))
    # ⑤ G = σ_PO/σ_Mie : PO 근사 자체가 가진 간극(우리 수치오차가 아니다)
    ranges = {}
    for tag, (lo, hi) in (("30-100", (30.0, 100.0)), ("30-1000", (30.0, 1000.0))):
        kr_g = np.geomspace(lo, hi, 800)     # 서베이와 같은 log 등간격
        gq = np.asarray(po_sphere_norm(kr_g)) / np.asarray(mie_pec_backscatter_norm(kr_g))
        ranges[tag] = dict(mean=float(gq.mean()), std_pct=float(100.0 * gq.std()),
                           min=float(gq.min()), max=float(gq.max()),
                           survey_std_pct=SURVEY_G_STD_PCT[tag])
    kr_p = np.arange(30.0, 100.0, 1e-4)      # PO 리플 주기(해석식이라 조밀 격자도 싸다)
    y_p = np.asarray(po_sphere_norm(kr_p))
    i_p = np.where((y_p[1:-1] > y_p[:-2]) & (y_p[1:-1] >= y_p[2:]))[0] + 1
    period = float(np.mean(np.diff(kr_p[i_p])))
    ok_g = bool(all(abs(v["mean"] - 1.0) < 0.01 and
                    abs(v["std_pct"] - v["survey_std_pct"]) < 0.05 for v in ranges.values())
                and abs(period - np.pi) < 0.01)
    res["po_vs_mie"] = dict(ranges=ranges, ripple_period=period, ok=ok_g)
    # ⑥ sphere_reference_set — 생산자들이 공유하는 기준해 dict 이 개별 함수와 같은 값인가.
    #    (여기가 깨지면 세 생산자의 잔차 장부가 조용히 어긋난다.)
    _rs = sphere_reference_set(0.5, 3.5e9)
    _dev = max(abs(_rs["po_sigma_m2"] - float(po_sphere_sigma_m2(0.5, 3.5e9))),
               abs(_rs["mie_sigma_m2"] - float(mie_pec_sigma_m2(0.5, 3.5e9))))
    res["reference_set"] = dict(kr=_rs["kr"], po_minus_go_db=_rs["po_minus_go_db"],
                                mie_minus_go_db=_rs["mie_minus_go_db"],
                                po_minus_mie_db=_rs["po_minus_mie_db"], max_abs_dev_m2=float(_dev),
                                ok=bool(_dev < 1e-15 and _rs["po_minus_go_db"] > 0.0
                                        and _rs["mie_minus_go_db"] < 0.0))
    res["ok"] = all(v["ok"] for v in res.values() if isinstance(v, dict))
    if verbose:
        print("=== PEC 구 Mie 구현 자기검증 ===")
        r = res["rayleigh"]
        print(f"  ① Rayleigh  ka={r['ka']}  σ/(πa²) 최대상대오차 = {r['max_rel_err']:.2e}  "
              f"(이론 9(ka)⁴)  {'PASS' if r['ok'] else 'FAIL'}")
        o = res["optical"]
        print(f"  ② 광학극한  ka={o['ka']}  값 = {[round(v,4) for v in o['got']]}  "
              f"→ 1 과의 최대편차 {o['max_dev']:.4f}  {'PASS' if o['ok'] else 'FAIL'}")
        z = res["resonance"]
        print(f"  ③ 첫 공진   최대 {z['peak']:.3f} @ ka={z['at_ka']:.3f}  "
              f"(교과서 3.6~3.7 @ ka≈1)  {'PASS' if z['ok'] else 'FAIL'}")
        q = res["po_quadrature"]
        print(f"  ④ 해석 PO   닫힌형 vs 직접 수치구적  kr={q['kr']}  "
              f"최대상대오차 = {q['max_rel_err']:.2e}  {'PASS' if q['ok'] else 'FAIL'}")
        g = res["po_vs_mie"]
        for tag, v in g["ranges"].items():
            print(f"  ⑤ G=σ_PO/σ_Mie  kr∈[{tag}]  평균 {v['mean']:.5f}  산포 {v['std_pct']:.3f}% "
                  f"(서베이 {v['survey_std_pct']:.3f}%)  범위 {v['min']:.4f}~{v['max']:.4f}")
        print(f"     PO 리플 주기 {g['ripple_period']:.5f} (π={np.pi:.5f})  "
              f"{'PASS' if g['ok'] else 'FAIL'}")
        s = res["reference_set"]
        print(f"  ⑥ 기준해 dict  r=0.5 m·3.5 GHz(kr={s['kr']:.3f})  πr² 대비 "
              f"해석PO {s['po_minus_go_db']:+.4f} dB · Mie {s['mie_minus_go_db']:+.4f} dB "
              f"(둘 사이 {s['po_minus_mie_db']:+.4f} dB)  {'PASS' if s['ok'] else 'FAIL'}")
        print(f"  → 전체 {'PASS' if res['ok'] else 'FAIL'}")
    return res


if __name__ == "__main__":
    r = selfcheck()
    print()
    print("=== 우리 검증 구(r=0.5 m)의 위치: 두 기준해를 πr² 옆에 나란히 ===")
    R0 = 0.5
    go_dbsm = 10 * np.log10(np.pi * R0 ** 2)
    print(f"  광학근사(GO) πr² = {go_dbsm:+.3f} dBsm  ·  Δ 는 모두 이 πr² 대비 기준해의 편차")
    print(f"  {'band [GHz]':12s} {'kr':>7s} | {'Mie σ/(πr²)':>11s} {'σ dBsm':>8s} {'Δ dB':>7s} |"
          f" {'PO σ/(πr²)':>10s} {'σ dBsm':>8s} {'Δ dB':>7s} | {'PO/Mie dB':>9s}")
    opposite = []
    for f, lab in ((1.843e9, "LTE 1.843"), (3.5e9, "5G 3.5"), (5.21e9, "WiFi 5.21")):
        lam = 299792458.0 / f
        kr = 2 * np.pi * R0 / lam
        n_mie = mie_pec_backscatter_norm(kr)
        n_po = po_sphere_norm(kr)
        print(f"  {lab:12s} {kr:7.3f} | {n_mie:11.5f} {10*np.log10(n_mie*np.pi*R0**2):+8.3f} "
              f"{10*np.log10(n_mie):+7.3f} | {n_po:10.5f} {10*np.log10(n_po*np.pi*R0**2):+8.3f} "
              f"{10*np.log10(n_po):+7.3f} | {10*np.log10(n_po/n_mie):+9.3f}")
        opposite.append((n_mie - 1.0) * (n_po - 1.0) < 0)   # πr² 대비 부호가 반대인가
    n_opp = sum(opposite)
    print(f"  → 세 대역 중 {n_opp}/3 에서 두 기준해가 πr² 대비 **서로 반대 부호**다"
          f"(리플 위상이 반대라 대역마다 어느 쪽이 위인지도 바뀐다).")
    print("     SBR+PO 커널의 수치 수렴을 보는 자리에서 과녁은 해석 PO 이고, Mie 와의 잔차는")
    print("     우리 오차가 아니라 PO 근사를 쓴 대가다. 기준을 섞으면 오차의 부호가 뒤집힌다.")
    raise SystemExit(0 if r["ok"] else 1)
