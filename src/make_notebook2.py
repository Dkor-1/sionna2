# -*- coding: utf-8 -*-
"""make_notebook2.py — report2.ipynb (레이더 구성 & RCS 특성화, WiFi/LTE/5G 비교) 생성기.
이미지를 markdown 으로 박아 커널 없이도 보이게 한다."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.abspath(os.path.join(HERE, "..", "report2.ipynb"))


def md(*l): return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}
def code(*l): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _s(list(l))}
def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


cells = []
cells.append(md(
    "# 📡 report2 — 레이더 구성 & RCS 특성화 (WiFi · LTE · 5G 비교)",
    "",
    "> **이 노트북 = 2단계: 레이더.** [report1](report1.ipynb)에서 만든 *차폐시설 + 드론 5종* 위에서,",
    "> **모노스태틱 레이더**를 구성하고 드론의 **RCS(레이더 반사면적)** 를 특성화한 뒤,",
    "> **실제 상용 신호(WiFi/LTE/5G)** 로 표적을 비추어 세 표준을 비교합니다.",
    "",
    "**왜 이걸 하나요?** 패시브 레이더는 주변에 이미 떠다니는 WiFi·LTE·5G 신호를 '레이더 송신기'처럼",
    "빌려 씁니다(illuminator of opportunity). 어떤 신호가 드론 탐지에 유리한지 비교하는 것이 목표입니다.",
    "",
    "**3줄 결론**",
    "1. 드론 RCS 는 **물리광학(PO)** 으로 메쉬에서 직접 계산 — 평판·구 이론과 일치하게 검증됨.",
    "2. 같은 드론도 **주파수가 높을수록 RCS 가 커지고**(∝A²/λ²), 방위각에 따라 크게 변동(글린트).",
    "3. **대역폭이 큰 5G(100MHz)** 가 거리분해능 최우수(≈1.5m), LTE(20MHz)는 ≈7.5m로 가장 거침.",
    "",
    "> 🧩 이번 판은 **모든 실험을 report1 의 3D 드론 메쉬 위에** 얹어 보여줍니다 — 측정 셋업·RCS '풍선'·조명면·도플러.",
))

cells.append(md(
    "## 1. 레이더 구성 — 모노스태틱 + 원거리장",
    "",
    "- **모노스태틱**: 송신(TX)과 수신(RX)을 같은 곳에 둠 → 표적이 되돌려보내는 **후방산란 RCS** 측정.",
    "  (가장 표준적인 챔버 측정. 이후 report3에서 바이스태틱으로 확장)",
    "- 안테나는 챔버 한쪽 끝, 표적은 반대쪽 **quiet zone** → 거리 R 최대 확보.",
    "- ⚠️ **원거리장(far-field)**: RCS 는 R ≥ 2D²/λ 에서만 정의됩니다. 작은 드론 4종은 OK,",
    "  거대한 **S1000+ 는 고주파에서 30m 챔버 안 far-field 가 안 됨**(아래 도식에 ✓/✗ 표시).",
    "",
    "![setup](outputs/figures/report2_setup.png)",
    "",
    "**메쉬로 보는 같은 장면** — report1 의 실제 3D 드론 메쉬를 quiet zone 에 놓고 원거리장(2D²/λ)까지 점검:",
    "![mesh setup](outputs/figures/report2_mesh_setup.png)",
    "",
    "왕복지연 τ=2R/c, 도플러 f_D=2v·f_c/c. 에코 전압이득 α ∝ G·λ·√σ / R² (레이더 방정식).",
))

cells.append(md(
    "## 2. RCS 특성화 — 물리광학(PO) 으로 메쉬에서 직접",
    "",
    "**왜 광선추적(Sionna RT)이 아니라 PO?** 작은 드론의 후방산란을 RT 확산반사로 뽑으면 표본잡음·글린트로",
    "절대 RCS 가 불안정합니다(예전 작업도 같은 이유로 RT RCS 를 안 믿음). 그래서 CAD 표적 RCS 의 표준기법인",
    "**물리광학**으로, report1에서 만든 *정확한 메쉬*에서 바로 계산합니다:",
    "",
    "$$\\sigma(\\hat u)=\\frac{4\\pi}{\\lambda^2}\\Big|\\sum_{\\text{조명면}} (\\hat n\\cdot\\hat u)\\,\\Delta A\\,e^{\\,j2k(\\mathbf r\\cdot\\hat u)}\\Big|^2$$",
    "",
    "**검증(이 방법이 맞다는 근거)** — 표준 표적과 이론값 비교:",
    "",
    "| 표적 | PO 결과 | 이론 | 오차 |",
    "|---|---|---|---|",
    "| 평판 0.3 m | 11.42 dBsm | 4πA²/λ² = 11.42 | 0.00 dB |",
    "| 구 r=0.3 m | −5.49 dBsm | πr² = −5.49 | 0.01 dB |",
    "",
    "→ 이론과 일치하므로 같은 코드로 드론 RCS 를 신뢰성 있게 계산할 수 있습니다.",
    "",
    "![rcs polar](outputs/figures/report2_rcs_polar.png)",
    "",
    "- (a) **RCS(방위각)**: 드론이 돌아가면 RCS 가 크게 출렁입니다. S1000+(검정)이 가장 크고,",
    "  쿼드들은 암 X자 대칭 때문에 **90° 주기 로브**가 보입니다(특정 각도에서 번쩍=글린트).",
    "- (b) **RCS(주파수)**: 모든 드론이 주파수↑ 일수록 RCS↑ (∝A²/λ²). 크기순(S1000+>…>Mini).",
    "",
    "### 표준 반송파별 RCS — 어떤 주파수로 보느냐에 따라 표적이 달라 보인다",
    "![rcs bands](outputs/figures/report2_rcs_bands.png)",
    "",
    "### 메쉬로 보는 RCS — '풍선'과 '번쩍이는 면'",
    "드론 메쉬 둘레에 RCS(방위×고각)를 **3D 풍선**으로 그리면 어느 각도가 크고 작은지 한눈에 보입니다.",
    "뾰족한 로브 = 글린트(평판·암이 거울처럼 반사). 쿼드(4암 X자)는 90° 주기 로브, 옥토(S1000+)는 더 촘촘·전체적으로 큽니다:",
    "![rcs balloon](outputs/figures/report2_mesh_rcs_balloon.png)",
    "",
    "왜 각도마다 RCS 가 다를까요? PO 는 **레이더로 향한 면(조명면)만** 위상 맞춰 더합니다. 보는 각도가 바뀌면 번쩍이는 면이 바뀝니다:",
    "![rcs facets](outputs/figures/report2_mesh_rcs_facets.png)",
))

cells.append(code(
    "# (선택 실행) 특정 드론의 RCS 를 직접 계산",
    "import sys; sys.path.insert(0, 'src')",
    "import numpy as np; from rcs_po import drone_rcs_pattern, dbsm",
    "az = np.arange(0, 360, 2.0)",
    "for fc in [1.84e9, 3.5e9, 5.21e9]:",
    "    sig,_ = drone_rcs_pattern('mavic4pro', fc, az)",
    "    print(f'Mavic4Pro @ {fc/1e9:.2f} GHz : 평균 {dbsm(sig.mean()):.1f} dBsm, 최대 {dbsm(sig.max()):.1f} dBsm')",
))

cells.append(md(
    "## 3. 어떻게 쏘는가 — 실제 상용 OFDM 파형 (WiFi / LTE / 5G)",
    "",
    "레이더 송신을 **실제 표준 신호 구조 그대로** 만들었습니다(뉴머롤로지·기준신호 충실). 핵심:",
    "",
    "| 표준 | 변형 | 반송파 | 대역폭 | SCS | FFT | 기준신호 | 이론 분해능 |",
    "|---|---|---|---|---|---|---|---|",
    "| **WiFi** | 802.11ac VHT | 5.2 GHz | 80 MHz | 312.5 kHz | 256 | **VHT-LTF**\\* | 1.9 m |",
    "| **LTE** | Rel-9 FDD | 1.8 GHz | 20 MHz | 15 kHz | 2048 | **PRS**/CRS | 7.5 m |",
    "| **5G NR** | Rel-16 n78 | 3.5 GHz | 100 MHz | 30 kHz | 4096 | **NR-PRS**/SSB | 1.5 m |",
    "",
    "\\* 80MHz 전대역 기준은 엄밀히 **VHT-LTF**입니다(레거시 L-LTF 는 20MHz). 코드에선 L-LTF 를 전대역으로 타일링해 근사합니다.",
    "",
    "- **기준신호**(L-LTF/PRS/SSB)는 송수신이 *미리 아는* 신호라 정합필터(matched filter)의 템플릿이 됩니다.",
    "  패시브 레이더에서 가장 중요한 부분 — 이걸로 표적까지의 거리/도플러를 잽니다.",
    "- 거리분해능 = c/(2·대역폭). **대역폭이 클수록 더 가까운 두 표적을 구분**합니다.",
    "",
    "![wave spectra](outputs/figures/report2_wave_spectra.png)",
))

cells.append(code(
    "# (선택 실행) 세 파형의 제원 확인",
    "from waveforms import all_waveforms",
    "for k, wf in all_waveforms().items():",
    "    print(f'{wf.name:15s} fc={wf.carrier_hz/1e9:.2f}GHz B={wf.bw_hz/1e6:.0f}MHz "
    "분해능={wf.range_resolution_m:.2f}m 기준={wf.ref_name} 길이={wf.duration_us:.0f}us')",
))

cells.append(md(
    "## 4. 현실 점검 — 실제 셀은 항상 꽉 차 있지 않다 (점유 상태 G1/G2/G3)",
    "",
    "상용 셀은 **항상 데이터로 꽉 차 있지 않습니다.** 한가하면 5G 는 SSB(동기/방송)만, LTE 는 동기+CRS(상시 기준)만",
    "띄우고, 측위 중이면 기준신호(PRS) 위주, 트래픽이 많을 때만 데이터(PDSCH)까지 찹니다. 그리고",
    "**패시브 레이더는 보통 우리가 미리 아는 파일럿/기준신호만** 정합필터로 씁니다. 그래서 세 가지",
    "점유 상태를 가정해 실험합니다 — **단, 점유 상태의 의미는 표준마다 다릅니다**(각 표준이 실제로 쓰는 채널로 구성):",
    "",
    "| 모드 | WiFi 802.11ac | LTE Rel-9 | 5G NR Rel-16 |",
    "|---|---|---|---|",
    "| **G1** 한가한 셀 | 프리앰블만(L-LTF) | 동기 + **CRS 상시(전대역)** | **SSB만**(협대역 비콘) |",
    "| **G2** 기준+제어 | + SIG 제어헤더 | + PRS 측위 + PDCCH | + PRS(전대역) + DMRS + PDCCH |",
    "| **G3** 풀로드 | + DATA 페이로드 | + PDSCH 데이터 | + PDSCH 데이터 |",
    "",
    "> **핵심 차이**: LTE 의 **CRS 는 매 서브프레임 전대역 상시** 송신 → 한가해도(G1) 거리분해능이 좋습니다.",
    "> 반면 5G 는 상시 셀기준이 없어 한가하면 **SSB(협대역)** 뿐 → G1 분해능이 나쁩니다(이것이 5G 패시브레이더의 고유 난제).",
    "",
    "### 리소스 그리드 '사진' — 각 자원요소(RE)가 싣는 채널을 색으로",
    "시간(OFDM 심볼) × 주파수(부반송파) 격자입니다. **G1은 작은 SSB 블록만, G3는 거의 꽉** 찹니다.",
    "",
    "![grids nr](outputs/figures/report2_grids_nr.png)",
    "![grids lte](outputs/figures/report2_grids_lte.png)",
    "![grids wifi](outputs/figures/report2_grids_wifi.png)",
    "",
    "### 점유 상태 실험 — 거리(주파수축) × 속도(시간축)",
    "(d) 거리분해능은 *기준신호 대역*, (e) 최대 무모호 속도는 *기준신호 반복률*이 좌우합니다(속도 이야기는 §4b):",
    "![occupancy](outputs/figures/report2_occupancy.png)",
    "",
    "**핵심 교훈** (패시브 레이더 현실):",
    "1. **거리분해능은 '기준신호가 실제 점유한 대역'이 좌우.** 표준마다 한가한 셀(G1)의 사정이 다릅니다:",
    "   - **5G G1 = SSB만(협대역 7.2 MHz)** → ≈21 m로 흐릿. PRS(G2)가 켜져 전대역 100 MHz → ≈1.5 m로 또렷.",
    "   - **LTE 는 CRS 가 상시 전대역(18 MHz)** → G1 부터 ≈8.3 m로 일정 (한가해도 또렷 — LTE 패시브레이더의 강점).",
    "   - **WiFi 는 프리앰블 L-LTF 가 늘 광대역(80 MHz)** → 모든 모드 ≈1.9 m로 또렷.",
    "2. **점유율↑ → 송신에너지↑ → 탐지 SNR↑.** 단, 데이터(PDSCH)는 *미지*라 진짜 패시브에선",
    "   기준신호만 정합필터에 쓸 수 있습니다(데이터는 재구성 필요).",
    "3. → 현실적으로 **5G 는 PRS(G2)** 가, **LTE 는 상시 CRS** 가 패시브 측위/탐지의 핵심(전대역+기지).",
))

cells.append(code(
    "# (선택 실행) 점유 모드별 신호 상태 비교 — 거리(대역) × 속도(반복률) 두 축",
    "from waveforms import all_waveforms",
    "for mode in ['G1','G2','G3']:",
    "    for k, wf in all_waveforms(mode).items():",
    "        print(f'{mode} {wf.name:15s} 점유율={wf.occupancy_frac*100:4.0f}% 기준={wf.ref_name:7s} "
    "대역={wf.ref_bw_hz/1e6:5.0f}MHz→{wf.range_resolution_m:5.1f}m "
    "반복률={wf.pilot_rate_hz:5.0f}Hz→{wf.v_unambiguous_ms:4.1f}m/s')",
    "    print()",
))

cells.append(md(
    "## 4b. 빠른 드론엔 빠른 샘플링 — 시간축(파일럿 반복률)",
    "",
    "거리분해능이 *주파수축(대역)* 이야기였다면, **속도**는 *시간축* 이야기입니다. 표적 속도 v 는 도플러",
    "f_d = 2v/λ 가 되고, 패시브 레이더는 **기준신호(파일럿)가 반복될 때마다** 채널을 한 번 샘플합니다.",
    "그 반복률(PRF)이 읽을 수 있는 최고속도를 가둡니다(Nyquist):",
    "",
    "$$v_{\\max} = \\mathrm{PRF}\\cdot\\frac{\\lambda}{4}\\qquad(\\lambda=c/f)$$",
    "",
    "**기준신호마다 시간축 반복률이 다릅니다 — SSB·CSI-RS 는 CRS 보다 훨씬 드문드문 옵니다:**",
    "",
    "| 기준신호 | 반복률(PRF) | 최대 무모호 속도 v_max |",
    "|---|---|---|",
    "| **LTE CRS** (1.8 GHz) | ~1 kHz (매 서브프레임) | **≈41 m/s** |",
    "| **WiFi L-LTF** (5.2 GHz) | ~1 kHz (패킷당, 혼잡 AP) | ≈14 m/s |",
    "| **5G PRS/CSI-RS** (3.5 GHz) | ≤200 Hz (촘촘한 측위 설정 상한; 유휴시 50~100Hz) | ≈4.3 m/s |",
    "| **5G SSB** (3.5 GHz) | ~50 Hz (20 ms 버스트) | **≈1.1 m/s** |",
    "",
    "→ **일반 드론(~20 m/s)을 도플러 모호 없이 읽으려면 LTE CRS 수준의 반복률이 필요**합니다. 5G 는 한가하면",
    "SSB(50 Hz)뿐이라 **1.1 m/s 만 넘어도 속도가 접힙니다(aliasing)** — LaSen 같은 최신 연구가 *기준신호+데이터를",
    "함께* 써서 샘플률을 끌어올리는 이유입니다.",
    "",
    "![doppler mesh](outputs/figures/report2_mesh_doppler.png)",
    "",
    "> **두 축 요약**: 5G 는 한가하면 SSB 뿐 → **대역도 좁고(거리 흐림)·반복률도 낮다(빠른 표적 못 읽음)** = 이중고.",
    "> LTE 의 CRS 는 상시 전대역 + 매 서브프레임 → **두 축 다 좋다**. (위 (d)거리 vs (e)속도 패널 참고)",
))

cells.append(md(
    "## 5. 측정 & 비교 — 세 파형으로 같은 표적 재기",
    "",
    "표적 에코를 만들고(레이더 방정식), **정합필터**로 거리 프로파일을 뽑습니다. 절대 RCS 는",
    "**기준 금속구(σ=πr²)** 를 똑같이 처리해 보정합니다.",
    "",
    "![range profiles](outputs/figures/report2_range_profiles.png)",
    "",
    "→ 세 신호 모두 실제 거리(10 m)에서 피크. **5G 가 가장 날카롭고 LTE 가 가장 넓습니다**(대역폭 차이).",
    "",
    "![summary](outputs/figures/report2_summary.png)",
    "",
    "→ **추정 RCS 가 참값(PO)과 일치** → 구 보정 정합필터가 정상 동작. 표준별 거리분해능 차이도 한눈에.",
))

cells.append(code(
    "# (선택 실행) 한 표적을 세 파형으로 측정 비교",
    "import numpy as np",
    "from waveforms import all_waveforms; from rcs_po import drone_rcs_pattern, dbsm",
    "from radar_process import range_profile, mainlobe_width_m, sphere_calib, estimate_rcs_dbsm",
    "R = 10.0; target='mavic4pro'",
    "for k, wf in all_waveforms().items():",
    "    sig,_ = drone_rcs_pattern(target, wf.carrier_hz, np.array([0.0])); sig=float(sig[0])",
    "    rng_m, prof, pkr, pkv = range_profile(wf, R, sig, snr_db=20, rng=np.random.default_rng(7))",
    "    cpk,csig = sphere_calib(wf, R); est = estimate_rcs_dbsm(pkv, cpk, csig)",
    "    print(f'{wf.name:15s} 참RCS={dbsm(sig):6.1f} 추정={est:6.1f} dBsm  피크R={pkr:.1f}m  분해능={mainlobe_width_m(rng_m,prof):.1f}m')",
))

cells.append(md(
    "## 6. 정리 & 다음 단계",
    "",
    "**한 일**",
    "- 모노스태틱 레이더 구성 + 원거리장 점검(거대 S1000+ 는 고주파 한계 명시).",
    "- 드론 RCS 를 **물리광학으로 검증된** 방식으로 특성화(방위각·주파수 의존성).",
    "- **실제 WiFi/LTE/5G OFDM 파형**(기준신호 포함)으로 표적을 재고, 거리분해능·RCS추정·반송파의존을 비교.",
    "- **모든 실험을 report1 의 3D 드론 메쉬로 시각화** — 측정 셋업·RCS '풍선'·조명면·도플러(메쉬 도면).",
    "",
    "**알게 된 것 (두 축)**",
    "- **거리분해능 ← 기준신호 대역(주파수축)**: 5G G2/G3(PRS,100MHz)≈1.5m, WiFi(80MHz)≈1.9m, LTE(CRS,18MHz)≈8.3m. 단 5G G1(SSB)은 ≈21m.",
    "- **최대속도 ← 기준신호 반복률(시간축)**: LTE CRS(1kHz)≈41 m/s ≫ 5G PRS(200Hz)≈4.3 ≫ 5G SSB(50Hz)≈1.1 m/s.",
    "- 같은 표적도 **반송파(주파수)** 에 따라 RCS 가 수~십 dB 달라짐 → 표준 비교 시 반드시 고려.",
    "- 즉 **5G 는 한가하면(SSB만) 거리·속도 두 축 다 나쁨** — 이것이 패시브 5G 센싱의 핵심 난제(LaSen 등의 출발점).",
    "",
    "**다음(report3 후보)**",
    "- 🛰️ **바이스태틱**(TX·RX 분리, 각도 β 스윕) — 진짜 패시브 레이더 구성.",
    "- 🌀 **마이크로-도플러**(회전 프로펠러) — 드론 식별의 핵심 단서.",
    "- 📊 **검출 성능**(Pd/Pfa) 과 클러터(챔버 벽) 영향 평가.",
))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)", "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(NB, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("notebook 생성:", os.path.relpath(NB), f"({len(cells)} cells)")
