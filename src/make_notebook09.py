# -*- coding: utf-8 -*-
"""
make_notebook09.py — report09.ipynb 생성기
============================================================================
report09 — "챔버 바닥의 함정: 유령 표적"

⚠ 이 파일이 소스다. report09.ipynb 를 직접 고치지 말고 여기를 고쳐 재실행할 것.

한 주제: **반사되는 챔버 바닥이 드론 탐지를 어떻게 방해하는가.**
  · 가만히 있는 바닥 반사 → 도플러가 0 → ECA 가 세기와 무관하게 지운다
    (⚠ 물리 발견이 아니라 모델의 귀결 = 구현 정합성 검사. §3 에 그대로 적는다)
  · 표적을 거쳐 바닥에 튄 경로 → 표적과 함께 도플러가 실림 → ECA 가 못 지운다
    → 진짜 드론 뒤에 유령 표적으로 남는다
  · 넓은 대역(5G)일수록 유령을 진짜와 별개로 분해 → 가짜 표적
    (궤적 중앙 스냅샷 100% ↔ 궤적 전체 평균은 verify_ghost_impact.json 으로 병기)

본문의 **모든 숫자는 outputs/*.json 에서 읽어 넣는다** — 손으로 안 적는다
(floor_ghost_verify.json = 스냅샷, verify_ghost_impact.json = 궤적 전체,
 detection_rx_sweep.json = report12 모드별 기준대역·거리분해능).
문헌값만 상수(PRIOR_*)로 두고 출처를 주석에 남긴다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from provenance import provenance_cells                      # noqa: E402

NB = os.path.join(ROOT, "report09.ipynb")


def _j(n):
    with open(os.path.join(ROOT, "outputs", n), encoding="utf-8") as f:
        return json.load(f)


def _j_opt(n):
    """있으면 읽고 없으면 None (E3 확장절은 이 산출물이 있을 때만 붙인다)."""
    try:
        return _j(n)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _pick5g(lst):
    """파형 리스트에서 5G 엔트리 하나 고르기(name 에 '5G' 포함)."""
    for e in lst or []:
        if "5G" in e.get("name", ""):
            return e
    return (lst or [None])[0]


D = _j("floor_ghost_verify.json")
A = D["A_static_floor"]                       # 가만히 있는 바닥 반사
AP = A["pred"]                                # 손계산(거울상+프레넬)
B = D["B_clutter_dead"]                       # 바닥 반사 세기 스윕 → SCR 불변
CD = {r["name"]: r for r in D["CD_ghost"]}    # 표적 경유 유령 (파형별, 궤적 중앙 스냅샷)

WFS = ("5G NR 100MHz", "WiFi 80MHz", "LTE 20MHz")
G5 = CD["5G NR 100MHz"]

# 궤적 전체(여러 위치)에서 같은 유령을 다시 잰 별도 실행 — 스냅샷 값의 적용 범위를 못박는다.
GI = _j("verify_ghost_impact.json")
# report12 모드별 기준대역/거리분해능(G1=상시 SSB, G2·G3=전대역 NR-PRS)
MODES = _j("detection_rx_sweep.json")["modes"]
G1M, G3M = MODES["G1"], MODES["G3"]

# E3 확장 — cold clutter 도플러퍼짐 (있으면 §5 확장절을 붙인다)
CDOP = _j_opt("verify_clutter_doppler.json")


def _traj(wf_name):
    """verify_ghost_impact.json 의 궤적 전체 CFAR 셀 통계 (손으로 적지 않고 여기서 계산)."""
    rows = [r for r in GI["C_cfar"] if r["wf"] == wf_name]
    n = len(rows)
    return dict(n=n, n_scen=len({r["scen"] for r in rows}),
                p_false=sum(r["ghost_p_false"] for r in rows) / n,
                margin_db=sum(r["ghost_margin_db"] for r in rows) / n,
                resolved=sum(1 for r in rows if r["resolved"]),
                sep_lo=min(r["sep_m"] for r in rows),
                sep_hi=max(r["sep_m"] for r in rows))


T5 = _traj("5G NR 100MHz")

# 두 실행은 **적분시간(CPI 길이 M)이 다르다** — 스냅샷 쪽 M 은 JSON 에 없으므로 생산자 코드의
# 기본값을 읽어 온다(손으로 적지 않는다). 도플러 빈 폭이 달라지므로 두 수치를 나란히 놓을 때 밝혀야 한다.
_SNAP_SRC = os.path.join(ROOT, "benchmark", "verify_floor_ghost.py")
_M_SNAP = int(re.search(r"def cd_ghost\([^)]*\bM=(\d+)", open(_SNAP_SRC, encoding="utf-8").read()).group(1))
_M_TRAJ = int(GI["config"]["M"])
_M_DIFFER = _M_SNAP != _M_TRAJ

# 스윕 폭(전력 dB) — 기준(×1) 대비 최강 클러터가 얼마나 커졌나
_CL_SWEEP_DB = B["rows"][-1]["strongest_db"] - B["rows"][1]["strongest_db"]

# ── 선행 문헌값(상수 — 원문/서지를 직접 확인한 것만. 출처는 각 주석) ────────────────
# ECA 계열 정준 서지: docs/PRIOR_WORK_COMPARISON.md §9 (Wifi_17 참고문헌 L510-514 에서 확인,
#   원문 PDF 미개봉 — ECA-S(sliding) 논문이다)
PRIOR_ECA = ("Colone, Palmarini, Martelli, Tilli, *IEEE TAES* 52(3):1309–1326, 2016")
# Wypich & Zielinski, *Sensors* 2026, DOI 10.3390/s26041317 — 실측 OTA 5G NR 패시브(ECA+ → CA-CFAR).
#   ⚠ 표적은 **차량**, 5.8 GHz (출처: papers_isac_sionna/pilot_findings.md P11; 원문 PDF 미확보)
PRIOR_WYPICH = "Wypich & Zielinski, *Sensors* 2026, DOI 10.3390/s26041317"
# Jopanya & Osorio, SPAWC 2025 — PDF 표지의 DOI 를 직접 확인.
#   원문 검증(전문 추출): CFAR·ambiguity·matched filter·measurement 0 hit, 검출은 2D-FFT +
#   peak-to-average factor 문턱, 클러터는 "assumed to be removed by the system", f_c=15 GHz 시뮬.
PRIOR_JOPANYA = "Jopanya & Osorio, SPAWC 2025, DOI 10.1109/SPAWC66079.2025.11143316"


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def mdl(lines):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(lines))}


def fig(name, alt=""):
    return md(f"![{alt}](outputs/figures/{name}.png)")


def render(name, alt=""):
    return md(f"![{alt}](outputs/renders/{name}.png)")


cells = []

# =========================================================================== #
#  앞머리 (provenance) — 라이브러리 척추 리드
# =========================================================================== #
_front = provenance_cells(
    report="report09",
    what="챔버 바닥의 함정 — **유령 표적**",
    question="전파를 반사하는 챔버 바닥은 드론 탐지를 어떻게 방해하는가?",
    spine=dict(
        core=(f"반사되는 챔버 바닥은 **드론을 거쳐 바닥에 튄 경로**를 만들고, 이 경로는 드론과 함께 "
              f"도플러가 실려 직접파 제거(ECA)를 통과한다 — 진짜 드론 **+{G5['sep_m']:.2f} m** 뒤에 "
              f"**유령 표적**으로 남아, 대역이 넓을수록(5G) 가짜 표적이 된다: 궤적 중앙 스냅샷에서 "
              f"**{G5['p_false']*100:.0f}%**, 궤적 전체 {T5['n']}개 지점 평균 "
              f"**{T5['p_false']*100:.0f}%**(⚠ 두 수치는 적분시간이 다른 별도 실행 — "
              f"M={_M_SNAP} vs M={_M_TRAJ})."),
        gap=(f"Sionna RT `PathSolver` 는 방의 경로(직접파·바닥반사·표적경유)를 **열거**해 주지만, "
             f"그 뒤에 필요한 **레이더 신호처리(직접파·클러터 제거·검출)가 없다** — 정지 클러터와 "
             f"움직이는 표적을 갈라낼 수단이 스톡 파이프라인에 없다."),
        prior=(f"패시브 레이더는 이 문제를 **표준 체인 ECA→CAF→CFAR** 로 푼다 — 직접파와 그 지연복제로 "
               f"설명되는 정지 신호 공간을 통째로 사영·제거한다(ECA 계열 정준 서지: {PRIOR_ECA}; "
               f"슬라이딩 변형 ECA-S 를 다룬 논문으로 **서지만 확인, 원문 미개봉**). 실측 OTA 5G NR "
               f"패시브 레이더도 ECA+ → CA-CFAR 로 같은 체인을 쓴다({PRIOR_WYPICH} — 단 **표적은 "
               f"차량**, 5.8 GHz, 원문 PDF 미확보). 상시 SSB 를 조명원으로 삼는 **발상**은 "
               f"{PRIOR_JOPANYA} 와 같지만, 그 논문의 처리는 2D-FFT + peak-to-average 문턱이고 "
               f"클러터는 “제거된 것으로 가정”한다 — 체인은 우리와 다르다."),
        lib=("레이더 신호처리(ECA·거리-도플러·CFAR)는 `src/passive_process.py` 가 하고, 그 입력 "
             "경로·지연·도플러는 **Sionna RT** 가 준다 — 전파는 Sionna, 신호처리는 우리 코드로 나눠 "
             "**중복계산이 없다**. 이 검출 사슬은 표준 **ECA→CAF→CFAR** 그대로이며, 오픈소스 "
             "**pyAPRiL**(GPLv3)로 교차검증해 NR/WiFi/LTE 모두에서 RD 맵 **최강 피크의 거리빈이 "
             "정답과 일치**함을 확인했다(거리빈 오차 0, `outputs/verify_pyapril.json`). ⚠ 그 대조는 "
             "**피크 위치 일치** 판정이지 CFAR 발화 판정이 아니다."),
        verify=(f"유령 경로의 지연·기하를 **거울상법+프레넬 손계산**과 대조 — 바닥 반사 여분지연 "
                f"{AP['delay_ns']:.1f} ns·세기 {AP['rel_db_tm']:.1f} dB 가 Sionna RT 잔향 탭과 눈금까지 "
                f"겹치고, 유령이 진짜 뒤 +{G5['sep_m']:.2f} m 에 뜬다. ⚠ Sionna 의 정반사 경로탐색 자체가 "
                f"image method 이고 프레넬 식도 같으므로 이 일치는 **독립 검증이 아니라 구현 일관성** "
                f"확인이다(report01 §4)."),
    ),
    sources=[
        dict(item="바닥 경로 지연·각도·세기 (손계산)", src="거울상법 + 프레넬 반사계수", kind="닫힌형"),
        dict(item="콘크리트 유전율 ε_r = 5.24", src="ITU-R P.2040 (3.5 GHz)", kind="규격"),
        dict(item="챔버 잔향 탭 (실측 CIR)", src="Sionna RT `PathSolver`", kind="측정"),
        dict(item="직접파 제거 ECA (계열 서지)", src=f"{PRIOR_ECA} — ECA-S 논문, 원문 미개봉",
             kind="문헌(서지만 확인)"),
        dict(item="유령의 궤적 전체 통계", src="outputs/verify_ghost_impact.json", kind="측정"),
        dict(item="바이스태틱 기하 (TX/RX 좌표)", src="src/bistatic_scene.py", kind="설계값"),
    ],
    engines=["sionna-rt", "radar-dsp", "matplotlib"],
    libs=["sionna", "mitsuba", "torch", "numpy", "matplotlib"],
    reproduce=[
        "cd benchmark && ~/.venvs/py312/bin/python verify_floor_ghost.py   # → outputs/floor_ghost_verify.json",
        "SIONNA2_GPU=3 ~/.venvs/py312/bin/python benchmark/verify_clutter_doppler.py  # §5 → outputs/verify_clutter_doppler.json",
        "~/.venvs/py312/bin/python src/make_notebook09.py                   # → report09.ipynb",
    ],
    artifacts=[
        dict(file="outputs/floor_ghost_verify.json",
             what="바닥 반사 손계산↔RT · 반사세기 스윕 · 파형별 유령(궤적 중앙 스냅샷)"),
        dict(file="outputs/verify_ghost_impact.json",
             what=f"같은 유령을 궤적 전체에서 다시 잰 통계(궤적 {T5['n_scen']}종 × "
                  f"{T5['n'] // T5['n_scen']}지점 = {T5['n']}셀)"),
        dict(file="outputs/figures/report3_f4_floor.png", what="바닥 반사: 거울상+프레넬 ↔ Sionna RT"),
        dict(file="outputs/figures/report3_f8_ghost.png", what="유령 + 대역폭이 가르는 오검출"),
        dict(file="outputs/verify_clutter_doppler.json",
             what="§5 클러터 도플러퍼짐 — 진폭 스윕(도플러 vs 제로도플러)·메커니즘 프로브·"
                  "표적속도 Pd·hot clutter (서베이 §V-A4 처방)"),
    ],
    caveats=[
        f"**'{G5['p_false']*100:.0f}%' 는 궤적 중앙 스냅샷의 값이다.** §4 의 유령 검출확률은 드론을 "
        f"궤적 중앙 **한 점**에 세워 두고 잡음만 반복 재추출한 몬테카를로다"
        f"(`benchmark/run_min_cell.py` — 기하는 스냅샷 1개). 궤적 전체를 훑은 별도 실행"
        f"(`outputs/verify_ghost_impact.json`: 궤적 {T5['n_scen']}종 × "
        f"{T5['n'] // T5['n_scen']}지점 = {T5['n']}셀, 각 N={GI['config']['N']}·M={_M_TRAJ})에서는 유령의 분리량이 "
        f"{T5['sep_lo']:.2f}~{T5['sep_hi']:.2f} m 로 변해 5G 의 가짜표적 확률이 평균 "
        f"**{T5['p_false']*100:.0f}%**, 유령의 CFAR 임계 여유가 평균 **{T5['margin_db']:+.2f} dB**"
        f"(= 평균적으로 임계 아래)가 된다 — 유령은 궤적 위치에 따라 임계를 오르내린다. "
        f"⚠ 두 수치는 **같은 처리 설정의 비교가 아니다** — 스냅샷 실행의 CPI 는 M={_M_SNAP}"
        f"(`benchmark/verify_floor_ghost.py` 의 `cd_ghost()` 기본값), 궤적 실행은 M={_M_TRAJ} 라 "
        f"도플러 빈 폭이 다르다. 그래서 '{G5['p_false']*100:.0f}% → {T5['p_false']*100:.0f}%' 를 "
        f"위치 효과만의 감소로 읽어서는 안 된다.",
        "**§3 의 정지 클러터 스윕은 물리 발견이 아니라 구현 정합성 검사다** — 세기와 무관한 소거는 "
        "0-도플러 노치의 **구성상 귀결**이다(주입 정지 클러터의 잔류가 RD 맵 0-도플러 능선에 앉아 "
        "노치+표적셀-측정에 배제된다). 그 한계 하나(**클러터 도플러 퍼짐**)를 실제로 넣어 시험한 것이 "
        "**§5**다(있을 때) — 결론: SCR '죽은 파라미터'는 정지 가정 하의 **항등식**이었고 도플러가 실리면 "
        "진폭²로 즉시 되살아나며, 나아가 **움직이는 클러터는 표적셀에 가짜 검출을 만든다**(표적을 지워도 "
        "표적셀 CFAR 가 울리고, 클러터를 빼면 0). ⚠ 유한 ADC 동적범위·양자화는 여전히 이 하네스에 없다.",
        f"**유령의 세기는 편파 가정에 걸려 있다.** 바닥 입사각 {G5['theta_i_deg']:.0f}° 는 콘크리트 "
        f"브루스터각 부근이라 수직편파(V)의 반사가 이례적으로 약하다(|Γ|≈{G5['gamma']:.2f}). "
        "수평편파(H)라면 유령이 더 세진다. 편파는 측정된 값이 아니라 가정이다.",
        "**유령의 표적 되비침 밝기(RCS)는 진짜 에코와 같다고 1차 근사했다.** 유령은 시선각이 "
        "다르므로 실제 밝기는 다르다.",
        "**흡수체 벽·천장의 −25 dB 는 실측이 아니라 설계 목표다** — 피라미드 형상의 다중반사로 "
        "달성되는 값이다.",
        "**검출기(CFAR) 자체의 문턱이 제대로 눈금 맞춰져 있는지는 여기서 다루지 않는다** → report10. "
        "이 리포트의 '100% 오검출'은 유령이 **물리적으로 별개 표적으로 분해된다**는 뜻이다.",
        "**여기의 '5G'는 전대역(98 MHz, NR-PRS/풀점유) 기준이다** — 상시 SSB(7.2 MHz)만 켠 5G 는 "
        "유령을 분해하지 못해 이 100% 가 적용되지 않는다(§4 적용 범위 참고, report12 G1/G3 구분).",
    ],
    cost="GPU 1장(자동 선택). 챔버 잔향 탭은 RT 측정 재사용. 검증 스크립트는 수 분.",
    related=[
        dict(rep="report08 (앞)", rel="표적 RCS·마이크로도플러 — 유령 세기 근사가 빌려 쓰는 표적 밝기"),
        dict(rep="report10 (다음)", rel="검출기(CFAR) 자체의 문턱이 눈금 맞춰져 있나"),
    ],
    glossary=[
        ("반무향 (semi-anechoic)", "벽·천장은 전파 흡수체지만 **바닥은 반사**하는 챔버. 우리 실험실이 이것"),
        ("클러터", "표적이 아닌 것에서 온 반사(벽·바닥·장비). 정지해 있으면 도플러가 0 이다"),
        ("도플러", "물체가 움직여 생기는 주파수 변화. 정지 반사(도플러 0)와 움직이는 표적을 가르는 축"),
        ("유령 (ghost)", "TX→**드론**→바닥→RX 경로의 반사. 드론을 거치므로 도플러가 실려, 클러터와 달리 "
                        "ECA 를 통과해 가짜 표적으로 뜬다"),
        ("ECA (직접파 제거)", "송신기→수신기 직접파와, 그것의 지연된 복제로 설명되는 모든 정지 반사를 "
                          "빼는 전처리. 세기를 안 보고 '정지 신호 공간'째로 지운다"),
        ("거울상법 (image source)", "반사면을 거울로 보고 수신기를 면 뒤에 대칭 복제해서 반사 경로를 "
                                "직선으로 펴 지연·각도를 손계산하는 방법"),
        ("프레넬 반사계수 Γ", "면에 부딪힌 파가 반사되는 비율(복소수). 편파·입사각·유전율에 따라 달라진다"),
        ("브루스터각", "수직편파(V)의 반사가 최소가 되는 입사각. 여기 부근이면 V 유령이 이례적으로 약하다"),
        ("바이스태틱 거리 R_b", "TX→표적→RX 경로의 총 길이. 이 값이 표적의 '거리 눈금'이다"),
        ("거리분해능 ΔR_b = c/B", "대역폭 B 가 넓을수록 가까운 두 반사를 **따로** 분해한다"),
        ("RCS (되비침 밝기)", "표적이 얼마나 밝게 되비추는가 [m²]. 밝아야 잡힌다"),
        ("CFAR", "주변 잡음 수준을 보고 검출 문턱을 스스로 정하는 검출기"),
    ],
)

cells += _front   # 척추 리드가 헤더에 있으므로 별도 5분요약은 싣지 않는다

# =========================================================================== #
#  §1  Sionna 의 공백
# =========================================================================== #
cells.append(md(
    "# §1. Sionna 의 공백 — 방은 풀지만 표적을 못 골라낸다",
    "",
    "드론의 되비침 밝기(RCS)는 앞 리포트에서 다뤘다(report08). 여기서는 드론이 아니라 "
    "**드론을 둘러싼 방** — 특히 바닥 — 이 탐지에 무엇을 하는지 본다. 방 안에서 전파가 어떤 길로 "
    "흐르는지는 손으로 열거하기 어렵다. 그 경로 목록을 만들어 주는 것이 **Sionna RT 의 경로 "
    "솔버(`PathSolver`)** 다 — 장면의 기하·재질로부터 직접파·반사·회절 경로를 모두 열거한다. 선행 "
    "ISAC 디지털트윈 연구도 환경의 결정론적 멀티패스(지연·도플러·각도)를 이렇게 RT 로 얻는다"
    "(*Deterministic Modeling of Dynamic ISAC Channels*, EuCAP 2026, arXiv:2603.28736).",
    "",
    "그런데 **거기서 끝난다.** `PathSolver` 는 경로 목록을 줄 뿐, 그 목록에서 **무엇이 표적이고 "
    "무엇이 지워야 할 클러터인지 가려 주지 않는다** — 직접파를 빼는 처리도, 정지 반사를 지우는 "
    "처리도, 검출 문턱을 세우는 처리도 스톡 파이프라인에는 없다(Sionna 에 레이더 DSP 가 없다). "
    "이 리포트의 위협은 정확히 그 공백에서 자란다: 반사하는 바닥이 만드는 여러 경로 중 하나가, "
    "아무 처리 없이는 진짜 드론과 구별되지 않는 **유령 표적**으로 남기 때문이다.",
    "",
    "아래는 챔버를 Sionna 로 렌더한 모습이다. 벽과 천장은 뾰족한 피라미드 흡수체로 덮여 전파를 "
    "먹지만, **바닥(체커판)은 딱딱한 콘크리트라 전파를 반사**한다. 빨간 점이 송신기(TX), 초록 점이 "
    "수신기(RX)이고, 둘 다 같은 벽 위에 떨어져 붙어 있다.",
))
cells.append(render("rt_05_grazing_floor", "Semi-anechoic chamber: absorbing walls/ceiling, reflective floor"))

cells.append(mdl([
    "이 방을 흔히 '무반사(anechoic) 챔버'라 부르지만, 정확히는 **반무향(semi-anechoic)** 이다 — "
    "**설계상 반사면으로 남긴 것이 바닥뿐**이다. 이 한 면 때문에 `PathSolver` 가 열거하는 경로가 늘어난다:",
    "",
    "- **직접파** — TX 에서 RX 로 곧장 가는 가시선.",
    "- **바닥 반사** — TX 에서 **바닥에 튕겨** RX 로. 조금 늦게 도착한다(정지).",
    "- **표적을 거친 바닥 경로** — TX 에서 드론에 맞고, 다시 **바닥에 튕겨** RX 로. 드론을 거쳐 움직인다.",
    "",
    "셋 다 RT 는 똑같이 '경로'로 내놓는다 — 어느 것이 무해하고 어느 것이 위협인지는 RT 가 말해 주지 "
    "않는다. §2 는 이 경로들이 실재함을 손계산으로 대조하고, §3 은 패시브 레이더가 이 셋을 어떻게 "
    "가르는지, §4 는 우리가 그 처리를 어떤 라이브러리로 얹었는지를 본다.",
]))

# =========================================================================== #
#  §2  증거 — 바닥 경로는 실재하고 손계산과 맞는다
# =========================================================================== #
cells.append(md(
    "---",
    "# §2. 증거 — 바닥 경로는 실재하고, 손계산과 맞는다",
    "",
    "'RT 가 바닥 경로를 열거한다'는 말을 손계산으로 못박는다. 표준 닫힌형 기법 — **거울상법**"
    "(반사면을 거울로 보고 RX 를 바닥 아래로 대칭 복제)과 **프레넬 반사계수** — 으로 각 경로의 "
    "지연·각도·세기를 짚는다. ⚠ 이것을 RT 의 **독립 검증**이라 부르지는 않는다 — Sionna 의 정반사 "
    "경로탐색 자체가 image method 이고(설치본 `sionna/rt/path_solvers/image_method.py`) 프레넬 식도 "
    "같으므로, 아래 일치는 **씬 좌표·단위·규약의 구현 일관성** 확인이다(근거는 report01 §4).",
    "",
    "### 2.1 정지 바닥 반사 — 거울상+프레넬 ↔ Sionna RT",
    "",
    "| 항목 | 값 |",
    "|---|---|",
    f"| 직접파 경로 | {AP['L_direct_m']:.2f} m |",
    f"| 바닥 경유 경로 | {AP['L_floor_m']:.2f} m |",
    f"| 여분 지연 (늦게 도착) | **{AP['delay_ns']:.1f} ns** |",
    f"| 바닥 입사각 (법선 기준) | {AP['theta_i_deg']:.1f}° — 스침각이 아니라 꽤 비스듬히 때린다 |",
    f"| 프레넬 반사계수 크기 \\|Γ\\| (콘크리트 ε_r=5.24, V편파=TM) | {AP['gamma_tm']:.3f} |",
    f"| **직접파 대비 세기** | **{AP['rel_db_tm']:.1f} dB** |",
    "",
    "이 닫힌형 값을 Sionna RT 가 챔버에서 낸 잔향 탭과 나란히 놓으면 **지연도 세기도 눈금까지 "
    "겹친다.** 즉 바닥 반사는 상상이 아니라 RT 가 경로 목록에 넣은 실재하는 경로이며, 그 세기·지연은 "
    "교과서 전파 이론과 어긋나지 않는다.",
    "",
    "> ⚠ **위 세 갈래가 방 안 경로의 전부는 아니다.** 흡수체 잔여 반사가 0 이 아니라서, 저심도 "
    "정반사만 봐도 천장 흡수체 1회 반사가 바닥보다 세고 정면 흡수체 2회 반사는 **바닥과 같은 지연 빈**에 "
    "더 세게 들어온다(수치는 report01 §2). 위 대조는 RT 가 분리해 준 **바닥 경로 탭 하나**에 대한 것이고, "
    "그 흡수체 잔여분을 실제로 무력화하는 것은 기하가 아니라 §3 의 ECA 도플러-0 제거다.",
))
cells.append(fig("report3_f4_floor", "Floor bounce: image source + Fresnel agrees with Sionna RT"))

cells.append(md(
    "### 2.2 표적을 거친 바닥 경로 — 유령이 서는 자리",
    "",
    "**TX → 드론 → 바닥 → RX** 경로를 보자. 같은 반사 기하를 이번엔 **움직이는 드론을 거쳐** 태우면 "
    "이 이차 경로가 된다. 물웅덩이 옆을 걷는 사람의 그림자가 사람을 따라 걷듯, 바닥에 비친 드론의 "
    "반사는 드론을 따라 움직인다 — 즉 이 경로에는 **도플러가 실린다**(§3 에서 이 차이가 결정적이 "
    "된다). 드론을 챔버 중앙(quiet zone)에 두고 이 경로의 좌표를 거울상법+프레넬(표준 닫힌형)로 짚으면:",
    "",
    "| 항목 | 값 |",
    "|---|---|",
    f"| 진짜 드론의 바이스태틱 거리 R_b | {G5['rb_true']:.2f} m |",
    f"| 유령의 R_b | {G5['rb_ghost']:.2f} m |",
    f"| **진짜 드론 뒤로 떨어진 거리** | **+{G5['sep_m']:.2f} m** |",
    f"| **진짜 에코 대비 세기** | **{G5['ghost_db']:.1f} dB** (진짜 에코보다 크게 어둡지만 진짜 에코 SNR 이 충분해 검출) |",
    f"| 바닥 입사각 | {G5['theta_i_deg']:.0f}° |",
    "",
    f"> **유령은 진짜 드론보다 딱 +{G5['sep_m']:.2f} m 뒤에, {G5['ghost_db']:.1f} dB 어둡게 뜬다.** "
    "이 위치와 세기는 순전히 방의 기하(TX·RX·바닥·드론 위치)로 정해지며, 어떤 통신 신호를 쓰든 "
    "거의 같다. 신호에 따라 달라지는 것은 단 하나 — 이 유령을 진짜와 갈라 볼 수 있느냐다.",
))
cells.append(md(
    "![.](outputs/renders/anim/radiomap_scan.gif)\n\n"
    "<sub>전파 세기 지도를 바닥→위로 훑는다 — 바닥 반사가 왜 유령을 만드는지 위치를 보여준다.</sub>"
))

# =========================================================================== #
#  §3  선행 연구의 방식 — 패시브 레이더 표준 체인
# =========================================================================== #
cells.append(mdl([
    "---",
    "# §3. 선행 연구의 방식 — 패시브 레이더 표준 체인 ECA→CAF→CFAR",
    "",
    "RT 가 가려 주지 않는 '무엇이 클러터이고 무엇이 표적인가'를, 패시브 레이더는 **표준 신호처리 "
    "체인**으로 푼다 — 직접파 제거(ECA) → 상호모호함수(CAF, 거리-도플러) → CA-CFAR 검출. 이건 우리가 "
    "지어낸 처리가 아니라 문헌의 정석이다: 직접파와 그 지연복제로 설명되는 정지 신호 공간을 통째로 "
    f"사영·제거하는 ECA 계열({PRIOR_ECA} — 슬라이딩 변형 ECA-S 논문이며 **서지만 확인했고 원문은 "
    f"미개봉**이다)을, 실측 OTA 5G NR 패시브 레이더가 ECA+ → CA-CFAR 로 그대로 쓴다"
    f"({PRIOR_WYPICH}; 단 그 실측의 **표적은 차량**이고 5.8 GHz 다 — 원문 PDF 는 우리 코퍼스에 "
    "없고 공개 전문 페이지 기반 노트다).",
    "",
    f"상시 SSB 를 조명원으로 삼는 발상의 선례는 {PRIOR_JOPANYA} 지만, **처리 체인은 우리와 다르다** — "
    "그 논문은 검출을 2D-FFT + peak-to-average factor 문턱으로 하고 클러터는 “시스템이 제거한 "
    "것으로 가정”하며, 15 GHz 대역의 순수 시뮬레이션이다(원문 전문 확인: CFAR·모호함수·정합필터 "
    "언급 0회). 즉 상시-SSB 조명원 아이디어만 공유하고, ECA→CAF→CFAR 체인의 선례는 아니다.",
    "",
    "이 체인의 핵심은 **ECA 가 세기를 보지 않고 '가만히 있는 신호가 사는 공간' 째로 뺀다**는 것이다. "
    "그래서 §2 의 두 바닥 경로가 정반대로 갈린다.",
    "",
    "우리 구현(`src/passive_process.py ECACanceller`)은 CPI 전체에 대해 기준신호의 지연 부분공간을 "
    "**1회** 최소제곱 사영하는 **standard ECA** 다 — 슬라이딩(ECA-S)·배치 변형이 아니다. 그래서 "
    "'도플러 0' 은 이진 스위치가 아니라 **유한한 폭의 노치**이고, 표적도 유령도 그 노치 밖에 있어야 "
    f"살아남는다(이 시나리오의 표적 f_d = {G5['fd_true']:.0f} Hz, 유령 {G5['fd_ghost']:.0f} Hz). "
    "노치 폭과 그로부터 나오는 최소검출속도는 report11 이 `outputs/verify_eca.json` 으로 따로 잰다 — "
    "여기서는 표적·유령이 노치 밖이라는 사실만 쓴다.",
    "",
    "**정지 바닥 반사(도플러 0)는 그 사영 공간 안에 있어 통째로 지워진다.** 세기를 아무리 키워도 "
    f"마찬가지다 — 바닥 반사 최강 탭을 없음에서 **+{_CL_SWEEP_DB:.0f} dB**(직접파보다 강해질 만큼)"
    "까지 키워 신호-대-클러터비(SCR)를 다시 재 보면 (기준 ×1 = "
    f"{B['rows'][1]['strongest_db']:.1f} dB 가정은 RT 실측 바닥반사 {A['match']['rel_db']:.1f} dB·최강 "
    f"{A['rt_strongest_db']:.1f} dB(§2.1)보다 "
    f"{abs(A['match']['rel_db'] - B['rows'][1]['strongest_db']):.0f}~"
    f"{abs(A['rt_strongest_db'] - B['rows'][1]['strongest_db']):.0f} dB 약하게 잡은 과소평가지만, "
    "이 스윕이 실측값까지 전부 덮는다):",
    "",
    "| 바닥 반사 최강 탭 | SCR [dB] | 탐지확률 Pd |",
    "|---|---|---|",
] + [
    (f"| 없음 | {r['scr']:.4f} | {r['pd']:.2f} |" if r["strongest_db"] is None
     else f"| {r['strongest_db']:+.0f} dB (×{r['scale']:.0f}) | {r['scr']:.4f} | {r['pd']:.2f} |")
    for r in B["rows"]
] + [
    "",
    f"> **SCR 이 전 구간에서 {B['scr_span_db']:.0e} dB 밖에 안 움직인다** — 이 하네스 안에서 정지한 "
    "바닥 반사는 세기와 무관하게 탐지에 **무해**하다.",
    "",
    "다만 이 표가 무엇을 증명하는지는 정확히 못박아야 한다. **이것은 물리 발견이 아니라 모델의 "
    "귀결이고, 읽는 방식은 '구현 정합성 검사'다.** 주입한 정지 클러터는 도플러가 없는 기준신호의 "
    "지연복제이고(`benchmark/geometry.py`), ECA 가 사영하는 기저가 바로 그 '지연복제들'이다 — 즉 "
    "진폭과 무관한 소거는 **구성상 보장**되어 있다. 이 표가 말해 주는 것은 '실제 정지 클러터가 정말 "
    "무해하다'가 아니라 **'ECA 사영이 설계대로 동작한다'** 이다. 실제 장비의 유한 동적범위·클러터 "
    "도플러 퍼짐·양자화는 이 하네스에 아직 없다.",
    "",
    "**반면 표적을 거친 바닥 경로(§2.2)는 드론을 따라 움직여 도플러가 실린다.** ECA 의 '정지 신호 "
    "공간' 밖에 있으므로 지워지지 않고 검출기에 그대로 노출된다 — 이것이 유령이 살아남는 이유다. "
    "정지 클러터를 지우는 바로 그 표준 체인이, 도플러가 실린 유령 앞에서는 무력하다.",
]))

# =========================================================================== #
#  §4  우리가 쓴 방식 — 표준 검출 사슬 + Sionna RT, 그리고 대역폭의 대가
# =========================================================================== #
cells.append(mdl([
    "---",
    "# §4. 우리가 쓴 방식 — 표준 검출 사슬(pyAPRiL 로 교차검증) + Sionna RT(경로), 그리고 대역폭의 대가",
    "",
    "이 표준 체인의 신호처리(ECA·거리-도플러·CFAR)는 `src/passive_process.py` 가 하고, 그 입력이 "
    "되는 경로·지연·도플러는 **Sionna RT** 가 준다. 역할이 겹치지 않아 **중복계산이 없다**: "
    "전파(경로·지연)는 Sionna, 신호처리(직접파·클러터 제거·검출)는 우리 코드다. 이 검출 사슬이 "
    "표준 ECA→CAF→CFAR 그대로임은 오픈소스 **pyAPRiL**(GPLv3)로 교차검증했다 — NR/WiFi/LTE 세 모드 "
    "모두에서 pyAPRiL 이 만든 RD 맵의 **최강 피크 거리빈이 정답 거리빈과 일치**했다(오차 0빈, "
    "`outputs/verify_pyapril.json`). ⚠ 이 대조가 보증하는 것은 **거리 눈금과 처리 순서의 일치**이지 "
    "문턱 교정이 아니다 — 판정 기준이 봉우리 위치이고 **CFAR 발화 여부는 이 기록으로 확정되지 않는다**"
    "(report10 §4 와 같은 규약). 문턱 교정은 report10 이 다룬다.",
    "",
    "이제 유령을 실제로 신호에 주입해 이 체인을 파형별로 돌린다(드론은 **궤적 중앙 한 점**, 잡음만 "
    "반복 재추출). 레이더가 두 물체를 따로 볼 수 있는 "
    "최소 간격이 **거리분해능 ΔR_b = c / B** 다. 대역폭 B 가 넓을수록 ΔR_b 가 작아져 가까운 둘을 "
    f"분해한다. 유령은 진짜 뒤 **+{G5['sep_m']:.2f} m** 고정이니, **분리 ÷ ΔR_b 가 1 을 넘으면** "
    "유령이 자기만의 자리를 얻어 **가짜 표적**이 된다:",
    "",
    "| 파형 | 대역폭 B | 거리분해능 ΔR_b | 분리 ÷ ΔR_b | 유령을 별개 표적으로 검출 (궤적 중앙 스냅샷) |",
    "|---|---|---|---|---|",
] + [
    (lambda r: f"| **{r['name']}** | {r['bw_hz']/1e6:.0f} MHz | {r['d_rb_m']:.1f} m | "
               f"**{r['sep_over_drb']:.2f}×** | "
               + (f"**{r['p_false']*100:.0f}% — 매 시행 가짜 표적**" if r["resolved"]
                  else f"{r['p_false']*100:.0f}% (진짜와 뭉쳐 못 분해)") + " |")(CD[n])
    for n in WFS
] + [
    "",
    f"> ### 5G 는 진짜 드론과 +{G5['sep_m']:.2f} m 뒤 유령을 **둘 다** 검출한다",
    f"> 5G 의 거리분해능은 {G5['d_rb_m']:.1f} m 인데 유령은 {G5['sep_m']:.2f} m 뒤에 있으니, 분리가 "
    f"분해능의 **{G5['sep_over_drb']:.2f} 배** — 여유 있게 넘는다. 그래서 이 스냅샷에서는 매 시행마다 "
    f"진짜 드론 하나에 **유령 하나가 가짜 표적으로 더 잡힌다({G5['p_false']*100:.0f}%).**",
    "",
    f"> **적용 범위.** 위 확률은 궤적 중앙 **한 지점**의 값이다. 드론이 움직이면 유령의 분리량이 "
    f"{T5['sep_lo']:.2f}~{T5['sep_hi']:.2f} m 로 변해 분해 여부가 지점마다 갈린다 — 궤적 전체 "
    f"{T5['n']}개 지점(`outputs/verify_ghost_impact.json`)에서는 5G 가 {T5['resolved']}/{T5['n']} 지점에서 "
    f"유령을 분해하고, 가짜표적 확률은 평균 **{T5['p_false']*100:.0f}%**, 유령의 CFAR 임계 여유는 평균 "
    f"**{T5['margin_db']:+.2f} dB**(평균적으로 임계 아래)다. 즉 정직한 한 줄은 *\"중앙 스냅샷에서 "
    f"{G5['p_false']*100:.0f}%, 궤적 평균 {T5['p_false']*100:.0f}%\"* 다.",
]))
cells.append(fig("report3_f8_ghost", "The floor ghost, and why bandwidth turns it into false alarms"))

cells.append(mdl([
    "그림 왼쪽: 진짜 드론(초록 원)과 유령(파란 X)이 거리-도플러 지도에서 둘 다 살아 있다 — 둘 다 "
    f"도플러가 실려 ECA 가 지우지 못했기 때문이다. 오른쪽: 유령이 진짜 뒤 {G5['sep_m']:.2f} m 에 "
    f"고정된 채, **대역이 넓은 5G 만 그 {G5['sep_m']:.2f} m 를 분해**해 유령을 세로 점선 "
    "오른쪽(=별개 표적)으로 밀어낸다.",
    "",
    "넓은 대역은 보통 '더 정밀하게 본다'는 장점으로 소개된다. 그런데 바닥 유령 앞에서는 바로 그 "
    "정밀함이 **가짜 표적을 하나 더 세우는 약점**이 된다. 좁은 대역(LTE)은 유령을 진짜와 뭉개 "
    f"안 보이지만({CD['LTE 20MHz']['sep_over_drb']:.2f}×), 그건 안전해서가 아니라 애초에 위치를 "
    "그만큼 못 재기 때문이다.",
    "",
    f"> ⚠️ 여기서 말하는 '{G5['p_false']*100:.0f}% 오검출'은 유령이 **물리적으로 별개 표적으로 "
    "분해된다**는 뜻이다. 그걸 실제로 검출하는 CFAR 문턱이 제대로 눈금 맞춰져 있는지는 **다음 "
    "리포트에서** 따로 본다.",
    "",
    f"> ⚠️ **적용 범위 — 이 표의 '5G'는 전대역 NR-PRS 기준신호({G5['bw_hz']/1e6:.0f} MHz) 기준이다** "
    f"(report12 의 G2·G3 가 이 기준대역 {G3M['ref_bw_mhz']:.2f} MHz 를 공유하며, 여기 주입한 파형은 "
    f"G3 풀로드다). 5G 가 **상시 신호(SSB {G1M['ref_bw_mhz']:.1f} MHz)만** 켠 경우(report12 의 G1)는 "
    f"ΔR_b ≈ {G1M['range_res_m']:.1f} m 라 +{G5['sep_m']:.2f} m 유령을 전혀 분해하지 못한다 — 유령 "
    "오검출은 0% 가 되지만, 대신 표적 위치도 그만큼 못 잰다(LTE 와 같은 이유). 즉 '유령 문제'는 "
    "**5G 를 넓게 쓸수록**(측위 세션·고점유) 나타나는 대가다.",
]))

# =========================================================================== #
#  §5  E3 확장 — 클러터에 도플러퍼짐을 주면 '죽은 파라미터'는 살아남는가
# =========================================================================== #
def _clutter_doppler_cells(C):
    """verify_clutter_doppler.json → §5 확장절(정직 서술 + 숫자 주입). 없으면 빈 리스트."""
    if not C:
        return []
    c1 = _pick5g(C.get("C1_cold_model"))
    c2 = _pick5g(C.get("C2_amplitude_sweep"))
    cb = C.get("C2b_M96") or {}
    _M_clut = int((C.get("meta") or {}).get("M_default", 48))   # 클러터 실행의 CPI 길이(궤적 M=48 과 동일 설정)
    c3 = C.get("C3_hot_clutter") or {}
    c4 = C.get("C4_target_speed") or {}
    if not (c1 and c2):
        return []
    dop, zero = c2["doppler"], c2["zero_dop"]

    def _row(rows, s):
        for r in rows:
            if r.get("scale_db") == s:
                return r
        return {}
    dn, d0, d40 = _row(dop["rows"], None), _row(dop["rows"], 0.0), _row(dop["rows"], 40.0)
    mech = c1.get("eca_mechanism", {})
    mz, md_ = mech.get("zero_dop", {}), mech.get("doppler", {})
    out = []

    out.append(md(
        "---",
        "# §5. 도플러퍼짐을 주면 — '죽은 파라미터'는 항등식이었다",
        "",
        "§3 에서 **정지** 바닥 반사는 세기와 무관하게 탐지에 무해했다(\"죽은 파라미터\"). 거기서 "
        "정직하게 단서를 달았다 — *실제 ECA 는 유한 동적범위·클러터 **도플러 퍼짐**·양자화 때문에 "
        "이만큼 완벽하지 않다, 그 한계는 아직 모델에 없다.* **이 절에서 그 한계 하나(클러터 도플러 "
        "퍼짐)를 실제로 넣고, 죽은 파라미터 결론이 살아남는지 시험한다**(`benchmark/verify_clutter_"
        "doppler.py` → `outputs/verify_clutter_doppler.json`).",
        "",
        "선행(Clutter-Aware ISAC 서베이 §V-A4, Proc. IEEE 114, 2026)의 정확한 처방을 챔버 기하로 "
        "그대로 옮겼다 — **cold clutter = C=100 산란체**, 표적 바이스태틱거리 앞뒤 **4개 iso-range "
        "링**(가까운 2·먼 2), 방위 U[−90°,90°], **반경속도 U[−1,+1] m/s**(느린 환경 클러터). "
        "반사계수는 CN(0,1), 앙상블 세기는 **RT 실측 최강 바닥탭**으로 앵커한다:",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 배치된 산란체 | {c1['C_placed']}/100, 링별 {c1['placed_per_ring']} |",
        f"| 4 링 지연 (표적 {(c1['ring_tau_ns'][1]+c1['ring_tau_ns'][2])/2:.1f} ns bracket) | "
        f"{[round(x,1) for x in c1['ring_tau_ns']]} ns |",
        f"| 도플러밴드 (M={_M_clut}, 궤적 실행과 동일 설정) | ±{c1['fd_band_hz']:.1f} Hz = **{c1['fd_band_over_dfd']:.2f}×빈** "
        f"(노치 반폭 {c1['notch_halfwidth_hz']:.1f} Hz) |",
        f"| CNR 앵커 (라벨=실현, 경험적 재스케일) | 공칭 {c1['cnr_nominal_db']:.1f} dB → 실현 "
        f"**{c1['cnr_realized_db']:.2f} dB** |",
        "",
        "> ⚠ 앵커는 RT **정적** specular 바닥탭(−9.8 dB)의 전력을 68~79 ns 의 **이동** 산란체 "
        "100개 총전력으로 이전한 것이다. GIT 경험식이 아니라 **RT 실측 탭**으로 앵커한다.",
    ))

    out.append(md(
        "### 5.1 핵심 시험 — 진폭 40 dB 스윕: 도플러 vs 제로도플러 대조군",
        "",
        "**동일 산란체·동일 시드**로 도플러를 실은 arm 과 fd 를 전부 0 으로 죽인 대조군을 나란히 "
        "돌린다 — 이러면 '도플러가 유일한 원인'인지가 격리된다. 억제 후 SCR 과, **노치·표적셀과 "
        "무관한 ref-region 전력**(진폭의존을 깨끗이 드러내는 프로브)을 함께 본다:",
        "",
        "| cold 진폭 (RT앵커 대비) | SCR 후, 도플러 | SCR 후, 제로도플러(대조군) | ref-region, 도플러 |",
        "|---|---|---|---|",
        f"| 없음 | {dn.get('scr_out_db',0):.2f} dB | {dn.get('scr_out_db',0):.2f} dB | "
        f"{dn.get('ref_region_db',0):.1f} dB |",
        f"| +0 dB (=RT앵커) | {d0.get('scr_out_db',0):.2f} dB | "
        f"{_row(zero['rows'],0.0).get('scr_out_db',0):.2f} dB | {d0.get('ref_region_db',0):.1f} dB |",
        f"| +40 dB | {d40.get('scr_out_db',0):.2f} dB | "
        f"{_row(zero['rows'],40.0).get('scr_out_db',0):.2f} dB | {d40.get('ref_region_db',0):.1f} dB |",
        "",
        f"> **제로도플러 대조군은 SCR 변동 {zero['scr_span_db']:.0e} dB** — 옛 §3 의 죽은 파라미터를 "
        f"정확히 재현한다. **도플러를 실으면 즉시 SCR span {dop['scr_span_db']:.1f} dB, 그리고 "
        f"ref-region 전력이 {dn.get('ref_region_db',0):.0f}→{d0.get('ref_region_db',0):.0f}→"
        f"{d40.get('ref_region_db',0):.0f} dB 로 정확히 진폭²에 비례해 커진다.** 동일 시드·동일 β 라 "
        "**도플러가 유일한 원인**이다. 즉 \"클러터 진폭은 죽은 파라미터\"는 물리가 아니라 **항등식**이었고, "
        "클러터가 **움직이는 순간 즉사**한다.",
    ))
    out.append(fig("verify_clutter_doppler",
                   "Cold-clutter Doppler spread: SCR/ref-region sweep, notch mechanism, Pd vs speed"))

    out.append(md(
        "### 5.2 그런데 §3 에서 왜 '죽었'었나 — ECA 가 아니라 0-도플러 노치였다",
        "",
        "정직하게 메커니즘을 다시 짚는다. §3 은 \"ECA 가 정지 클러터를 세기와 무관하게 지운다\"고 "
        "했지만, 환경 산란체는 조명원이 방사하는 **전체(파일럿+데이터)** 를 되쏘는데 ECA 의 기저는 "
        "**파일럿뿐**이다. 그래서 이 클러터를 ECA 에 통과시키면:",
        "",
        "| arm | ECA 잔류/입력 | RD 맵 0-도플러 노치(zd±1) 안 전력 |",
        "|---|---|---|",
        f"| 제로도플러 | {mz.get('eca_resid_db',0):+.2f} dB | {mz.get('notch_frac',0)*100:.2f}% |",
        f"| 도플러퍼짐 | {md_.get('eca_resid_db',0):+.2f} dB | {md_.get('notch_frac',0)*100:.2f}% |",
        "",
        f"> ECA 는 두 경우 모두 **{mz.get('eca_resid_db',0):+.1f} dB 밖에 못 지운다**(도플러와 거의 "
        "무관). 그러니 죽음/부활을 가른 건 ECA 사영이 아니다 — 정지 잔류는 RD 맵 0-도플러 능선에 "
        f"**{mz.get('notch_frac',0)*100:.1f}%** 앉고, `det[zd,:]=False` 노치 + 표적셀(fd≠0)에서 "
        "SCR 측정이 그걸 배제한다. **죽인 건 0-도플러 노치**이고, 도플러가 실리면 잔류가 노치 밖으로 "
        f"({md_.get('off_notch_frac',0)*100:.1f}% off-notch) 새어 **되살아난다**. "
        "(⚠ `verify_eca.json` S5 의 파일럿-클러터는 ECA 가 −300 dB 로 지우는 **진짜 span(X) 항등식**으로 "
        "이것과 별개다 — 둘을 같은 것으로 서술하면 안 된다.)",
    ))

    # C4 / C2b
    if c4 and c4.get("rows"):
        rr = c4["rows"]
        r_lo, r_hi = rr[0], rr[-1]
        notgt_all1 = all(r["pd_notarget"] >= 0.99 for r in rr)
        clean_all0 = all(r["pd_notgt_noclut"] <= 0.02 for r in rr)
        out.append(mdl([
            "### 5.3 탐지확률(Pd) — 저속 검출은 표적인가, 움직이는 클러터인가",
            "",
            "SCR 항등식은 죽었다. 그럼 벤치마크의 **탐지확률**도 무너지나? 여기서 함정에 빠지기 쉽다 — "
            "cold 클러터가 있으면 Pd 는 전 속도에서 1.00 으로 보인다. 하지만 그 검출이 **표적**인지 "
            "**클러터**인지 갈라야 한다. 표적 속도(호버 0.2 ~ 3 m/s)마다 세 조건을 돌렸다(전부 MTI 노치 on):",
            "",
            "| 표적속도 | fd/Δfd (클러터밴드 내?) | Pd, 진짜 표적 | Pd, **표적 지움**+클러터 | Pd, 표적·클러터 둘 다 없음 |",
            "|---|---|---|---|---|",
        ] + [
            f"| {r['v_ms']:.1f} m/s | {r['fd_over_dfd']:+.2f} "
            f"({'**IN**' if r['in_clutter_band'] else 'out'}) | {r['pd_bench']:.2f} | "
            f"**{r['pd_notarget']:.2f}** | {r['pd_notgt_noclut']:.2f} |"
            for r in rr
        ] + [
            "",
            f"> **핵심** — 표적을 {abs(c4.get('notarget_db',-80)):.0f} dB 낮춰 **사실상 지워도** "
            + ("전 속도에서 표적셀 CFAR 가 계속 울린다(Pd≈1.00)" if notgt_all1 else
               "저속에서 표적셀 CFAR 가 계속 울린다") +
            ", 그런데 **클러터까지 빼면 즉시 0.00**(마지막 열). 즉 이 검출들은 **표적이 아니라 "
            "움직이는 클러터가 만든 것**이다. 서베이 §V-A4 처방대로 클러터 링이 표적의 바이스태틱 "
            "거리를 bracket 하므로(챔버 거리분해능이 거칠어 4 링이 표적 거리빈 ±1 안에 든다), 도플러가 "
            "실린 클러터가 표적셀을 오염시킨다.",
            "",
            f"> **정직한 H2 답**: \"Pd 가 무너진다\"도 \"Pd 가 버틴다\"도 아니다 — **표적셀의 CFAR "
            "발화가 표적을 인증하지 못한다**(움직이는 클러터가 같은 셀을 울린다). 특히 저속 드론"
            f"(fd < 클러터밴드 ±{c1.get('fd_band_hz',0):.0f} Hz)은 움직이는 클러터와 **분간되지 "
            "않는다** — 서베이의 경고(*'slow-time-only processing is insufficient when dominant "
            "moving objects overlap the Doppler of the ToI'*)가 우리 챔버에서 그대로 재현된다. "
            "이것이 §3 의 \"무해\"를 정면으로 뒤집는다: 정지 클러터는 무해했지만 **움직이는 클러터는 "
            "가짜 검출을 만든다.**",
        ]))

    if cb and cb.get("doppler"):
        out.append(md(
            f"또한 CPI 를 **M=96 으로 늘리면** 도플러 분해능이 {cb.get('dfd_hz',0):.1f} Hz 로 좁아져 "
            f"클러터밴드가 노치의 **{cb.get('fd_band_over_dfd',0):.2f}×빈**(> 1빈)이 되어 노치 밖으로 "
            f"더 새고, SCR span 이 **{cb['doppler']['scr_span_db']:.0f} dB** 로 커진다 — 긴 관측이 "
            "오히려 도플러퍼짐 클러터에 더 취약하다.",
        ))

    if c3 and c3.get("cold_only"):
        co, hi20, hicm = c3["cold_only"], c3.get("cold_hot_inr20", {}), c3.get("cold_hot_cnrmatched", {})
        sr = c3.get("survey_ref", {})
        out.append(md(
            "### 5.4 hot clutter — 외부 비협조 이미터",
            "",
            "cold(우리 클러터)에 더해, 실측 필드에는 우리 신호와 **무상관인 외부 이미터**(다른 AP·gNB)가 "
            "있다 — 서베이가 '절반이 통째로 빠졌다'고 지적한 **hot clutter**다. 독립 OFDM 이미터 1기를 "
            "감시신호에 직접 더해(ECA 영공간 밖, 정합필터 코히어런트 이득 없음) 억제 후 SCR 을 다시 잰다:",
            "",
            "| 조건 | scr_in (pre-ECA, DPI제외) | SCR 후 | Pd |",
            "|---|---|---|---|",
            f"| cold-only | {co['scnr_in_db']:.1f} dB | {co['scr_out_db']:.1f} dB | {co['pd']:.2f} |",
            f"| cold + hot (INR 20 dB) | {hi20.get('scnr_in_db',0):.1f} dB | "
            f"{hi20.get('scr_out_db',0):.1f} dB | {hi20.get('pd',0):.2f} |",
            f"| cold + hot (CNR-matched {c3.get('clutter_to_noise_db',0):.0f} dB) | "
            f"{hicm.get('scnr_in_db',0):.1f} dB | {hicm.get('scr_out_db',0):.1f} dB | {hicm.get('pd',0):.2f} |",
            "",
            f"> 약한 hot(INR 20)은 미미하고, cold 와 **동급 세기**(CNR-matched)면 SCR 이 "
            f"{co['scr_out_db']:.1f}→{hicm.get('scr_out_db',0):.1f} dB 로 열화한다. "
            f"⚠ 서베이 값(cold-only {sr.get('cold_only','?')} → cold+hot {sr.get('cold_hot','?')} → "
            f"Sionna RT site-spec {sr.get('sionna_rt_sitespec','?')} dB)은 **입력 SCNR** 축이라 우리 "
            "pre-ECA·DPI제외 값과 **정확한 apples-to-apples 가 아니다** — hot 기여의 **방향**만 대조한다.",
        ))

    out.append(md(
        "### 5.5 정리 — 이 확장이 §3 에 대해 정정하는 것",
        "",
        "| 주장 | §3(정지만) | §5(도플러퍼짐 추가) |",
        "|---|---|---|",
        "| SCR 이 클러터 진폭에 무반응 | 참(관측) | **거짓 — 항등식이었다.** 움직이면 amp² 로 복귀 |",
        "| 무해의 원인 | \"ECA 가 지운다\" | **0-도플러 노치**(ECA 는 tx-클러터를 ~1.4 dB 만 지움) |",
        "| 클러터는 탐지에 무해 | 참(정지) | **거짓 — 움직이면 표적셀에 가짜 검출**(표적 지워도 Pd≈1, 클러터 빼면 0) |",
        "",
        "> **한 줄**: 클러터 진폭이 죽은 파라미터라는 §3 의 결론은 **정지 가정 하의 항등식**이었다. "
        "도플러 퍼짐을 넣으면 그 항등식은 즉사하고(잔류가 진폭²로 복귀), 더 나아가 **움직이는 클러터는 "
        "표적의 거리·도플러 이웃에 가짜 검출을 만든다** — 특히 저속 드론은 움직이는 클러터와 분간되지 "
        "않는다. **클러터를 정교하게 모델링하는 일은 이제 (움직이는 클러터에 한해) 반드시 필요하다.**",
    ))
    return out


cells += _clutter_doppler_cells(CDOP)

# =========================================================================== #
#  마무리
# =========================================================================== #
cells.append(md(
    "---",
    "# 정리",
    "",
    "반사되는 챔버 바닥은 탐지를 **두 갈래**로 건드린다:",
    "",
    "| 바닥 경로 | 움직이나 | ECA 가 지우나 | 탐지에 미치는 영향 |",
    "|---|---|---|---|",
    "| 가만히 있는 바닥 반사 | ✗ 정지 | ✅ 세기와 무관하게 지운다(구성상 보장) | **이 모델에서는 무해** |",
    f"| 드론 거쳐 바닥에 튄 경로 | ✅ 드론 따라 이동 | ❌ 못 지운다 | **유령 표적**(+{G5['sep_m']:.2f} m, {G5['ghost_db']:.1f} dB) |",
    "",
    f"핵심은, 바닥이 아무리 세게 반사해도 **가만히만 있으면** 필터가 지워 무해하고(단 이건 물리 "
    f"발견이 아니라 이 하네스의 구성상 귀결이다 — §3), 정작 문제는 **드론을 거쳐 움직이는** 바닥 "
    f"경로라는 점이다. 그리고 대역이 넓을수록(5G) 이 유령을 진짜와 별개로 분해해 가짜 표적을 만든다 "
    f"— 궤적 중앙 스냅샷에서 **{G5['p_false']*100:.0f}%**, 궤적 전체 {T5['n']}개 지점 평균 "
    f"**{T5['p_false']*100:.0f}%**(유령의 CFAR 임계 여유 평균 {T5['margin_db']:+.2f} dB; "
    f"⚠ 적분시간이 다른 별도 실행 M={_M_SNAP} vs M={_M_TRAJ}). 광대역의 "
    "정밀함이 그대로 오검출로 되돌아온다. 이 유령을 걸러내는 것은 앞으로의 탐지 설계가 반드시 안고 "
    "가야 할 문제다.",
    "",
    "> **다음 리포트: report10 — 검출기 자체가 눈금이 맞나.** 여기서 유령이 '별개 표적'으로 물리적으로 "
    "분해되는 걸 봤다. 그런데 그걸 검출하는 CFAR 의 문턱(명목 오경보율 = 실제 오경보율)이 맞는지는 "
    "아직 안 봤다. 그게 어긋나면 이 리포트의 유령 검출확률도, 앞으로의 모든 탐지확률도 흔들린다.",
))


def main():
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)",
                                      "language": "python", "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(NB, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"notebook 생성: {os.path.relpath(NB, ROOT)}  ({len(cells)} cells)")


if __name__ == "__main__":
    main()
