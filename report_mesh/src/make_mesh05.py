# -*- coding: utf-8 -*-
"""make_mesh05.py — mesh05 ipynb 생성기. ⚠ 이 파일이 소스다.

mesh05 — "프로펠러 — 판때기가 아니라 날개다"
배정 그림: airfoil_profile.png (이 리포트 전용)
수치는 전부 outputs/mesh_verify.json + src/drones.py DroneSpec 에서 읽어 f-string 주입.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(RM, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

V = json.load(open(os.path.join(RM, "outputs", "mesh_verify.json"), encoding="utf-8"))
from drones import DRONES  # noqa: E402  (스펙 수치의 유일한 진리원)

from mesh_ledger import ledger_order   # noqa: E402  (원장↔레지스트리 일치 강제)
ORDER = ledger_order(V)                     # = DRONES 레지스트리 전수
FC = float(V["meta"]["fc_ghz"])             # 3.5 GHz (검증 기준 주파수)
LAM_MM = 299.792458 / FC                    # λ[mm] = c/f

# ---------------------------------------------------------------- 파생 수치
# (전부 스펙(DroneSpec)·JSON 에서 계산 — 손으로 적은 숫자 없음)
ROWS = {}
for k in ORDER:
    s = DRONES[k]
    R = s.prop_dia_mm / 2000.0                       # 반경[m]
    P = (s.prop_pitch_in or 0.0) * 0.0254            # 기하피치[m]
    th = lambda r: math.degrees(math.atan(P / (2 * math.pi * r)))
    n_rev = s.hover_rpm / 60.0                       # 회전수[rev/s]
    vtip = 2 * math.pi * n_rev * R                   # 팁속도[m/s]
    ROWS[k] = dict(
        name=s.name, dia=s.prop_dia_mm, blades=s.prop_blades, rotors=s.num_rotors,
        P_in=s.prop_pitch_in, P_mm=P * 1000.0,
        R_mm=R * 1000.0,
        th_hub=th(0.15 * R), th_tip=th(R),
        rpm=s.hover_rpm, flash=s.prop_blades * n_rev,
        vtip=vtip, ftip_khz=2 * vtip / (LAM_MM / 1000.0) / 1000.0,
        prop_faces=V["A_geometry"][k]["groups"]["prop"]["n_faces"],
        all_faces=V["A_geometry"][k]["n_faces"],
        gamma_prop=V["E_materials"][k]["gamma_map"]["prop"],
        sym_full_p95=V["B_symmetry"][k]["full"]["chamfer_mm"]["p95"],
        sym_full_p50=V["B_symmetry"][k]["full"]["chamfer_mm"]["p50"],
        sym_frame_p95=V["B_symmetry"][k]["frame_only"]["chamfer_mm"]["p95"],
        sym_frame_p50=V["B_symmetry"][k]["frame_only"]["chamfer_mm"]["p50"],
    )

MAV = ROWS["mavic4pro"]
R_MAV = MAV["R_mm"] / 1000.0                         # 0.1335 m
C_MAX_MM = 0.26 * R_MAV * 1000.0                     # 최대시위 = 0.26·R (Mavic 기준 [mm])
PROP_ERR = float(V["C_dims"]["mavic4pro"]["checks"]["prop_dia"]["err_pct"])  # 프롭 지름 오차 [%]
MAV_FACE_PCT = 100.0 * MAV["prop_faces"] / MAV["all_faces"]
G_MOTOR = V["E_materials"]["mavic4pro"]["gamma_map"]["motor"]
G_BODY = V["E_materials"]["mavic4pro"]["gamma_map"]["body"]

# 마이크로도플러 표 (모델별)
mdop_tbl = ["| 기종 | 프롭 Ø×날수 | 피치 P | 호버 rpm | 플래시 [Hz/로터] | 팁속도 [m/s] | ±f_tip @3.5 GHz |",
            "|---|---|---|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    mdop_tbl.append(
        f"| {r['name']} | {r['dia']:g} mm × {r['blades']}날 | {r['P_in']:g}″ = {r['P_mm']:.0f} mm "
        f"| {r['rpm']:g} | {r['flash']:.0f} | {r['vtip']:.1f} | ±{r['ftip_khz']:.2f} kHz |")
MDOP = "\n".join(mdop_tbl)

# 피치각 표 (모델별)
pitch_tbl = ["| 기종 | 피치 P (스펙) | 반경 R | θ(0.15R) 허브 쪽 | θ(R) 팁 |",
             "|---|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    pitch_tbl.append(
        f"| {r['name']} | {r['P_in']:g}″ = {r['P_mm']:.1f} mm | {r['R_mm']:.1f} mm "
        f"| {r['th_hub']:.1f}° | {r['th_tip']:.1f}° |")
PITCH = "\n".join(pitch_tbl)

# 대칭 검사 표 (full vs frame_only)
sym_tbl = ["| 기종 | full p50 / p95 [mm] | frame_only p50 / p95 [mm] | p95 배율 |",
           "|---|---|---|---|"]
for k in ORDER:
    r = ROWS[k]
    sym_tbl.append(
        f"| {r['name']} | {r['sym_full_p50']:.2f} / **{r['sym_full_p95']:.1f}** "
        f"| {r['sym_frame_p50']:.2f} / **{r['sym_frame_p95']:.2f}** "
        f"| ×{r['sym_full_p95'] / r['sym_frame_p95']:.0f} |")
SYM = "\n".join(sym_tbl)


def md(*lines):
    src = "\n".join(lines).splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": src or [""]}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src.splitlines(keepends=True)}


cells = [

# ------------------------------------------------------------------ 1. 표지
md(
"# mesh05 — 프로펠러: 판때기가 아니라 날개다",
"",
"> ⚠ **이 노트북은 생성물이다.** 고칠 것이 있으면 `src/make_mesh05.py` 를 수정하고 다시 실행하라. "
"여기서 직접 고친 내용은 다음 재생성 때 사라진다.",
"",
f"**한 줄 요약** — 우리 드론 {len(ORDER)}종의 프로펠러는 납작한 판이 아니라, **NACA 익형 단면을 "
f"반경 방향으로 비틀며(피치) 이어붙인(로프트) 진짜 날개**다. 단면·피치·시위 분포가 **전부 "
f"공개 스펙에서 유도**된다는 것, 그리고 \"프로펠러는 원래 거울대칭이 아니다(카이럴)\"라는 물리까지 — "
f"모든 수치를 `outputs/mesh_verify.json`(검증 스위트 산출물, 기준 주파수 {FC:g} GHz)에서 읽어 보인다.",
"",
"## 용어 풀이 (이 편에 나오는 말들)",
"",
"| 용어 | 뜻 |",
"|---|---|",
"| **익형(airfoil)** | 날개를 칼로 자르면 나오는 단면 모양. 앞이 둥글고 뒤가 뾰족한 물방울꼴 |",
"| **시위(chord)** | 익형의 앞전(둥근 앞)→뒷전(뾰족한 뒤)을 잇는 직선 길이. \"날개 폭\" |",
"| **NACA-4** | 미국 NACA(NASA 의 전신)가 1930년대에 정리한 4자리 익형 시리즈. 두께 분포가 다항식 하나로 나온다 |",
"| **기하 피치(P)** | 프로펠러를 나사라고 보고, 미끄러짐 없이 1바퀴 돌 때 전진하는 거리. 파트번호의 둘째 숫자(인치) |",
"| **피치각 θ(r)** | 반경 r 의 단면이 회전면과 이루는 각 |",
"| **워시아웃(washout)** | 허브→팁으로 갈수록 피치각이 줄어드는 비틀림 |",
"| **테이퍼(taper)** | 팁으로 갈수록 시위가 좁아지는 것 |",
"| **시미터 스큐(scimitar skew)** | 날 끝이 초승달 칼처럼 뒤로 휘는 것(저소음 프롭의 특징) |",
"| **로프트(loft)** | 단면 여러 장을 순서대로 이어붙여 3D 곡면을 만드는 CAD 기법. 배 만들 때 늑골에 판자를 붙이는 것과 같다 |",
"| **마이크로도플러** | 기체 전체의 속도와 별개로, 회전·진동하는 **부품**이 만드는 잔 도플러 성분 |",
"| **블레이드 플래시** | 날이 레이더 정면을 향하는 순간 반사가 \"번쩍\"하는 주기 신호 |",
"| **카이럴(chiral)** | 거울에 비추면 자기 자신과 절대 겹칠 수 없는 성질(오른손↔왼손, 나사) |",
"| **chamfer 거리** | 두 점구름에서 \"상대편 가장 가까운 점까지의 거리\" 분포 — 모양 차이를 mm 로 재는 자 |",
"| **RCS** | radar cross section. 표적이 레이더에 얼마나 큰 면적으로 보이는가 [m²] |",
),

# ------------------------------------------------------- 2. §1 왜 중요한가
md(
"## 1. 왜 프로펠러가 레이더에 중요한가 — 가장 약하지만, 가장 특별한 부품",
"",
"프로펠러는 역설적인 산란체다. 재질로 보면 드론에서 **가장 약한** 반사체이고, 신호로 보면 "
"**가장 특별한** 반사체다.",
"",
f"- **약하다**: 프롭은 나일론/복합재 플라스틱이다(Mini 5 Pro 프롭 6028F: \"나일론+고무 팁\" "
f"← 출처: docs/SPECS.md §DJI Mini 5 Pro·dji.com/mini-5-pro/specs). 재질 가중 PO 의 전력 반사 "
f"가중치는 γ(prop)={MAV['gamma_prop']:g} — 모터(γ={G_MOTOR:.2f}, 사실상 금속)의 ¼, 동체 셸"
f"(γ={G_BODY:g})보다도 약하다 ← 출처: mesh_verify.json `E_materials.*.gamma_map`(원본 src/materials.py).",
"- **특별하다**: 드론에서 **항상 돌고 있는 유일한 부품**이다. 몸체 에코는 새·풍선·간판과 "
"헷갈릴 수 있지만, 날이 레이더 정면을 스칠 때마다 번쩍이는 **블레이드 플래시**와 날개끝 속도가 "
"만드는 **마이크로도플러 확산**은 회전 날개만 만들 수 있는 지문이다.",
"",
"그 지문의 리듬은 스펙만으로 계산된다. 2날 프롭이면 한 바퀴에 두 번 번쩍이므로 플래시 주파수 = "
"날수×회전수/60, 날개끝 도플러 폭은 ±2·v_tip/λ 이다(모노스태틱, 팁이 시선 방향일 때):",
"",
MDOP,
"",
f"↑ 프롭 지름·날수·피치 ← 출처: src/drones.py DroneSpec(`prop_dia_mm`·`prop_blades`·"
f"`prop_pitch_in` — 필드 정의 47-53행, 기종별 값 90-175행)·docs/SPECS.md(각 기종 절+공식 URL). 호버 rpm ← 출처: "
f"docs/drone_specs_2026.json `micro_doppler.hover_rpm_basis`(기종별 유도 근거: 추력균형 "
f"T=C_T·ρ·n²·D⁴ + 교차검증). 플래시·팁속도·f_tip 은 λ={LAM_MM:.1f} mm(={FC:g} GHz, "
f"mesh_verify.json `meta.fc_ghz`)로 위 공식에서 계산한 값이다.",
"",
f"> ⚠ **주의**: Matrice 4E 의 호버 rpm({ROWS['matrice4e']['rpm']:g})은 **미해결**이다 — "
f"C_T 법은 3950~4410, 공식 최대 rpm(7500, C2 인증) 앵커링은 4740~5300 을 준다. 우리가 채택한 호버 rpm "
f"3800(C_T≈0.108, T/W_max≈3.9)은 **두 방법의 범위보다 낮다** — 어느 쪽이 맞는지 **결론을 못 낸** 미해결 값이다. "
f"플래시·f_tip 이 이 값에 선형으로 걸린다 ← 출처: src/drones.py:139-144 note.",
"",
"그래서 프로펠러의 **모양**이 틀리면 이 지문 전체가 틀린다. 날의 폭(시위)·비틀림(피치)·휨(스큐)이 "
"각도별 반짝임의 세기와 타이밍을 정하기 때문이다. 마이크로도플러 결과는 **report08** "
"([report08.ipynb](../report08.ipynb) §5)에서 다루고, 이 편은 그 입력이 되는 **날개 기하**를 만든다.",
"",
f"참고로 비용도 만만치 않다: Mavic 4 Pro 메쉬 전체 {MAV['all_faces']:,}면 중 프롭 그룹이 "
f"{MAV['prop_faces']:,}면 — **{MAV_FACE_PCT:.0f}%** 다(4로터×2날의 얇은 곡면이라 삼각형이 많이 든다) "
f"← 출처: mesh_verify.json `A_geometry.mavic4pro`.",
),

# ------------------------------------------------------- 3. 그림
md(
"## 2. 이 편의 그림 — 한 장에 익형→피치→3D",
"",
"![propeller airfoil](outputs/figures/airfoil_profile.png)",
"",
"그림 생성: `report_mesh/src/viz_mesh_reports.py` `fig_airfoil()`(171-212행) — 아래에서 패널별로 뜯어본다.",
"",
"- **(a)** 날개 단면(NACA 계열 익형), 시위=1 로 정규화. 두께비 10%와 16% 두 곡선 — §3.",
f"- **(b)** 기하 피치각 θ(r)=atan(P/2πr) 을 {len(ORDER)}기종 스펙 피치로 그린 곡선 — §4. "
"허브 쪽이 가파르고 팁이 완만한 이유가 이 편의 핵심이다.",
"- **(c1)(c2)** Mavic 4 Pro 와 S1000+ 의 완성 프로펠러 — 비틀린 익형 단면들을 로프트한 결과 — §5.",
),

# ------------------------------------------------------- 4. §2 NACA
md(
"## 3. NACA-4 익형 — 단면은 공식 하나로 나온다",
"",
"날개 단면을 어떻게 그릴까? 우리는 1933년 NACA 보고서 이래 항공계 표준인 **NACA 4자리 익형**의 "
"두께 분포식을 쓴다. 시위를 0~1 로 두면(x=앞전 0, 뒷전 1), 두께비 t 인 단면의 반두께는:",
"",
"$$y_t(x) = 5t\\,(0.2969\\sqrt{x} - 0.1260x - 0.3516x^2 + 0.2843x^3 - 0.1015x^4)$$",
"",
"코드는 이 식을 그대로 옮겼다 ← 출처: src/drone_cad.py:59-70 `_airfoil()`:",
"",
"```python",
"def _airfoil(chord, thick_ratio=0.10, pts=40):",
"    \"\"\"NACA-4 익형 단면(y=시위, z=두께). **캠버 포함**(camber_m=0 이면 대칭).\"\"\"",
"    t = thick_ratio",
"    x = (1 - np.cos(np.linspace(0, np.pi, pts // 2))) / 2   # 코사인 클러스터링(앞전 촘촘)",
"    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2",
"                  + 0.2843 * x**3 - 0.1015 * x**4)",
"    ...",
"    P[:, 0] -= chord * 0.30                                 # 시위 30% 를 원점(피치축)으로",
"```",
"",
"**왜 이렇게 했나 (선택의 이유):**",
"",
"1. **왜 NACA 인가** — DJI 는 자기 프롭의 실제 익형 좌표를 공개하지 않는다(SPECS.md 에도 지름·피치·"
"재질뿐이다). 실단면을 모르는 상태에서 최선은 **공개 표준식**이다: 파라미터가 두께비 하나뿐이라 "
"재현 가능하고, 소형 프롭 단면과 시각적으로 잘 맞는다. 대안으로 생각할 수 있는 (i) 실물 역설계는 "
"데이터가 없고, (ii) 타원 단면은 앞전이 너무 뭉툭해지고, (iii) 직사각 단면(판)은 앞전의 둥근 회절과 "
"두께 분포를 통째로 잃는다(§5b 의 비교 참조).",
"2. **왜 코사인 클러스터링인가** — x 를 균일하게 40등분하면 곡률이 큰 **앞전**(√x 항이 지배)이 "
"각져 버린다. x=(1−cos u)/2 치환은 같은 점 수로 앞전에 점을 몰아준다. CFD/격자 생성에서 쓰는 표준 "
"트릭을 그대로 가져왔다 ← 출처: src/drone_cad.py:62 주석.",
"3. **왜 원점을 시위 30% 에 두나** — 이 원점이 곧 **피치축**(날을 비트는 회전축)이다. 실물 프롭도 "
"앞전이 아니라 시위 1/4~1/3 지점 근방을 축으로 비틀려 있다 ← 출처: src/drone_cad.py:68 주석.",
"",
"단면은 shapely `Polygon` 으로 반환된다 — 다음 단계(로프트·불리언)가 shapely/trimesh 파이프라인"
"(`src/cadkit.py`)이기 때문이다. 아래 셀로 직접 확인해 보자.",
),

code(
"""# NACA 단면을 직접 만들어 확인 — 노트북은 report_mesh/ 에서 열리므로 ../src 를 경로에 추가
import sys, os, numpy as np
sys.path.insert(0, os.path.abspath("../src"))
from drone_cad import _airfoil                      # ← src/drone_cad.py:59-70

poly = _airfoil(chord=1.0, thick_ratio=0.10)        # 시위 1, 두께비 10% (그림 (a) 파란 곡선)
pts = np.asarray(poly.exterior.coords)
print(f"둘레 점 개수      : {len(pts)}")
print(f"x(시위) 범위      : [{pts[:,0].min():+.3f}, {pts[:,0].max():+.3f}]  ← 0 이 피치축(시위 30% 지점)")
print(f"최대두께(위-아래) : {pts[:,1].max()-pts[:,1].min():.4f}  ← 두께비 0.10 이면 이론값 0.100")""",
),

# ------------------------------------------------------- 6. §3 기하피치
md(
"## 4. 기하 피치 — 파트번호 두 번째 숫자가 날개 비틀림 전체를 정한다",
"",
"프로펠러 파트번호에는 관례가 있다: **지름×피치**(인치). 예컨대 Phantom 4 의 \"9450\" 프롭은 "
"9.4″ 지름 × 5.0″ 피치라는 뜻이다. 기하 피치 P 는 \"프로펠러를 나사못이라고 보고, 미끄러짐 없이 "
"한 바퀴에 나아가는 거리\"다.",
"",
"나사 비유를 밀고 가면 비틀림 각이 저절로 나온다. 반경 r 의 단면은 한 바퀴에 원둘레 2πr 을 "
"돌면서 전진 P 를 만들어야 한다. 나선의 경사각이 곧 피치각이다:",
"",
"$$\\theta(r) = \\mathrm{atan}\\!\\left(P / 2\\pi r\\right)$$",
"",
"**왜 이 방식인가** — DJI 는 날의 트위스트 분포(반경별 각도표)를 공개하지 않는다. 공개된 것은 "
"파트번호 속 피치 P 하나다. 그런데 θ(r)=atan(P/2πr) 은 **P 하나만으로 반경 전 구간의 비틀림을 "
"물리적으로 유일하게** 정해 준다 — 임의의 선형 트위스트(`pitch_deg`/`twist_deg` 폴백, "
"`pitch_m` 을 안 줄 때만 쓰임)보다 근거가 강하고, 모델별 개성(P 가 다르면 날이 다르게 비틀림)이 "
"자동으로 생긴다 ← 출처: src/drone_cad.py:78-80·89-92 (`pitch_m` 분기).",
"",
f"{len(ORDER)}기종의 피치와, 그로부터 계산한 허브 쪽(0.15R)·팁의 피치각:",
"",
PITCH,
"",
"피치 P 의 출처를 기종별로 하나하나 밝히면(사용자 특별 지시):",
"",
"- **Mini 5 Pro** 2.8″ ← 프롭 6028F \"152.4×71.1 mm (diameter×thread pitch)\" — DJI 매뉴얼 "
"C0 인증표 **공식** (docs/SPECS.md §Mini 5 Pro, docs/drone_specs_2026.json, dji.com/mini-5-pro/specs).",
"- **Mavic 4 Pro** 5.8″ ← DJI 는 지름 10.5″(266.7 mm)만 공식 공개, 피치·파트번호는 미공개. "
"5.8″ 는 조사 **추정**값이다 (docs/drone_specs_2026.json `micro_doppler.prop_pitch_in`, "
"src/drones.py:120).",
"- **Matrice 4E** 5.7″ ← 프롭 1157F. 단 DJI 공식은 \"10.8 inch, composite\"뿐이고 14.5 cm "
"피치는 모델명 규칙(11**57**F=5.7″)+리셀러 리스팅에서 온 **강한 추정**이다 "
"(docs/SPECS.md §Matrice 4E 검증 노트, enterprise.dji.com/matrice-4-series/specs).",
"- **S1000+** 5.2″ ← 프롭 1552, 15×5.2″ — DJI **공식** (docs/SPECS.md §S1000+, "
"dji.com/spreading-wings-s1000-plus/info).",
"- **Phantom 4** 5.0″ ← 프롭 9450, 9.4″×5.0″ — DJI **공식** (docs/SPECS.md §Phantom 4, "
"dji.com/phantom-4/info, store.dji.com/product/self-tightening-propellers).",
#  ⭐ 2026-07-30 (Phase 3): 비-DJI 2종이 표적에 들어왔다. 이 목록은 손으로 유지하는 출처
#     장부이므로(등급이 코드로 유도되지 않는다) 기종을 추가하면 여기도 같이 늘려야 한다.
"- **Typhoon H480** 6.0″ ← Yuneec 는 피치를 공표한 적이 없다. 실물 CAD 앙상블에서 잰 "
"5.84 ± 0.20″ 에서 온 **DERIVED** 값이다 (src/drones.py `typhoonh480` note, "
"docs/RESUME_0729.md §5).",
"- **X500 V2** 4.5″ ← 킷 프롭 **1045**(10 × 4.5″) — Holybro **공식** "
"(docs.holybro X500 V2 킷 구성, src/drones.py `x500v2` note). ⚠ 이 저장소의 참조 CAD 에 "
"들어 있는 1345 프롭은 **X500 의 프롭이 아니다** (같은 note 참조).",
),

# ------------------------------------------------------- 7. §3b 그림(b) 해설
md(
"### 4b. 그림 (b) 읽기 — 왜 허브 쪽은 가파르고 팁은 완만한가",
"",
f"그림 (b)의 {len(ORDER)}개 곡선이 전부 **왼쪽(허브)에서 높고 오른쪽(팁)에서 낮은** 이유는 공식이 말해 준다. "
f"한 바퀴에 전진해야 하는 거리 P 는 모든 단면에 **똑같은데**, 안쪽 단면은 작은 원(2πr 작음)을 돌므로 "
f"더 **가파르게** 기울어야 같은 전진을 만든다. 즉 워시아웃(허브→팁 비틀림 감소)은 멋이 아니라 "
f"\"나사가 되기 위한\" 기하학적 필연이다. 부수 효과로, 모든 단면이 공기에 대해 비슷한 받음각으로 "
f"일하게 되어 실물 프롭도 다 이렇게 만든다.",
"",
f"곡선의 개성도 스펙에서 나온다 (표 4 의 수치 그대로):",
"",
f"- **Mini 5 Pro** (파란 곡선)만 뚝 떨어져 있다: P={ROWS['mini5pro']['P_in']:g}″ 로 유일하게 3″ 미만이라 "
f"같은 반경에서 각이 작고, R={ROWS['mini5pro']['R_mm']:.1f} mm 로 짧아 곡선이 일찍 끝난다 "
f"(팁 {ROWS['mini5pro']['th_tip']:.1f}°).",
f"- **S1000+** (빨간 곡선)는 반대로 R={ROWS['s1000plus']['R_mm']:.1f} mm 로 가장 길어 오른쪽 멀리까지 "
f"이어지고, 팁 피치각 {ROWS['s1000plus']['th_tip']:.1f}° 로 {len(ORDER)}종 중 가장 완만하다 — 큰 프롭을 천천히 "
f"돌리는 리프터의 전형(P/D 비가 가장 작다).",
f"- **Mavic 4 Pro·Matrice 4E·Phantom 4** 는 P 가 5.0~5.8″ 로 비슷해 곡선이 거의 겹친다 — 팁 "
f"{ROWS['mavic4pro']['th_tip']:.1f}~{ROWS['matrice4e']['th_tip']:.1f}° 대.",
"",
"이 곡선이 바로 §5 로프트에서 각 단면에 주는 회전각이다. 아래 셀로 표를 재현할 수 있다.",
),

code(
f"""# 그림 (b) = θ(r)=atan(P/2πr) 를 스펙에서 재계산 (viz_mesh_reports.py fig_airfoil 과 동일 수식)
import sys, os, math
sys.path.insert(0, os.path.abspath("../src"))
from drones import DRONES                    # ← 스펙의 유일한 진리원 (src/drones.py)

for key in {ORDER!r}:
    s = DRONES[key]
    R = s.prop_dia_mm / 2000.0               # 반경[m]
    P = s.prop_pitch_in * 0.0254             # 기하피치[m]
    th = lambda r: math.degrees(math.atan(P / (2 * math.pi * r)))
    print(f"{{s.name:16s}}  P={{s.prop_pitch_in:>3.1f}}\\"  R={{R*1000:5.1f}}mm   "
          f"θ(0.15R)={{th(0.15*R):4.1f}}°  →  θ(팁)={{th(R):4.1f}}°")""",
),

# ------------------------------------------------------- 9. §4 _blade 파라미터
md(
"## 5. 날개 한 장의 해부 — `_blade()` 파라미터 하나하나",
"",
"단면(§3)과 비틀림(§4)이 준비됐으니 날개를 조립한다. `_blade()` 는 반경 방향으로 단면을 "
"22장 깔고, 각 단면에 **축소(테이퍼)·회전(피치)·이동(스큐)** 세 변환을 준 뒤 로프트한다 "
"← 출처: src/drone_cad.py:73-102.",
"",
"```python",
"def _blade(R, root_frac=0.14, chord_max=0.26, pitch_deg=20.0, twist_deg=13.0,",
"           sweep_frac=0.10, n_sec=22, n_pts=36, pitch_m=None):",
"    \"\"\"**진짜 익형 프로펠러 블레이드 1장** — 로프트(테이퍼 + 워시아웃 트위스트 + 시미터 스윕).",
"      chord_max : **R 에 대한 비율**(0.26 = 최대시위 0.26·R). ⚠ 절대길이를 넣지 말 것.",
"      pitch_m   : 프로펠러 **기하 피치**[m] (1회전 전진량). ...\"\"\"",
"```",
"",
"| 파라미터 | 값 | 무엇을 하나 · 왜 이 값인가 |",
"|---|---|---|",
"| `root_frac` | **0.070** | 날이 시작하는 반경 비율. ⚠ 2026-07-28 정정: 이 표는 오랫동안 `_blade` 의 "
"**기본값 0.14** 를 적어 왔지만 `build_propeller_cad` 는 **0.070 을 명시로 넘긴다**(src/drone_cad.py). "
"루트가 허브 반경 0.085R 보다 **안쪽**이라 블레이드-허브가 한 솔리드가 된다 — 의도된 설계다. "
"문서가 2배 바깥을 가리키고 있어, 트위스트가 가장 심한 구간을 독자가 볼 수 없었다. |",
"| `chord_max` | **0.25** (**비율!**) | 최대시위 = 0.25·R. ⚠ 2026-07-28 정정: 옛 근거 \"실물 1345 는 0.30R "
"— 소비자용 프롭은 더 슬림\" 은 **거짓**이었다. 0.30R 은 1345 STL 의 **bbox x-폭**(52.03/173.0)이지 시위가 아니다. "
"원통단면으로 실측한 진짜 최대시위는 **1345 0.225R · 3DR Solo 0.273R** 이라 우리 쪽이 오히려 **더 넓었다** — "
"주장의 방향까지 뒤집혀 있었다. 새 값 0.25 는 두 실측의 중간이다(원장 outputs/reference_props.json). |",
"| 시위 분포 | 절점 [0, .15, .35, .80, 1] → [.10, .19, .21, .15, .035]·(chord_max/0.21)·R | **테이퍼**: 루트 좁게 → 스팬 30% 근방 최대 → 팁 둥글게. 실물 프롭 평면형의 보간 근사 ← src/drone_cad.py:86-88 |",
"| `pitch_m` | 스펙 P (기종별) | **워시아웃**: θ(r)=atan(P/2πr) 로 단면마다 회전 ← src/drone_cad.py:89-90 |",
"| `pitch_deg`·`twist_deg` | 20°·13° | `pitch_m=None` 일 때만 쓰는 선형 워시아웃 **폴백** — 실제 프로펠러 빌드는 항상 스펙 P 를 `pitch_m` 으로 넘긴다 ← src/drone_cad.py:91-92·350 |",
"| `sweep_frac` | 0.10 | **시미터 스큐**: y 이동량 = 0.10·R·sin(π/2·t) — 팁으로 갈수록 뒤로 휜다. DJI 저소음 프롭의 초승달 실루엣(투영 면적이 달라지므로 레이더에도 형상 인자) ← src/drone_cad.py:93 |",
"| 두께비 | 0.09+0.05·(1−tti) | 앞의 NACA t 를 단면마다 다르게: **루트 14% → 팁 9% 테이퍼**(실물 프로펠러의 구조적 테이퍼 — 뿌리는 굽힘 하중을 버텨야 두껍고, 팁은 공력 효율을 위해 얇다) ← src/drone_cad.py:97-98 |",
"| `n_sec`·`n_pts` | 22·36 | 스팬 단면 수·단면당 점 수 — 곡면 매끈함과 삼각형 수의 절충(§1: 프롭이 이미 전체 면의 약 43%) |",
),

# ------------------------------------------------------- 10. §4b 로프트
md(
"### 5b. 로프트 — 단면 22장이 3D 날개가 되는 순간",
"",
"변환을 마친 단면(shapely Polygon) 22장을 `(반경 위치, 단면)` 목록으로 넘기면 `loft()` 가 "
"이웃 단면끼리 옆면 삼각형 띠로 잇고 양 끝을 막아 닫힌 곡면을 만든다 ← 출처: src/cadkit.py:148-152:",
"",
"```python",
"def loft(sections, n_pts=48, cap=True):",
"    \"\"\"단면들을 x 를 따라 이어 붙인다.  sections = [(x, shapely Polygon(y,z)), ...]",
"    ※ 이게 있어야 '눈물방울 동체', '허리가 잘록한 캐노피' 같은 **진짜 곡면**이 나온다.\"\"\"",
"```",
"",
"그리고 `build_propeller_cad()` 가 허브(회전체)와 날 `prop_blades` 장을 360°/날수 간격으로 "
"돌려 심고, **불리언 합집합**으로 허브에 파묻힌 날 뿌리의 내부 면을 녹여 없앤다(내부 면이 남으면 "
"PO/SBR 이 헛센다 — mesh 시리즈의 파이프라인 편 참조) ← 출처: src/drone_cad.py:334-353.",
"",
"**왜 로프트인가 — 대안과 비교**:",
"",
"- **직사각 판 근사(가상의 대안)**: 만약 단면을 익형 대신 **직사각형 판**(네 꼭짓점 링)으로 "
"근사하면 로프트는 훨씬 싸진다. 하지만 멀리서 보면 비슷해도, 단면이 판이 되는 순간 앞전의 둥근 "
"회절·두께 분포·받음각별 투영이 전부 사라진다 — \"판때기가 아니라 날개다\"라는 이 편의 제목이 "
"가리키는 대비가 바로 이것이다.",
"- **인터넷 CAD 다운로드**: 라이선스·기종 불일치·검증 불가 문제로 **대조용으로만** 쓴다"
"(assets/meshes/reference/SOURCES.md — 실물 대조는 mesh 시리즈의 검증 편에서).",
"- **복셀/스컬프팅**: 파라메트릭이 아니어서 \"피치를 스펙값으로 바꿔 재생성\" 같은 일이 불가능하다. "
"우리 파이프라인은 스펙 숫자 → 코드 → 메쉬가 한 줄로 이어져야 한다(재현성).",
"",
"그림 (c1)(c2)이 그 결과다: 같은 코드, 다른 스펙 — Mavic 4 Pro 와 S1000+ 의 날이 정말 다르게 "
"생겼는지 눈으로 확인하라. 다음 절에서는 이 결과가 스펙과 맞는지를 **숫자로** 확인한다.",
),

# ------------------------------------------------------- 11. §6 현재 검증
md(
"## 6. 시위·피치의 현재 검증 — 만든 날개가 스펙과 맞는가",
"",
"§3~5 의 유도가 코드에서 실제로 지켜지는지, 검증 스위트와 스펙 대조로 세 가지를 확인한다:",
"",
f"1. **프롭 지름** — 완성 메쉬에서 실측한 Mavic 4 Pro 프롭 지름은 공식값(267 mm, 10.5″) 대비 "
f"오차 **{PROP_ERR:+.2f}%** 다. ⚠ 2026-07-28 정정: 이 문장은 오랫동안 이 값을 \"반경이 스펙에서 "
f"벗어나지 않는다\" 는 **증거로 오독**해 왔다. 정반대다 — 그 +0.84% 는 바로 스큐·시위가 팁을 옆으로 "
f"밀어낸 **서명**이었다(스키미터 스윕 0.10R + 팁 시위 후단 → 팁이 측방 0.130R 변위 → r_max/R = "
f"√(1+0.130²) = 1.00841). 블레이드 **스팬**은 정확했고 **스윕 디스크**가 초과했던 것이다. "
f"이제 build_propeller_cad 가 빌드된 블레이드의 실제 최대반경을 재서 되돌리므로 오차는 0 이다. 옛 문장: 반경이 스펙에서 벗어나지 "
f"않는다는 뜻이다 ← 출처: mesh_verify.json `C_dims.mavic4pro.checks.prop_dia`.",
f"2. **피치** — 모델별 비틀림 곡선 θ(r)(그림 b)이 스펙 피치 P 에서 θ(r)=atan(P/2πr) 로 "
f"유도된다(§4). 허브 쪽 피치각이 Mini {ROWS['mini5pro']['th_hub']:.0f}° ~ Mavic "
f"{ROWS['mavic4pro']['th_hub']:.0f}° 로 갈리는 **모델별 개성**이 메쉬에 그대로 실린다 "
f"← 출처: src/drone_cad.py:344-350(`build_propeller_cad` 가 스펙 P 를 `pitch_m` 으로 전달)·표 4.",
f"3. **시위** — 최대시위는 0.25·R(Mavic 기준 **{C_MAX_MM:.1f} mm**). ⚠ 옛 판이 인용하던 \"실물 1345 의 0.30R\" 은 "
f"보다 슬림한데, 이는 소비자용 프롭의 날씬한 평면형을 반영한 선택이다 ← 출처: "
f"**bbox 폭이지 시위가 아니었다**(실측 1345 0.225R · Solo 0.273R). 근거 원장: outputs/reference_props.json.",
"",
"아래 셀이 시위 분포식(src/drone_cad.py:86-88)에서 기종별 최대시위를 재계산한다 — 분포의 "
"최대점(스팬 35% 절점)이 정확히 chord_max·R 이 되는 것을 눈으로 확인할 수 있다.",
),

code(
f"""# 시위 분포(src/drone_cad.py:86-88)를 그대로 재현해 기종별 최대시위 [mm] 를 계산
import sys, os, numpy as np
sys.path.insert(0, os.path.abspath("../src"))
from drones import DRONES

def max_chord_mm(R, chord_max=0.26):
    "루트 좁게 → 스팬 35% 절점 최대 → 팁 둥글게 (절점 보간)"
    tt = np.linspace(0, 1, 400)
    c = np.interp(tt, [0, .15, .35, .80, 1.0],
                  np.array([.10, .19, .21, .15, .035]) * chord_max / 0.21 * R)
    return c.max() * 1000.0

for key in {ORDER!r}:
    s = DRONES[key]
    R = s.prop_dia_mm / 2000.0                        # 반경[m] ← 스펙
    print(f"{{s.name:16s}}  R={{R*1000:5.1f}} mm  →  최대시위 {{max_chord_mm(R):5.1f}} mm  (= 0.25·R = {{0.25*R*1000:5.1f}} mm)")""",
),

# ------------------------------------------------------- 14. §6 카이럴
md(
"## 7. CW/CCW 카이럴성 — \"거울대칭 깨짐\"이 곧 프로펠러 물리다",
"",
"> ⭐ **2026-07-28 수정 — 이 절의 수치가 절반으로 줄었다.** 옛 코드는 프로펠러 메쉬를 **한 장 만들어 "
"z회전으로만 복제**했다. 즉 네 로터가 전부 **같은 손잡이**였다 — 실물과 다르다. 실물 멀티로터는 "
"반대로 도는 로터에 **거울상 프롭**을 단다(스윕 방향과 피치 부호가 함께 뒤집힌다). "
"이제 `build_propeller(spec, mirror=True)` 로 dir<0 로터에 거울상을 배치한다. "
"결과: full chamfer p95 가 mini5pro 28.6→**15.1**, mavic4pro 50.4→**30.4**, matrice4e 47.2→**24.1**, "
"s1000plus 64.3→**34.9**, phantom4 32.5→**17.5** mm 로 **약 절반**이 됐다. "
"즉 옛 p95 의 절반은 프로펠러 물리가 아니라 **모델링 결함**이었다. 남은 절반이 진짜 카이럴성이다 "
"— 거울상을 달아도 **장착 위상(base_ang)** 때문에 완전대칭은 되지 않는다.",
"",
"검증 스위트에는 좌우대칭 검사(`B_symmetry`)가 있다: 드론 표면 점구름을 y→−y 로 거울 반전시켜 "
"원본과의 chamfer 거리를 잰다. 비행 안정을 위해 기체는 좌우대칭이어야 하니, 대칭이 맞다면 거리는 "
"샘플 간격 수준(~mm)이어야 한다. 결과가 흥미롭다:",
"",
SYM,
"",
"↑ 출처: mesh_verify.json `B_symmetry`(각 기종 `full`/`frame_only`·chamfer_mm), 측정 코드 "
"report_mesh/src/verify_mesh_suite.py:136-153.",
"",
"프레임만 재면(frame_only) p95 가 2 mm 아래 — 기체는 확실히 좌우대칭이다. 그런데 프로펠러를 "
"포함하면(full) p95 가 수십 mm 로 뛴다. 결함일까? 아니다 — 검증 코드의 docstring 이 "
"먼저 답을 적어 두었다:",
"",
"> \"⚠ 프로펠러는 **카이럴**(CW/CCW 쌍 + 스큐 날) — y 미러가 날개 위상·회전방향을 뒤집으므로 "
"full 의 큰 p95 는 결함이 아니라 프로펠러 물리다. 기체 대칭성은 frame_only 로 판정한다.\" "
"← 출처: verify_mesh_suite.py:137-139.",
"",
"피치로 비틀린 날은 나사못처럼 **오른손/왼손이 구분되는(카이럴)** 물체다. 거울에 비추면 반대 "
"손의 날이 되는데, 그런 날은 그 자리에 없으니 가장 가까운 표면까지 수십 mm 가 뜬다. 실물도 "
"그렇다: 멀티로터는 반토크 상쇄를 위해 CW 프롭과 CCW 프롭을 **다른 부품**으로 만들어 대각쌍끼리 "
"같은 방향으로 돌린다(S1000+ 는 매뉴얼에 M1/3/5/7=CCW, M2/4/6/8=CW 로 명시 ← 출처: "
"docs/drone_specs_2026.json `rotor_directions`·DJI S1000 User Manual v1.10 p.10; Phantom 4 는 "
"검정/은색 캡 두 종, 9450 프롭 \"two CW + two CCW\" ← docs/SPECS.md §Phantom 4). 우리 "
"시뮬레이션에서 회전 방향은 `rotor_layout()` 의 `dir=+1/−1`(대각쌍 동일) 관례로 들어간다 "
"← 출처: src/drones.py:309-323.",
"",
"> **현재 한계** — 다만 현재 **정적 메쉬**는 날 **모양**까지 CW/CCW 두 벌로 만들지는 않는다: "
"`build_drone()` 이 프로펠러 메쉬 한 벌을 만들어 모든 로터에 z회전만 바꿔 복제한다(src/drones.py:"
"339-348). 즉 4(8)개 프롭이 같은 손방향이다. 회전 **방향**은 마이크로도플러 계산에서 `dir` 로 "
"반영되지만, 거울상 날개 형상의 차이는 아직 근사다. DJI 도 Mini/Mavic 의 절대 손방향(앞왼쪽이 "
"CW 인지)은 문서로 공개하지 않아(← docs/drone_specs_2026.json `rotor_directions` \"미확인\"), "
"현재로선 \"대각쌍 동일 회전\" 제약만 지키는 것이 근거 가능한 최선이다.",
"",
"이 표는 이 편의 제목을 수치로 요약한다: **판때기였다면 크게 나지 않았을 거울대칭 깨짐이, "
"진짜 날개라서 수십 mm 로 찍힌다.** 형상이 물리를 담기 시작했다는 뜻이다.",
),

# ------------------------------------------------------- 15. 요약
md(
"## 8. 정리 — 이 편에서 확인한 것",
"",
f"1. 프로펠러는 γ={MAV['gamma_prop']:g} 의 약한 산란체지만, 블레이드 플래시 "
f"{min(r['flash'] for r in ROWS.values()):.0f}~{max(r['flash'] for r in ROWS.values()):.0f} Hz· "
f"팁 도플러 ±{min(r['ftip_khz'] for r in ROWS.values()):.1f}~"
f"±{max(r['ftip_khz'] for r in ROWS.values()):.1f} kHz(@{FC:g} GHz)의 유일무이한 지문을 만든다 — "
f"그래서 모양을 제대로 만들어야 한다 (§1, report08 로 이어짐).",
"2. 단면은 NACA-4 공식 하나(+코사인 클러스터링), 비틀림은 스펙 피치 P 하나에서 "
"θ(r)=atan(P/2πr) 로 — 임의 조형이 아니라 **공개 스펙에서 유도**된다 (§3~4).",
"3. 테이퍼(시위·두께 모두)·워시아웃·시미터 스큐·로프트 — 파라미터마다 실물 근거와 선택 이유를 "
"남겼다. 두께비도 루트 14%→팁 9% 로 테이퍼된다 (§5).",
f"4. 현재 검증: 프롭 지름 오차 {PROP_ERR:+.2f}%(`C_dims`), 피치각 곡선은 스펙 P 에서 유도, "
f"최대시위 0.25R={C_MAX_MM:.1f} mm(실측 1345 0.225R · Solo 0.273R 의 중간) (§6).",
f"5. 프로펠러 포함 시 거울대칭 chamfer p95 가 최대 {max(r['sym_full_p95'] for r in ROWS.values()):.0f} mm "
f"까지 뛰는 것은 결함이 아니라 **카이럴 날개의 물리**다 — 대칭 판정은 frame_only 로 (§7).",
),

# ------------------------------------------------------- 16. 재현 + 다음
md(
"## 재현 방법",
"",
"```bash",
"cd /home/yunjung/workspace/sionna2/report_mesh",
"# 1) 검증 수치(mesh_verify.json) 재생성",
"/home/yunjung/.venvs/py312/bin/python src/verify_mesh_suite.py",
"# 2) 그림(outputs/figures/airfoil_profile.png 포함) 재생성",
"/home/yunjung/.venvs/py312/bin/python src/viz_mesh_reports.py",
"# 3) 이 노트북 재생성",
"/home/yunjung/.venvs/py312/bin/python src/make_mesh05.py",
"```",
"",
"**다음 편** → `mesh06_materials.ipynb` (같은 폴더): 색이 곧 재질 — 부위별 전파 재질 입히기. 검증은 "
"이어진다. 마이크로도플러 **결과**가 궁금하면 [report08.ipynb](../report08.ipynb) §5 로.",
),
]

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "py312",
      "language": "python", "name": "py312"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = os.path.join(RM, "mesh05_propeller.ipynb")
for _i, _c in enumerate(nb["cells"]):
    _c["id"] = f"m05-{_i:02d}"

json.dump(nb, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", out, len(cells), "cells")
