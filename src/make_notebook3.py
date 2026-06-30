# -*- coding: utf-8 -*-
"""make_notebook3.py — report3.ipynb (분절 드론 + 마이크로도플러 + PX4 연동 가능성) 생성기.
이미지를 markdown 으로 박아 커널 없이도 보이게 한다."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.abspath(os.path.join(HERE, "..", "report3.ipynb"))


def md(*l): return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}
def code(*l): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _s(list(l))}
def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


cells = []
cells.append(md(
    "# 🚁 report3 — 분절(articulation) 드론 모델 & 마이크로-도플러 (+ PX4 연동 가능성)",
    "",
    "> **이 노트북 = 3단계.** [report1](report1.ipynb)(환경)·[report2](report2.ipynb)(레이더/RCS) 위에서,",
    "> 드론을 **움직이는(분절) 모델**로 끌어올립니다: 몸체 자세(롤·피치·요)와 **프로펠러 회전을 분리**해 제어하고,",
    "> 그 결과 생기는 **회전 블레이드의 마이크로-도플러** 전파 시그니처를 계산합니다.",
    "",
    "**왜?** (1) 정적 메쉬로는 '회전 블레이드가 만드는 도플러'(드론 식별의 핵심 단서)를 못 만듭니다.",
    "(2) 로터를 개별 분절 객체로 분리하면 **마이크로-도플러**와 **PX4/Gazebo 비행 시뮬**의 토대가 *동시에* 생깁니다.",
    "",
    "**3줄 결론**",
    "1. 드론 모델을 **프레임(비회전) + 로터별 프로펠러**로 분리 — 몸체 RPY 와 블레이드 스핀이 **독립**(실측 검증됨).",
    "2. 회전 블레이드 → **마이크로-도플러**(블레이드 플래시 + 팁 도플러 ±수 kHz)를 PO 복소장 E(t)로 계산.",
    "3. **같은 분절 모델**(로터 link+joint)이 PX4/Gazebo 비행 시뮬의 전제 — 단, 비행엔 관성텐서·모터계수·믹서설정이 *추가로* 필요.",
))

cells.append(md(
    "## 1. 분절 검증 — 몸체 자세(RPY) ⟂ 프로펠러 회전",
    "",
    "기존 모델은 '부위별 색/재질을 가진 **단일 정적 메쉬**'라, 블레이드 개별 회전·몸체와의 분리가 불가능했습니다.",
    "`drones.py` 를 **프레임 / 프로펠러 / 로터배치**로 분리하고, `pose_articulated()` 로 몸체 자세와 로터별 스핀위상을",
    "독립 적용하게 바꿨습니다. (기존 `build_drone()` 출력은 **그대로 유지** → report1/2 RCS 불변)",
    "",
    "| 검증 항목 | 이전 | 지금 | 실측 근거 |",
    "|---|---|---|---|",
    "| 블레이드(로터) 개별 회전 | ❌ | ✅ | `rotor_phase_deg=[θ₀…θₙ]` 로터마다 다른 위상 |",
    "| 몸체 회전 ↔ 블레이드 회전 분리 | ❌ | ✅ | 블레이드만 90° 스핀 시 **프레임 정점 이동 = 0.000000 m** |",
    "| 롤·피치·요(RPY) | ⚠ yaw만 | ✅ | `body_rpy=(roll,pitch,yaw)` 독립 |",
    "| └ RPY 상태에서 로터별 회전 | ❌ | ✅ | RPY+로터별 위상 동시 적용 |",
    "| mesh 전파 반사 | ✅정적 | ✅+동적 | 정적 RCS/RT + **회전 마이크로도플러**(아래 §2) |",
    "",
    "아래: **위 행** = 몸체만 기울임(프로펠러 정지), **아래 행** = 몸체 고정 + 프로펠러만 회전 → 두 자유도가 분리됨.",
    "![articulation](outputs/figures/report3_articulation.png)",
    "",
    "**회전 애니메이션** — 몸체가 흔들리는 동안 프로펠러가 도는 모습(분리 입증):",
    "![articulation gif](outputs/figures/report3_articulation.gif)",
))

cells.append(code(
    "# (선택 실행) 분절 모델 — 몸체 자세와 로터별 위상을 직접 줘 보기",
    "import sys; sys.path.insert(0, 'src')",
    "import numpy as np",
    "from drones import DRONES, build_frame, pose_articulated",
    "spec = DRONES['phantom4']",
    "base = pose_articulated(spec)                              # 정지·위상0 (= build_drone)",
    "spun = pose_articulated(spec, rotor_phase_deg=[90,90,90,90])  # 블레이드만 90도",
    "# 프레임 정점은 안 움직이고(분리), 프로펠러 정점만 움직임",
    "fv = set(i for f,g in zip(base.f, base.g) if g!='prop' for i in f)",
    "V0=np.array(base.v); V1=np.array(spun.v); fv=sorted(fv)",
    "print('블레이드 90도 스핀 시 프레임 정점 평균 이동 [m]:', round(float(np.linalg.norm(V1[fv]-V0[fv],axis=1).mean()),8))",
    "mix = pose_articulated(spec, body_rpy=(20,15,40), rotor_phase_deg=[0,45,90,135])",
    "print('RPY(20,15,40)+로터위상[0,45,90,135] 메쉬 tris:', mix.n_tris())",
))

cells.append(md(
    "## 2. 마이크로-도플러 — 회전 블레이드의 전파 시그니처",
    "",
    "표적이 **호버(정지)** 해도, 회전하는 블레이드는 표면점 위치를 시간에 따라 바꿔 **위상을 변조**합니다.",
    "프레임(몸체)은 0 도플러 상수항이고, 각 로터의 블레이드만 ω로 회전시켜 **슬로타임 복소 산란장 E(t)** 를",
    "물리광학(PO)으로 계산한 뒤 STFT 하면, 스펙트로그램에 **블레이드 플래시(세로 줄무늬)** 와 **팁 도플러(±f_tip)** 가 보입니다:",
    "",
    "$$E(t)=E_{\\text{frame}}+\\sum_{\\text{로터}} e^{\\,j2k\\,\\mathbf c\\cdot\\hat u}\\sum_{p}[\\hat n\\!\\cdot\\!\\mathbf v>0]\\,(\\hat n\\!\\cdot\\!\\mathbf v)\\,\\Delta A\\,e^{\\,j2k\\,\\mathbf P_{\\text{local}}\\cdot\\mathbf v(t)},\\quad \\mathbf v(t)=R_z(-\\theta(t))\\,\\hat u$$",
    "",
    "![microdoppler](outputs/figures/report3_microdoppler.png)",
    "",
    "- **블레이드 플래시 주파수** = (날 수)×(회전수). 2엽·6000rpm → 200 Hz 마다 번쩍.",
    "- **팁 도플러** f_tip ≈ 2·v_tip/λ·cos(el), v_tip=ω·R. Phantom4(R=0.12m,6000rpm)→ v_tip 75 m/s → f_tip≈±1.7 kHz.",
    "- 강한 **정적 몸체항(0-도플러)** 은 클러터로 제거(`spectrogram(remove_dc=True)`)해 약한 블레이드 성분이 드러나게 했습니다 — 패시브레이더의 정적배경 차감과 동일.",
    "",
    "> **report2 의 파일럿 반복률과 연결**: f_tip 이 수 kHz라, 모호 없이 보려면 **PRF ≳ 2·f_tip(수 kHz↑)** 이 필요합니다.",
    "> 그런데 5G SSB(50Hz)·CSI-RS(200Hz)·LTE CRS(1kHz) 같은 파일럿 반복률로는 **블레이드 마이크로도플러가 접힙니다.**",
    "> → 회전 블레이드까지 보려면 LaSen 류처럼 *기준+데이터*로 샘플률을 더 끌어올려야 합니다.",
))

cells.append(code(
    "# (선택 실행) 마이크로-도플러 시그니처 파라미터",
    "from drones import DRONES",
    "from microdoppler import microdoppler_series",
    "for k in ['phantom4','s1000plus']:",
    "    t,E,info = microdoppler_series(DRONES[k], rpm=6000)",
    "    print(f\"{k:10s} 로터{info['n_rotors']} v_tip={info['v_tip']:.0f}m/s \"",
    "          f\"f_tip=±{info['f_tip']:.0f}Hz 플래시={info['flash_hz']:.0f}Hz\")",
))

cells.append(md(
    "## 3. PX4 연동 가능성 — '스펙을 넣으면 시뮬된다'는 어디까지 참인가",
    "",
    "**검증 결과(공식 문서 기준): 부분적으로만 참.** 기하+무게는 *출발용 airframe* 을 주지만, **날 수 있는** PX4 SITL 모델엔",
    "관성텐서·모터계수·믹서설정이 *추가로* 필요하며 이건 DJI 스펙시트에 없습니다.",
    "",
    "- 물리는 **PX4 가 아니라 시뮬레이터(Gazebo)** 에 있습니다 → ① Gazebo 모델(SDF, 동역학) + ② PX4 airframe(제어할당) 둘 다 필요.",
    "",
    "| 필요한 것 | DroneSpec 로 충족? |",
    "|---|---|",
    "| 로터 수 → `CA_ROTOR_COUNT`, 로터 link 수 | ✅ `num_rotors` |",
    "| 로터 X/Y 위치 → `CA_ROTORn_PX/PY` + joint | ✅ `diagonal/2` + `rotor_layout()` 각도 |",
    "| 총질량 → SDF `<mass>` | ✅ `weight_g` |",
    "| **관성텐서** ixx/iyy/izz | ❌ 총질량만으론 불가 — 질량분포(몸체+모터 배치)로 추정 |",
    "| **모터 추력/토크계수**(`motorConstant`/`CT`,`KM`)·시정수·maxRPM | ❌ 모터/프롭 데이터 필요(호버추력서 추정) |",
    "| **제어할당/믹서**(`CA_*`)+airframe(`SYS_AUTOSTART`,`PX4_SIM_MODEL`) | ❌ 별도 작성 |",
    "",
    "**핵심 시너지**: Gazebo 는 **로터마다 별도 link + revolute joint** 를 요구 — 이는 마이크로도플러에 필요한 '개별 회전 강체'와",
    "**정확히 동일**합니다. 즉 **이번에 만든 분절 모델 하나가 마이크로도플러와 PX4 비행시뮬 둘 다의 토대**입니다.",
    "(S1000+ 는 8로터 옥토 → 옥토 믹서 필요. 출처: docs.px4.io 제어할당, gz-sim MulticopterMotorModel, X500 레퍼런스 모델.)",
    "",
    "**최소 연동 경로**: PX4 레퍼런스 모델(x500/옥토)에서 시작 → `rotor_layout()` 으로 로터 위치/방향 주입 →",
    "질량·치수로 관성텐서 추정(또는 메쉬+밀도로 Gazebo 자동계산) → 호버추력(=무게/로터수)으로 모터계수 역산 →",
    "`CA_*`+airframe 작성 → SITL 기동·호버 확인 후 게인 튜닝.",
))

cells.append(md(
    "## 4. 정리 & 다음 단계",
    "",
    "**한 일**",
    "- 드론을 **분절 모델**로: 프레임/로터 분리, 몸체 RPY ⟂ 블레이드 스핀(실측 검증), `build_drone` 호환 유지.",
    "- 회전 블레이드 **마이크로-도플러**(PO 복소장 E(t) → 스펙트로그램) — 블레이드 플래시·팁 도플러 시각화.",
    "- PX4/Gazebo 연동 가능성 검증: 분절 모델이 공통 토대, 단 관성텐서·모터계수·믹서가 추가로 필요함을 명시.",
    "",
    "**다음 후보**",
    "- 🛰️ 바이스태틱(TX·RX 분리) + 클러터제거(ECA)·CFAR·추적(MTT) — 진짜 패시브 레이더 처리체인(문헌의 보편 구성).",
    "- 🔁 분절 모델 → **Gazebo SDF(로터 link+joint+모터모델) + PX4 airframe** 자동 내보내기(관성텐서 추정 포함).",
    "- 🎯 마이크로-도플러 기반 **드론 vs 새 분류**(블레이드 시그니처).",
))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)", "language": "python", "name": "py312"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
with open(NB, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("notebook 생성:", os.path.relpath(NB), f"({len(cells)} cells)")
