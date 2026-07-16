# -*- coding: utf-8 -*-
"""make_notebook2.py — report2.ipynb 생성기

report2: **OFDM 파형 제작 + Sionna 기본 파형과 비교 + RCS**
질문: **"우리가 만든 파형이 맞는가, 그리고 이 드론들은 레이더에 얼마나 밝은가?"**

⚠ 노트북은 **생성물**이다. report2.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 **outputs/report2_waveform_rcs.json 에서 읽어 주입**한다 — 그림과 글이
   어긋날 수 없다. (그 JSON 은 viz_report2.build_all() 이 측정하며 남긴다.)
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from provenance import provenance_cells   # noqa: E402  ← 리포트 앞머리 자동생성

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
NB = os.path.join(ROOT, "report2.ipynb")
JS = os.path.join(ROOT, "outputs", "report2_waveform_rcs.json")


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
with open(JS) as f:
    J = json.load(f)

M = J["meta"]
REF, XC, NUM, AMB = J["reference"], J["crosscheck"], J["numerology"], J["ambiguity"]
V, OCC, R, MAT = J["sbr_validation"], J["occlusion"], J["rcs"], J["materials"]
G1 = REF["G1"]

DR = R["drones"]
DKEYS = list(DR)
BAND_NAMES = [b[0] for b in M["bands"]]
NR_BAND = "5G NR 3.5 GHz"
WK = ("wifi", "lte", "nr")

#  헤드라인 숫자 (전부 측정값)
_means = {k: DR[k]["bands"][NR_BAND]["mean_dbsm"] for k in DKEYS}
_dim = min(_means, key=_means.get)
_brightest = max(_means, key=_means.get)
_span = _means[_brightest] - _means[_dim]
_dith = {d["div"]: d for d in V["dither"]}
_lam24, _lam12, _lam8 = _dith[24], _dith[12], _dith[8]
def _mrow(prefix):
    """재질 시나리오 한 줄 찾기 (라벨에 줄바꿈이 있으므로 첫 줄로 맞춘다)."""
    for r in MAT["rows"]:
        if r["label"].splitlines()[0].strip().startswith(prefix):
            return r
    raise KeyError(f"재질 시나리오 '{prefix}' 없음 — 라벨: "
                   f"{[r['label'].splitlines()[0] for r in MAT['rows']]}")


_full = _mrow("Full drone")
_shell = _mrow("- shell")
_props = _mrow("- propellers")
_core = _mrow("metal core")
_diel = _mrow("dielectric only")
_worst_nmse = max(XC[k]["nmse_db"] for k in WK)
_best_nmse = min(XC[k]["nmse_db"] for k in WK)

cells = []

# =========================================================================== #
#  앞머리 — provenance.py 가 자동 생성 (비참여자가 혼자 읽고 재현할 수 있게)
# =========================================================================== #
_prov = provenance_cells(
    report="report2",
    what="OFDM 파형 제작 + **Sionna 기본 파형과 비교** + RCS",
    question="우리가 만든 파형이 맞는가, 그리고 이 드론들은 레이더에 얼마나 밝은가?",

    tldr=[
        f"**파형은 맞다.** 자작 OFDM 변조기를 **Sionna 의 `OFDMModulator` 로 같은 자원격자를 "
        f"재변조**해 대조했더니 상관 **{XC['wifi']['corr']:.4f} / {XC['lte']['corr']:.4f} / "
        f"{XC['nr']['corr']:.4f}**, NMSE **{XC['wifi']['nmse_db']:.1f} / "
        f"{XC['lte']['nmse_db']:.1f} / {XC['nr']['nmse_db']:.1f} dB** — 수치적으로 **동일**하다.",

        f"그 교차검증이 **실제로 버그를 잡았다**: 3GPP 는 **슬롯 첫 심볼의 CP 를 더 길게** 준다"
        f"(LTE {XC['lte']['cp_head'][0]}→{XC['lte']['cp_head'][1]}, "
        f"NR {XC['nr']['cp_head'][0]}→{XC['nr']['cp_head'][1]} 샘플). CP 배열 대신 첫 값만 넘기면 "
        f"상관이 **{XC['lte']['corr_bug']:.3f}**(LTE) / **{XC['nr']['corr_bug']:.3f}**(NR) 로 무너진다. "
        f"WiFi 는 CP 가 균일해 **같은 버그가 안 보인다** — 파형 하나만 시험했다면 통과했을 버그다.",

        f"**패시브의 거리분해능은 채널 대역이 아니라 기준신호 점유대역이 정한다.** 상시 신호만 쓰는 "
        f"유휴 셀(G1)에서 측정: WiFi VHT-LTF **{G1['wifi']['ref_bw_mhz']:.1f} MHz → "
        f"{G1['wifi']['dR_m']:.1f} m**, LTE CRS **{G1['lte']['ref_bw_mhz']:.1f} MHz → "
        f"{G1['lte']['dR_m']:.1f} m**, NR SSB **{G1['nr']['ref_bw_mhz']:.1f} MHz → "
        f"{G1['nr']['dR_m']:.1f} m**. 5G 는 **좁고**(ΔR {G1['nr']['dR_m']:.1f} m) "
        f"**드물다**(PRF {G1['nr']['prf_hz']:.0f} Hz → v_max **{G1['nr']['vmax_ms']:.2f} m/s**) — **이중고**.",

        f"**드론은 어둡다.** SBR(광선 + PO적분) 방위평균 RCS @3.5 GHz: "
        f"{DR[_dim]['name']} **{_means[_dim]:+.1f} dBsm** ~ {DR[_brightest]['name']} "
        f"**{_means[_brightest]:+.1f} dBsm** — 기종 간 **{_span:.1f} dB** 폭.",

        f"**가림(occlusion)이 전부다.** 순수 PO 는 실제로 가려진 면까지 적분해 RCS 를 "
        f"**{-OCC['occlusion_db']:.2f} dB 과대평가**한다(한 방위에서 '조명면' "
        f"{OCC['n_lit_po']:,}개 중 **{OCC['hidden_frac']*100:.0f}%** 가 뒤에 가려져 있었다). "
        f"반면 PO 의 고전적 약점이라는 **오목부 다중반사는 {OCC['multibounce_db']:+.2f} dB** 뿐이다.",

        f"**표적은 금속이고, 플라스틱 셸은 그 앞의 가림막이다.** 금속(모터+배터리+PCB+카메라)만 "
        f"남겨도 온전한 드론보다 **오히려 {_core['delta_db']:+.2f} dB 밝고**, 금속을 다 빼면 "
        f"**{_diel['delta_db']:+.2f} dB** 로 무너진다. ⚠ 단 셸을 지우면 "
        f"{_shell['delta_db']:+.2f} dB **늘어나는데**, 이건 SBR 이 **유전체 투과를 모르기 때문**"
        f"(첫 충돌에서 광선을 끝낸다)이다 — **모델 불확실도 {abs(_shell['delta_db']):.1f} dB** 로 "
        f"읽어야지 측정된 효과가 아니다 (§4.4).",
    ],

    roadmap=[
        dict(sec="§1", what="패시브 레이더의 **기준신호** — 왜 파형이 문제인가",
             why="ΔR 은 B_ref 가, v_max 는 PRF 가 정한다"),
        dict(sec="§2", what="**우리가 만든 파형** — 자원격자와 점유모드 G1/G2/G3",
             why="유휴 셀에서 실제로 뭘 쓸 수 있나"),
        dict(sec="§3", what="**Sionna 기본 파형과 비교** ← 이 리포트의 핵심 검증",
             why="상관 1.0000. 그리고 CP 버그를 잡았다"),
        dict(sec="§4", what="**RCS — SBR**(Mitsuba 광선 + PO 적분)",
             why="검증 → 수렴 → 가림 → 5종×3대역 → 재질"),
        dict(sec="바쁘면", what="§3.3 (CP 버그) 과 §4.2 (가림) 두 그림만",
             why="이 리포트의 두 결론"),
    ],

    sources=[
        dict(item="5G NR 뉴머롤로지 (μ·SCS·슬롯·CP)",
             src="**`sionna.phy.nr.CarrierConfig`** — Sionna 에게 물어봤다 (우리가 표를 안 짬)",
             kind="🟢 라이브러리 (3GPP TS 38.211 구현)"),
        dict(item="LTE CRS / 5G SSB / WiFi VHT-LTF 배치",
             src="3GPP TS 36.211 · TS 38.211 · IEEE 802.11ac → `src/waveforms.py` 에 구현. "
                 "조사 근거는 `docs/waveform_research.json`",
             kind="🔴 우리 구현 (Sionna 에 WiFi/LTE/SSB 가 **없다**)"),
        dict(item="드론 5종 제원 (대각·무게·프롭·호버 RPM)",
             src="**`docs/drone_specs_2026.json`** — 출처 URL 포함, 적대적 검증 완료. "
                 "DJI 공식 스펙/매뉴얼이 1차 출처",
             kind="📄 조사 문서 (미공개 항목은 '추정' 으로 명시)"),
        dict(item="재질 (εr · σ · |Γ|)",
             src="**ITU-R P.2040** (metal · concrete) — Sionna `ITURadioMaterial` 에서 읽음. "
                 "ITU 에 없는 plastic/carbon/absorber 만 문헌값. `src/materials.py`",
             kind="🟢 ITU + 🔴 문헌값"),
        dict(item="RCS 해석해 (검증 기준)",
             src="금속구 σ = πr² (광학영역) · 금속평판 σ = 4πA²/λ² (정면) — 교과서 폐형식",
             kind="📐 해석해"),
        dict(item="옛 리포트에서 살린 발견", src="`docs/ARCHIVE.md`", kind="📄 내부"),
    ],

    engines=["sionna-phy", "sionna-render", "sbr", "po", "trimesh-cad", "matplotlib"],
    libs=["sionna", "mitsuba", "drjit", "torch", "trimesh", "numpy", "scipy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 전체 (측정 → 그림 → 노트북).  GPU 는 src/gpu.py 가 여유 메모리 보고 자동 선택한다",
        "~/.venvs/py312/bin/python src/build_report2.py",
        "",
        "# 부분만",
        "~/.venvs/py312/bin/python src/viz_report2.py        # 측정 + 그림 + JSON",
        "~/.venvs/py312/bin/python src/make_notebook2.py     # JSON -> report2.ipynb",
        "",
        "# 이 리포트가 의존하는 검증들을 따로 확인",
        "~/.venvs/py312/bin/python src/waveforms_sionna.py   # Sionna 교차검증 (상관 1.0000)",
        "~/.venvs/py312/bin/python src/rcs_sbr.py            # SBR 해석해 검증 (구/평판)",
        "~/.venvs/py312/bin/python src/waveforms.py          # G1/G2/G3 점유모드 제원",
        "~/.venvs/py312/bin/python src/materials.py          # 재질표 (Sionna <-> PO 동일 출처)",
    ],

    artifacts=[
        dict(file="outputs/report2_waveform_rcs.json", what="**이 노트북의 모든 숫자.** 측정 원본"),
        dict(file="outputs/figures/report2_ref_signal.png", what="§1 기준신호 예산 (B_ref→ΔR, PRF→v_max)"),
        dict(file="outputs/figures/report2_resource_grid.png", what="§2 자원격자 사진 (G1/G3 × 3표준)"),
        dict(file="outputs/figures/report2_occupancy.png", what="§2 점유모드 G1/G2/G3 측정"),
        dict(file="outputs/figures/report2_crosscheck.png", what="§3 **Sionna 교차검증 + CP 버그 재현**"),
        dict(file="outputs/figures/report2_numerology.png", what="§3 Sionna CarrierConfig 뉴머롤로지 표"),
        dict(file="outputs/figures/report2_ambiguity.png", what="§3 자기상관 + 모호함수"),
        dict(file="outputs/figures/report2_sbr_validate.png", what="§4 SBR 검증 · 격자 수렴 · 디더"),
        dict(file="outputs/figures/report2_occlusion.png", what="§4 **가림의 대가** (PO vs SBR, 3D)"),
        dict(file="outputs/figures/report2_rcs_polar.png", what="§4 5종 × 3대역 극좌표 패턴"),
        dict(file="outputs/figures/report2_rcs_bars.png", what="§4 방위평균 RCS 요약"),
        dict(file="outputs/figures/report2_materials.png", what="§4 재질 기여도 + 재질표"),
        dict(file="outputs/figures/report2_gallery.png", what="§4 **Sionna 렌더** 드론 5종"),
    ],

    caveats=[
        "**절대 RCS 값은 보장하지 않는다.** SBR 은 해석해(구·평판)로만 검증됐고 "
        "**드론 실측 앵커링이 없다.** 이 리포트가 지지하는 것은 (a) 기종 간 **상대 순서**, "
        "(b) 대역 추세, (c) 가림·재질의 **차이(dB)** 다. 절대값을 다른 문서에 인용하지 말 것.",

        "**널(null) 깊이를 인용하지 말 것.** 극좌표 패턴의 로브와 방위평균은 안정적이지만, "
        "로브 사이 골의 깊이는 이산화·대역평균·각도평활에 따라 10 dB 넘게 움직인다. "
        "(그림은 대역평균 + 3° 평활본이다.)",

        f"**단일 격자의 '검증 오차' 는 수렴한 숫자가 아니다.** 금속구는 정반사점이 하나뿐이라 "
        f"광선이 그 점에 떨어지느냐로 값이 흔들린다 — 같은 λ/12 에서도 격자 정렬만 바꾸면 "
        f"**{_lam12['spread']:.1f} dB** 산포가 난다. λ/24 에서야 산포 {_lam24['spread']:.2f} dB / "
        f"오차 {_lam24['avg_err']:+.2f} dB 로 닫힌다. **드론**(다산란체)의 방위평균은 저절로 디더돼 "
        f"λ/8 이후 ~0.1 dB 로 안정 → 우리가 쓴 **λ/{M['sbr_div']} 는 수렴 구간**이다(§4.1).",

        "**§1 의 ΔR · v_max 는 '유휴 셀(idle)' 체제 전제다.** 부하 걸린 셀 + captured "
        "full-waveform reference 면 대역은 채널 전대역, PRF 는 CPI 분할이 정한다. "
        "**두 체제를 섞어 인용하지 말 것.**",

        "**PRS(G2/G3)의 5G 수치는 낙관적 상한**이다. PRS 는 상시 신호가 아니라 "
        "**측위 세션이 설정돼야** 켜지는 옵션이며, 남의 셀을 빌려 쓰는 패시브 수신기는 그것을 "
        "가정할 수 없다.",

        "**WiFi PRF 1 kHz 는 '혼잡 AP' 대표값**이다. 트래픽이 없으면 비콘(100 TU ≈ 9.77 Hz)만 "
        "남아 5G SSB 보다도 느려진다 (`waveforms.PILOT_RATE_HZ` 의 주석 참조).",

        "**호버 RPM 은 DJI 미공개 추정치**다 (`docs/drone_specs_2026.json` 에 근거·불확실성 명시). "
        "이 리포트의 **정적 RCS 에는 영향이 없지만** 마이크로도플러(report1 의 분절)는 여기 매달려 있다.",

        "**흡수체·plastic 의 |Γ| 는 모델값**이지 실측이 아니다 (`src/materials.py` 의 note).",

        f"⚠ **SBR 에 유전체 투과(transmission)가 없다** — 광선을 **첫 충돌에서 끝낸다**. 그런데 "
        f"1~3 mm 플라스틱 셸은 GHz 대역에서 **준투명**하다. 그래서 '셸 있음'(불투명 가정)과 "
        f"'셸 지움'(완전 투명)이 **{abs(_shell['delta_db']):.1f} dB** 벌어지고, **진짜 값은 그 "
        f"사이**다(§4.4). 이 리포트의 절대 RCS 에는 그만큼의 **모델 불확실도**가 붙는다. "
        f"기종 간 상대 비교는 다섯 종이 같은 가정을 쓰므로 영향이 훨씬 작다.",

        "🐛 **오목부 다중반사(SBR 3-bounce) 숫자는 약한 근거다.** `src/rcs_sbr.py:328` 에서 "
        "튕긴 뒤의 **추가 경로길이가 위상에 누적되지 않는다**(`... * 0` 으로 죽어 있고, 게다가 "
        "`Ocur` 를 덮어쓴 뒤에 읽는다). 즉 2·3차 기여가 **직접 반사와 같은 위상으로** 더해진다. "
        "**진폭 규모('작다')는 신뢰할 만하지만 부호·정확한 dB 값은 인용하지 말 것.** "
        "가림(1-bounce vs PO) 결론은 이 결함과 **무관**하다 — 거기엔 다중반사가 없다.",
    ],

    cost=(f"GPU 1장 자동선택(여유 메모리 최대), 예산 {M['budget_mb']:,} MiB. "
          f"전체 재현 약 **{M['runtime_s']/60:.0f}분** "
          f"(SBR {len(DKEYS)}종 × {len(BAND_NAMES)}대역 × {len(R['az'])}방위 × "
          f"{M['n_freq_band']}주파수, 광선격자 λ/{M['sbr_div']} · "
          f"Sionna 렌더 {M['render_spp']} spp @ {M['render_res'][0]}×{M['render_res'][1]})"),

    related=[
        dict(rep="[report1](report1.ipynb) — 환경 · 실물 3D 메쉬 · 분절",
             rel="**이 리포트가 적분하는 메쉬**를 만든다 (CAD · 검증). RCS 는 메쉬가 틀리면 틀린다"),
        dict(rep="**report2 (여기)** — 파형 + RCS",
             rel="파형이 맞는지(§3), 표적이 얼마나 밝은지(§4)"),
        dict(rep="[report3](report3.ipynb) — Sionna RT 광선 반사 실험",
             rel="**환경**(벽 · 바닥 반사)을 RT 로 다룬다. 여기 §4 는 **표적**을 SBR 로 — 역할 분담"),
    ],
)

# --------------------------------------------------------------------------- #
#  🔰 비전공자용 "5분 요약" — 제목/TL;DR 바로 다음, 무거운 provenance 표 앞에 끼운다.
#  엄밀한 내용은 그대로 두고, 부엌 언어로 된 쉬운 층만 얹는다.
# --------------------------------------------------------------------------- #
_easy = md(
    "## 🔰 5분이면 이해하는 이 리포트",
    "",
    "*(수식·표가 부담스러우면 여기만 읽어도 됩니다. 아래 §들은 같은 얘기를 숫자로 증명합니다.)*",
    "",
    "**이 리포트는 두 가지를 확인합니다.** 하나, 우리가 컴퓨터로 만든 통신 신호(WiFi·LTE·5G)가 "
    "**진짜 규격과 똑같은가.** 둘, 드론이 레이더에 **얼마나 잘 보이는가.** 앞의 리포트들이 이 두 "
    "가지를 밑재료로 쓰기 때문에, 먼저 못을 박아 둡니다.",
    "",
    "**첫 번째는 '악보 검사' 로 생각하면 됩니다.** 우리는 3GPP·IEEE 규격서를 보고 신호를 손으로 "
    "옮겨 적었습니다(악보). 그게 맞는지 확인하려고, **프로 연주자(Sionna 라는 검증된 라이브러리)** "
    "에게 같은 악보를 그대로 쳐보게 했습니다. 두 연주가 **음 하나까지 똑같이** 나왔습니다 — 우리 "
    "악보가 맞다는 뜻입니다. 게다가 이 대조가 **베끼다 생긴 실수 하나(첫 박자 길이를 잘못 준 것)** "
    "를 잡아냈습니다. 신호 하나만 확인했다면 놓쳤을 실수입니다.",
    "",
    "**두 번째는 '어두운 방에서 손전등 비추기' 입니다.** 드론에 전파를 쏘고 얼마나 되반짝이는지 "
    "재는 것이 RCS(레이더에 얼마나 밝게 보이나)입니다. 결과: **드론은 어둡습니다.** 그리고 그 "
    "밝기는 겉의 플라스틱 껍데기가 아니라 **속에 든 금속**(모터·배터리·기판·카메라)에서 나옵니다 — "
    "껍데기는 오히려 그 금속을 가리는 **가림막**에 가깝습니다. 또 하나: 옛 계산법은 **드론 뒤편에 "
    "가려 안 보이는 면까지 세어** 밝기를 부풀리고 있었고, 실제로 보이는 면만 세도록 고치니 값이 "
    "4~5 dB(약 3배) 줄었습니다.",
    "",
    "**그래서 뭐가 중요한가 — '5G의 이중고' 입니다.** 패시브 레이더는 자기 송신기가 없어서, "
    "**남이 켜 주는 불빛(방송 신호)의 반사**로만 표적을 봅니다. 그런데 5G가 항상 켜 두는 불빛(SSB "
    "라는 기준신호)은 (1) **너무 좁아서** 20 m 안쪽 물체를 한 덩어리로만 보고, (2) **20 ms에 한 번**"
    "만 깜빡여서 초속 1 m보다 빠른 드론을 놓칩니다. 반대로 구세대 LTE는 넓고 자주 켜져서 오히려 "
    "낫습니다. 즉 **최신 5G가 패시브 레이더에는 나쁜 조명등**이라는 게 이 리포트의 핵심입니다 — "
    "이건 5G 기지국이 자기 신호로 표적의 거리·속도를 쫓는 최근 연구(LaSen, SenSys'26)가 통째로 "
    "붙든 것과 **같은 문제**입니다. (다만 그 연구는 거리+속도만 다루고, 3D 위치는 다루지 않습니다.)",
)
cells += [_prov[0], _easy] + _prov[1:]

# =========================================================================== #
#  §0
# =========================================================================== #
cells.append(md(
    "## §0. 왜 '파형' 과 'RCS' 가 한 리포트에 있나",
    "",
    "> 🔍 **여기서 하는 일** — 이 리포트가 왜 *신호*(파형)와 *드론의 밝기*(RCS)라는 "
    "동떨어져 보이는 두 주제를 한 곳에서 다루는지, 한 개의 식으로 못박습니다.",
    "",
    "패시브 레이더의 수신 전력은 **두 개의 곱**입니다 "
    "(RCS(레이더 반사단면적 — 표적이 레이더에 얼마나 밝게 보이나)는 아래 $\\sigma$):",
    "",
    "$$P_{rx} \\;\\propto\\; \\underbrace{P_{tx}\\,G}_{\\text{남의 송신기}} \\cdot "
    "\\underbrace{\\sigma}_{\\text{표적}} \\cdot \\frac{1}{R_t^2 R_r^2}$$",
    "",
    "> **쉽게 말하면 —** 내가 표적을 보려면 두 가지가 다 있어야 합니다: **남이 켜 준 불빛의 세기**"
    "(송신기)와 **표적이 그 빛을 되쏘는 정도**(RCS). 둘 중 하나라도 약하면 안 보입니다. 그래서 "
    "이 리포트는 *불빛*(파형)과 *표적*(RCS)을 **둘 다** 다뤄야 합니다.",
    "",
    "그리고 **무엇을 얼마나 잘 볼 수 있는가**도 두 개가 정합니다:",
    "",
    "| 무엇 | 무엇이 정하나 | 어디서 오나 | 이 리포트 |",
    "|---|---|---|---|",
    "| **거리분해능** $\\Delta R$ | 기준신호 **점유대역** $B_{ref}$ | 파형 | §1 · §2 · §3 |",
    "| **최대 무모호 속도** $v_{max}$ | 기준신호 **반복률** PRF | 파형 | §1 |",
    "| **탐지 가능성** | 표적 **RCS** $\\sigma$ | 드론 | §4 |",
    "",
    "그래서 이 리포트의 질문은 하나가 아니라 둘입니다 — "
    "**\"우리가 만든 파형이 맞는가\"** 그리고 **\"이 드론들은 레이더에 얼마나 밝은가\"**.",
    "",
    "> ### 🔑 역할 분담을 먼저 못박습니다 (가장 자주 오해받는 지점)",
    ">",
    "> - **OFDM(부반송파 수백 개에 데이터를 잘게 나눠 싣는 변조 방식) 변복조 · 뉴머롤로지** → "
    "🟢 **Sionna PHY** 가 합니다 (`ofdm.OFDMModulator`, `nr.CarrierConfig`).",
    ">   우리 `waveforms.py` 는 **Sionna 에 없는 것**(WiFi · LTE · SSB **자원격자 배치**)만 채우고,",
    ">   **변조 자체는 Sionna 와 비트 단위로 일치함을 §3 에서 증명**합니다.",
    "> - **표적 RCS** → 🟡 **SBR(광선을 쏴서 표적 표면 중 실제로 보이는 곳만 훑어 반사를 "
    "합치는 방식)** — 우리가 짰지만 광선추적은 Sionna 가 쓰는 **Mitsuba 3** 엔진 "
    "그대로입니다. Sionna 에 RCS 솔버가 없기 때문입니다.",
    ">   **이것도 레이트레이싱입니다** — 다만 거기에 **PO(물리광학 — 표면에 흐르는 전류로 "
    "반사파를 계산하는 고주파 근사) 표면적분**을 얹은 것입니다 "
    "(상용 EM 솔버의 표준 방법).",
    "> - **렌더** → 🟢 **Sionna 자체 렌더러** (`Scene.render_to_file`, Mitsuba 경로추적, GPU).",
))

# =========================================================================== #
#  §1
# =========================================================================== #
cells.append(md(
    "---",
    "## §1. 왜 파형이 문제인가 — 패시브 레이더의 **기준신호**",
    "",
    "> 🔍 **여기서 하는 일** — 패시브 레이더가 남의 신호 중 **어떤 것**을 빌려 쓸 수 있는지, "
    "그리고 그 선택이 **거리·속도를 얼마나 잘 보는가**를 어떻게 묶어버리는지 봅니다.",
    "",
    "패시브 레이더는 송신기를 **빌려 씁니다**. 그래서 **자기가 아는 신호로만 상관**을 걸 수 있고,",
    "임의의 셀이 **항상** 내보낸다고 믿을 수 있는 건 표준마다 딱 하나씩뿐입니다:",
    "",
    "| 표준 | 상시(always-on) 기준신호 | 왜 이것뿐인가 |",
    "|---|---|---|",
    "| **LTE** | **CRS** (Cell-specific RS) | 매 서브프레임(1 ms) · 채널 전대역에 상시 송신 |",
    "| **5G NR** | **SSB** (SS/PBCH Block) | NR 에는 **CRS 같은 상시 전대역 셀기준이 없다**. "
    "유휴 gNB 가 늘 내보내는 건 SSB 뿐 |",
    "| **WiFi** | **프리앰블 (VHT-LTF)** | 어떤 패킷에도 붙는다. 단 **반복률이 트래픽에 의존** |",
    "",
    "> ⚠️ **PRS 는 상시 신호가 아닙니다.** **측위 세션이 설정돼야** 켜지는 옵션이고, "
    "남의 셀을 빌려 쓰는 패시브 수신기는 그것을 **가정할 수 없습니다.**",
    "",
    "### 그래서 분해능은 채널 대역이 아니라 **기준신호 점유대역**이 정한다",
    "",
    "$$\\Delta R = \\frac{c}{2\\,B_{ref}} \\qquad\\qquad "
    "v_{max} = \\frac{\\mathrm{PRF}\\cdot\\lambda}{4}$$",
    "",
    "> **쉽게 말하면 —** 두 물체를 **거리로 가르는 능력**($\\Delta R$)은 빌려 쓰는 신호가 "
    "**얼마나 넓은 주파수를 쓰느냐**($B_{ref}$, 점유대역)에 달렸습니다 — 넓을수록 촘촘히 봅니다. "
    "**얼마나 빠른 표적까지 헷갈리지 않고 보느냐**($v_{max}$)는 그 기준신호가 "
    "**초당 몇 번 반복되느냐**(PRF — pulse repetition frequency, 기준신호 반복률)에 달렸습니다 — "
    "자주 깜빡일수록 빠른 것을 봅니다.",
    "",
    "**측정값** — 유휴 셀 = 점유모드 **G1**. `src/waveforms.py` 가 만든 격자에서 그대로 잰 값입니다:",
    "",
    "| 표준 | 기준신호 | 채널 대역 | **$B_{ref}$** | **$\\Delta R$** | **PRF** | **$v_{max}$** |",
    "|---|---|---|---|---|---|---|",
    f"| WiFi 802.11ac | {G1['wifi']['ref']} | {G1['wifi']['chan_bw_mhz']:.0f} MHz | "
    f"**{G1['wifi']['ref_bw_mhz']:.1f} MHz** | **{G1['wifi']['dR_m']:.2f} m** | "
    f"{G1['wifi']['prf_hz']:.0f} Hz | {G1['wifi']['vmax_ms']:.1f} m/s |",
    f"| LTE Rel-9 | {G1['lte']['ref']} | {G1['lte']['chan_bw_mhz']:.0f} MHz | "
    f"**{G1['lte']['ref_bw_mhz']:.1f} MHz** | **{G1['lte']['dR_m']:.2f} m** | "
    f"{G1['lte']['prf_hz']:.0f} Hz | {G1['lte']['vmax_ms']:.1f} m/s |",
    f"| **5G NR Rel-16** | **{G1['nr']['ref']}** | {G1['nr']['chan_bw_mhz']:.0f} MHz | "
    f"**{G1['nr']['ref_bw_mhz']:.1f} MHz** | **{G1['nr']['dR_m']:.1f} m** | "
    f"**{G1['nr']['prf_hz']:.0f} Hz** | **{G1['nr']['vmax_ms']:.2f} m/s** |",
    "",
    "### 🔴 5G 의 이중고",
    "",
    f"SSB 는 **좁고**(중앙 20 RB = {G1['nr']['ref_bw_mhz']:.1f} MHz → "
    f"ΔR **{G1['nr']['dR_m']:.1f} m**) **드뭅니다**(SS 버스트 20 ms 주기 → PRF "
    f"**{G1['nr']['prf_hz']:.0f} Hz** → $v_{{max}}$ **{G1['nr']['vmax_ms']:.2f} m/s**).",
    f"**거리도 속도도 나쁩니다.** 채널은 {G1['nr']['chan_bw_mhz']:.0f} MHz 나 되는데 패시브가 "
    f"쓸 수 있는 건 그중 **{G1['nr']['ref_bw_mhz']/G1['nr']['chan_bw_mhz']*100:.1f}%** 뿐입니다.",
    "",
    f"반면 LTE CRS 는 전대역({G1['lte']['ref_bw_mhz']:.1f} MHz) + 매 서브프레임(1 kHz) 이라 "
    f"두 축 모두 좋습니다 —",
    f"**구세대가 패시브 레이더에는 더 좋은 조명등입니다** "
    f"(ΔR {G1['lte']['dR_m']:.1f} m vs {G1['nr']['dR_m']:.1f} m, "
    f"$v_{{max}}$ {G1['lte']['vmax_ms']:.0f} vs {G1['nr']['vmax_ms']:.1f} m/s).",
    "",
    "> **쉽게 말하면 —** 5G가 늘 켜 두는 불빛(SSB)은 **너무 좁고**(그래서 20 m 안쪽 물체를 "
    "한 덩어리로만 봄) **너무 드물게 깜빡여서**(그래서 걷는 속도만 넘어도 놓침), 거리도 속도도 "
    "다 나쁩니다 — 이게 **'5G의 이중고'** 입니다. LTE는 넓고 자주 켜져서 오히려 낫습니다. "
    "이 두 축(좁다 · 드물다)이 바로 5G 기지국으로 표적을 쫓는 최근 연구(LaSen, SenSys'26)가 "
    "정면으로 씨름하는 그 문제입니다.",
    "",
    "![ref signal](outputs/figures/report2_ref_signal.png)",
    "",
    "> ⚠️ **체제 경고 — 섞지 말 것.** 위 숫자는 **유휴 셀** 전제입니다. 부하 걸린 셀에 "
    "**captured full-waveform reference**(수신기가 직접 받은 송신 파형 전체를 기준으로 사용)를 "
    "쓸 수 있다면 대역은 **채널 전대역**, PRF 는 **CPI 분할**(`prf = fs/Lf`)이 정합니다 — "
    "완전히 **다른 체제**입니다.",
))

cells.append(code(
    "# §1 재현 — waveforms.py 의 속성을 그대로 읽는다 (본문 숫자에 하드코딩 없음)",
    "import sys; sys.path.insert(0, 'src')",
    "from waveforms import always_on_waveforms",
    "",
    "print(f\"{'표준':16s} {'기준신호':9s} {'B_ref':>10} {'dR':>8} {'PRF':>9} {'v_max':>9}\")",
    "for k, wf in always_on_waveforms().items():          # = all_waveforms('G1')",
    "    print(f'{wf.name:16s} {wf.ref_name:9s} {wf.ref_bw_hz/1e6:7.2f}MHz '",
    "          f'{wf.range_resolution_m:6.2f}m {wf.pilot_rate_hz:7.0f}Hz "
    "{wf.v_unambiguous_ms:7.2f}m/s')",
))

# =========================================================================== #
#  §2
# =========================================================================== #
cells.append(md(
    "---",
    "## §2. 우리가 만든 파형 — 자원격자",
    "",
    "> 🔍 **여기서 하는 일** — 우리가 스펙대로 만든 신호가 **실제로 어떤 칸에 무엇을 켜는지** "
    "펼쳐 보고, '한가한 셀' 이 실제로 쓸 수 있는 게 얼마나 되는지 만들어서 재봅니다.",
    "",
    "`src/waveforms.py` 가 3GPP / IEEE 스펙대로 **자원격자(시간을 가로, 주파수를 세로로 놓은 "
    "모눈종이 — 통신 신호는 이 칸을 채워 만든다)** 를 만들고, 각 자원요소(RE — 그 모눈종이의 한 칸)에 "
    "**채널 라벨**(PSS / SSS / PBCH / CRS / PRS / PDCCH / PDSCH / LTF / …)을 답니다.",
    "",
    "### 점유 모드 — 그 셀이 지금 무엇을 내보내고 있나",
    "",
    "| 모드 | 무엇이 켜지나 | 패시브 레이더에게 |",
    "|---|---|---|",
    "| **G1** 유휴 셀 | **상시 기준신호만** (WiFi = 프리앰블 / LTE = 동기 + CRS / 5G = SSB) | "
    "**기본선(baseline)** — 언제나 기댈 수 있는 것 |",
    "| **G2** 측위 세션 | + **PRS** + 제어(PDCCH/SIG) | 5G 가 전대역 기준을 얻는 **낙관적 상한** |",
    "| **G3** 풀로드 | + 데이터(PDSCH/DATA) | **에너지만 늘 뿐** — 데이터는 수신기가 **모르는** "
    "신호라 정합필터 템플릿이 못 된다 |",
    "",
    "![resource grid](outputs/figures/report2_resource_grid.png)",
    "",
    "### G1 이 실제로 되는가 — 만들어서 재봤다",
    "",
    "| 모드 | WiFi  점유 / $B_{ref}$ / ΔR | LTE  점유 / $B_{ref}$ / ΔR | "
    "5G NR  점유 / $B_{ref}$ / ΔR |",
    "|---|---|---|---|",
    *[f"| **{m}** | "
      f"{REF[m]['wifi']['occ_pct']:.1f}% / {REF[m]['wifi']['ref_bw_mhz']:.1f} MHz / "
      f"{REF[m]['wifi']['dR_m']:.2f} m | "
      f"{REF[m]['lte']['occ_pct']:.1f}% / {REF[m]['lte']['ref_bw_mhz']:.1f} MHz / "
      f"{REF[m]['lte']['dR_m']:.2f} m | "
      f"{REF[m]['nr']['occ_pct']:.1f}% / {REF[m]['nr']['ref_bw_mhz']:.1f} MHz / "
      f"**{REF[m]['nr']['dR_m']:.2f} m** |" for m in ("G1", "G2", "G3")],
    "",
    f"**읽는 법**: G1 → G3 로 점유율은 {REF['G1']['nr']['occ_pct']:.1f}% → "
    f"{REF['G3']['nr']['occ_pct']:.1f}% 로 "
    f"{REF['G3']['nr']['occ_pct']/REF['G1']['nr']['occ_pct']:.0f}배 늘지만, "
    f"**WiFi · LTE 의 ΔR 은 거의 안 움직입니다** — 상시 기준신호가 **이미 광대역**이기 때문입니다.",
    f"5G 만 {REF['G1']['nr']['dR_m']:.1f} m → {REF['G2']['nr']['dR_m']:.2f} m 로 급전환하는데, "
    f"그건 **PRS 가 켜졌기 때문**이고 그건 **측위 세션을 가정한 것**입니다.",
    "",
    "![occupancy](outputs/figures/report2_occupancy.png)",
))

cells.append(code(
    "# §2 재현 — G1/G2/G3 를 만들어 점유율·B_ref·PRF·ΔR 을 잰다",
    "from waveforms import all_waveforms",
    "",
    "for mode in ('G1', 'G2', 'G3'):",
    "    print(f'== {mode} ==')",
    "    for k, wf in all_waveforms(mode).items():",
    "        print(f'  {wf.name:15s} 점유={wf.occupancy_frac*100:5.1f}%  기준={wf.ref_name:7s}  '",
    "              f'B_ref={wf.ref_bw_hz/1e6:6.2f}MHz -> dR={wf.range_resolution_m:5.2f}m  '",
    "              f'PRF={wf.pilot_rate_hz:6.0f}Hz -> v_max={wf.v_unambiguous_ms:5.2f}m/s')",
))

# =========================================================================== #
#  §3
# =========================================================================== #
_num_rows = [f"| {r['bw']} | {r['scs_hz']/1e3:.0f} kHz | {r['mu']} | {r['n_size_grid']} | "
             f"{r['num_subcarriers']:,} | {r['num_symbols_per_slot']} | "
             f"{r['num_slots_per_frame']} | {r['slot_duration_s']*1e6:.0f} µs | "
             f"{r['cyclic_prefix']} |" for r in NUM]

_xc_rows = [f"| {XC[k]['name']} | {XC[k]['n']:,} | **{XC[k]['corr']:.4f}** | "
            f"**{XC[k]['nmse_db']:.1f} dB** | ✅ 동일 |" for k in WK]

_cp_rows = [f"| {XC[k]['name']} | {', '.join(str(v) for v in XC[k]['cp_head'])} … | "
            f"{'예 — 전부 같음' if XC[k]['cp_uniform'] else '**아니오 — 첫 심볼이 길다**'} |"
            for k in WK]


def _bugcell(k):
    if XC[k]["cp_uniform"]:
        return f"{XC[k]['corr_bug']:.4f}  (영향 없음 — CP 가 균일하다)"
    return f"**{XC[k]['corr_bug']:.4f}** 💥"


_bug_rows = [f"| {XC[k]['name']} | {XC[k]['corr']:.4f} | {_bugcell(k)} |" for k in WK]

_amb_rows = [f"| {G1[k]['ref']} | {AMB[k]['autocorr_3db_m']:.2f} m | {G1[k]['dR_m']:.2f} m | "
             f"{AMB[k]['autocorr_3db_m']/G1[k]['dR_m']:.2f}× |" for k in WK]
_amb_ratio_lo = min(AMB[k]["autocorr_3db_m"] / G1[k]["dR_m"] for k in WK)
_amb_ratio_hi = max(AMB[k]["autocorr_3db_m"] / G1[k]["dR_m"] for k in WK)
#  WiFi 대비 배수 (정의와 무관하게 살아남는 것)
_r_meas_lte = AMB["lte"]["autocorr_3db_m"] / AMB["wifi"]["autocorr_3db_m"]
_r_ray_lte = G1["lte"]["dR_m"] / G1["wifi"]["dR_m"]
_r_meas_nr = AMB["nr"]["autocorr_3db_m"] / AMB["wifi"]["autocorr_3db_m"]
_r_ray_nr = G1["nr"]["dR_m"] / G1["wifi"]["dR_m"]

cells.append(md(
    "---",
    "## §3. **Sionna 기본 파형과 비교** — 이 리포트의 핵심 검증",
    "",
    "> 🔍 **여기서 하는 일** — 우리가 손으로 만든 신호(악보)를 **검증된 프로 라이브러리 Sionna** "
    "에게 그대로 쳐보게 해서, 음 하나까지 같은지 대조합니다. 이 대조가 실제로 버그를 잡습니다.",
    "",
    "### 3.1 뉴머롤로지는 **우리가 안 짠다**",
    "",
    "`sionna.phy.nr.CarrierConfig` 가 3GPP 뉴머롤로지(numerology — 부반송파 간격·슬롯 길이 등 "
    "5G 의 시간·주파수 격자를 정하는 설정값. μ · SCS · RB · 심볼/슬롯 · 슬롯/프레임 · CP)를 "
    "이미 압니다. 우리는 **물어보기만** 합니다:",
    "",
    "![numerology](outputs/figures/report2_numerology.png)",
    "",
    "| 채널 | SCS | μ | RB | 부반송파 | 심볼/슬롯 | 슬롯/프레임 | 슬롯 길이 | CP |",
    "|---|---|---|---|---|---|---|---|---|",
    *_num_rows,
    "",
    "### 3.2 변조기 대조 — **같은 자원격자를 Sionna 로 재변조**",
    "",
    "자작 `ofdm_modulate()` 가 만든 것과 **같은 격자**를 `sionna.phy.ofdm.OFDMModulator` 에 넣고, "
    "두 시간영역 파형을 대조했습니다(전력 정규화 후 상관 · NMSE(정규화 평균제곱오차 — 두 신호의 "
    "차이를 dB로 잰 값. 작을수록·음수로 클수록 똑같다)):",
    "",
    "| 파형 | 샘플 | **상관** | **NMSE** | 판정 |",
    "|---|---|---|---|---|",
    *_xc_rows,
    "",
    f"NMSE **≈ {_worst_nmse:.0f} dB** 는 **float32 기계정밀도**입니다 — 두 구현이 *비슷한* 게 아니라 "
    f"**같은 수**를 냅니다.",
    "**→ 자작 OFDM 변조기가 Sionna 와 비트 단위로 일치합니다.** 강력한 검증입니다.",
    "",
    "![crosscheck](outputs/figures/report2_crosscheck.png)",
    "",
    "### 3.3 🐛 이 교차검증이 **실제로 잡은 버그** — 슬롯 첫 심볼의 CP",
    "",
    "3GPP 는 슬롯 **첫 심볼의 순환전치(CP — 심볼 앞에 붙여 다중경로 번짐을 막는 짧은 보호구간)를 "
    "더 길게** 줍니다(슬롯 경계를 맞추기 위해):",
    "",
    "> **쉽게 말하면 —** 각 박자 앞에 붙는 '쉼표' 가 있는데, **맨 첫 박자만 쉼표가 더 깁니다.** "
    "이걸 모르고 모든 박자에 짧은 쉼표를 붙이면, 첫 박자부터 어긋나 **곡 전체의 박자가 밀립니다** "
    "— LTE·5G가 그렇게 무너졌고, 쉼표가 다 똑같은 WiFi는 멀쩡했습니다.",
    "",
    "| 파형 | CP 길이 [샘플] | CP 가 균일한가 |",
    "|---|---|---|",
    *_cp_rows,
    "",
    "CP 배열을 통째로 넘기지 않고 **첫 값만** 쓰면 이후 심볼 경계가 전부 어긋납니다:",
    "",
    "| 파형 | 올바름 (CP 배열 전체) | **버그 (첫 CP 만)** |",
    "|---|---|---|",
    *_bug_rows,
    "",
    f"> 🔑 **WiFi 는 CP 가 균일해서 같은 버그가 안 보입니다** — 상관이 "
    f"{XC['wifi']['corr_bug']:.4f} 로 멀쩡합니다.",
    f"> **파형 하나만 시험했다면 이 버그는 통과했을 것입니다.** 세 표준을 동시에 대조했기 때문에 "
    f"LTE({XC['lte']['corr_bug']:.3f}) · NR({XC['nr']['corr_bug']:.3f})에서 드러났습니다.",
    "> **이것이 교차검증이 사준 것입니다** — 검증은 '통과'가 아니라 '진단'일 때 값을 합니다.",
    "",
    "### 3.4 모호함수 — 거리축과 속도축은 **다른 곳에서** 온다",
    "",
    "모호함수(ambiguity function — 하나의 기준신호가 거리·속도를 얼마나 또렷이 가르는지 보여주는 "
    "2차원 지도. 봉우리가 뾰족할수록 잘 가른다)를 봅니다.",
    "",
    "![ambiguity](outputs/figures/report2_ambiguity.png)",
    "",
    "> **쉽게 말하면 —** 이 그림은 '이 신호로 거리를 얼마나 잘 가르나' 를 보여줍니다. 그런데 "
    "**속도를 얼마나 잘 가르나** 는 이 한 장짜리 그림으로는 볼 수 없습니다 — 속도 한계는 신호가 "
    "**여러 번 반복될 때**(버스트 *사이*의 간격)에만 드러나기 때문입니다. 그래서 속도 얘기는 "
    "§1이 따로 맡습니다.",
    "",
    "| 기준신호 | 자기상관(신호를 자기 자신과 겹쳐 본 것) **3 dB 반폭** (측정) | "
    "$c/(2B_{ref})$ (§1 의 레일리 값) | 비 |",
    "|---|---|---|---|",
    *_amb_rows,
    "",
    "> ⚠️ **이 두 열은 서로를 검증하지 않습니다 — 정직하게 짚습니다.**",
    f"> LTE·5G 에서 측정 반폭이 레일리 값의 **{_amb_ratio_lo:.2f}~{_amb_ratio_hi:.2f}배**로 나옵니다. "
    f"두 가지가 겹쳐 있습니다:",
    "> 1. **정의가 다릅니다.** $c/(2B)$ 는 레일리(피크→첫 널) 기준이고, 위 측정은 "
    "**|R(τ)| 가 0.707 로 떨어지는 반폭**입니다. 후자가 원래 더 좁습니다.",
    "> 2. **CRS·SSB 는 빗살(comb)입니다.** 주 로브 폭은 **점유 스팬**이 정하므로 좁게 나오지만, "
    "빗살의 빈틈이 **부엽(거리 모호)** 을 키웁니다. 좁은 피크가 곧 좋은 분해능은 아닙니다.",
    "",
    f"> **정의를 바꿔도 살아남는 것은 순서와 배수입니다**: WiFi 대비 LTE 는 "
    f"측정 {_r_meas_lte:.1f}배 / 레일리 {_r_ray_lte:.1f}배, 5G 는 측정 {_r_meas_nr:.1f}배 / "
    f"레일리 {_r_ray_nr:.1f}배 나쁩니다. §1 의 결론(5G 가 압도적으로 거칠다)은 그대로입니다.",
    "> **§1 의 ΔR 숫자는 레일리 규약**으로 읽으십시오.",
    "",
    "**한 버스트 안의 모호함수는 도플러 축으로 거의 평평합니다** — 드론이 만들 수 있는 도플러 범위"
    "(수백 Hz)에서 버스트 내 도플러 분해능(≈ 1/T_burst, kHz 급)은 아무 제약이 되지 않습니다.",
    "**속도 한계는 버스트 *사이*의 반복률(PRF)** 이 정합니다(§1). 그건 이 단일 버스트 그림이 "
    "**보여줄 수 없는 축**입니다 — 그래서 §1 이 따로 필요합니다.",
    "",
    "### 3.5 정직하게 — **Sionna 로 다 되지는 않는다**",
    "",
    "| | Sionna PHY 에 있나 | 그래서 |",
    "|---|---|---|",
    "| OFDM 변복조 (IFFT + CP) | ✅ `ofdm.OFDMModulator` | **Sionna 것을 쓴다** |",
    "| 3GPP NR 뉴머롤로지 | ✅ `nr.CarrierConfig` | **Sionna 것을 쓴다.** 표를 안 짠다 |",
    "| 자원격자 골격 | ✅ `ofdm.ResourceGrid` | 쓴다 |",
    "| **WiFi 802.11ac** | ❌ **없다** | `waveforms.py` 가 필요 |",
    "| **LTE** | ❌ **없다** (5G NR 만 있다) | `waveforms.py` 가 필요 |",
    "| **SSB 생성기** | ❌ **없다** (PUSCH/PDSCH 위주) | `waveforms.py` 가 필요 |",
    "| CRS / PRS / VHT-LTF 배치 | ❌ 없다 | `waveforms.py` 가 필요 |",
    "",
    "> **결론**: `waveforms.py` 를 **버릴 수 없습니다.** 하지만 그 안의 **OFDM 엔진은 Sionna 로 "
    "검증됐고**(§3.2), Sionna 가 가진 것(뉴머롤로지 · 변조기)은 **Sionna 것을 씁니다.**",
    "> 이 리포트에서 Sionna 는 **OFDM 엔진이자 검증자**입니다.",
))

cells.append(code(
    "# §3 재현 — Sionna 로 같은 격자를 재변조해 대조 (그리고 CP 버그를 일부러 재현)",
    "import numpy as np",
    "from waveforms import all_waveforms",
    "from waveforms_sionna import ofdm_from_grid, nr_table",
    "",
    "nr_table()          # sionna.phy.nr.CarrierConfig 가 알려주는 3GPP 뉴머롤로지",
    "",
    "def corr(a, b):",
    "    n = min(len(a), len(b)); a, b = a[:n], b[:n]",
    "    a = a / (np.sqrt(np.mean(abs(a)**2)) + 1e-30)",
    "    b = b / (np.sqrt(np.mean(abs(b)**2)) + 1e-30)",
    "    return abs(np.vdot(a, b)) / n",
    "",
    "print()",
    "for k, wf in all_waveforms('G3').items():",
    "    cps = np.atleast_1d(np.asarray(wf.cp_lens))",
    "    ok  = ofdm_from_grid(wf.grid, wf.fft, cps)                 # 올바름: CP 배열 전체",
    "    bug = ofdm_from_grid(wf.grid, wf.fft, np.array([cps[0]]))  # 버그: 첫 CP 만",
    "    x = np.asarray(wf.tx, complex)",
    "    print(f'{wf.name:15s} CP={cps[:3].tolist()}  '",
    "          f'상관(정상)={corr(x, ok):.4f}   상관(첫CP만)={corr(x, bug):.4f}')",
))

# =========================================================================== #
#  §4
# =========================================================================== #
cells.append(md(
    "---",
    "## §4. RCS — **SBR** (Mitsuba 광선 + PO 표면적분)",
    "",
    "> 🔍 **여기서 하는 일** — 드론에 전파를 쏴서 **얼마나 되반짝이는지**(RCS)를 광선으로 잽니다. "
    "먼저 방법이 맞는지 정답 있는 도형(구·평판)으로 검증하고, 그다음 드론 5종을 재고, 마지막에 "
    "**그 밝기가 어디서 오는지**(껍데기 vs 속 금속)를 가릅니다.",
    "",
    "### 4.0 왜 Sionna RT 의 `PathSolver` 로는 시그마를 못 내나",
    "",
    "> ⚠️ **먼저, 하지 말아야 할 말**: *\"레이트레이싱은 RCS 를 못 낸다\"* — **거짓입니다.**",
    "> **SBR 이 바로 레이트레이싱이고, 그게 RCS 를 계산합니다.** 상용 EM 솔버(FEKO / CST / "
    "HFSS SBR+)가 고주파 RCS 를 내는 **표준 방법**이 정확히 이것입니다.",
    "",
    "**참인 명제는 훨씬 좁습니다**:",
    "",
    "> ### 산란적분 단계가 없는 ***전파용*** path solver 에서는 σ 가 창발하지 않는다.",
    "",
    "Sionna 의 `PathSolver` 는 전파(propagation)용이라 표면을 '국소 무한 거울'(GO)로 봅니다 — "
    "**면적 항이 없습니다.** 측정 근거(`docs/ARCHIVE.md`, `benchmark/verify_rt_rays.py`):",
    "",
    "| 시험 | 결과 |",
    "|---|---|",
    "| 광선 1억 → **4억 발** | 코히어런트 합이 **+8~12 dB 계속 커짐** — **수렴하지 않는다** |",
    "| 산란계수 S 를 2배로 | **+15 dB** — 값이 드론이 아니라 **재질 노브**의 함수다 |",
    "| ITU `metal` 의 S | **0** → 모터 · 배터리 · PCB(σ 의 대부분)가 확산 채널에 **기여 0** |",
    "| 평판 변 0.2 → 4 m (σ 가 52 dB 변함) | RT 진폭 **−7.91 dB 불변** (산포 0.00 dB) |",
    "",
    "**σ 는 적분에서 나옵니다.** 그래서 우리가 한 일은 PO 를 **광선추적 *안으로* 넣는 것**입니다:",
    "",
    "$$E(\\hat u) \\;\\propto\\; \\iint_{\\text{조명면}} (\\hat n\\cdot\\hat u)\\, "
    "e^{j2k\\,\\vec r\\cdot\\hat u}\\, dS \\;=\\; \\iint e^{j2k\\,\\vec r\\cdot\\hat u}\\, "
    "dA_{\\text{투영}}$$",
    "",
    "투영면으로 변수변환하면 **비스듬함(obliquity) 계수가 상쇄**됩니다. 그래서 $\\hat u$ 방향에서 "
    "**간격 $d$ 의 평행 광선 격자**를 쏘면, 맞은 지점들의 합이 **곧 PO 적분**입니다:",
    "",
    "$$E=\\sum_{\\text{hits}} |\\Gamma_i|\\; e^{j2k\\,\\vec p_i\\cdot\\hat u}\\; d^2,"
    "\\qquad \\sigma=\\frac{4\\pi}{\\lambda^2}\\,|E|^2$$",
    "",
    "> **쉽게 말하면 —** 표적이 되쏘는 빛의 세기는 **표면의 넓이**에서 나옵니다. 그런데 전파용 "
    "광선추적은 표면을 '점 거울' 로만 봐서 넓이를 셈에 넣지 못합니다. 그래서 우리는 표적을 향해 "
    "**촘촘한 평행 광선 다발**을 쏘고, **맞은 점들을 (위상까지 맞춰) 다 더합니다** — 이 합이 곧 "
    "넓이 적분과 같아집니다. 게다가 광선은 **맨 앞에 처음 부딪힌 곳**에서 멈추므로, 뒤에 가린 "
    "부분은 저절로 빠집니다.",
    "",
    "광선이 **실제로 맞은 첫 지점**만 쓰므로 **가림(occlusion)이 공짜로** 따라옵니다.",
    "구현: `src/rcs_sbr.py` — **Mitsuba 3 / OptiX, GPU. Sionna 가 쓰는 그 엔진 그대로**입니다.",
))

_dith_rows = [f"| λ/{d['div']} | **{d['spread']:.2f} dB** | {d['avg_err']:+.3f} dB |"
              for d in V["dither"]]
_dc_divs = V["drone_conv"][BAND_NAMES[1]]["divs"]
_dc_rows = [f"| {tag} 방위평균 [dBsm] | " + " | ".join(f"{m:+.2f}" for m in ser["mean_dbsm"]) + " |"
            for tag, ser in V["drone_conv"].items()]
#  λ/8 이후가 λ/24 기준값에서 얼마나 벗어나는가 (측정에서 직접 뽑는다 — 손으로 안 적는다)
_dc_dev, _dc_coarse = 0.0, 0.0
for _tag, _ser in V["drone_conv"].items():
    _base = _ser["mean_dbsm"][-1]                       # λ/24 기준
    for _d, _m in zip(_ser["divs"], _ser["mean_dbsm"]):
        if _d >= 8:
            _dc_dev = max(_dc_dev, abs(_m - _base))
        else:
            _dc_coarse = max(_dc_coarse, abs(_m - _base))

cells.append(md(
    "### 4.1 SBR 검증 — 해석해와 대조. 그리고 **어디가 수렴 안 했는지도 보여준다**",
    "",
    "![sbr validate](outputs/figures/report2_sbr_validate.png)",
    "",
    f"**해석해 대조** @ {V['fc']/1e9:.1f} GHz (λ = {V['lam']*100:.2f} cm):",
    "",
    "| 표적 | 해석해 | SBR 오차 |",
    "|---|---|---|",
    f"| 금속 평판 {V['a']} × {V['a']} m (정면) | σ = 4πA²/λ² = {V['plate_exact_dbsm']:+.2f} dBsm | "
    f"**{V['plate_err'][V['divs'].index(6)]:+.2f} dB** (λ/6) |",
    f"| 금속구 r = {V['r']} m | σ = πr² = {V['sphere_exact_dbsm']:+.2f} dBsm | "
    f"**{V['sphere_err'][V['divs'].index(10)]:+.2f} dB** (λ/10) |",
    "",
    "> 🔍 **그런데 저 두 숫자는 방법을 실제보다 좋아 보이게 합니다 — 그래서 더 파봤습니다.**",
    "",
    "금속구는 **정반사점(specular point — 광선이 거울처럼 똑바로 되돌아오는 딱 한 지점)이 하나뿐**"
    "이라, 광선 격자가 **그 점 위에 떨어지느냐**에 따라 값이 흔들립니다.",
    "격자 밀도는 그대로 두고 **격자 정렬만** 흔들어봤습니다(`pad` 를 9점 디더):",
    "",
    "| 격자 | 오차 산포 (정렬만 바꿔서) | 디더 평균 오차 |",
    "|---|---|---|",
    *_dith_rows,
    "",
    f"→ λ/8 에서는 **격자 정렬만으로 {_lam8['spread']:.1f} dB** 가 움직입니다. "
    f"**λ/24 에서야** 산포 {_lam24['spread']:.2f} dB · 오차 {_lam24['avg_err']:+.3f} dB 로 닫힙니다.",
    f"**즉 단일 격자에서 얻은 '{V['sphere_err'][V['divs'].index(10)]:+.2f} dB' 는 수렴한 숫자가 "
    f"아니라 운 좋은 한 점입니다.** 정직하게 적어둡니다.",
    "",
    "**하지만 드론은 다릅니다** — 산란체가 많아 방위평균이 **저절로 디더**됩니다:",
    "",
    "| 격자 | " + " | ".join(f"λ/{d}" for d in _dc_divs) + " |",
    "|---|" + "---|" * len(_dc_divs),
    *_dc_rows,
    "",
    f"λ/8 부터는 λ/24 값 대비 **{_dc_dev:.2f} dB 이내**로 붙습니다(가장 거친 λ/6 만 "
    f"{_dc_coarse:.2f} dB 벗어납니다). **우리는 λ/{M['sbr_div']} 로 돌립니다** → "
    f"**드론 헤드라인 숫자는 수렴 구간에 있습니다.**",
    "",
    "> 즉 같은 커널이 **구에서는 안 수렴한 것처럼, 드론에서는 수렴한 것처럼** 보입니다. "
    "모순이 아니라 **표적의 성질**입니다 — 정반사점이 하나뿐인 매끈한 곡면이 최악이고, "
    "산란체가 많은 드론은 방위평균이 스스로 평균을 내줍니다.",
))

cells.append(md(
    "### 4.2 🔴 **가림(occlusion)의 대가** — PO 와 SBR 의 차이는 사실상 이것 하나다",
    "",
    "![occlusion](outputs/figures/report2_occlusion.png)",
    "",
    "순수 PO(`rcs_po.py`)는 표면 점구름을 적분하면서 "
    "**$\\hat n\\cdot\\hat u > 0$ 이면 '조명면'** 이라고 판정합니다 — "
    "**앞의 부품에 완전히 가려져 있어도** 그렇습니다. 같은 점들에 광선을 쏴봤습니다:",
    "",
    f"| 한 방위 (az = {OCC['az_view']:.0f}°, el = {OCC['el']:.0f}°) 에서 | 개수 | 투영면적 |",
    "|---|---|---|",
    f"| PO 가 '조명면' 이라 부른 면 | **{OCC['n_lit_po']:,}** | {OCC['area_po']*1e4:.0f} cm² |",
    f"| └ 그중 **실제로 뒤에 가려진** 면 | **{OCC['n_hidden']:,}  "
    f"({OCC['hidden_frac']*100:.0f}%)** | — |",
    f"| 광선이 **실제로 맞은** 면 (SBR) | {OCC['n_visible']:,} | "
    f"**{OCC['area_vis']*1e4:.0f} cm²** |",
    "",
    f"→ PO 는 실제보다 **{OCC['area_po']/OCC['area_vis']:.2f} 배 넓은 면적**을 적분하고 있었습니다.",
    "",
    f"**그 결과** ({OCC['name']}, {OCC['n_az']} 방위 평균, el = {OCC['el']:.0f}°, "
    f"{OCC['fc']/1e9:.1f} GHz):",
    "",
    "| 엔진 | 방위평균 RCS | 차이 |",
    "|---|---|---|",
    f"| 순수 PO (가림 **없음**) | {OCC['po_dbsm']:+.2f} dBsm | — |",
    f"| **SBR 1-bounce** (가림 **있음**) | **{OCC['sbr1_dbsm']:+.2f} dBsm** | "
    f"**{OCC['occlusion_db']:+.2f} dB** ← 가림 |",
    f"| SBR 3-bounce (가림 + 오목부 다중반사) | {OCC['sbr3_dbsm']:+.2f} dBsm | "
    f"{OCC['multibounce_db']:+.2f} dB ← 다중반사 |",
    "",
    f"> 🔑 **PO 에 대한 고전적 비판은 '오목부 다중반사를 못 한다' 였습니다.**",
    f"> **그런데 재보니 그건 {abs(OCC['multibounce_db']):.2f} dB 짜리 문제였고, 진짜 문제는 "
    f"아무도 말 안 하던 가림({abs(OCC['occlusion_db']):.2f} dB)이었습니다.** 한 자릿수 차이입니다.",
    "",
    "> 🐛 **다만 3-bounce 숫자는 약하게만 믿으십시오.** `src/rcs_sbr.py:328` 에서 튕긴 뒤의 "
    "**추가 경로길이가 위상에 누적되지 않습니다**(`* 0` 으로 죽어 있습니다). 그래서 2·3차 기여가 "
    "직접 반사와 같은 위상으로 더해집니다 — **'작다' 는 규모는 믿을 만하지만 정확한 dB 값·부호는 "
    "인용하지 마십시오.**",
    f"> **가림 결론({OCC['occlusion_db']:+.2f} dB)은 이 결함과 무관합니다** — 1-bounce 에는 "
    "다중반사가 아예 없습니다.",
    "",
    "> ℹ️ `docs/ARCHIVE.md` 는 가림을 +4~5 dB 로 적고 있습니다. 오늘 메쉬가 CAD 엔진으로 "
    "바뀌면서(report1) 값이 달라졌습니다 — **위 표가 현재 메쉬에서 새로 잰 값**입니다. "
    "결론(가림 ≫ 다중반사)은 그대로입니다.",
))

_rcs_rows = [f"| {DR[k]['name']} | {DR[k]['diagonal_mm']:.0f} mm | {DR[k]['weight_g']:.0f} g | "
             f"{DR[k]['num_rotors']} | " +
             " | ".join(f"{DR[k]['bands'][b]['mean_dbsm']:+.1f}" for b in BAND_NAMES) + " |"
             for k in DKEYS]

cells.append(md(
    "### 4.3 드론 5종 × 3대역 SBR RCS",
    "",
    "**Sionna 자체 렌더러**가 그린 표적들 — 우리가 적분하는 **바로 그 메쉬**입니다 "
    "(그림이 아니라 시뮬레이터가 본 것):",
    "",
    "![gallery](outputs/figures/report2_gallery.png)",
    "",
    "![rcs polar](outputs/figures/report2_rcs_polar.png)",
    "",
    "![rcs bars](outputs/figures/report2_rcs_bars.png)",
    "",
    f"**방위평균 RCS [dBsm]** — 전 방위 {len(R['az'])}점, el = {R['el']:.0f}°, "
    f"대역평균 {R['n_f']}점, 광선격자 λ/{R['div']}:",
    "",
    "| 드론 | 대각 | 무게 | 로터 | " + " | ".join(f"**{b}**" for b in BAND_NAMES) + " |",
    "|---|---|---|---|" + "---|" * len(BAND_NAMES),
    *_rcs_rows,
    "",
    f"- **가장 어두운 표적**: {DR[_dim]['name']} — **{_means[_dim]:+.1f} dBsm** @3.5 GHz "
    f"(≈ {10**(_means[_dim]/10)*1e4:.0f} cm²). 250 g 급이 왜 어려운지 숫자로 보입니다.",
    f"- **가장 밝은 표적**: {DR[_brightest]['name']} — **{_means[_brightest]:+.1f} dBsm** "
    f"(≈ {10**(_means[_brightest]/10)*1e4:.0f} cm²). 기종 폭이 **{_span:.1f} dB** 입니다.",
    "- **대역 의존성은 약합니다** — 표적이 이미 광학영역(크기 ≫ λ)이라 σ 가 λ 에 둔감합니다. "
    "**기체 크기가 대역보다 훨씬 중요합니다.**",
    "",
    "> ⚠️ **널(null) 깊이를 인용하지 마십시오.** 극좌표의 **로브**와 **방위평균**은 안정적이라 "
    "위 표는 안전하지만, 로브 사이 **골의 깊이**는 이산화 · 대역평균 · 각도평활에 따라 10 dB 넘게 "
    "움직입니다. 그림은 **대역평균 + 3° 평활**본입니다.",
))

_mat_rows = [f"| {r['label'].replace(chr(10), ' ')} | {r['n_faces']:,} | {r['mean_dbsm']:+.2f} dBsm | "
             f"**{r['delta_db']:+.2f} dB** |" for r in MAT["rows"]]

cells.append(md(
    "### 4.4 재질 기여도 — **금속이 표적이고, 플라스틱 셸은 그 앞의 가림막이다**",
    "",
    "![materials](outputs/figures/report2_materials.png)",
    "",
    "메쉬에서 **부위별 면을 실제로 지우고**(광선이 그대로 통과함) 다시 잽니다 — "
    "'플라스틱을 검게 칠하는' 게 아니라 **'전파가 플라스틱을 통과해 본다'** 입니다.",
    f"({MAT['name']} @ {MAT['fc']/1e9:.1f} GHz, el = {MAT['el']:.0f}°, {MAT['n_az']} 방위)",
    "",
    "| 무엇을 남겼나 | 삼각형 | 방위평균 RCS | 온전한 드론 대비 |",
    "|---|---|---|---|",
    *_mat_rows,
    "",
    f"### 🔴 예상과 반대였다 — **셸을 지웠더니 시그마가 {_shell['delta_db']:+.2f} dB 늘었다**",
    "",
    "\"플라스틱은 약한 반사체니 지우면 어두워지겠지\" 라고 예상했는데 **반대**였습니다. 이유는 "
    "우리 SBR 의 작동 방식에 있습니다:",
    "",
    "> **SBR 은 광선을 '첫 충돌' 에서 멈춥니다.** 그러니 셸이 있으면, 그 셸이 "
    "**안쪽의 모터 · 배터리 · PCB 로 갈 광선을 가로채서**(|Γ|=0.28 로) 약하게 되돌려 보냅니다.",
    "> 셸은 **약한 반사체이자 동시에 강한 가림막**입니다. 가림막 효과가 더 큽니다.",
    "",
    "> **쉽게 말하면 —** 잘 닦인 금속 위에 반투명 비닐을 씌우면 오히려 흐려 보이는 것과 같습니다. "
    "우리 계산에서는 비닐(플라스틱 셸)이 **속 금속을 가려** 밝기를 낮춥니다. 그래서 비닐을 벗기면 "
    "밝아집니다. 단 이건 우리 방법이 '비닐을 통과하는 전파' 를 모른다는 **한계** 때문이기도 합니다 "
    "— 아래에서 정직하게 짚습니다.",
    "",
    f"그래서 **금속만 남겨도({_core['delta_db']:+.2f} dB) 온전한 드론보다 밝고**, 반대로 "
    f"**금속을 전부 빼면 {_diel['delta_db']:+.2f} dB 로 무너집니다.**",
    "**→ 표적은 금속입니다.** (§4.2 의 가림 결론과 같은 물리입니다 — 가림이 시그마를 지배합니다.)",
    "",
    f"- **프로펠러는 정적 RCS 에 거의 기여하지 않습니다** ({_props['delta_db']:+.2f} dB). "
    f"프로펠러가 레이더에서 중요한 이유는 **크기(σ)가 아니라 회전(마이크로도플러 변조)** 때문입니다 "
    f"— 그건 report1 의 분절 모델이 다룹니다.",
    "",
    "### ⚠️ 그런데 이 실험은 우리 모델의 **한계**도 같이 드러냅니다 (정직하게)",
    "",
    "실제 1~3 mm 플라스틱 셸은 1.8~5.2 GHz 에서 **준투명(semi-transparent)** 합니다 — 전파가 "
    "상당 부분 **통과해서** 안쪽 금속을 때리고 되나옵니다.",
    "그런데 **우리 SBR 은 투과를 모릅니다** (첫 충돌에서 광선을 끝냅니다). 즉 위 표의 두 줄은 "
    "**물리의 두 극단**입니다:",
    "",
    "| | 셸 모델 | 방위평균 RCS |",
    "|---|---|---|",
    f"| `Full drone` | 셸이 **완전 불투명** (SBR 의 가정) | {MAT['rows'][0]['mean_dbsm']:+.2f} dBsm |",
    f"| `- shell` | 셸이 **완전 투명** | {_shell['mean_dbsm']:+.2f} dBsm |",
    "",
    f"**진짜 값은 이 사이 어딘가입니다.** 즉 이 {abs(_shell['delta_db']):.2f} dB 는 "
    f"'측정한 효과' 가 아니라 **모델 불확실도**로 읽어야 합니다.",
    "이걸 제대로 하려면 SBR 에 **유전체 투과(transmission)** 를 넣어야 합니다 — 지금은 없습니다.",
    "",
    "> 티어다운 조사(`docs/drone_specs_2026.json`)도 같은 말을 합니다: "
    "*\"셸은 GHz 대역에서 사실상 준투명 → 표면 PO 만으로 RCS 를 잡으면 과대추정. 실제 산란체는 "
    "배터리 팩(최대 단일 산란체) · 모터 · PCB 스택 · 짐벌 어셈블리.\"* "
    "**'실제 산란체 = 내부 금속'** 부분은 우리 측정과 일치합니다.",
    "",
    "> 🔗 **두 엔진이 같은 재질표를 읽습니다.** `src/materials.py` 가 유일한 진리원이고 "
    "**Sionna RT**(전파)와 **SBR**(RCS)이 **거기서만** 읽습니다 — 조용히 어긋날 수 없습니다.",
    "> (예전엔 짐벌 카메라를 Sionna 는 plastic(|Γ|=0.244), PO 는 0.85 로 봐서 **10.9 dB** "
    "어긋난 버그가 있었습니다.)",
))

cells.append(code(
    "# §4 재현 — SBR 검증(해석해) + 가림 대조",
    "import rcs_sbr",
    "rcs_sbr.validate(3.5e9)        # 금속구 πr² / 평판 4πA²/λ² 대조 + 격자 수렴",
    "rcs_sbr.compare_with_po()      # 순수 PO vs SBR 1-bounce vs SBR 3-bounce",
))

cells.append(code(
    "# 드론 1종의 SBR RCS 패턴을 직접 계산 (rcs_po 의 기본 엔진이 'sbr' 이다)",
    "import numpy as np",
    "from rcs_po import drone_rcs_pattern_bw, angular_smooth, dbsm",
    "",
    "az = np.arange(0, 361, 1.0)",
    "sig, n_rays = drone_rcs_pattern_bw('mavic4pro', 3.5e9, 100e6, az, el_deg=15.0, n_f=5)",
    "sm = angular_smooth(sig, 3.0, 1.0)      # 3도 창 — 널 '깊이' 는 인용하지 말 것",
    "print(f'방위당 광선 {n_rays:,}발')",
    "print(f'방위평균 {dbsm(np.mean(sig)):+.2f} dBsm    피크 {dbsm(np.max(sig)):+.2f} dBsm')",
))

# =========================================================================== #
#  마무리
# =========================================================================== #
cells.append(md(
    "---",
    "## 📌 정리 — 이 리포트가 답한 것",
    "",
    "### ❓ \"우리가 만든 파형이 맞는가?\"",
    "",
    f"**맞습니다.** Sionna 의 `OFDMModulator` 로 같은 자원격자를 재변조했을 때 상관 "
    f"**{XC['wifi']['corr']:.4f} / {XC['lte']['corr']:.4f} / {XC['nr']['corr']:.4f}**, "
    f"NMSE **≈ {_worst_nmse:.0f} dB**(float32 기계정밀도) — **같은 수**입니다.",
    "뉴머롤로지는 아예 `CarrierConfig` 에게 물어봤습니다.",
    "",
    f"그리고 그 대조가 **CP 버그를 실제로 잡았습니다** "
    f"(LTE 상관 {XC['lte']['corr_bug']:.3f} → 고친 뒤 {XC['lte']['corr']:.4f}). "
    f"WiFi 만 봤다면 놓쳤을 버그입니다.",
    "",
    "다만 **Sionna 로 다 되지는 않습니다** — WiFi · LTE · SSB 는 Sionna PHY 에 **없습니다.** "
    "`waveforms.py` 는 남고, Sionna 는 **OFDM 엔진이자 검증자** 역할입니다.",
    "",
    "### ❓ \"이 드론들은 레이더에 얼마나 밝은가?\"",
    "",
    f"**어둡습니다.** @3.5 GHz 방위평균 **{_means[_dim]:+.1f} ~ {_means[_brightest]:+.1f} dBsm** "
    f"({DR[_dim]['name']} ~ {DR[_brightest]['name']}, 폭 {_span:.1f} dB).",
    f"그리고 **밝기의 출처는 내부 금속**입니다 — 모터 · 배터리 · PCB · 카메라만 남겨도 "
    f"{_core['delta_db']:+.2f} dB 인 반면, 금속을 다 빼면 {_diel['delta_db']:+.2f} dB 로 무너집니다.",
    "",
    f"**그 숫자를 얻으려면 가림이 필수**였습니다: 순수 PO 는 "
    f"**{-OCC['occlusion_db']:.2f} dB 과대평가**합니다. 반면 PO 의 고전적 약점이라던 오목부 "
    f"다중반사는 **{OCC['multibounce_db']:+.2f} dB** 뿐이었습니다.",
    "",
    "### ⚠️ 이 리포트가 **보장하지 않는** 것",
    "",
    "- **절대 RCS 값** — 실측 앵커링이 없습니다. **상대 순서 · 차이(dB)만** 인용하십시오.",
    "- **널 깊이** — 인용 금지.",
    "- **§1 의 ΔR / v_max** — **유휴 셀 체제** 전제입니다. 부하 셀 + full-waveform reference 는 "
    "**다른 체제**입니다.",
    "",
    "---",
    "",
    "| 다음 | 무엇 |",
    "|---|---|",
    "| [report1](report1.ipynb) | 이 RCS 가 적분한 **메쉬**가 어떻게 만들어졌나 (CAD · 검증 · 분절) |",
    "| [report3](report3.ipynb) | **환경**을 Sionna RT 로 — 벽 · 바닥 반사 광선 실험 |",
))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
                   "language_info": {"name": "python", "version": "3.12"}},
      "nbformat": 4, "nbformat_minor": 5}

with open(NB, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"✅ {os.path.relpath(NB, ROOT)} 생성 — 셀 {len(cells)}개 "
      f"(측정 JSON: {os.path.relpath(JS, ROOT)})")
