# -*- coding: utf-8 -*-
"""make_pw03.py — pw03_positioning.ipynb 생성기. ⚠ 이 파일이 소스다.

pw03 — "우리 방법의 위치 — 선행 대비 동일점·차이점, 그리고 무엇을 수용하나"
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pw_common import SYN, md, code, write_nb  # noqa: E402

cells = [
    md(
        "# pw03 — 우리 방법의 위치, 그리고 선행 방법론 수용",
        "",
        "> ⚠ **이 노트북은 생성물이다. 수정은 `prior_work/src/make_pw03.py` 에서** 하고 재실행할 것.",
        "",
        "pw01(논문)·pw02(도구)에서 확인한 선행을 바탕으로 **우리가 정확히 어디에 서 있는지**, "
        "**무엇이 주류와 같고 무엇이 덜 점유된 틈새인지**, 그리고 **선행 방법론을 우리 파이프라인에 "
        "어떻게 녹일지**를 정한다.",
    ),
    md(
        "## §1. 우리는 주류 아키텍처 위에 있다 (이상하지 않다)",
        "",
        "가장 자주 받은 의문 — *\"σ 를 따로 구해 주입하는 게 편법 아닌가?\"* — 에 대한 답은 **아니오, "
        "그것이 표준이다**이다. 선행이 이를 뒷받침한다:",
        "",
        "| 구성요소 | 우리 | 주류 선행 | 판정 |",
        "|---|---|---|---|",
        "| 표적/배경 채널 분리 `h = h_bg + h_target` | ✅ (report12) | NIST 5GNRad·3GPP ISAC·MATLAB | **동일** |",
        "| 표적 밝기를 σ 로 채널에 주입 | ✅ (c) | NIST 5GNRad·MATLAB(MeanRCS) | **동일** |",
        "| 환경 전파를 광선추적으로 담보 | ✅ Sionna RT | Deterministic-Modeling·SimART·ns3sionna | **동일** |",
        "| 그 σ 를 **소형 드론 메쉬에서 SBR+PO 로 산출** | ✅ (d, report07) | 대개 확산계수 S 가정 or RCS 상수 | **차이(강화)** |",
        "",
        "즉 우리 뼈대(분리채널+주입+RT담보)는 NIST 5GNRad·3GPP·MATLAB 과 **같은 주류 구조**다. "
        "다른 점은 표적 밝기를 *가정*하지 않고 *계산*한다는 것 — 이건 약점이 아니라 강화다.",
        "",
        "**정식화(선행 방법론 반영).** 외부 산란계수 $s_q$ 를 Sionna 두 전파구간 사이에 끼운다:",
        "$$h_{target}(t,\\tau)=\\sum_q\\sum_p\\sum_r h^{(p)}_{T\\to q}(t)\\,"
        "s_q(f,\\Omega_i,\\Omega_s,\\mathbf{R}_q(t))\\,h^{(r)}_{q\\to R}(t)\\,"
        "\\delta\\!\\left(\\tau-\\tau^{(p)}_{Tq}-\\tau^{(r)}_{qR}\\right),\\qquad "
        "h_{surv}=h_{dir}+h_{bg}+h_{target}.$$",
        "이게 LAMBDA(CADFEKO $s_q$)·Temporal-GNN(점산란체 $s_q$)·우리(SBR+PO $s_q$)가 공유하는 뼈대다. "
        "⭐ **한 발 앞선 점:** $s_q$ 를 스칼라 $\\sigma_b$ 로 주면 위상을 잃지만(RD/CAF 에서 여러 반사가 복소 "
        "위상으로 합쳐지므로 손해), **복소 바이스태틱 산란행렬** "
        "$\\mathbf{S}_b=\\begin{bmatrix}S_{\\theta\\theta}&S_{\\theta\\phi}\\\\ S_{\\phi\\theta}&S_{\\phi\\phi}\\end{bmatrix}$ "
        "가 이상적이다 — **우리 SBR+PO 는 이미 복소장 $E$ 를 내므로** 스칼라-RCS 주입(대다수 선행)보다 앞선다.",
    ),
    md(
        "---",
        "## §2. 덜 점유된 틈새 — 여기가 우리 기여",
        "",
        "선행 지도를 겹쳐 보면 **세 축이 동시에 비어 있는 자리**에 우리가 있다:",
        "",
        "1. **기회신호 패시브 바이스태틱** — 선행 Sionna-ISAC 은 대부분 **능동/모노스태틱**(NIST 5GNRad, "
        "MATLAB) 또는 **CSI 기반**(Great-X, ns3sionna)이다. 상용 WiFi/LTE/5G 를 *제어 없이 빌려* "
        "기준·감시 채널로 쓰는 패시브 바이스태틱은 드물다.",
        "2. **드론 RCS 를 확산계수 가정 대신 SBR+PO 로 메쉬에서 산출** — Great-X·Deterministic-Modeling "
        "은 확산 S 를, NIST/MATLAB 은 RCS 상수를 쓴다. 우리는 재질·형상별 σ 를 광선조준+PO 적분으로 "
        "직접 낸다(report07/08).",
        "3. **상시 vs 세션 9모드 벤치마크** — '패시브가 잠글 수 있는 기준신호'(WiFi 프리앰블·LTE CRS·"
        "5G SSB vs NR-PRS)로 탐지 난이도를 가르는 비교는 선행에서 못 봤다(report12).",
        "",
        "> ⚠️ **과장 금지.** 각 축은 개별적으로는 선행이 있다(패시브 레이더 일반, 드론 RCS 측정, ISAC "
        "벤치마크). 우리 기여는 **이 셋의 결합을 하나의 재현가능 파이프라인으로** 묶은 것이다.",
    ),
    md(
        "---",
        "## §3. 선행 방법론·오픈소스 수용 — 우리 파이프라인에 무엇을 녹이나",
        "",
        "조사에서 배운 것을 **실제 작업으로** 옮긴다(사용자 방침: 직접 만든 것을 최대한 오픈소스로 대체):",
        "",
        "| 우리 조각 | 대체/검증 오픈소스 | 상태 |",
        "|---|---|---|",
        "| 검출체인 **ECA/CAF/CFAR** (`passive_process.py`) | **pyAPRiL**(GPLv3, DVB-T/FM 실검증) — 드롭인 대체 | 도입 예정(검증 후 대체) |",
        "| 대량 몬테카를로(K=6000) | 우리 **detection_gpu.py**(torch 배치) 유지, pyAPRiL 로 단일실현 정합성 검증 | 유지 |",
        "| 드론 **RCS·마이크로도플러** (`rcs_sbr/po`) | **RadarSimPy**(메쉬RCS) + **openEMS**(full-wave 앵커) 교차검증 | 도입 예정 |",
        "| **추적**(future work) | **Stone Soup**(EKF/UKF·바이스태틱 custom 측정모델) | future work |",
        "| **실측**(X410) | **OpenISAC**(OTA 바이스태틱) + **GNU Radio**(SigMF I/Q 통일) | 실측 단계 |",
        #: ⛔«NMSE −135 dB 검증» 은 **자기일치 바닥**이다 — 같은 구현으로 넣고 뺀 값이라
        #  부동소수점 한계를 재는 것이지 «현실과 맞다» 를 재는 것이 아니다. 한 격자 칸에서
        #  잰 값이기도 하다(2026-09-04 정정).
        "| **파형/채널** | **Sionna PHY**(자기일치 바닥 NMSE −135 dB — ⚠같은 구현으로 "
        "넣고 뺀 값이라 float 한계를 재는 것이지 현실 대조가 아니다) | 유지 |",
        "| 표적/배경 분리 `h=h_bg+h_target` | NIST 5GNRad·3GPP 와 동일 구조임을 report12 §2c 로 명시 | 반영됨 |",
        "",
        "**5단계 로드맵**(선행이 권한 순서, 우리 상황 맞춤):",
        "",
        "1. **최소 동작** — Sionna RT+PHY 채널 → **pyAPRiL** ECA/CAF/CFAR (점표적 드론). *← 지금 우리 위치*",
        "2. **추적 추가** — +**Stone Soup**(바이스태틱 EKF/UKF, RMSE).",
        "3. **드론 물리** — 멀티산란체 모델 $r_{drone}[n]=\\sum_i \\alpha_i x[n-d_i]e^{j2\\pi f_{D,i}nT_s}$, "
        "$\\alpha_i=\\sqrt{\\sigma_i}e^{j\\phi_i}$ (1 body + 4 motor + 8~16 blade-tip) → body Doppler ↔ rotor μD 분리. "
        "*← 우리는 SBR+PO 로 이미 여기(report07/08)*.",
        "4. **AI·sim-to-real** — +PyTorch(분류·domain randomization "
        "$\\Theta=\\{SNR,SCR,CFO,SFO,\\phi_{noise},\\sigma_{RCS},p_{Tx},p_{Rx},p_{drone},v_{drone}\\}$).",
        "5. **실측** — +**OpenISAC**+**GNU Radio**+**USRP X410**: 시뮬과 **동일 I/Q 인터페이스**(SigMF)로 "
        "같은 처리코드가 둘 다 먹게.",
        "",
        "> 💡 **핵심 판단(선행 종합).** *Sionna + pyAPRiL + Stone Soup + OpenISAC* 가 우리 드론 패시브 센싱에 "
        "가장 직접적인 조합이다. 다만 pyAPRiL 을 그대로 끝내지 말고 **핵심 ECA/CAF/CFAR 를 검증한 뒤 우리 "
        "GPU 커널과 정합**시켜, 같은 처리코드를 Sionna 데이터와 X410 데이터에 적용한다 — 그래야 연구 기여와 "
        "재현성이 동시에 선다.",
    ),
    md(
        "---",
        "## §4. 정직한 한 문단 (외부에 말할 때)",
        "",
        "> *\"우리는 NVIDIA Sionna RT 로 챔버 전파를 담보하고(선행 Deterministic-Modeling·SimART 와 "
        "같은 용례), 표적 채널을 배경과 분리해 주입하는 주류 ISAC 아키텍처(NIST 5GNRad·3GPP)를 따른다. "
        "차이는 표적 밝기 σ 를 확산계수로 가정하지 않고 소형 드론 메쉬에서 SBR+PO 로 산출한다는 것, "
        "그리고 이를 상용 WiFi/LTE/5G 를 빌린 패시브 바이스태틱 구조에서 9모드로 벤치마크한다는 것이다. "
        "검출체인(ECA·CAF·CFAR)은 어느 시뮬레이터도 제공하지 않는 연구 대상이라 직접 구현·검증했다.\"*",
        "",
        "이 문단은 **모든 주장에 선행 근거**가 붙어 있어(pw01·pw02), 과장 없이 방어된다.",
    ),
    code(
        "# 조사 종합 — prior_work.json synthesis",
        "import json",
        "S = json.load(open('outputs/prior_work.json', encoding='utf-8'))['synthesis']",
        "for k in ['q1_prior_sionna_isac', 'q2_gap_workarounds', 'our_position',",
        "          'support_for_our_claim', 'adoption_plan']:",
        "    print(f'■ {k}'); print('  ', S[k]); print()",
    ),
    md(
        "---",
        "## §5. 맺음",
        "",
        f"- **{SYN['q1_prior_sionna_isac']}**",
        f"- **{SYN['our_position']}**",
        "",
        "조사 원문 요약은 `/data/public/sionna_jeong/papers_isac_sionna/`(지속 확인용)와 이 폴더의 "
        "`prior_work.json` 에 보존한다. 새 선행이 나오면 JSON 에 추가하고 세 리포트를 재빌드하면 된다.",
    ),
]

write_nb(cells, "pw03_positioning.ipynb", "pw03")
