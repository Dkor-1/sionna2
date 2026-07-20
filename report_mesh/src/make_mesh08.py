# -*- coding: utf-8 -*-
"""make_mesh08.py — mesh08 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh08 — "검증 ② 실물·물리 — 진짜 드론과 물리학에 얼마나 가까운가"
mesh_verify.json 의 C(치수)/D(부피)/G(스캔)/H(PO 수렴)/I(SBR 이중검사)를 해설한다.
모든 수치는 mesh_verify.json 에서 f-string 주입(손숫자 금지, 하우스 규약).
배정 그림: dims_check.png, scan_overlay.png, convergence.png
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))

from drones import DRONES  # noqa: E402  (스펙 숫자는 DroneSpec 에서 — 하우스 규약 허용)

C = V["C_dims"]; D = V["D_volume"]; G = V["G_scan"]
H = V["H_po_convergence"]; I = V["I_sbr_subdiv"]
META = V["meta"]

NAME = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro", "matrice4e": "Matrice 4E",
        "s1000plus": "S1000+", "phantom4": "Phantom 4"}
ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]

C0 = 299_792_458.0
LAM35 = C0 / (META["fc_ghz"] * 1e9) * 1e3          # 검증 주파수 파장 [mm] ← meta.fc_ghz
LAM52 = META["lam_hi_mm"]                           # 최고 대역 파장 [mm] ← meta.lam_hi_mm

# 자주 쓰는 수치 미리 꺼내기 (전부 JSON)
worst = {k: C[k]["worst_err_pct"] for k in ORDER}
diag_err = {k: C[k]["checks"]["diagonal"]["err_pct"] for k in ORDER}
prop_err = {k: C[k]["checks"]["prop_dia"]["err_pct"] for k in ORDER}
hm, hp = H["mavic4pro"], H["phantom4"]
SUB = I["subdivision_invariance"]; RAY = I["ray_spacing_convergence"]
s2c, c2s = G["scan_to_cad_mm"], G["cad_to_scan_mm"]


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src.splitlines(keepends=True)}


cells = [

# ── 0. 제목 + 경고 + 용어풀이 ──────────────────────────────────────────────
md(
"# mesh08 — 검증 ② 실물·물리: 진짜 드론과 물리학에 얼마나 가까운가",
"",
"> ⚠ **이 노트북은 생성물이다.** 수정은 `src/make_mesh08.py` 에서 하라 (직접 고치면 재생성 때 사라진다).",
"",
f"**한 줄 요약** — 우리가 만든 드론 메쉬 5종을 (1) 공식 치수, (2) 무게·부피 물리, (3) 실기체 3D 스캔, (4) PO 수치 수렴, (5) SBR 이중 검사의 다섯 잣대로 재봤다. 치수는 최악 {max(worst.values()):.1f}% 이내, 실기체 스캔과는 표면 중앙값 {s2c['p50']:.1f} mm, 수치 해상도를 두 배로 올려도 방위평균 RCS 는 ±{max(abs(hm['azavg_dbsm']['diff']), abs(hp['azavg_dbsm']['diff']), abs(RAY['azavg_dbsm']['diff'])):.1f} dB 안에서 버틴다 — 단, 개별 널(null) 각도는 최대 {hm['per_angle_absdiff_db']['max']:.0f} dB 까지 흔들리므로 믿을 것과 조심할 것을 끝에 명확히 가른다. ← 출처: 본문 전 수치 `report_mesh/outputs/mesh_verify.json` C/D/G/H/I 섹션",
"",
"앞 편(mesh07)이 \"삼각형이 **기하학적으로** 건강한가\"(watertight·법선·대칭·겹침)를 물었다면, 이번 편은 한 단계 위의 질문이다 — **\"그래서 이게 진짜 DJI 드론과, 그리고 전자기 물리와 얼마나 가까운가?\"**",
"",
"## 용어풀이 (이 리포트에 나오는 말)",
"",
"| 용어 | 뜻 |",
"|---|---|",
"| **chamfer 거리** | 한 점구름의 각 점에서 상대 점구름의 **가장 가까운 점**까지 거리. 두 3D 표면이 얼마나 붙어 있는지를 mm 로 재는 자 |",
"| **p50 / p90 / p99** | 백분위수. p50=중앙값(절반이 이보다 가깝다), p90=90% 지점. \"최악 하나\"보다 분포 전체를 보는 요약 |",
"| **PO (Physical Optics, 물리광학)** | 표면을 작은 거울 조각으로 덮고 각 조각의 반사를 **위상까지 더해** 레이더 반사를 계산하는 고전 근사 |",
"| **SBR (Shooting & Bouncing Rays)** | 광선을 무수히 쏘아 표면에서 튕기는 경로를 좇는 GPU 레이트레이싱 계열 RCS 계산법 |",
"| **RCS / dBsm** | Radar Cross Section, 레이더에 보이는 '유효 크기'[m²]. dBsm 은 그 로그 눈금(0 dBsm=1 m²) |",
"| **널 (null)** | 여러 반사파가 정확히 **상쇄**되어 RCS 가 푹 꺼지는 각도. 노이즈캔슬링 이어폰의 상쇄 지점처럼 아주 민감하다 |",
"| **방위평균** | 드론을 한 바퀴(방위각 0–360°) 돌며 잰 RCS 의 전력 평균. 개별 각도보다 훨씬 안정적인 통계 |",
"| **수렴 검사** | 계산 격자를 두 배 촘촘히 해도 답이 안 변하면 \"격자 탓이 아니라 물리가 답\"이라는 증명. 모눈종이를 잘게 바꿔 넓이를 다시 재보는 것과 같다 |",
"| **테셀레이션 / 세분화(subdivision)** | 곡면을 삼각형으로 쪼개는 일 / 각 삼각형을 4개로 더 잘게 쪼개는 일 |",
"| **watertight (수밀)** | 구멍 없이 닫힌 표면. 닫혀 있어야 '부피'가 정의된다 |",
"| **TOW (takeoff weight)** | 이륙중량. 기체 자중 + 배터리/페이로드. S1000+ 처럼 '기체만 무게'와 크게 다른 기종이 있다 |",
"| **암시밀도** | (공식 무게) ÷ (메쉬 부피). 모델이 물리적으로 말이 되는지 보는 스모크 테스트용 가상 밀도 |",
"| **z-shift 정렬** | 두 점구름의 높이 원점이 달라 생기는 어긋남을 z 방향 평행이동으로 맞추는 일 |",
),

# ── 1. 왜 이 검증인가 ────────────────────────────────────────────────────
md(
"## 0. 왜 '실물·물리' 검증이 따로 필요한가",
"",
"기하 검사(mesh07)를 다 통과한 메쉬도 여전히 두 가지 방식으로 틀릴 수 있다.",
"",
"1. **실물과 다른 모양일 수 있다** — 삼각형이 아무리 깨끗해도 '팬텀 4 를 닮은 무언가'일 뿐 팬텀 4 가 아닐 수 있다.",
"2. **계산이 격자 탓일 수 있다** — RCS 숫자가 물리가 아니라 \"점을 몇 개 찍었는가\"에 따라 변한다면 그 숫자는 의미가 없다.",
"",
"그래서 이 편은 다섯 개의 독립 잣대를 쓴다. 잣대마다 \"무엇과 비교하는가\"가 다르다는 점이 핵심이다 — 한 잣대의 약점을 다른 잣대가 메운다. ← 출처: 검사 설계는 `report_mesh/src/verify_mesh_suite.py` 모듈 docstring(9개 섹션 A–I 정의, 3–21행)",
"",
"| § | 검사 | 비교 대상 | JSON 섹션 |",
"|---|---|---|---|",
"| 1 | 치수 대조 | **DJI 공식 스펙시트** | `C_dims` |",
"| 2 | 부피→암시밀도 | **공식 무게 + 물리 상식** | `D_volume` |",
"| 3 | 표면 chamfer | **실기체 0.4 mm 3D 스캔** (Phantom 4) | `G_scan` |",
"| 4 | PO 점간격 수렴 | **자기 자신(격자 2배)** | `H_po_convergence` |",
"| 5 | SBR 이중 검사 | **자기 자신(삼각형 4배·광선 2배)** | `I_sbr_subdiv` |",
"",
f"검증 기준 주파수는 {META['fc_ghz']:.1f} GHz(5G NR, 파장 {LAM35:.1f} mm), 메쉬 엔진은 `{META['mesh_engine']}` 이다. ← 출처: mesh_verify.json `meta` 섹션·`verify_mesh_suite.py:42-44`(FC 정의)",
),

# ── 2. 셋업 코드 ─────────────────────────────────────────────────────────
code(
"""# 셋업 — 증거 JSON 로드 (이 리포트의 모든 숫자가 여기서 나온다)
import json, os, sys
sys.path.insert(0, os.path.abspath("../src"))          # sionna2/src (DroneSpec 등)

with open("outputs/mesh_verify.json", encoding="utf-8") as f:
    V = json.load(f)

NAME = {"mini5pro": "Mini 5 Pro", "mavic4pro": "Mavic 4 Pro", "matrice4e": "Matrice 4E",
        "s1000plus": "S1000+", "phantom4": "Phantom 4"}
ORDER = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4"]

print("검증 대상 :", ", ".join(NAME[k] for k in V["meta"]["drones"]))
print(f"기준 주파수: {V['meta']['fc_ghz']:.1f} GHz  |  메쉬 엔진: {V['meta']['mesh_engine']}")
print("이번 편 섹션:", ", ".join(k for k in V if k.startswith(("C_", "D_", "G_", "H_", "I_"))))"""
),

# ── 3. §1 치수 대조 설명 ─────────────────────────────────────────────────
md(
"## 1. 치수 대조 — 공식 스펙시트와 몇 % 안에서 맞는가 (`C_dims`)",
"",
"옷을 다 만든 뒤 **줄자로 다시 재보는** 단계다. 설계에 넣은 숫자를 그대로 믿지 않고, **완성된 메쉬를 독립적으로 실측**해 공식 스펙과 비교한다: 외형 L×W×H 는 `frame_envelope_mm()`(빌드된 프레임의 바운딩박스를 실측 ← `src/drones.py:390`), 프로펠러 지름은 빌드된 프롭 메쉬의 xy 최대 반경×2, 대각(모터-모터 거리)은 실제 로터 배치 좌표에서 잰다. ← 출처: `report_mesh/src/verify_mesh_suite.py:159-183` `sec_C_dims()`",
"",
"**읽는 법 — 오차 0% 가 다 같은 0% 가 아니다.** 항목이 세 부류로 나뉜다는 것을 알아야 정직한 해석이 된다.",
"",
"1. **맞춰진 값 (L/W/H, 오차 0.0%)** — 빌드 파이프라인이 프레임을 공식 외형에 **맞추도록 스케일**하기 때문에(`frame_fit_scale`, `drones.py:343-349` `build_frame`) 0% 는 검증이 아니라 **구성상 보장**이다. \"자로 재서 0\" 이 아니라 \"자에 맞춰 잘라서 0\".",
"2. **직접 먹인 값 (프로펠러 지름)** — 스펙 지름을 파라메트릭 블레이드에 직접 넣는다. 그런데 5종 모두 오차가 약 "
f"+{prop_err['mavic4pro']:.2f}% 로 **똑같다** — 5종이 같은 블레이드 함수(`drone_cad.py:333` `build_propeller_cad`, 스키미터 후퇴 + 팁 마감)를 반경만 바꿔 쓰므로, 팁 최외곽점이 명목 반경을 살짝 넘는 파라메트릭 형상 특성이 공통 비율로 나타난 것이다. 결함이 아니라 형상 선택의 흔적이다.",
"3. **따라나온 값 (대각선)** — 외형을 공식값에 맞춘 **결과로 유도되는** 모터-모터 거리. 아무도 직접 맞추지 않았으므로 이것이 **진짜 교차검증**이다. 최대 "
f"{max(abs(v) for v in diag_err.values()):+.2f}% ({NAME[max(diag_err, key=lambda k: abs(diag_err[k]))]}) 로, 두 공식값(외형 상자 vs 대각)이 동시에 정확히는 양립하지 않는 기종에서 외형을 우선한 대가다.",
),

# ── 4. 치수 표 코드 ──────────────────────────────────────────────────────
code(
"""# §1 치수 대조 — 5종 전 항목 (공식 vs 메쉬 실측)  ← mesh_verify.json C_dims
C = V["C_dims"]
print(f"{'드론':<12} {'항목':<9} {'공식[mm]':>9} {'실측[mm]':>9} {'오차[%]':>8}")
print("-" * 52)
for key in ORDER:
    for chk, v in C[key]["checks"].items():
        print(f"{NAME[key]:<12} {chk:<9} {v['official']:>9.1f} {v['measured']:>9.1f} "
              f"{v['err_pct']:>+8.2f}")
    print(f"{'':<12} {'→ 최악':<9} {'':>9} {'':>9} {C[key]['worst_err_pct']:>8.2f}")
    print("-" * 52)
worst_key = max(ORDER, key=lambda k: C[k]["worst_err_pct"])
print(f"전체 최악: {NAME[worst_key]} {C[worst_key]['worst_err_pct']:.2f}% (대각선)")"""
),

# ── 5. dims_check 그림 + 공식/추정 구분 ──────────────────────────────────
md(
"![dims_check](outputs/figures/dims_check.png)",
"",
f"왼쪽: 5종 × 전 항목의 공식(회색) vs 실측(파랑) 막대 — 눈으로 봐도 겹친다. 오른쪽: 드론별 최악 오차. 5종 모두 **2% 가이드선 아래**다: Mini {worst['mini5pro']:.2f}% · Mavic {worst['mavic4pro']:.2f}% · Matrice {worst['matrice4e']:.2f}% · S1000+ {worst['s1000plus']:.2f}% · Phantom {worst['phantom4']:.2f}%. ← 출처: mesh_verify.json `C_dims.*.worst_err_pct`, 그림 `report_mesh/src/viz_mesh_reports.py:269-295` `fig_dims()`",
"",
"### 공식값과 '추정'값의 정직한 구분",
"",
"위 표의 '공식[mm]' 열이 전부 같은 무게의 진실은 아니다. 기준값 자체의 출처 등급을 밝혀 둔다 (**오차 0% 여도 기준이 추정이면 진실과 0% 라는 뜻이 아니다**):",
"",
"| 드론 | 대각 기준값 | 등급 | 근거 |",
"|---|---|---|---|",
f"| Mini 5 Pro | {C['mini5pro']['checks']['diagonal']['official']:.0f} mm | ⚠ **추정 (±20 mm)** | DJI 는 Mini 시리즈 대각을 공개하지 않는다. 언폴드 외형+프롭 지름에서 유도한 값으로, 독립 검증자도 \"±~20 mm 로 취급하고 실기체로 확인하라\" 고 명시 ← 출처: docs/SPECS.md 'Mini 5 Pro' 주의·검증 절(dji.com/mini-5-pro/specs), `src/drones.py:98-101` note |",
f"| Mavic 4 Pro | {C['mavic4pro']['checks']['diagonal']['official']:.0f} mm | 공식 외형에서 **유도** | 원래 추정 400 mm 는 공식 외형 328.7×390.5 와 기하학적으로 **모순**(400 으로는 그 상자를 걸칠 수 없다) → 공식 외형에 맞추면 440.9 mm 가 함의된다 ← 출처: `src/drones.py:123-126` note, docs/SPECS.md 'Mavic 4 Pro' |",
f"| Matrice 4E | {C['matrice4e']['checks']['diagonal']['official']:.1f} mm | **공식** | DJI 공식 스펙 438.8 mm ← 출처: docs/SPECS.md 'Matrice 4E'(dji.com 스펙페이지 확인) |",
f"| S1000+ | {C['s1000plus']['checks']['diagonal']['official']:.0f} mm | **공식** | DJI 공식 1045 mm ← 출처: docs/SPECS.md 'S1000+' |",
f"| Phantom 4 | {C['phantom4']['checks']['diagonal']['official']:.0f} mm | **공식** | DJI 공식 350 mm(모터-모터, 프롭 제외) ← 출처: docs/SPECS.md 'Phantom 4', DJI Quick Start Guide v1.2 |",
"",
f"Phantom 4 의 대각 {diag_err['phantom4']:+.2f}% 는 공식 외형 상자(289.5×289.5×196)와 공식 대각(350)을 **동시에** 정확히 만족시키기 어려워 외형을 우선한 타협이고, Matrice 4E 의 {diag_err['matrice4e']:+.2f}% 도 같은 종류다. 파장 {LAM35:.0f} mm 짜리 전파 입장에서 {abs(C['phantom4']['checks']['diagonal']['measured'] - C['phantom4']['checks']['diagonal']['official']):.0f} mm 어긋남은 파장의 {abs(C['phantom4']['checks']['diagonal']['measured'] - C['phantom4']['checks']['diagonal']['official']) / LAM35 * 100:.0f}% 수준이다. ← 출처: mesh_verify.json `C_dims.phantom4/matrice4e.checks.diagonal`, 외형 우선 원칙은 `src/drones.py:317-319` 주석",
),

# ── 6. §2 부피→밀도 설명 ─────────────────────────────────────────────────
md(
"## 2. 부피 → 암시밀도 — 물리적으로 말이 되는가 (`D_volume`)",
"",
"택배 상자를 들어보고 \"이 무게면 안에 뭐가 들었겠구나\" 가늠하는 것과 같은 스모크 테스트다. 무게는 DJI 공식값이고 부피는 우리 메쉬에서 나오므로, 둘을 나눈 **암시밀도 = 공식 무게 ÷ 메쉬 부피** 가 상식적인 범위에 있는지 보면 \"메쉬가 크게 잘못 만들어지진 않았는가\"를 빠르게 걸러낼 수 있다. 부피는 그룹(부위)별 watertight 컴포넌트의 닫힌 부피 합이다. ← 출처: `report_mesh/src/verify_mesh_suite.py:189-206` `sec_D_volume()`",
"",
"**솔리드 근사의 정직한 한계** — 실물 드론은 **속이 비어 있다**(플라스틱 셸 안에 공기·배선 공간). 우리 모델은 부위마다 **꽉 찬 덩어리**(솔리드)다. 그래서 모델 부피가 실물의 '재료 부피'보다 훨씬 크고, 암시밀도는 실제 재료 밀도(ABS 플라스틱 ≈1.05 g/cm³, 물=1.0 — 일반 물성 상식값)보다 **한참 낮게 나오는 것이 정상**이다. 속 빈 기체일수록 낮다: 0.2~0.8 g/cm³ 구간이면 \"셸+공기 구조를 솔리드로 근사한 물체\"로서 말이 된다. 반대로 1 을 크게 넘거나 0.05 아래로 떨어지면 스케일이나 단위가 틀렸다는 신호다.",
),

# ── 7. 밀도 표 코드 ──────────────────────────────────────────────────────
code(
"""# §2 부피·암시밀도 — 5종  ← mesh_verify.json D_volume
D = V["D_volume"]
print(f"{'드론':<12} {'부피[cm3]':>10} {'공식무게[g]':>11} {'암시밀도[g/cm3]':>15}")
print("-" * 52)
for key in ORDER:
    r = D[key]
    print(f"{NAME[key]:<12} {r['total_cm3']:>10.0f} {r['weight_g']:>11.0f} "
          f"{r['implied_density_g_cm3']:>15.3f}")
    if "airframe_g" in r:   # S1000+ 만: TOW 와 기체 자중 병기
        print(f"{'  (자중기준)':<12} {r['total_cm3']:>10.0f} {r['airframe_g']:>11.0f} "
              f"{r['implied_density_airframe_g_cm3']:>15.3f}")
print("-" * 52)
print("참고(일반 물성 상식): 발포폼 ~0.03 / ABS 플라스틱 ~1.05 / 물 1.0 / CFRP ~1.6 g/cm3")"""
),

# ── 8. 밀도 해석 ─────────────────────────────────────────────────────────
md(
"### 읽기 — 왜 S1000+ 만 두 줄인가",
"",
f"소비자 쿼드 4종은 {min(D[k]['implied_density_g_cm3'] for k in ['mini5pro','mavic4pro','phantom4']):.2f}~{D['matrice4e']['implied_density_g_cm3']:.2f} g/cm³ — \"플라스틱 셸 + 빈 속을 솔리드로 근사한 물체\"로 전부 타당한 범위다. Mini/Mavic 이 {D['mini5pro']['implied_density_g_cm3']:.2f} 수준으로 가장 낮은 것은 접이식 경량 기체(빈 공간 비율이 큼)와 일치하고, Matrice 4E({D['matrice4e']['implied_density_g_cm3']:.2f})는 같은 크기급에서 배터리·센서가 더 눌러 담긴 엔터프라이즈 기체라는 사실과 방향이 맞는다. ← 출처: mesh_verify.json `D_volume.*.implied_density_g_cm3`",
"",
f"**S1000+ 는 무게의 정의가 두 개다**: DroneSpec 의 `weight_g={DRONES['s1000plus'].weight_g:.0f}` 은 대표 **이륙중량(TOW, 페이로드 포함)** 이고, 기체 자중(airframe)은 4400 g 이다(권장 TOW 6.0~11.0 kg). ← 출처: docs/SPECS.md 'S1000+'(기체 자중 4400 g 절), `src/drones.py:41-42` weight_g 주석, `verify_mesh_suite.py:202-204`(병기 로직). 그래서:",
"",
f"- TOW 기준 {D['s1000plus']['implied_density_g_cm3']:.2f} g/cm³ — 카메라 짐벌 등 **페이로드까지 얹은 가상 밀도**라 높게 나온다(우연히 CFRP ~1.6 근처).",
f"- 자중 기준 {D['s1000plus']['implied_density_airframe_g_cm3']:.2f} g/cm³ — 카본 프레임 옥토콥터의 솔리드 근사로 타당한 값. **모델 검증에는 이쪽이 맞는 잣대**다.",
"",
"한 값만 적으면 어느 쪽이든 독자를 속이게 되므로 **둘을 병기**한다. 그리고 분명히 해 두면: 이 검사는 \"자릿수가 틀리지 않았다\" 수준의 스모크 테스트지 정밀 검증이 아니다 — 정밀한 형상 검증은 다음 절의 실기체 스캔이 맡는다.",
),

# ── 9. §3 스캔 대조 배경 ─────────────────────────────────────────────────
md(
"## 3. 실기체 스캔 대조 — 진짜 팬텀 4 표면과 몇 mm 인가 (`G_scan`)",
"",
"치수 대조는 '자로 잰 몇 개의 길이'만 본다. 이번엔 **실제 팬텀 4 한 대를 0.4 mm 해상도로 3D 스캔한 데이터**와 우리 파라메트릭 CAD 의 **표면 전체**를 점 대 점으로 비교한다. 5종 중 팬텀 4 만 가능한 이유는 간단하다 — 라이선스가 확인된 실기체 스캔이 공개된 기종이 팬텀 4 뿐이었다.",
"",
f"**스캔 출처** — \"DJI PHANTOM 4 HI RES SCAN\", Thingiverse thing:1456295, 작성자 NeverDun(Eamon McQuaide), 라이선스 **CC-BY**(저작자표시 필수, 여기서 표시함). 원본 STL 은 154 MB·3.09M 삼각형이라 저장소에 넣지 않고 archive.org 미러에서 내려받아 전처리한다. ← 출처: mesh_verify.json `G_scan.source`, `src/prep_cad_scan.py` docstring(7-19행, 다운로드 URL 포함), `assets/meshes/cad/SOURCE.txt`",
"",
"**전처리 파이프라인** (`src/prep_cad_scan.py`) — 왜 이렇게 했는지가 각 단계에 있다:",
"",
"1. **binary STL 을 numpy 로 직접 파싱** — 3.09M 삼각형에 무거운 라이브러리 대신 50바이트 레코드 규격을 그대로 읽는 편이 빠르고 의존성이 없다 (`prep_cad_scan.py:36-43`).",
"2. **스케일 보정 ×1.0125** — 스캔의 모터 허브 대각이 345.7 mm 로 공식 350 mm 보다 1.25% 작게 스캔돼 있어(스캐너 보정 오차) 공식 대각에 맞춰 늘린다 (`prep_cad_scan.py:32`). 실물 스캔도 '측정'이라 오차가 있다는 좋은 예다.",
"3. **PCA 로 z-up 정렬** — 스캔 좌표축은 임의라, 면적가중 분산이 최소인 축을 z 로 삼고 랜딩기어(긴 꼬리)가 아래로 가게 부호를 정한다 (`prep_cad_scan.py:65-81`).",
f"4. **3 mm 복셀 클러스터** — 3.09M 삼각형 → {G['n_scan']:,} 점으로 압축. 3 mm 는 최고 대역(5.2 GHz) 파장 {LAM52:.0f} mm 의 λ/10(≈5.8 mm)보다 조밀해 PO 용으로 충분하다. 셀 안에서 법선이 상쇄된(양면 접힘) 점은 버리고 유효면적을 법선 벡터합 크기로 줄여 **PO 물리와 정합**시킨다 (`prep_cad_scan.py:33, 84-96`).",
"",
f"**비교 방법** (`verify_mesh_suite.py:277-308` `sec_G_scan()`) — 스캔에는 **프로펠러와 짐벌 카메라가 없다**(탈거 후 스캔) → 공정하게 CAD 쪽도 prop/camera/gimbal 그룹을 제외하고 3 mm 간격으로 표면 점 {G['n_cad']:,}개를 뽑는다. 정렬은 수평 중심 맞춤 + **z 오프셋만 ±30 mm 그리드 탐색**(2 mm 스텝): 회전까지 맞추는 ICP 같은 방법은 잘못 수렴하면 오차를 몰래 숨기므로, 일부러 자유도를 z 하나로 묶어 **보수적으로** 잰다. 탐색 결과 z-shift = {G['z_shift_mm']:+.0f} mm — 스캔(몸체만)의 무게중심 높이와 CAD(랜딩기어 포함 전체) 중심 높이가 달라 생기는 자연스러운 어긋남이다.",
),

# ── 10. chamfer 수치 코드 ────────────────────────────────────────────────
md(""),  # placeholder — 아래에서 교체
]

# placeholder 교체: chamfer 수치 코드 셀
cells[-1] = code(
"""# §3 스캔 chamfer 수치  ← mesh_verify.json G_scan
G = V["G_scan"]
print(f"스캔 점 {G['n_scan']:,}개  vs  CAD 표면 점 {G['n_cad']:,}개   "
      f"(z-shift {G['z_shift_mm']:+.0f} mm 정렬 후)")
print()
print(f"{'방향':<28} {'p50':>7} {'p90':>7} {'p99':>7} {'max':>7}  [mm]")
for tag, d in [("스캔 → CAD (실물이 기준)", G["scan_to_cad_mm"]),
               ("CAD → 스캔 (모델이 기준)", G["cad_to_scan_mm"])]:
    print(f"{tag:<28} {d['p50']:>7.1f} {d['p90']:>7.1f} {d['p99']:>7.1f} {d['max']:>7.1f}")
print()
print(f"출처: {G['source']['thing']} ({G['source']['license']}, {G['source']['author']})")"""
)

cells += [

# ── 11. scan_overlay 그림 + 해설 ─────────────────────────────────────────
md(
"![scan_overlay](outputs/figures/scan_overlay.png)",
"",
f"왼쪽: CAD(파랑)와 실기체 스캔(빨강) 오버레이 — 실루엣이 겹친다. 가운데: 스캔의 각 점을 \"CAD 까지 거리\"로 색칠한 지도. **어디가 다른지**가 보인다: 동체 셸의 매끈한 중앙부는 어둡고(수 mm), 암 뿌리·셸 곡률이 급히 변하는 모서리·랜딩기어 접합부가 밝다(수십 mm) — 파라메트릭 CAD 가 뭉뚱그린 디테일이 정확히 그 자리들이다. 오른쪽: 거리 히스토그램과 p50/p90. ← 출처: 그림 `report_mesh/src/viz_mesh_reports.py:324-366` `fig_scan_overlay()`",
"",
"### 두 방향의 비대칭이 말해주는 것",
"",
f"- **스캔→CAD: p50 {s2c['p50']:.1f} mm, p90 {s2c['p90']:.1f} mm** — \"실물 표면의 절반은 우리 모델에서 {s2c['p50']:.1f} mm 안에 상대를 찾는다\". 이것이 형상 충실도의 본 지표다. 중앙값 {s2c['p50']:.1f} mm 는 기준 주파수 {META['fc_ghz']:.1f} GHz 파장({LAM35:.0f} mm)의 약 1/{LAM35 / s2c['p50']:.0f} — 전파 입장에서 '표면이 거의 같은 자리에 있다'고 말할 수 있는 크기다.",
f"- **CAD→스캔: p50 {c2s['p50']:.1f} mm 로 3배쯤 크다** — 이건 모델이 나빠서가 아니라 **스캔에 구멍이 있어서**다. 실기체 스캔은 기체를 세워 놓고 돌려 찍기 때문에 **바닥면(동체 하부)이 스캔되지 않았고**, 그 자리의 CAD 점들은 짝을 찾아 멀리 헤매게 된다. 비다양체·부유 링 아티팩트(~0.8%)도 스캔 쪽 잡음이다. ← 출처: `src/prep_cad_scan.py:18-19` 주의 절, mesh_verify.json `G_scan.cad_to_scan_mm`",
"",
"방향 있는 chamfer 를 **둘 다** 공개하는 이유가 이것이다: 좋은 쪽 하나만 보여주면 스캔 구멍이 모델 결함으로 둔갑하거나(역방향만 볼 때), 모델 결함이 숨는다(순방향만 볼 때).",
),

# ── 12. §4 PO 수렴 ───────────────────────────────────────────────────────
md(
"## 4. PO 점간격 수렴 — 격자를 반으로 줄여도 답이 같은가 (`H_po_convergence`)",
"",
"여기서부터는 \"모양\"이 아니라 \"계산\"의 검증이다. PO 는 표면을 점(작은 거울 조각)으로 덮고 반사를 위상까지 합산한다(`src/rcs_po.py:66` `mesh_to_points`, `:144` `drone_rcs_pattern`). 점 간격이 성기면 위상 합산이 부정확해진다 — 그럼 몇이면 충분한가? **수렴 검사**로 답한다: 간격을 λ/10 에서 λ/20 으로 **절반**(점 개수 4배)으로 줄였는데 결과가 그대로면, 답은 격자가 아니라 물리가 정한 것이다. 모눈종이 칸을 반으로 줄여 넓이를 다시 쟀는데 값이 같다면 처음 모눈도 충분했던 것과 같다.",
"",
f"Mavic 4 Pro 와 Phantom 4, 방위 {hm['n_az']}개(5° 간격)·고도 {hm['el_deg']:.0f}°·{hm['fc_ghz']:.1f} GHz 에서 쟀다. ← 출처: `report_mesh/src/verify_mesh_suite.py:314-335` `sec_H_po_convergence()`, 수치는 mesh_verify.json `H_po_convergence`",
),

# ── 13. H 수치 코드 ──────────────────────────────────────────────────────
code(
"""# §4 PO 점간격 수렴 λ/10 → λ/20  ← mesh_verify.json H_po_convergence
H = V["H_po_convergence"]
for key, h in H.items():
    a = h["azavg_dbsm"]; d = h["per_angle_absdiff_db"]
    print(f"[{NAME[key]}]  ({h['n_az']} 방위, el={h['el_deg']:.0f}°, {h['fc_ghz']:.1f} GHz)")
    print(f"  방위평균 RCS : λ/10 {a['lam10']:+.2f} dBsm → λ/20 {a['lam20']:+.2f} dBsm  "
          f"(이동 {a['diff']:+.2f} dB)")
    print(f"  개별 각도 |Δ|: 평균 {d['mean']:.2f} dB · p95 {d['p95']:.2f} dB · "
          f"최대 {d['max']:.1f} dB  ← 최대는 깊은 널에서")"""
),

# ── 14. convergence 그림 + 해설 ──────────────────────────────────────────
md(
"![convergence](outputs/figures/convergence.png)",
"",
f"(a) Mavic 4 Pro 의 방위 RCS 패턴 — λ/10(파랑)과 λ/20(빨강)이 로브(봉우리) 영역에서는 거의 포개진다. 방위평균 이동은 {hm['azavg_dbsm']['diff']:+.2f} dB(Phantom 4 는 {hp['azavg_dbsm']['diff']:+.2f} dB) — **±0.4 dB 이내**다. (b) 는 다음 절의 SBR 검사. ← 출처: 그림 `report_mesh/src/viz_mesh_reports.py:372-412` `fig_convergence()`",
"",
"### 왜 개별 널은 " f"{hm['per_angle_absdiff_db']['max']:.0f} dB 씩 튀는데 괜찮다고 하는가",
"",
f"널은 여러 산란 기여가 **정확히 상쇄**되는 각도다. 노이즈캔슬링 이어폰이 위상이 조금만 어긋나도 '싹 사라짐'이 '조금 사라짐'으로 바뀌듯, 상쇄점 근처에서는 점 배치가 파장의 몇 % 만 달라져도 dB 눈금으로는 폭발적으로 변한다(0 에 가까운 값의 로그라 더 그렇다). 실제로 개별 각도 차이의 **평균은 {hm['per_angle_absdiff_db']['mean']:.1f}~{hp['per_angle_absdiff_db']['mean']:.1f} dB** 인데 최대만 {hp['per_angle_absdiff_db']['max']:.1f}~{hm['per_angle_absdiff_db']['max']:.1f} dB 다 — 흔들리는 것은 소수의 깊은 널뿐이다.",
"",
"**그리고 검출 문제에서 중요한 것은 평균이다.** 실제 드론은 자세가 계속 변하고 프로펠러가 돌아 널 위치가 쉼 없이 이동한다 — 수신기가 겪는 것은 특정 널 하나가 아니라 각도 분포의 **평균적 에너지**다. 그래서 이 시리즈의 RCS 결론(순서·규모)은 전부 방위평균 통계로 말하고, 개별 널 깊이는 애초에 주장하지 않는다. 이는 실측 문헌들의 RCS 도 세팅에 따라 ±수 dB 씩 흩어진다는 report08 의 스프레드 논거와 같은 이유다. ← 출처: `../report08.ipynb`(RCS 결과·문헌 대조 편)",
),

# ── 15. §5 SBR 이중 검사 ─────────────────────────────────────────────────
md(
"## 5. SBR 이중 검사 (GPU) — 테셀레이션 무의존 + 광선 수렴 (`I_sbr_subdiv`)",
"",
"SBR(`src/rcs_sbr.py:117` `rcs_sbr_batch`)은 PO 와 독립인 두 번째 계산 엔진이라 자기만의 수렴 놉이 있다. 검사를 **두 겹**으로 설계한 이유가 중요하다 (← 출처: `report_mesh/src/verify_mesh_suite.py:363-406` `sec_I_sbr_subdiv()` docstring):",
"",
f"**① 세분화 ×4 불변** — 삼각형을 4배로 쪼개도(faces {SUB['faces_base']:,} → {SUB['faces_fine']:,}) **표면 자체는 동일**하다. 그러니 답이 같아야 '자명'하지만, 이를 실측하는 것은 파이프라인(BVH 교차, 법선 계산, 면적 적분)이 테셀레이션 밀도에 숨은 의존이 없음을 못박는 회귀 검사다. 결과: 방위평균 차이 {SUB['azavg_dbsm']['diff']:+.6f} dB, 개별 각도 최대 {SUB['per_angle_absdiff_db']['max']:.5f} dB — 사실상 **0.000 dB**. 버그가 있었다면 여기서 걸렸다.",
"",
f"**② 광선 간격 λ/12 → λ/24** — 이쪽이 SBR 의 **진짜 수치 놉**이다(광선을 몇 개 쏘는가). 2배 조밀하게 해도 방위평균 이동 {RAY['azavg_dbsm']['diff']:+.2f} dB, 개별 각도 평균 {RAY['per_angle_absdiff_db']['mean']:.1f} dB(최대 {RAY['per_angle_absdiff_db']['max']:.1f} dB, 역시 널) — PO 의 점간격 검사와 같은 등급으로 수렴한다.",
"",
f"둘을 나눠 놓지 않으면 \"메쉬를 잘게 하니 결과가 변하더라\" 같은 관찰이 **형상 문제인지 광선 밀도 문제인지** 구분할 수 없게 된다. 측정은 Mavic 4 Pro, 방위 {I['n_az']}개, GPU 에서 {I['runtime_s']:.1f} 초. ← 출처: mesh_verify.json `I_sbr_subdiv`",
),

# ── 16. I 수치 코드 ──────────────────────────────────────────────────────
code(
"""# §5 SBR 이중 검사  ← mesh_verify.json I_sbr_subdiv
I = V["I_sbr_subdiv"]
sub, ray = I["subdivision_invariance"], I["ray_spacing_convergence"]
print(f"대상 {NAME[I['drone']]} · 방위 {I['n_az']}개 · {I['fc_ghz']:.1f} GHz · "
      f"GPU {I['runtime_s']:.1f}s")
print()
print(f"① 세분화 ×4  (faces {sub['faces_base']:,} → {sub['faces_fine']:,}, 표면 동일)")
print(f"   방위평균 차이 {sub['azavg_dbsm']['diff']:+.2e} dB · "
      f"개별각 최대 {sub['per_angle_absdiff_db']['max']:.1e} dB   → 테셀레이션 무의존")
print(f"② 광선 {ray['spacing_a']} → {ray['spacing_b']}  (진짜 수치 놉)")
print(f"   방위평균 이동 {ray['azavg_dbsm']['diff']:+.2f} dB · "
      f"개별각 평균 {ray['per_angle_absdiff_db']['mean']:.2f} dB / "
      f"최대 {ray['per_angle_absdiff_db']['max']:.1f} dB")"""
),

# ── 17. §6 종합 판정 ─────────────────────────────────────────────────────
md(
"## 6. 종합 판정 — 무엇을 믿고, 무엇을 조심할 것인가",
"",
"다섯 잣대를 한 표로 모으면 이 메쉬·RCS 파이프라인의 **신뢰 경계**가 나온다. 아래 수치는 전부 이 편에서 나온 것의 재인용이다 (← 출처: mesh_verify.json C/D/G/H/I).",
"",
"### 믿어도 되는 것",
"",
f"- **순서 (드론 간 상대 비교)** — 치수 최악 {max(worst.values()):.1f}% · 스캔 p50 {s2c['p50']:.1f} mm 수준의 형상 충실도면 \"S1000+ > Mavic > Mini\" 같은 기종 간 RCS 서열은 형상 오차로 뒤집히지 않는다.",
f"- **규모 (방위평균 dBsm 의 자릿수)** — 수치 해상도를 2배로 올렸을 때 방위평균 이동이 PO {hm['azavg_dbsm']['diff']:+.2f}/{hp['azavg_dbsm']['diff']:+.2f} dB, SBR {RAY['azavg_dbsm']['diff']:+.2f} dB. 계산 격자가 결론을 흔들지 않는다.",
"- **평균·분포 통계** — 방위평균, 백분위수, 히스토그램. 널이 흔들려도 이 통계들은 안정적이었다.",
"",
"### 조심할 것",
"",
f"- **개별 널·개별 각도의 dB 값** — PO 점간격에 최대 {hm['per_angle_absdiff_db']['max']:.0f} dB, SBR 광선 밀도에 최대 {RAY['per_angle_absdiff_db']['max']:.0f} dB 까지 민감하다. \"방위 137° 에서 −38 dBsm\" 같은 문장은 이 파이프라인이 보증하지 않는다.",
f"- **절대 dBsm 은 ±2~3 dB 로 읽어라** — 수치 수렴(±0.5 dB 급)에 재질 |Γ| 불확실성과 형상 단순화가 얹힌다. 이는 실측 문헌 자체가 세팅(자세·대역·편파)에 따라 ±수 dB 흩어진다는 report08 의 스프레드 논거와 정확히 맞물리는 폭이다 — 우리 절대값 주장도 그 이상 정밀한 척하지 않는다.",
f"- **Mini 5 Pro 의 대각 기준값은 추정(±20 mm)** — 오차표의 0% 는 추정치 대비 0% 다. 실기체 실측(프로젝트 방향의 Mavic4Pro+Matrice4E 실측 2종에 준하는 확인)이 생기기 전까지 Mini 절대 크기 관련 주장에는 이 꼬리표가 붙는다. ← 출처: docs/SPECS.md 'Mini 5 Pro' 검증 절",
"- **솔리드 근사** — 부피·밀도는 스모크 테스트용이다. 내부 구조(빈 공간·배선)가 필요한 논의에는 쓰지 마라.",
"",
"### 기존 리포트와의 연결",
"",
"- `../report03.ipynb` — **실물 대조** 편: 여기서 검증한 그 스캔 점구름으로 파라메트릭 vs 실물 형상의 **RCS 패턴 A/B** 비교까지 수행한다 (형상 리얼리즘이 RCS 에 주는 영향 정량화).",
"- `../report08.ipynb` — **RCS 결과·문헌 대조** 편: 이 편이 세운 신뢰 경계(±2~3 dB, 평균 중심) 위에서 문헌 실측치와 앵커링한다.",
),

# ── 18. 재현 + 다음 ──────────────────────────────────────────────────────
md(
"## 재현 방법",
"",
"```bash",
"# 1) 증거 JSON 재생성 (A~I 전 섹션; I 는 GPU 필요 — 없으면 --skip-sbr)",
"~/.venvs/py312/bin/python report_mesh/src/verify_mesh_suite.py",
"# 2) 그림 재생성",
"~/.venvs/py312/bin/python report_mesh/src/viz_mesh_reports.py",
"# 3) 이 노트북 재생성",
"~/.venvs/py312/bin/python report_mesh/src/make_mesh08.py",
"```",
"",
"실물 스캔 점구름이 없다면: `src/prep_cad_scan.py` docstring 의 archive.org 미러에서 원본 STL 을 받아 같은 스크립트로 전처리한다 (Thingiverse thing:1456295, CC-BY — 저작자표시 유지).",
"",
"---",
"",
"**다음 리포트** → `mesh09_*.ipynb` — mesh 가이드 시리즈의 다음 편 (이 저장소 `report_mesh/` 에서 이어진다).",
),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh08_verify_reality.ipynb")
json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
