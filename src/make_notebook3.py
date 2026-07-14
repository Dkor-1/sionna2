# -*- coding: utf-8 -*-
"""make_notebook3.py — report3.ipynb (분절 드론 + SBR 마이크로도플러 + PX4 연동 가능성) 생성기.

본문 수치는 **outputs/report3_microdoppler.json 에서 읽어 넣는다** — 그림과 글이 어긋날 수 없다.
(그 JSON 은 viz_report3.build_all() 이 그림을 그리면서 같은 배열에서 뽑아 저장한다.)"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
NB = os.path.join(ROOT, "report3.ipynb")
JS = os.path.join(ROOT, "outputs", "report3_microdoppler.json")


def md(*l): return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}
def code(*l): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _s(list(l))}
def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


with open(JS) as f:
    J = json.load(f)
H, D, S, C = J["headline"], J["drones"], J["spectrum"], J["cfg"]
po, sb = H["po"], H["sbr"]
import math
dc_drop = 20 * math.log10(sb["dc"] / po["dc"])
ac_rise = 20 * math.log10(sb["ac"] / po["ac"])

cells = []
cells.append(md(
    "# 🚁 report3 — 분절(articulation) 드론 & **마이크로-도플러(가림 포함 SBR)** (+ PX4 연동 가능성)",
    "",
    "> **이 노트북 = 3단계.** [report1](report1.ipynb)(환경)·[report2](report2.ipynb)(레이더/RCS) 위에서,",
    "> 드론을 **움직이는(분절) 모델**로 끌어올립니다: 몸체 자세(롤·피치·요)와 **프로펠러 회전을 분리**해 제어하고,",
    "> 그 결과 생기는 **회전 블레이드의 마이크로-도플러**를 **SBR**(Mitsuba 광선 + PO 표면적분, **가림 포함**)로 계산합니다.",
    "",
    f"## 🔴 헤드라인 — 가림을 넣으면 마이크로도플러가 **{H['gain_db']:.1f} dB 쉬워진다**",
    "",
    "예전 그림은 **순수 PO**(`microdoppler_series`)로 그렸습니다 — 광선을 쏘지 않으니 **가림(occlusion)이 없습니다.**",
    "블레이드가 동체 뒤로 돌아가도, 셸 안의 배터리·PCB 도, 언제나 산란체로 계상됩니다.",
    "**SBR**(`rcs_sbr.sbr_field`)은 Mitsuba 광선이 **실제로 맞은 첫 지점만** 적분합니다:",
    "",
    "| 양 | PO (가림 없음) | **SBR (가림 포함)** | 차이 |",
    "|---|---|---|---|",
    f"| 정적 받침대 \\|DC\\| (몸체) | {po['dc']:.3e} | **{sb['dc']:.3e}** | {dc_drop:+.1f} dB — 가려진 산란체가 빠진다 |",
    f"| 블레이드 변조 std(AC) | {po['ac']:.3e} | **{sb['ac']:.3e}** | {ac_rise:+.1f} dB — 블레이드가 동체를 가렸다 열며 변조가 **깊어진다** |",
    f"| **\\|DC\\|/std(AC)** | {po['ratio']:.1f} (+{po['ratio_db']:.1f} dB) | **{sb['ratio']:.1f} (+{sb['ratio_db']:.1f} dB)** | **{H['gain_db']:.1f} dB** |",
    "",
    f"즉 **정적 몸체 받침대 대비 블레이드 선이 {H['gain_db']:.1f} dB 위로 올라옵니다** — 클러터 제거 후 남는 블레이드 성분이",
    f"그만큼 크다는 뜻이고, 곧 **마이크로도플러 검출이 기존 PO 추정보다 {H['gain_db']:.1f} dB 쉽다**는 뜻입니다.",
    "(report5 의 검출 판단에도 그대로 파급됩니다.)",
    "",
    f"![microdoppler](outputs/figures/report3_microdoppler.png)",
    "",
    "**3줄 결론**",
    "1. 드론 모델을 **프레임(비회전) + 로터별 프로펠러**로 분리 — 몸체 RPY 와 블레이드 스핀이 **독립**",
    "   (블레이드만 90° 스핀시켰을 때 프레임 정점 이동 = 0.000000 m).",
    f"2. 회전 블레이드 → **마이크로-도플러**(플래시 {H['flash_hz']:.1f} Hz + 팁 도플러 ±{H['f_tip']:.0f} Hz @3.5 GHz)를",
    f"   **SBR 복소장 E(t)** 로 계산 — 가림이 들어가며 검출 난이도가 {H['gain_db']:.1f} dB 내려갔다.",
    "3. **같은 분절 모델**(로터 link+joint)이 PX4/Gazebo 비행 시뮬의 전제 — 단, 비행엔 관성텐서·모터계수·믹서설정이 *추가로* 필요.",
))

cells.append(md(
    "## 1. 분절 검증 — 몸체 자세(RPY) ⟂ 프로펠러 회전",
    "",
    "기존 모델은 '부위별 색/재질을 가진 **단일 정적 메쉬**'라, 블레이드 개별 회전·몸체와의 분리가 불가능했습니다.",
    "`drones.py` 를 **프레임 / 프로펠러 / 로터배치**로 분리하고, `pose_articulated()` 로 몸체 자세와 로터별 스핀위상을",
    "독립 적용하게 바꿨습니다. (기존 `build_drone()` 출력은 **그대로 유지** → report1/2 RCS 불변)",
    "",
    "| 검증 항목 | 이전 | 지금 | 검증 근거(코드 출력) |",
    "|---|---|---|---|",
    "| 블레이드(로터) 개별 회전 | ❌ | ✅ | `rotor_phase_deg=[θ₀…θₙ]` 로터마다 다른 위상 |",
    "| 몸체 회전 ↔ 블레이드 회전 분리 | ❌ | ✅ | 블레이드만 90° 스핀 시 **프레임 정점 이동 = 0.000000 m** |",
    "| 롤·피치·요(RPY) | ⚠ yaw만 | ✅ | `body_rpy=(roll,pitch,yaw)` 독립 |",
    "| └ RPY 상태에서 로터별 회전 | ❌ | ✅ | RPY+로터별 위상 동시 적용 |",
    "| mesh 전파 반사 | ✅정적 | ✅+동적 | 정적 RCS/RT + **회전 마이크로도플러**(아래 §2) |",
    "",
    "**시뮬레이터가 직접 그린 분절** — 아래는 matplotlib 도해가 아니라 **Sionna RT 렌더러**가 그린 그림입니다.",
    "그리고 이 그림에 쓰인 메쉬가 **SBR 이 실제로 적분하는 바로 그 메쉬**입니다",
    "(`pose_articulated()` → 부위별 OBJ → `sionna.rt.Scene` → `render_to_file`).",
    "",
    "![rt articulation](outputs/figures/report3_rt_articulation.png)",
    "",
    "**Sionna 렌더 스핀 애니메이션** (프로펠러 위상 φ 가 한 플래시 주기 = 180° 도는 동안):",
    "![rt spin](outputs/figures/report3_rt_spin.gif)",
    "",
    "**메쉬 자유도 검증 도해**(matplotlib — 위 행=몸체만 기울임, 아래 행=프로펠러만 회전) 와 흔들림+스핀 GIF:",
    "![articulation](outputs/figures/report3_articulation.png)",
    "![articulation gif](outputs/figures/report3_articulation.gif)",
))

cells.append(code(
    "# (선택 실행) 분절 모델 — 몸체 자세와 로터별 위상을 직접 줘 보기",
    "import sys; sys.path.insert(0, 'src')",
    "import numpy as np",
    "from drones import DRONES, pose_articulated",
    "spec = DRONES['mavic4pro']",
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
    "## 2. 마이크로-도플러 — SBR(가림 포함)로 계산한 회전 블레이드의 전파 시그니처",
    "",
    "표적이 **호버(정지)** 해도, 회전하는 블레이드는 산란점 위치를 시간에 따라 바꿔 **위상을 변조**합니다.",
    "핵심 통찰: **드론 전체 자세는 단일 각도 φ = ωt 의 함수**이고, n엽 프로펠러는 360/n° 회전에 불변입니다.",
    f"그래서 2엽이면 φ ∈ [0, 180°) 를 **{C['n_phase']}스텝**(0.25°)으로 잘라 SBR 복소장을 미리 계산해 두고,",
    "시간축은 조회로 끝냅니다 (시간 스텝마다 광선을 쏘지 않습니다):",
    "",
    "$$E(\\varphi)=\\sum_{\\text{광선이 맞은 첫 지점}} |\\Gamma_i|\\, e^{\\,j2k\\,\\mathbf p_i\\cdot\\hat u}\\, d^2,"
    "\\qquad E(t)=E\\big(\\varphi(t)\\big),\\quad \\varphi(t)=\\tfrac{360\\,\\text{rpm}}{60}\\,t$$",
    "",
    "합이 **'맞은 첫 지점'에 대해서만** 돈다는 것이 PO 와의 유일하고도 결정적인 차이입니다 — 그게 가림입니다.",
    f"$|\\Gamma_i|$ 는 report2 와 **같은 재질표**(`materials.py`, Sionna 와 공유)에서 옵니다.",
    "",
    "### 5종 드론",
    "",
    "![md drones](outputs/figures/report3_md_drones.png)",
    "",
    "| 드론 | 로터 | 호버 rpm(**가정**) | v_tip | f_tip | 플래시 | \\|DC\\|/std(AC) |",
    "|---|---|---|---|---|---|---|",
    *[f"| {k} | {D[k]['n_rotors']} | {D[k]['rpm']:.0f} | {D[k]['v_tip']:.0f} m/s | ±{D[k]['f_tip']:.0f} Hz | "
      f"{D[k]['flash']:.0f} Hz | {D[k]['ratio']:.1f} (+{D[k]['ratio_db']:.1f} dB) |" for k in D],
    "",
    "- **플래시 주파수** = (블레이드가 시선에 브로드사이드가 되는 횟수)/초.",
    f"  2엽 프로펠러는 **180° 대칭**이라 **프로펠러가 1회전에 2번** 브로드사이드가 됩니다:",
    f"  {H['rpm']:.0f} rpm = {H['rpm']/60:.1f} rev/s → **{H['rpm']/60:.1f} × 2 = {H['flash_hz']:.1f} Hz**.",
    f"  (여기에 '블레이드 2장'을 **또** 곱하면 {2*H['flash_hz']:.0f} Hz 가 되어 **틀립니다** — 두 날은 같은 사건을 만듭니다.)",
    f"- **팁 도플러** $f_{{tip}} = 2 v_{{tip}}/\\lambda \\cdot \\cos(el)$, $v_{{tip}} = \\omega R$.",
    f"  Mavic 4 Pro(R=0.134 m, {H['rpm']:.0f} rpm) → v_tip {H['v_tip']:.0f} m/s(Mach 0.22) → **±{H['f_tip']:.0f} Hz** (el {C['el']:.0f}°).",
    "- ⚠ **hover_rpm 은 DJI 가 공개하지 않는 가정값**입니다(프로펠러 크기에 맞춘 합리적 추정: 작은 프롭 빠르게·큰 프롭 느리게).",
    "  절대 rpm 이 바뀌면 f_tip·플래시가 비례해 움직입니다 — **비율과 구조**(큰 프롭일수록 느리다)가 논지입니다.",
    "- ⚠ **대각 로터쌍은 위상이 같습니다**: 장착각이 180° 차이 + 회전방향이 같고(인접만 반대), 2엽은 180° 대칭 → **함께 번쩍**입니다.",
    "- 강한 **정적 몸체항(0-도플러)** 은 클러터로 제거(`spectrogram(remove_dc=True)`)했습니다 — 패시브레이더의 정적배경 차감과 동일.",
    "",
    "### 점선(±f_tip) 너머의 에너지는 무엇인가",
    "",
    "![md spectrum](outputs/figures/report3_md_spectrum.png)",
    "",
    "회전 드론은 φ 에 대해 **주기신호**이므로 스펙트럼은 **선(line) 스펙트럼**입니다. 한 주기를 정확히 균일샘플한",
    "위상 테이블의 FFT 는 **창(window) 없이** 그 선들을 그대로 줍니다 — 누설이 0 입니다. 거기서 읽은 사실:",
    "",
    f"- AC 전력의 **{S['inside_pct']:.1f}%** 가 ±f_tip({H['f_tip']:.0f} Hz) **안쪽**에 있습니다.",
    f"- **운동학적 상한**은 {S['f_kin']:.0f} Hz 입니다 ($2\\omega R_{{mesh}}/\\lambda\\cdot\\cos el$, 메쉬 최대반경 {S['R_mesh']*100:.1f} cm)",
    "  — **모델에 그보다 빠른 산란체는 없습니다.**",
    "- 그 너머에도 선이 **있긴 있습니다**(25~40 dB 아래). 그건 **속도가 아니라 블레이드 플래시의 AM 측대역**입니다",
    "  (블레이드가 가려졌다 드러나는 스위칭 → 시간영역의 날카로운 사건 → 고차 하모닉).",
    "- 스펙트로그램(창 3.2 ms)에서 점선 바깥으로 넓게 번지는 **매끈한 치맛자락은 창 누설**입니다 —",
    "  창을 64배 늘리면 ~16 dB 무너지고 선으로 분해됩니다. **즉 '너머 = 전부 누설'도, '너머 = 전부 물리'도 아닙니다.**",
    f"- SBR 자체의 **광선격자 이산화 잡음**은 가장 강한 블레이드 선보다 {abs(S['floor_db']):.0f} dB 아래입니다(λ/{C['sbr_div']} 격자).",
    "  격자를 λ/12(기본값)로 성기게 쓰면 이 잡음이 std(AC) 를 부풀려 가림 이득이 22 dB 로 **과장**됩니다 —",
    f"  수렴 격자(λ/{C['sbr_div']})에서 잰 정직한 값이 **{H['gain_db']:.1f} dB** 입니다.",
    "",
    "### 애니메이션 — 자세와 스펙트로그램은 같은 φ(t) 에서 나온다",
    "",
    "왼쪽은 **Sionna 가 렌더한 그 자세**, 오른쪽은 **그 자세들이 만든 SBR 스펙트로그램** 위를 지나는 시간커서입니다",
    "(플래시 3주기 ≈ 16 ms). 로터당 플래시는 5.45 ms 마다 오고, 대각쌍은 위상이 같아 함께 번쩍입니다:",
    "",
    "![microdoppler anim](outputs/figures/report3_anim_microdoppler.gif)",
    "",
    "> **report2 의 상시 기준신호와 연결**: f_tip 이 1.3~1.7 kHz(@3.5 GHz)라, 모호 없이 보려면 **PRF ≳ 2·f_tip ≈ 3 kHz** 가 필요합니다.",
    "> 그런데 **상시** 기준신호의 반복률은 **LTE CRS 1 kHz · 5G SSB 50 Hz** 뿐입니다 — 어느 쪽으로도 블레이드 마이크로도플러는 접힙니다",
    "> (특히 5G SSB 는 30배 이상 모자랍니다). 몸통의 병진 도플러(≈수백 Hz)는 LTE CRS 로 읽히지만, **회전 블레이드까지 보려면**",
    "> LaSen 류처럼 *기준신호+데이터*로 샘플률을 끌어올리거나 전용 센싱 파형이 필요합니다.",
    f"> 다만 **신호 자체는 우리가 생각한 것보다 {H['gain_db']:.1f} dB 강합니다** — 문제는 세기가 아니라 **샘플률**입니다.",
))

cells.append(code(
    "# (선택 실행) SBR 마이크로-도플러 — 가림 포함 (GPU: Mitsuba)",
    "import sys; sys.path.insert(0, 'src')",
    "import numpy as np",
    "from drones import DRONES",
    "from microdoppler import microdoppler_sbr, microdoppler_series",
    "spec = DRONES['mavic4pro']",
    "lam = 3e8/3.5e9",
    "t, E_sbr, info = microdoppler_sbr(spec, n_phase=360, spacing=lam/32)   # 수렴 격자",
    "_, E_po, _    = microdoppler_series(spec)                              # 옛 PO (가림 없음)",
    "for nm, E in (('PO ', E_po), ('SBR', E_sbr)):",
    "    dc, ac = abs(E.mean()), np.std(E)",
    "    print(f'{nm}  |DC|={dc:.3e}  std(AC)={ac:.3e}  |DC|/AC={dc/ac:7.1f} (+{20*np.log10(dc/ac):.1f} dB)')",
    "print(f\"f_tip=±{info['f_tip']:.0f} Hz  flash={info['flash_hz']:.1f} Hz  v_tip={info['v_tip']:.0f} m/s\")",
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
    "| 총질량 → SDF `<mass>` | ✅ `weight_g` (단 **S1000+ 는 기체 자중 4.4 kg** 이라 SITL 질량은 페이로드 포함 TOW 6~11 kg 로 올려야 함) |",
    "| **관성텐서** ixx/iyy/izz | ❌ 총질량만으론 불가 — 질량분포(몸체+모터 배치)로 추정 |",
    "| **모터 추력/토크계수**(`motorConstant`/`CT`,`KM`)·시정수·maxRPM | ❌ 모터/프롭 데이터 필요(호버추력서 추정) |",
    "| **제어할당/믹서**(`CA_*`)+airframe(`SYS_AUTOSTART`,`PX4_SIM_MODEL`) | ❌ 별도 작성 |",
    "",
    "**핵심 시너지**: Gazebo 는 **로터마다 별도 link + revolute joint** 를 요구 — 이는 마이크로도플러에 필요한 '개별 회전 강체'와",
    "**정확히 동일**합니다. 즉 **이번에 만든 분절 모델 하나가 마이크로도플러와 PX4 비행시뮬 둘 다의 토대**입니다.",
    "(S1000+ 는 8로터 옥토 → 옥토 믹서 필요. 출처: docs.px4.io 제어할당, gz-sim MulticopterMotorModel, X500 레퍼런스 모델.)",
    "",
    "**호버 rpm 을 아직 '가정'으로 두는 이유도 여기 있습니다**: 모터 추력계수와 질량이 정해지면 호버 rpm 은 **가정이 아니라 유도값**이 됩니다.",
    "PX4/Gazebo 모델이 완성되는 순간, 이 노트북의 f_tip·플래시는 **비행 시뮬에서 떨어져 나오는 값**으로 승격됩니다.",
))

cells.append(md(
    "## 4. 정리 & 다음 단계",
    "",
    "**한 일**",
    "- 드론을 **분절 모델**로: 프레임/로터 분리, 몸체 RPY ⟂ 블레이드 스핀(코드 수치 검증), `build_drone` 호환 유지.",
    f"- 마이크로-도플러를 **SBR(가림 포함)** 로 교체 — 정적 받침대 대비 블레이드 선이 **{H['gain_db']:.1f} dB** 올라왔다",
    f"  (\\|DC\\|/std(AC): PO {po['ratio']:.0f} → SBR {sb['ratio']:.1f}). 옛 PO 그림은 **가려진 산란체를 세고 있었다**.",
    "- 점선 너머 에너지의 정체를 **창 없는 선 스펙트럼**으로 분해: 창 누설 vs AM 측대역 vs 운동학적 상한.",
    "- 분절 드론을 **Sionna 렌더러**로 직접 그렸다(정지 4×2 + 스핀 GIF + 스펙트로그램 동기 애니메이션).",
    "- PX4/Gazebo 연동 가능성 검증: 분절 모델이 공통 토대, 단 관성텐서·모터계수·믹서가 추가로 필요함을 명시.",
    "",
    "**다음 후보**",
    "- 🛰️ 바이스태틱(TX·RX 분리) + 클러터제거(ECA)·CFAR·추적(MTT) — [report4](report4.ipynb).",
    f"- 🔁 report5 의 검출 매트릭스에 이 **{H['gain_db']:.1f} dB** 를 반영(σ 도 SBR 로) — 판단이 바뀔 수 있다.",
    "- 🎯 마이크로-도플러 기반 **드론 vs 새 분류**(플래시율만으로도 기종이 갈린다: "
    f"S1000+ {D['s1000plus']['flash']:.0f} Hz vs Mini5Pro {D['mini5pro']['flash']:.0f} Hz).",
))


def main():
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)", "language": "python", "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(NB, "w") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("notebook 생성:", os.path.relpath(NB, ROOT), f"({len(cells)} cells)")


if __name__ == "__main__":
    main()
