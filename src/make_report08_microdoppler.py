# -*- coding: utf-8 -*-
"""
make_report08_microdoppler.py — ⭐**리포트 07 한 편을 네 편으로 쪼갠다** (사용자 지시 2026-08-10)

사용자:
> *"report07_microdoppler 의 전체적인 내용을 **쪼개서 새로운 레포트에** 넣도록 해.
>  이 파일 하나의 크기가 너무 커서 여러 개로 쪼개주면 좋겠어. 예: **08_1, 08_2, 08_3** 이런 식으로"*

왜 쪼개는가 — 크기와 메시지 둘 다
----------------------------------
옛 `report07_microdoppler.ipynb` 는 그림 14 장을 base64 로 박아 **23.4 MB** 였다. 열기도 무겁고,
한 편이 «시나리오 · 엔진 비교 · 무늬의 원인 · 표본화 한계» 네 이야기를 한꺼번에 했다.
⭐크기는 증상이고 원인은 **한 편에 메시지가 넷** 이었다는 것이다. 그래서 메시지 단위로 자른다.

    08_1  무엇을 보고 있나        시나리오·표적·측정모형        애니메이션 · f0 · f0c
    08_2  어떻게 계산하나        세 엔진과 거리                f12 · f8 · f5
    08_3  무엇이 무늬를 정하나    회전수·가림·산포              f1 · f2 · f3 · f4 · f7 · f11 · f13
    08_4  무엇을 잴 수 있나      광선 비용과 반복률            f9 · f10

⚠ 이 스크립트는 `src/make_report07_overview.py` 를 **대체**한다. 옛 빌더는 그대로 두되
  (되돌릴 수 있게) 산출물 `report07_microdoppler.ipynb` 는 더 쓰지 않는다.
⚠ 실행 순서: ① 조각 빌더 12 개 → ② **이 스크립트** → ③ `src/build_volumes.py`
  (build_volumes 가 08_3 뒤에 옛 조각 34~39 를 절로 덧붙인다)

    python src/make_report08_microdoppler.py
"""
from __future__ import annotations

import base64
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

FIG = os.path.join(_ROOT, "outputs", "figures")
OUT = os.path.join(_ROOT, "reports")

# ── 원장 ────────────────────────────────────────────────────────────────────
MDB = json.load(open(f"{_ROOT}/outputs/report15b_microdoppler.json"))
TRI = json.load(open(f"{_ROOT}/outputs/report07_three_engines.json"))
MDP = json.load(open(f"{_ROOT}/outputs/report00_microdoppler.json"))
HOV = json.load(open(f"{_ROOT}/outputs/report07_hover_long.json"))["_meta"]
VERD = json.load(open(f"{_ROOT}/outputs/report15_verdict.json"))
RNGS = json.load(open(f"{_ROOT}/outputs/report07_sionna_ranges.json"))
W5G = json.load(open(f"{_ROOT}/outputs/report07_5g_waveform.json"))


def _opt(path):
    return json.load(open(path)) if os.path.exists(path) else None


HOD_J = _opt(f"{_ROOT}/outputs/report07_hover_long_outdoor.json")
HOD = HOD_J["_meta"] if HOD_J else None
ANIM = _opt(f"{_ROOT}/outputs/report07_anim.json")
_HAS_ANIM = bool(ANIM) and os.path.exists(f"{FIG}/report07_anim.gif")
_HAS_F13 = os.path.exists(f"{FIG}/report07_f13.png")
RBT = _opt(f"{_ROOT}/outputs/report07_ray_budget_test.json")
TRR_J = _opt(f"{_ROOT}/outputs/report07_three_engine_ranges.json")
TRR = TRR_J["ranges"] if TRR_J else None
# ⭐변조 깊이를 p-p 와 p5~p95 두 자로 잰 원장(benchmark/ledger_ptp_robust.py).
#   본문에 손으로 적혀 있던 수치를 이것으로 갈음한다.
DEP = _opt(f"{_ROOT}/outputs/report07_depth_robust.json")

RGM, RGR = RNGS["_meta"], RNGS["ranges"]
WM, WA = W5G["_meta"], W5G["arms"]
LEAD = MDB["cells"]["matrice4e/belly"]
PH, FND = LEAD["physics"], LEAD["findings"]
TM = TRI["_meta"]
R = FND["rpm_spread_makes_it_time_varying"]
V = TRI["verdict"]["cosine_in_ftip"]
CEN = MDP["specular_census"]["total"]
SPREAD = float(MDB["_meta"]["rpm_spread_frac"])
FARFIELD_M = next(r for r in MDP["rows"] if r["drone"] == "matrice4e")["farfield_m"]


def _tail_gap(drone: str) -> float:
    c = VERD["tail_excess"]["by_cell"][f"{drone}/3/nose"]
    return c["sionna_tail"]["mean_db"] - c["po_tail"]["mean_db"]


GAP_MINI2, GAP_M4E = _tail_gap("mini2"), _tail_gap("matrice4e")

# ── 셀 도구 ─────────────────────────────────────────────────────────────────
_SEEN: dict[str, list[str]] = {}
_CUR = [""]


def embed(stem: str, ext: str = "png") -> str:
    _SEEN.setdefault(_CUR[0], []).append(stem)
    with open(os.path.join(FIG, f"{stem}.{ext}"), "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return f"![{stem}](data:image/{ext};base64,{b})"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in "\n".join(lines).split("\n")]}


def write(no: str, slug: str, cells: list) -> None:
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "py312", "language": "python",
                                      "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{no}_{slug}.ipynb")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    mb = os.path.getsize(p) / 1e6
    figs = _SEEN.get(no, [])
    print(f"  ✅ reports/{no}_{slug}.ipynb — 셀 {len(cells):2d} · 그림 {len(figs):2d}장 · "
          f"{mb:5.1f} MB   ({', '.join(figs)})")


NAV = ("> **8 권은 다섯 편이다** — "
       "[08_1 시나리오](08_1_scene.ipynb) · [08_2 세 엔진과 거리](08_2_engines.ipynb) · "
       "[08_3 무늬를 정하는 것](08_3_pattern.ipynb) · [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) · "
       "[08_5 바이스태틱](08_5_bistatic.ipynb)")

LEDGER_NOTE = ("⭐ 숫자는 전부 계산 결과 JSON(원장)에서 주입된다 — 원장이 다시 계산되면 "
               "`python src/make_report08_microdoppler.py` 한 번으로 본문 숫자가 따라 바뀐다.")


# =========================================================================== #
#  08_1 — 무엇을 보고 있나
# =========================================================================== #
def build_08_1():
    _CUR[0] = "08_1"
    c = [
        md("# 리포트 8-1 — 마이크로도플러: 무엇을 보고 있나", "", NAV, "",
           "> **호버링하는 드론은 제자리에 있지만 프로펠러는 돈다.** "
           "그 회전만이 되돌아오는 신호를 흔든다 — 이 편은 그 장면을 먼저 세운다.", "",
           "이 편은 **시나리오와 측정 모형**만 다룬다. 계산 엔진의 비교는 8-2, 무늬를 정하는 "
           "요인들은 8-3, 표본화 한계는 8-4 다.", "", LEDGER_NOTE),

        md("## 표적이 실제로 무엇을 하고 있나", "",
           "" if not _HAS_ANIM else embed("report07_anim", "gif"), "",
           "" if not _HAS_ANIM else
           f"호버링하는 {ANIM['_meta'].get('name', 'DJI Matrice 4E')}. **아래칸이 배치**다 — "
           "붉은 공 하나가 레이더이고, 거기서 3 m 떨어진 곳에 드론이 떠 있다"
           f"(방위 {ANIM['_meta']['az_deg']:.0f}° · 앙각 {ANIM['_meta']['el_deg']:.0f}°, "
           "즉 레이더가 드론을 올려다본다). 공이 하나인 이유는 기선이 0 인 **진짜 모노스태틱**이라 "
           "송신기와 수신기가 같은 점에 있기 때문이다. **위칸**은 그 레이더 시선에서 표적을 "
           "당겨 본 모습이다.", "",
           "" if not _HAS_ANIM else
           "⭐볼 것은 하나다 — **동체는 한 픽셀도 안 움직이는데 프로펠러 넷의 날 방향만 "
           f"프레임마다 바뀐다**(호버 {ANIM['rotors']['rpm_mean']:.0f} rpm, 로터마다 조금씩 "
           "다르고 CW/CCW 가 섞여 있다). 그 바뀌는 부분이 되돌아오는 신호의 위상을 흔들고, "
           "그것이 이 편들이 다루는 마이크로도플러다.", "",
           "" if not _HAS_ANIM else
           f"⚠ 실제 날은 초당 {ANIM['rotors']['rpm_mean']/60:.0f} 바퀴를 돌아 눈으로는 볼 수 없다 — "
           f"이 애니메이션은 프레임 사이 실시간 "
           f"{ANIM['loop']['loop_real_ms']/int(ANIM['loop']['n_frames']):.2f} ms 를 "
           f"{int(ANIM['loop']['frame_delay_ms'])} ms 로 늘여 튼 "
           f"**약 {ANIM['loop']['slowmotion_factor']:.0f} 배 슬로모션**이다"
           f"(프레임당 {ANIM['loop']['blade_deg_per_frame']:.0f}° 회전, "
           f"{ANIM['loop']['n_frames']} 프레임 = 블레이드 {ANIM['loop']['n_periods']} 주기). "
           f"⚠ 로터 간 누적 어긋남이 {ANIM['loop']['seam_mismatch_deg']:.1f}° 뿐이라 "
           "**산포는 여기 안 보인다** — 그 성질은 8-3 이 담당한다."),

        md("## 배치 — 무엇이 어디에 있나", "",
           embed("report07_f0"), "",
           "**공통**: DJI Matrice 4E 한 대가 **제자리 호버링**한다(이동 0, 벌크 도플러 0). "
           "환경은 자유공간이다 — 지면도 벽도 클러터도 잡음도 두지 않았다. "
           "레이더는 기체의 **배 쪽 아래**에서 본다(방위 0°, 앙각 −15°). "
           "지상 레이더가 나는 드론을 보는 각도다.", "",
           "| | |", "|---|---|",
           f"| 기체 | {LEAD['name']} |",
           f"| 자세 | 방위 {LEAD['az_deg']:.0f}° · 앙각 {LEAD['el_deg']:.0f}° (배 쪽) |",
           f"| 반송파 | {TM['fc_hz']/1e9:.2f} GHz (5G n78 대역의 반송파만 빌렸다) |",
           f"| 호버 회전수 | {PH['rpm']:.0f} rpm |",
           f"| 날개끝 도플러 | {PH['f_tip']:.0f} Hz |",
           f"| 블레이드 통과율 | {PH['f_flash']:.1f} Hz (= 플래시 {1000/PH['f_flash']:.1f} ms 마다) |",
           f"| 원거리장 경계 | 2D²/λ = {FARFIELD_M:.1f} m |",
           "",
           "⭐ **측정 모형 — 파형이 아니다.** 이 편들의 신호는 "
           f"h(t) = Σ a_p·exp(−j2πf_c·τ_p) 로, **{TM['fc_hz']/1e9:.2f} GHz 단일 톤(CW)** 의 "
           "채널 응답이다. 5G 파형을 변조해 쏜 것이 아니라 반송파 주파수만 n78 에서 빌렸다. "
           "PRF 는 «채널을 얼마나 자주 재느냐»(슬로타임 표본율)이지 펄스 반복률이 아니다. "
           "실제 5G 파형을 태우면 어떻게 되는지는 **8-4** 가 잰다.", "",
           "⚠ **없는 것을 적어 둔다** — 잡음 0 · 클러터 0 · 지면 0 · 다중경로 0. "
           "즉 이 편들의 수치는 **상한**이고, 현실 성능이 아니다."),

        md("## 경로 렌더 — Sionna 가 실제로 찾은 것", "",
           embed("report07_f0c"), "",
           "**PathSolver 가 실제로 찾은 경로 10개**(TX→RX 직행 1 + 표적 경유 **9개**)가 씬 위에 "
           "겹쳐 그려져 있다. 8-2 의 맵에서 Sionna 무늬가 성긴 이유가 이 그림에 있다 — "
           "경로 열 개 남짓이 그 엔진의 재료 전부다.", "",
           "⭐ 여기서 «경로» 는 광선이 표적을 맞고 돌아온 **한 가닥**이다. 우리 SBR+PO 는 "
           "표적 표면을 λ/12 격자로 덮어 **수십만 점**을 적분하므로 재료의 밀도가 다르다 — "
           "그 차이가 무엇을 만드는지가 8-2 의 주제다."),

        md("## 이 편이 서 있는 자리", "",
           "| 다음 | 무엇을 답하나 |", "|---|---|",
           "| [08_2 세 엔진과 거리](08_2_engines.ipynb) | 같은 장면을 세 가지로 계산하면 무엇이 갈리나 |",
           "| [08_3 무늬를 정하는 것](08_3_pattern.ipynb) | 회전수·가림·산포가 무늬를 어떻게 바꾸나 |",
           "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 광선 비용과 조명원 반복률의 한계 |",
           "",
           "⚠ 이 편은 **모노스태틱**이다. 바이스태틱 기하로 가면 무엇이 달라지는지는 "
           "[08_5 바이스태틱](08_5_bistatic.ipynb) 이 다룬다 — 단 그 편도 **기하만** 다루고 "
           "기준·감시 2채널 처리(ECA·CAF)는 아직 쓰지 않는다."),
    ]
    write("08_1", "scene", c)


# =========================================================================== #
#  08_2 — 어떻게 계산하나
# =========================================================================== #
def build_08_2():
    _CUR[0] = "08_2"
    c = [
        md("# 리포트 8-2 — 마이크로도플러: 세 엔진과 거리", "", NAV, "",
           "> **같은 장면을 세 가지로 계산하면 무엇이 갈리나.** "
           "대조군이 없으면 우리 맵이 틀렸는지 알 방법이 없다.", "",
           "장면은 [08_1](08_1_scene.ipynb) 이 세웠다. 이 편은 **계산 엔진**만 다룬다.", "",
           LEDGER_NOTE),

        md("## 세 엔진이 각각 무엇을 하나", "",
           "| 엔진 | 무엇을 쏘나 | 무엇을 세나 | 무엇이 빠지나 |",
           "|---|---|---|---|",
           "| **Sionna PathSolver** | TX 에서 광선을 뿌린다 | 표적을 맞고 돌아온 **경로**의 "
           "진폭·지연으로 h = Σ a_p·e^(−j2πf_cτ_p) | 경로가 열 개 남짓이라 재료가 성기다. "
           "프롭 정반사 경로는 **0 개**(아래) |",
           "| **Ours (SBR+PO, 기본)** | 표적에 **앵커한** λ/12 격자로 평면파 조명 | 광선이 "
           "**처음 맞은 지점만** 면적분 — |Γ|·(n̂·û)·ΔA·위상 | 가려진 면이 자동으로 빠진다 "
           "(가림이 공짜) |",
           "| **Ours w/o occlusion (대조)** | 광선을 안 쓴다 | 점구름의 **모든 면**을 더한다 "
           "(법선이 등진 면만 제외) | ⚠**아무것도 안 빠진다** — 남의 뒤에 숨은 면도 셈에 든다 |",
           "",
           "⭐ 셋째 열은 **물리적으로 불가능한 상태**다. 오직 «가림이 얼마나 바꾸나» 를 재는 "
           "대조군으로만 쓴다. ⚠«드론 일부만 그린 것» 이 아니다 — 동체도 프로펠러도 다 들어간다.", "",
           "⚠ **둘째와 셋째는 가림 말고 이산화 방식도 다르다**(광선 격자 ↔ 점구름). "
           "그래서 둘의 차이가 «가림만» 의 값은 아니다. 가림만 떼어낸 깨끗한 축은 "
           "`report15b` 의 F(동체 Γ=0 — 막되 산란 안 함) ↔ G(동체 면만 제거, 정점은 남겨 "
           "광선 격자 동일) 이고, 그 실측이 배 쪽에서 최대 −15.96 dB 다."),

        md("## 세 엔진을 같은 격자에, 거리 3 / 8 / 15 m", "",
           "**시나리오** — 같은 기체·자세·주파수·PRF·로터별 회전수로 세 엔진을 돌리고 거기에 "
           f"거리축을 얹었다. {TM['n']} 표본 @ PRF {TM['prf_hz']:.0f} Hz = "
           f"{TM['blade_periods']:.0f} 블레이드 주기, 로터 산포 "
           f"±{TM['rpm_spread_frac']*100:.2f} %(PX4 **SITL**(소프트웨어 시뮬) 중간값 — "
           "⚠실기 계측이 아니다). 기하는 **진짜 모노스태틱**"
           "(TX=RX, 기선 0)이다.", "",
           "" if TRR is None else embed("report07_f12"), "",
           "⭐ **왼쪽 열만 거리마다 다시 풀었다.** 가운데·오른쪽 열은 표적 앵커 평면파 조명이라 "
           "**거리라는 변수 자체가 없고**, 그래서 세 줄에서 같은 맵이 반복된다 — 그 반복이 이 "
           f"그림의 절반이다.", "",
           "⚠ **8 m 가 원거리장 경계 곁이라는 사실은 이 그림에서 아무 역할도 하지 않는다.** "
           "Sionna PathSolver 에는 근/원거리장 구분이 아예 없고(경로의 지연이 2R/c 를 표적 반지름만큼만 "
           "감싼다), 8 m 를 특별하게 만드는 것은 기하가 아니라 **난수 추첨**이다 — 아래 참조.", "",
           "**깊이는 두 자로 잰다** — p-p(max−min)는 자세 하나가 혼자 끌 수 있어서, 양 끝 "
           "5 %를 버린 **p5~p95** 를 함께 낸다. 둘의 **비**가 그 팔의 안정성이다."
           + ("" if DEP is None else
              " 아래 표는 `outputs/report07_depth_robust.json` 을 읽는다."), "",
           "" if DEP is None else "\n".join([
               "| 엔진 | p-p | p5~p95 | 비 | 무늬 |", "|---|---|---|---|---|"] + [
               f"| {nm} | {DEP['engines'][k]['ptp_db']:.1f} dB | "
               f"{DEP['engines'][k]['p5p95_db']:.1f} dB | "
               f"{DEP['engines'][k]['ptp_over_p5p95']:.1f}× | {desc} |"
               for k, nm, desc in [
                   ("sionna", "Sionna PathSolver", "무늬가 성기고 날개끝 근처에서 잦아든다"),
                   ("sbr", "Ours (SBR+PO, 기본)",
                    "⚠능선이 대역을 채우고 날개끝 밖에도 남는다"),
                   ("po", "Ours w/o occlusion", "능선이 몇 가닥에 그친다")]]), "",
           "⚠ **이 표의 깊이를 물리량으로 인용하지 마라.** 같은 Sionna 팔을 거리만 바꿔 "
           "재면 p-p 가 "
           + (" / ".join(f"{DEP['sionna_by_range'][k]['ptp_db']:.1f}"
                         for k in ("R3", "R8", "R15"))
              if DEP and "sionna_by_range" in DEP else "32.6 / 2.5 / 50.1")
           + " dB 로 요동친다(3 / 8 / 15 m). 그 요동은 물리가 아니라 **광선 표본화**다 — "
           "강건한 p5~p95 로 보면 "
           + (" / ".join(f"{DEP['sionna_by_range'][k]['p5p95_db']:.1f}"
                         for k in ("R3", "R8", "R15"))
              if DEP and "sionna_by_range" in DEP else "7.5 / 1.1 / 20.2")
           + " dB 다. ⚠ 그중 **8 m 의 작은 값은 «변조가 얕다» 가 아니라 «플래시가 없다» 는 뜻**이다 — 얼어붙은 정적 받침대가 프롭 변조보다 27.6 dB 높아 깊이가 눌린 것이다(위 참조). ⚠ 그리고 **«자세 하나가 전폭을 혼자 정한다» 는 과장이었다** — 최솟값 "
           "자세를 빼고 다시 재도 3 m 는 "
           + (f"{DEP['sionna_by_range']['R3']['ptp_db_drop1']:.1f}"
              if DEP and "sionna_by_range" in DEP else "27.1")
           + " dB, 15 m 는 "
           + (f"{DEP['sionna_by_range']['R15']['ptp_db_drop1']:.1f}"
              if DEP and "sionna_by_range" in DEP else "45.1")
           + " dB 가 남는다. 이상치 **하나**가 아니라 **꼬리가 두꺼운 것**이다.", "",
           f"⭐ 셋 다 **(a) 0 도플러 동체 선 · (b) 통과율 간격 능선 · (c) 날개끝 근처 감쇠**를 "
           f"낸다 — 구조가 일치한다. 날개끝 안 스펙트럼 코사인은 "
           f"Sionna↔SBR+PO **{V['sionna_vs_sbr']:.3f}** · Sionna↔w/o occ **{V['sionna_vs_po']:.3f}** · "
           f"기본↔대조 **{V['sbr_vs_po']:.3f}** 다.", "",
           "⚠ **코사인 세 자리를 그대로 인용하지 마라 — 격자에 딸려 움직인다.** 같은 두 팔을 "
           "다른 광선 격자로 다시 재니 기본↔대조가 0.44 에서 0.29 로 내려갔다. 즉 이 수는 "
           "«두 무늬가 얼마나 닮았나» 의 절대 척도가 아니라 **이 실행에서의 순서**(Sionna 는 "
           "우리 기본팔과 가장 닮았고, 우리 두 팔끼리가 가장 덜 닮았다)만 말한다. "
           "절대값이 필요하면 격자 사다리를 먼저 태워야 한다.", "",
           "" if TRR is None else "\n".join([
               "| 거리 | 광선 수 | 자세당 경로(중앙값) | 경로 0 자세 | 평균 레벨 |",
               "|---|---|---|---|---|"] + [
               f"| {TRR[k]['range_m']:.0f} m | {TRR[k]['spp']/1e6:.1f}M | "
               f"{TRR[k]['paths_median']:.0f} | {TRR[k]['paths_zero_frac']:.1%} | "
               f"{TRR[k]['level_db']:.1f} dB |" for k in ("R3", "R8", "R15")]),
           "",
           "⚠⚠ **이 표의 경로 수와 레벨은 물리량이 아니라 «추첨 한 장» 이다.** Sionna 는 확산 경로를 "
           "몬테카를로로 **발견**하는데, 이 스윕은 자세 4,096 개를 전부 같은 시드로 풀었다. 드론에서 "
           "움직이는 것은 로터뿐이라 동체·랜딩기어의 경로 집합이 전 자세에서 **비트 단위로 동일**하고"
           "(정적 성분의 유일값이 1 개), 그래서 207 ms 기록 전체가 추첨 한 번을 받침대로 깔고 있다. "
           "자세를 4,096 개 평균해도 그 추첨은 평균되지 않는다.", "",
           "⭐ 기하·자세·광선 수를 **하나도 안 바꾸고 시드만** 바꾼 실측(8 m, 512 자세): "
           "레벨이 −118.0 / −136.0 / −121.4 dB 로 **18 dB** 흔들리고, 최강선이 3.018 / 1.006 / 0.999 "
           "·f_flash 로 바뀐다. 즉 «8 m 만 3 배 조화» 도 «레벨이 안 떨어진다» 도 **거리의 성질이 아니라 "
           "이 시드의 성질**이다. 세 거리를 모두 같은 광선 수(25M)로 다시 풀면 최강선이 "
           "0.976 / 0.998 / 0.991 ·f_flash 로 셋 다 기본파에 꽂힌다.", "",
           "⚠ 그리고 이 팔의 절대 레벨은 **광선 수에 수렴하지 않는다**. 우리가 재는 것은 "
           "h = Σ a_p e^(−j2πf_c τ_p) 인데, Sionna 는 확산 경로 진폭을 **전력 합**이 광선 수와 무관하도록 "
           "정규화한다. 그것을 코히어런트로 더하면 광선을 늘릴수록 값이 커진다 — 실측 기울기 +0.52~+0.69 "
           "(√spp), 반면 Σ|a_p|² 의 기울기는 −0.02 로 평평하다. 거리마다 다른 광선 수를 준 이 표는 "
           "거리마다 다른 부풀림을 섞고 있다.", "",
           "⇒ **이 표에서 인용해도 되는 것은 «빈 자세 0 %» 뿐이다**(그것은 시드에 둔감하다). "
           "원장: `outputs/probe_8m_anomaly.json`."),

        md("## 블레이드 플래시를 세 엔진으로 나란히 (60 ms 확대)", "",
           "**시나리오** — 위와 **같은 원장·같은 슬로타임 격자·같은 로터 회전수**에서 60 ms 만 "
           "잘라 확대했다. 세 패널의 차이는 **산란 엔진뿐**이다. 조각은 블레이드 한 주기의 "
           "0.45 배라 플래시가 시간평균으로 지워지지 않는다.", "",
           embed("report07_f8"), "",
           f"⭐ 세로 아치가 블레이드 플래시이고 **{1000/TM['f_flash_hz']:.1f} ms 마다** 반복한다"
           f"(= f_flash {TM['f_flash_hz']:.0f} Hz). 세 엔진이 그 주기를 같이 낸다는 것이 "
           "이 그림의 첫 확인이다. 모양은 갈린다 — 가림을 켠 우리 기본팔은 아치가 굵고 도플러축으로 "
           "넓게 퍼지고, 가림을 끈 대조군은 좁고 또렷한 점처럼 떨어지며, Sionna 는 아치라기보다 "
           "얼룩에 가깝다.", "",
           f"⭐ **Sionna 가 왜 얼룩인가** — 프로펠러를 맞은 **정반사 경로가 0 개**다. "
           f"자세×위상 격자 {CEN['n_cells']} 칸 전수에서 정반사가 잡힌 칸이 "
           f"{CEN['n_with_specular']} 칸인데 그중 **프롭 정반사는 "
           f"{CEN['n_with_prop_specular']} 칸**이다(광선 2.56 억 발, 앙각 0~60°). "
           "남은 것은 확산 산란뿐이라 아치가 뭉개진다.", "",
           "⚠⚠ **이 «0» 은 아직 예산 사다리를 안 태웠다.** 2.56 억은 이 프로젝트가 쓰는 광선 "
           "사다리의 **맨 아랫칸**이고, 같은 사다리의 윗칸은 40.96 억(16 배)이다. "
           "우리는 바로 이번 주에 «40 m 는 PathSolver 의 구조적 한계» 라고 적었다가 "
           "예산을 올리니 빈 자세가 77.3 % → 0 % 로 사라지는 것을 봤다 — 같은 함정이다. "
           "⇒ 지금 정직하게 말할 수 있는 것은 «**이 예산에서는** 프롭 정반사가 안 잡힌다» "
           "까지다. 윗칸 인구조사를 큐에 넣어 두었고, 결과가 나오면 이 절을 고친다. "
           "⚠ 앙각도 60° 까지만이다 — 프롭 법선이 향하는 더 가파른 쪽은 이 격자 밖이다.", "",
           "⭐ **시간 분해능을 주파수 분해능보다 앞세운다.** 조각을 한 주기보다 길게 잡으면 "
           "플래시는 그 안에서 평균돼 사라지고 가로 능선만 남는다. 그래서 조각을 "
           "**한 주기보다 짧게**(0.45 주기) 잡는다.", "",
           "⚠ 예전 판은 여기에 «플래시 대비» 라는 지표의 표를 붙여 0.45 가 최대라고 적었다. "
           "**그 표는 내렸다** — 독립 재구현에서 재현되지 않았고(같은 지표를 다시 재니 0.60 이 "
           "더 컸다), 지표의 정의가 산문 한 줄뿐이라 사람마다 다르게 잰다. 원장 JSON 도 없다. "
           "0.45 는 **그림이 실제로 또렷해서** 유지하는 값이지 측정으로 증명된 최적점이 아니다. "
           "지금 인용해도 되는 것은 정의가 하나뿐인 양뿐이다 — 조각 "
           f"{round(0.45*TM['prf_hz']/TM['f_flash_hz'])} 표본 · "
           f"Δt {0.45/TM['f_flash_hz']*1e3:.2f} ms · "
           f"Δf {TM['f_flash_hz']/0.45:.0f} Hz.", "",
           "⚠ 세 패널은 각자 최대로 정규화했다 — 이 그림은 **구조를 비교하지 레벨을 비교하지 않는다**.", "",
           "⚠⚠ **레벨을 «Sionna 가 60 dB 아래» 라고 읽으면 안 된다.** 두 팔이 내는 양의 **단위가 "
           "다르다** — Sionna 는 1/R² 를 두 번 먹은 **수신 전력장**을 주고, 우리 커널은 표적의 "
           "**산란 진폭**[m²]을 준다. 3 m 에서 그 환산항만 −20log₁₀(4πR²) = **−41.1 dB** 다. "
           "실측 격차 −59.9 dB 에서 환산을 빼면 남는 것은 **약 −19 dB** 이고, 그것이 «프롭 정반사 "
           "경로가 0 개» 로 설명해야 할 몫이다. 단위가 다른 두 수를 빼서 얻은 «60 dB» 를 "
           "물리량으로 인용하지 마라."),

        md("## 두 엔진이 날개끝 아래에서 겹치고 위에서 갈린다", "",
           embed("report07_f2"), "",
           f"1 차원 스펙트럼으로 보면 두 엔진이 **날개끝 주파수 아래에서 겹치고 위에서 갈린다**. "
           f"Sionna 꼬리가 순수 PO 대비 **{GAP_M4E:.1f} dB**(matrice4e) · "
           f"**{GAP_MINI2:.1f} dB**(mini2) 높다.", "",
           "⚠ **이 그림만 자세가 다르다** — 08_1 의 배 쪽(el −15)이 아니라 nose(el +15)다. "
           "원장이 2026-08-04 판이라 그렇다. 무늬 세부를 위 맵들과 직접 견주면 안 된다."),

        md("## 이 편이 서 있는 자리", "",
           "세 엔진이 **같은 주기**를 내고 **모양이 갈린다**. 그 갈림의 원인은 가림과 경로 수다.", "",
           "| 다음 | 무엇을 답하나 |", "|---|---|",
           "| [08_3 무늬를 정하는 것](08_3_pattern.ipynb) | 회전수·가림·산포가 무늬를 어떻게 바꾸나 |",
           "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 이 계산을 얼마나 멀리·얼마나 자주 할 수 있나 |",
           "| `reports/09_microdoppler-limits.ipynb` | 자세·보정·광선 예산의 단일축 분해 |"),
    ]
    write("08_2", "engines", c)


# =========================================================================== #
#  08_3 — 무엇이 무늬를 정하나
# =========================================================================== #
def build_08_3():
    _CUR[0] = "08_3"
    c = [
        md("# 리포트 8-3 — 마이크로도플러: 무엇이 무늬를 정하나", "", NAV, "",
           "> **회전수·가림·산포 세 가지가 무늬를 정한다.** 각각을 갈라서 얼마나 바꾸는지 잰다.", "",
           "엔진 비교는 [08_2](08_2_engines.ipynb) 가 했다. 이 편은 **표적 쪽 요인**만 다룬다.", "",
           LEDGER_NOTE),

        md("## 회전수가 같으면 무늬가 시간에 안 변한다", "",
           embed("report07_f1"), "",
           f"왼쪽은 네 로터를 **같은 회전수**로 돌린 것이다. 줄무늬가 시간축 내내 같은 자리에 선다 — "
           f"창을 반으로 갈라 두 스펙트럼의 상관을 재면 **{R['locked_half_corr']:.4f}** 다. "
           "우연이 아니라 원리다: 네 로터가 같은 속도로 돌면 신호가 완전한 주기함수가 되고, "
           "주기함수의 스펙트로그램은 창 내내 자기 모습을 지킨다.", "",
           f"오른쪽은 로터마다 회전수를 **±{SPREAD*100:.2f} %** 흩뜨린 것이다 — 추측이 아니라 "
           "**PX4 SITL**(소프트웨어 인더루프 = 시뮬) 로그에서 모터 간 0.07~0.29 % 를 재서 "
           "고른 중간값이다. ⚠**실기 텔레메트리가 아니다** — 아래 «로터 산포 프리셋 비교» 가 "
           "실기 비행로그 세 종으로 이 값이 야외 호버를 한 자릿수 과소평가함을 보인다. "
           "이 그림에서 ±0.22 % 는 «산포가 무늬를 시간에 변하게 한다» 를 보이는 **하한 예시**다. "
           f"상관이 **{R['spread_half_corr']:.4f}** 로 내려가고(낙차 {R['drop']:.4f}) 줄이 "
           "숨쉬듯 흔들린다. ⭐그 내려감이 «시간에 따라 변한다» 의 정량이다."),

        md("## 동체가 막으면 무엇이 달라지나", "",
           embed("report07_f4"), "",
           f"가림 단일축(F↔G)의 실측이다 — 광선 엔진·재질·기하·운동학·**광선 격자**까지 같고 "
           "오직 «동체가 막느냐» 만 다르다. "
           f"레벨은 {FND['occlusion_level_db']:+.2f} dB, 변조 깊이는 "
           f"{FND['occlusion_ptp_db']:+.2f} dB 움직인다.", "",
           "⚠ 합이 코히런트라 **가림이 레벨을 올릴 수도 있다** — 항이 줄어도 남은 항끼리 상쇄가 "
           "덜 되면 그렇다. 부호를 물리로 단정하지 말 것."),

        md("## 블레이드는 강하고 동체가 덮는다", "",
           embed("report07_f3"), "",
           "⭐ 이 편들의 핵심 발견 하나 — **블레이드 신호가 약한 게 아니라 동체가 덮고 있다.** "
           "전체 드론으로 재면 변조가 2.84 dB p-p 인데, 프로펠러 채널만 떼면 32.32 dB p-p 다"
           "(3.5 GHz, el −15°). 열 배 넘게 차이 난다.", "",
           "⚠ 이 그림의 수치는 원장 JSON 이 아니라 **빌더에 기록된 2026-08-07 실측값**이다 — "
           "원장으로 승격하는 일이 남아 있다(부록 이력 표)."),

        md("## 2 초 호버링 — 능선과 로터 회전수", "",
           embed("report07_f7"), "",
           f"{HOV['seconds']:.0f} 초 · {HOV['n']:,} 표본 · {HOV['blade_periods']:.0f} 블레이드 주기. "
           "아래 패널이 네 로터의 회전수다 — 능선이 어떻게 움직이는지의 원인이 거기 있다.", "",
           f"⭐ 로터별 산포는 **{HOV['static_spread']:.2%}** 다. 로터들이 이만큼 가까운 속도로 "
           "돌기 때문에 네 빗살이 고조파마다 정렬되고 능선이 가늘게 선다.", "",
           f"⚠ 제어루프 흔들림(±{HOV['wobble_amp']:.2%} @ {HOV['wobble_hz']:.1f} Hz)은 "
           "**선언된 가정**이다 — 우리 표적의 실측 비행 로그가 그 자리를 채운다."),
    ]
    if HOD is not None:
        c.append(md(
            "## 로터 산포 프리셋 비교: 실내-이상 하한 vs 야외 앵커", "",
            "**시나리오** — 위와 완전히 같은 계산(같은 기체·자세·2 초·SBR 팔)이고, 바꾼 것은 "
            f"**로터 산포 프리셋 하나**다. 왼쪽이 실내-이상(±{HOV['static_spread']:.2%}), "
            f"오른쪽이 **야외 프리셋**(±{HOD['static_spread']:.0%} · 흔들림 "
            f"±{HOD['wobble_amp']:.1%} @ {HOD['wobble_hz']:.1f} Hz)이다.", "",
            "⭐ 야외 프리셋의 출처는 **논문이 아니라 공개 비행로그 데이터셋 세 종**이다 — "
            "우리가 직접 내려받아 호버 구간을 잘라 재서 얻은 값이다.", "",
            "| 데이터셋 | 기체·환경 | 신호 | 정적 산포(중앙) | 흔들림 |",
            "|---|---|---|---|---|",
            "| NeuroBEM (UZH RPG) | 레이싱 쿼드 · **실내** 무풍 | 모터별 실측 회전수 400 Hz | 0.54 % | 0.74 % @ 0.7~2.2 Hz |",
            "| PX4 · CODEV AQUILA V3 | 상용 대형 쿼드 · **야외** | ESC 실측 rpm 4 Hz | 2.35 % | 2.52 % @ ~0.74 Hz |",
            "| DJI Phantom 3 DAT | ⭐**진짜 DJI** · 야외 | 모터 PWM **명령** 50 Hz | 5.8 %(PWM) | 5.3 %(PWM) |",
            "",
            "⚠ 세 줄 다 한계가 분명하다. 앞의 둘은 **DJI 가 아니고**, CODEV 는 표본율 4 Hz 라 "
            "2 Hz 초과가 접혀 진폭이 과대측정일 수 있다. 셋째만 진짜 DJI 인데 **실측 rpm 이 아니라 "
            "PWM 명령**이다. 그래서 야외 프리셋 ±2 % 는 **세 줄을 합쳐 반올림한 자릿수 앵커**이지 "
            "우리 표적의 실측이 아니다.", "",
            embed("report07_f11"), "",
            "⭐ 읽는 법 — 왼쪽은 로터들이 거의 같은 속도라 고조파 빗살이 정렬된다. 오른쪽은 "
            "로터별 f_tip 이 수십 Hz 씩 갈라져 능선이 **얽힌 뱀처럼** 교차한다. "
            "⭐⭐그런데 **세로 플래시 아치는 양쪽 다 남는다** — 산포는 능선(주파수축 구조)을 "
            "뭉개지만 플래시(시간축 사건)는 못 지운다. 시간 분해능을 우선하는 표시 규약이 "
            "야외에서 더 중요해지는 물리적 이유가 이것이다."))
    if _HAS_F13:
        c.append(md(
            "## 그 «야외 앵커» 를 눈으로: 공개 비행로그 세 종의 실측", "",
            "위 표의 근거를 그림으로 본다. 곡선과 상자는 인용이 아니라 **그 로그를 직접 열어 "
            "우리가 잰 값**이다. 세 로그에서 호버 구간(|v| < 0.3 m/s)을 전부 뽑아 같은 규약으로 쟀다.", "",
            embed("report07_f13"), "",
            "윗줄은 데이터셋마다 호버 창 하나를 골라 모터 넷을 겹쳐 그린 것이고, 아랫줄은 "
            "**찾아낸 모든 호버 창**의 산포·흔들림 분포에 우리 두 프리셋을 가로선으로 얹은 것이다. "
            "⭐야외선이 PX4 야외 상자를 관통하고 실내선은 NeuroBEM 상자 **아래**에 놓인다.", "",
            "⭐ 세 독립 원천이 **같은 방향**을 가리킨다 — SITL 유래 ±0.22 % 는 실기체 야외 호버를 "
            "한 자릿수 과소평가한다. 우리 표적(Mavic 4 Pro·Matrice 4E)의 실측 rpm 로그는 여전히 "
            "없고(Mavic Air 이후 DJI DAT 은 암호화), 그 구멍은 X410 필드테스트로만 닫힌다."))
    c.append(md(
        "## 이 편이 서 있는 자리", "",
        "무늬를 정하는 것은 **회전수의 균일함 · 동체의 가림 · 로터 산포** 셋이다.", "",
        "| 다음 | 무엇을 답하나 |", "|---|---|",
        "| [08_4 무엇을 잴 수 있나](08_4_sampling.ipynb) | 광선 비용과 조명원 반복률 |",
        "| `reports/09_microdoppler-limits.ipynb` | 자세·보정·광선 예산의 단일축 분해 |",
        "| `reports/10_illuminators.ipynb` | 조명원별로 무엇을 쓸 수 있나 |"))
    write("08_3", "pattern", c)


# =========================================================================== #
#  08_4 — 무엇을 잴 수 있나
# =========================================================================== #
def build_08_4():
    _CUR[0] = "08_4"
    c = [
        md("# 리포트 8-4 — 마이크로도플러: 무엇을 잴 수 있나", "", NAV, "",
           "> **두 가지가 잴 수 있는 것을 제한한다 — 광선 비용과 조명원 반복률.** "
           "앞의 것은 우리가 감당하는 문제이고, 뒤의 것은 우리가 못 정하는 조건이다.", "",
           LEDGER_NOTE),

        md("## 거리 — 벽인가 예산인가", "",
           "**시나리오** — 진짜 모노스태틱(TX=RX, 기선 0), 배 쪽(방위 0·앙각 −15), "
           f"{RGM['fc_hz']/1e9:.1f} GHz CW. 표적을 3 → 10 → 20 → 40 m 로 물리며 자세당 "
           "발견 경로 수를 셌다.", "",
           embed("report07_f9"), "",
           "⚠ **정직 정정** — 처음에 «40 m 에서 자세의 78 % 가 경로 0 이니 PathSolver 의 "
           "구조적 한계» 라고 적었다. **그것은 틀렸다.** 그 스윕의 광선 예산이 규칙값 "
           "(R/3)² 의 1.00 / 0.72 / 0.36 / **0.18배**였기 때문이다.", "",
           "" if RBT is None else "⭐ 그래서 **결판 시험**을 했다 — 40 m 를 고정하고 자세·기하·"
           "회전수를 그대로 둔 채 **광선만** 사다리로 올렸다.", "",
           "" if RBT is None else "\n".join([
               "| 40 m 광선 | 경로 중앙 | 경로 평균 | 빈 자세 |", "|---|---|---|---|"] + [
               f"| {k} | {v['paths_median']:.0f} | {v['paths_mean']:.2f} | {v['zero_frac']:.1%} |"
               for k, v in RBT["ladder"].items()]), "",
           "" if RBT is None else
           f"⭐ **판정 — {RBT['_meta']['verdict_ko']}** 규칙값의 절반도 안 되는 지점에서 이미 "
           "빈 자세가 사라진다.", "",
           "⭐ **그러면 무엇이 남는가 — 비용이다.** 거리가 두 배면 광선을 네 배 부어야 같은 경로 "
           "수를 얻는다. 40 m 규칙값이 178M 이면 100 m 에서는 그 여섯 배가 필요하고, 자세를 "
           "수천 개 쌓는 마이크로도플러에서는 그 곱이 감당 밖으로 간다. "
           "반면 우리 SBR+PO 는 광선 격자를 **표적에 앵커**(λ/12 간격)한 평면파 조명이라, "
           f"원거리장 경계({FARFIELD_M:.1f} m) 밖에서는 무늬가 거리에 **불변**이고 수신 레벨만 "
           "1/R² 로 내려간다 — 즉 **한 번 계산하면 거리에 무관**하다.", "",
           "⭐ 그러므로 원거리 마이크로도플러를 SBR+PO 가 맡는 이유는 «PathSolver 가 못 해서» 가 "
           "아니라 **«비용이 거리와 함께 터지기 때문»** 이다."),

        md("## 같은 채널에 5G 파형을 실제로 태우면", "",
           "**시나리오** — 채널은 08_3 의 2 초 호버링 h(t) **그대로**다(같은 원장). 바꾼 것은 "
           f"파형뿐이다: 5G NR 형 OFDM — SCS {WM['scs_hz']/1e3:.0f} kHz(n78) · "
           f"유효 부반송파 {WM['n_sc']:,}개 · 심볼마다 무작위 QPSK · "
           f"심볼율 {WM['sym_rate_hz']/1e3:.0f}k sym/s. 수신은 기지 심볼 나눗셈으로 심볼마다 "
           "채널 ĥ 을 꺼낸다. 네 팔은 **«채널을 얼마나 자주 읽나»(반복률)만** 다르다.", "",
           embed("report07_f10"), "",
           "| 팔 | 표본율 | 나이퀴스트 | 날개끝 ±1229 Hz | 플래시 127 Hz |",
           "|---|---|---|---|---|",
           "\n".join(
               f"| {WA[k]['label']} | {WA[k]['fs_hz']:g} Hz | ±{WA[k]['nyquist_hz']:g} Hz | "
               f"{'⚠접힘' if WA[k]['ftip_folds'] else '보임'} | "
               f"{'⚠접힘' if WA[k]['fflash_folds'] else '보임'} |"
               for k in ("cw_5k", "nr_full_28k", "nr_crs_1k", "nr_ssb_50")),
           "",
           "⭐ 이것이 **5G 이중고**의 그림판이다 — 패시브가 기댈 상시 신호 기준으로, LTE CRS 급 "
           "1 kHz 는 날개끝이 나이퀴스트 500 Hz 안으로 **접혀** 들어오고, 5G SSB 급 50 Hz 는 "
           "**플래시선마저** 접힌다. 관측 창이 ±25 Hz, 속도로는 ±1.07 m/s 뿐인데 날개끝은 "
           "초당 52.7 m 로 움직인다.", "",
           "⭐ **네 패널은 축이 완전히 같다.** 그래서 낮은 반복률의 대가가 **빈 자리**로 보인다 — "
           "회색으로 덮은 영역은 «조용함» 이 아니라 **그 표본율로는 측정 자체가 불가능한 영역**이다.", "",
           f"⚠ **이 수치가 무엇을 재는지 정확히 적는다.** «풀캡처 ≡ CW» 의 "
           f"{WM['full_capture_max_rel_err']:.1e} 는 **OFDM 수신 사슬이 채널을 정확히 되돌려주는가**"
           "를 잰 것이다. 평탄-채널 근사 아래에서 그 사슬은 항등식이므로 이 값이 작은 것은 "
           "**구현이 맞다는 확인**이지, 5G 와 CW 가 같은 물리를 본다는 **독립 검증이 아니다**. "
           "⭐이 그림의 진짜 내용은 오른쪽 두 팔, 즉 **반복률**에 있다.", "",
           "⚠ 정직 한계 둘 — 5 kHz 채널열을 28 kHz 로 다상 보간했고(대역제한 가드 "
           f"{WM['bandlimit_guard_energy']:.1e}), 심볼 안에서 채널이 도는 ICI 를 1차 근사로 재면 "
           f"바닥이 {WM['ici_floor_db_first_order']:.1f} dB 인데 채널 모형에는 넣지 않았다."),

        md("## 부록 — 그림별 데이터 이력", "",
           "그림마다 딛고 선 원장과 그 시점이 다르다. ⭐**원장의 PRF 가 다르면 시간 분해능도 "
           "다르다** — 그래서 그림마다 선명도가 갈릴 수 있다.", "",
           "| 그림 | 편 | 원장 | 생성 | PRF |", "|---|---|---|---|---|",
           f"| 애니메이션 · f0 · f0c | 08_1 | 렌더(수치 없음) | 2026-08-10 | — |",
           f"| f12 · f8 · f2 | 08_2 | `report07_three_engines.json` | "
           f"{TM['generated'][:16]} | {TM['prf_hz']:.0f} Hz |",
           f"| f1 · f4 · f3 | 08_3 | `report15b_microdoppler.json` | "
           f"{MDB['_meta']['generated'][:16]} | {PH['prf']:.0f} Hz |",
           f"| f7 | 08_3 | `report07_hover_long.json` | {HOV['generated'][:16]} | "
           f"{HOV['prf_hz']:.0f} Hz |",
           ("" if HOD is None else
            f"| f11 | 08_3 | `report07_hover_long_outdoor.json` | {HOD['generated'][:16]} | "
            f"{HOD['prf_hz']:.0f} Hz |"),
           ("" if not _HAS_F13 else
            "| f13 | 08_3 | `rotor_log_traces.json` (공개 비행로그) | 2026-08-10 | 로그 원본 |"),
           f"| f9 | 08_4 | `report07_ray_budget_test.json` + `report07_sionna_ranges.json` | "
           f"{RGM['generated'][:16]} | {RGM['prf_hz']:.0f} Hz |",
           f"| f10 | 08_4 | `report07_5g_waveform.json` | {WM['generated'][:16]} | 팔마다 다름 |",
           "",
           "**표시 규약**(전 그림 공통) — 조각 = 블레이드 **0.45 주기**(실측 최적) · hop 2 · "
           "제로패딩 8 배 · Hann · gouraud · jet · 색역 0~−40 dB · 0 도플러 안 지움 · "
           "도플러축 ±1.9·f_tip. 정본은 `src/md_mapstyle.py` 다.", "",
           "**재현**", "", "```bash",
           "# 원장 재계산(GPU)",
           "PYTHONPATH=src python benchmark/report07_three_engine_maps.py --n 4096   # SIONNA2_MD_PRF_MULT=16",
           "PYTHONPATH=src python benchmark/report07_hover_long.py --sec 2.0",
           "PYTHONPATH=src python benchmark/report15b_microdoppler_recompute.py",
           "PYTHONPATH=src python benchmark/report07_ray_budget_test.py",
           "# 그림",
           "PYTHONPATH=src python benchmark/build_three_engine_ranges_fig.py",
           "PYTHONPATH=src python benchmark/build_flash_zoom.py",
           "PYTHONPATH=src python benchmark/build_range_sweep_fig.py",
           "PYTHONPATH=src python benchmark/build_5g_fig.py",
           "# 이 네 편",
           "PYTHONPATH=src python src/make_report08_microdoppler.py",
           "```"),
    ]
    write("08_4", "sampling", c)


if __name__ == "__main__":
    print("── 8 권(마이크로도플러) 네 편 빌드 ──")
    build_08_1()
    build_08_2()
    build_08_3()
    build_08_4()
    print("✅ reports/08_1~08_4")
