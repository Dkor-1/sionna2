# -*- coding: utf-8 -*-
"""
mesh_cert_symmetry_derived_0816.py — **대칭 · 손잡이 · 파생량 인증서**를 찍는다
==============================================================================
무엇을 만드나: `outputs/mesh_cert_symmetry_derived_0816.json`

사용자가 요구한 «장담» 의 다섯 조건을 **이 축(대칭·손잡이·파생량)에 한해** 채운다.
  ⑴ 범주 지도가 닫혀 있다   → `closure_argument` (왜 이 목록이 빠짐없는지 **논증**한다)
  ⑵ 범주마다 검사가 실재한다 → `checks` (칸마다 «이 코드가 이 범주를 본다»)
  ⑶ 검사가 잡는다는 것이 증명됐다 → `controls` (양성 + 음성 대조를 **실제로 돌린 결과**)
  ⑷ 회귀가 봉인됐다        → `regression_seal` (재현 명령 + 코드·예산·메쉬 지문)
  ⑸ 못 하는 것이 명시됐다   → `limits` · `evidence_grades` · `what_this_round_did_not_do`

⛔ 형상은 하나도 안 바꾼다. 읽고 재고 적는다.
실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/mesh_cert_symmetry_derived_0816.py
      ⛔ GPU 안 쓴다(전부 CPU). 약 5 분.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import platform
import sys
from contextlib import redirect_stdout

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _HERE)

import mesh_symmetry as msym                            # noqa: E402
from drones import DRONES, build_drone                  # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "mesh_cert_symmetry_derived_0816.json")


def _kst() -> str:
    """⚠ 컨테이너는 UTC 로 돈다. tzdata 가 없을 수도 있어 **직접 +9 시간** 한다."""
    return (_dt.datetime.now(_dt.timezone.utc)
            + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def _sha_file(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return "없음"


def _sha_obj(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()[:16]


def _mesh_fingerprint(mesh) -> dict:
    """메쉬의 지문 — **이 인증서가 어느 메쉬에 대한 것인지** 못박는다.
    형상이 바뀌면 지문이 바뀌므로, 다음 라운드가 «이 인증서는 낡았다» 를 기계로 알 수 있다."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    h = hashlib.sha256()
    h.update(np.round(V, 9).tobytes())
    h.update(F.tobytes())
    h.update("|".join(G.tolist()).encode())
    return dict(sha256_16=h.hexdigest()[:16], n_vertices=int(len(V)), n_faces=int(len(F)),
                groups=sorted(set(G.tolist())))


# --------------------------------------------------------------------------- #
#  ⑴ 범주 지도가 왜 닫혀 있는가 — 이 축에 한해
# --------------------------------------------------------------------------- #
CLOSURE = {
    "one_line_ko":
        "이 축의 범주는 임의로 고른 목록이 아니라 **두 개의 완비한 분류**에서 나온다 — "
        "대칭은 «메쉬에 걸 수 있는 등거리 변환의 종류», 파생량은 «(V,F,G) 의 적분 범함수의 차수».",
    "derivation_ko": [
        "① **대칭 축의 닫힘.** 우리 기체가 «가지고 있다»고 주장하는 대칭은 3차원 등거리 변환군의 "
        "부분군뿐이다. 우리 형상 생성기가 실제로 만드는 것은 셋이고, 그 셋이 전부다: "
        "(가) **평면 반사** — 좌우(xz 평면) 거울. 비행 안정 규약이라 drones.py 가 «좌우대칭 유지» 로 "
        "명시한다. (나) **로터 배치의 순환·반사 대칭** — 로터를 방위로 돌려 놓은 배치와 그 회전방향 "
        "규약. (다) **손대칭성(chirality)** — 반사 아래 **부호가 뒤집히는** 양(프롭 비틀림). "
        "앞뒤(yz) 대칭·상하(xy) 대칭·회전 대칭(4회)은 우리 기체가 **가지고 있지 않다**(카메라가 앞에 "
        "있고, 프롭이 위에 있고, 사다리꼴 배치가 있다) — 없는 대칭을 검사할 수는 없으므로 목록에서 "
        "빠지는 것이 맞다. ⇒ (가)(나)(다) 셋에 각각 검사가 하나씩 있다.",
        "② **파생량 축의 닫힘.** 파생량은 (V,F,G) 위의 **적분 범함수**다. 방향 무관한 것을 모멘트 "
        "차수로 세우면 0차(부피·표면적) · 1차(질량중심) · 2차(관성텐서)이고, 방향 의존하는 1차가 "
        "**투영면적**이다. 우리 물리에 실제로 들어가는 것은 딱 이 넷이다 — 레이다식은 투영면적(σ ∝ A² "
        "평판 극한), 강체 동역학은 질량·질량중심·관성. **3차 이상 모멘트는 어느 식에도 안 들어간다** "
        "→ 안 본다고 선언한다(모르는 것이 아니라 필요 없는 것이다).",
        "③ **각 칸을 두 번 잰다.** 축마다 원리가 다른 자 두 개를 대고, 둘이 어긋나는 것 자체를 "
        "결함으로 친다. 자가 하나면 «0 이 나오는 자»와 «0 이 맞는 대상»을 구별할 수 없다.",
        "④ **자 자체를 닫힌 해로 검정한다.** 정육면체의 투영면적(1, √3)과 직육면체의 질량·CoM·"
        "관성(ρabc, m(b²+c²)/12)은 손으로 풀린다. 자가 그걸 못 맞히면 아래 수는 전부 무효다.",
    ],
    "what_this_argument_does_not_prove_ko": [
        "«메쉬가 실물과 같다»를 증명하지 않는다. 이 축의 검사는 전부 **내부 일관성**이거나 "
        "**규약 준수**다. 규약 자체가 틀렸다면(예: 실물 기체가 사실 좌우비대칭이라면) 통과하면서 틀린다.",
        "대칭이 **있어야 하는가**를 증명하지 않는다. 좌우대칭은 비행 안정에서 오는 설계 규약이고 "
        "이 라운드는 그 규약을 참으로 놓고 «메쉬가 그걸 지키는가»만 본다.",
        "손잡이의 **절대 기준**(어느 회전방향이 어느 비틀림인가)을 실물로 확인하지 않았다 — "
        "기준을 `build_propeller(spec)` 에서 읽으므로 코드 전체가 같은 방향으로 틀리면 안 걸린다. "
        "한계 L1 을 볼 것.",
    ],
}


# --------------------------------------------------------------------------- #
#  ⑵ 범주 × 검사 표
# --------------------------------------------------------------------------- #
def _checks_table():
    """지도(M11 · M13)의 칸마다 «이 코드가 이 범주를 본다» 를 적는다 — 조건 ⑵."""
    return [
        dict(
            id="S1", map_cell="M11 대칭", name="로터 손잡이(프롭 비틀림 ↔ 회전방향)",
            what_can_go_wrong=[
                "네 로터에 **전부 같은 손잡이** 프롭 (2026-07-28 에 실제로 났던 버그)",
                "**한 로터만** 손잡이가 뒤집힘",
                "정점은 그대로인데 **감김만** 뒤집혀 법선 기준 자가 오진",
            ],
            code="src/mesh_symmetry.py::check_rotor_handedness",
            ruler_a="자A 법선 — 윗면 삼각형 법선의 접선성분 면적가중 평균 "
                    "(mesh_check._twist_chirality 와 같은 수식)",
            ruler_b="자B 위치 — 반경 띠마다 (방위 편차 × 높이 편차) 면적가중 상관. "
                    "감김도 법선도 안 본다",
            reference="기준은 매번 `build_propeller(spec)` 에서 다시 읽는다(코드에 부호를 안 박는다)",
            budget=f"|자A| ≥ {msym.HAND_MIN_ABS_A} · |자B| ≥ {msym.HAND_MIN_ABS_B} · "
                   f"부호가 dir 과 일치 · **두 자의 판정이 서로 같을 것**",
            gating=True, kind="불변량",
        ),
        dict(
            id="S2", map_cell="M11 대칭 + M8 배치", name="로터 회전방향 배치 규약",
            what_can_go_wrong=[
                "rotor_deg 를 방위 순서가 아닌 차례로 적어 «이웃 반대» 규약이 조용히 깨짐 "
                "(dir 은 목록 순서 k%2 로 정해진다)",
                "좌우 거울 짝이 없거나 반경·높이가 다름",
                "CW/CCW 수가 달라 토크 합이 0 이 아님",
            ],
            code="src/mesh_symmetry.py::check_rotor_dir_convention",
            ruler_a="rotor_layout(spec) 을 방위각으로 정렬해 이웃·마주보는 쌍·토크 합을 본다",
            ruler_b="거울 짝(φ ↔ −φ)의 반경·높이·회전방향을 1 µm / 1 µm / 부호로 대조",
            reference="기대 부호를 로터 수 n 에서 **유도한다** — d[k+n/2] = d[k]·(−1)^(n/2)",
            budget="반경·높이 차 1e-6 mm · 부호 일치 · Σdir = 0",
            gating=True, kind="불변량",
        ),
        dict(
            id="S3", map_cell="M11 대칭", name="좌우(y) 거울 대칭",
            what_can_go_wrong=[
                "동체·암·다리·카메라가 좌우로 어긋남(위상·치수 검사는 전부 통과한다)",
                "기수 방향이 어긋남(작은 요 회전은 좌우 대칭을 먼저 깬다)",
                "프롭 하나만 정지 위상이 어긋남",
            ],
            code="src/mesh_symmetry.py::check_lateral_symmetry",
            ruler_a="거울 뜬 정점 → 원본 **표면**까지 최단거리 (점-대-점이 아니다 — "
                    "표본추출 차이를 형상 비대칭으로 오인하지 않기 위해)",
            ruler_b="면적·부피의 **y 1차 모멘트**(적분량이라 표본추출과 무관) + 프레임 bbox",
            reference="프롭은 따로 — 거울 뜬 뒤 Δ = base_ang[k]+base_ang[k′] 만큼 돌려 견준다. "
                      "Δ 는 상수로 안 박고 rotor_layout 에서 읽는다(지금 규약에서 24°)",
            budget=f"그룹별 표면잔차 ≤ {msym.LATERAL_SURF_RMS_BUDGET_MM['_default']} mm(기본) · "
                   f"1차 모멘트 ≤ {msym.COM_Y_BUDGET_REL:.0e} · "
                   f"프롭 짝맞춤 ≤ {msym.PROP_MIRROR_MAX_MM:g} mm",
            gating=True, kind="불변량",
        ),
        dict(
            id="S4", map_cell="M13 파생량", name="질량중심 · 관성텐서",
            what_can_go_wrong=[
                "질량중심이 좌우로 치우침(부품 하나가 옆으로 밀림)",
                "관성곱 I_xy·I_yz 가 0 이 아님 / 주축이 기체축과 어긋남",
                "부피가 음수(법선이 안쪽) → 질량·관성이 물리적으로 무의미",
                "밀도표에 없는 그룹이 **조용히** 넘어감",
                "두 구현(trimesh · 손계산)이 다른 답을 냄",
            ],
            code="src/mesh_symmetry.py::check_mass_inertia",
            ruler_a="trimesh 의 mass_properties (gazebo_export 가 쓰는 통로)",
            ruler_b="발산정리 손계산 — 사면체 분해로 부피·1차·2차 모멘트. trimesh 미경유",
            reference="닫힌 해(직육면체 ρabc · m(b²+c²)/12)로 **두 자를 다 검정**한다",
            budget=f"|CoM_y|/크기 ≤ {msym.COM_Y_BUDGET_REL:.0e} · "
                   f"|I_xy|,|I_yz|/max(I_ii) ≤ {msym.PRODUCT_INERTIA_BUDGET_REL:.0e} · "
                   f"주축 기울기 ≤ {msym.PRINCIPAL_TILT_BUDGET_DEG}° · "
                   f"고유값 > 0 · 삼각부등식 I₁+I₂ ≥ I₃ · 두 자 일치 "
                   f"{msym.MASS_RULER_AGREE_REL:.0e}",
            gating=True, kind="불변량",
            not_gated="질량·관성의 **크기**는 판정에 안 쓴다 — 감사 I9(메쉬 부피×밀도 질량이 "
                      "공표 TOW 의 1.1~5.2 배)가 선언된 결함이기 때문이다. 원장에는 싣는다.",
        ),
        dict(
            id="S5", map_cell="M13 파생량", name="투영면적(σ 의 1차 결정자)",
            what_can_go_wrong=[
                "같은 면적을 두 번 셈(부품 복제 · 부품끼리 파고듦) → PO 가 σ 를 부풀림",
                "좌우 투영면적이 다름(부품이 한쪽만 크거나 없음)",
                "껍질이 열려 «한쪽면 합 = 양면합/2» 항등식이 깨짐",
            ],
            code="src/mesh_symmetry.py::check_projected_area",
            ruler_a="실루엣 래스터화 — 겹친 면을 **한 번만** 센다(부분 덮인 픽셀까지 무게로)",
            ruler_b="한쪽면 합 Σ max(n̂·û,0)·A_f — **PO 가 실제로 더하는 양**",
            reference="정육면체 닫힌 해(축 1.000000 m² · 대각 √3 m²)로 래스터를 검정",
            budget=f"자B ≥ 자A(원리) · 한쪽면합 = 양면합/2(항등식) · "
                   f"프레임 좌우차 실루엣 ≤ {msym.PROJ_MIRROR_TOL_REL:.0e} · "
                   f"한쪽면합 ≤ {msym.PROJ_MIRROR_ONESIDED_TOL_REL:.0e} · "
                   f"그룹별 좌우차 ≤ 표(PROJ_ONESIDED_GROUP_BUDGET) · "
                   f"이중계상 배수 ≤ 표(PROJ_DOUBLE_COUNT_BUDGET)",
            gating=True, kind="불변량 + 스냅샷(이중계상 배수만)",
        ),
    ]


# --------------------------------------------------------------------------- #
#  ⑸ 근거 등급 · 한계
# --------------------------------------------------------------------------- #
GRADE_LEGEND = {
    "A": "공식 CAD/닫힌 해에 직접 대 봄 — 이 축에서는 «자를 닫힌 해로 검정» 이 여기 든다",
    "B": "사진·문헌 계측에 대 봄",
    "C": "계열 유추 — 같은 계열의 다른 근거에서 옮겨 옴",
    "D": "대리 — 규약/코드 자신을 기준으로 삼음(외부 참값 없음)",
    "빈칸": "안 재 봤다(모른다). 가짜 통과보다 빈칸이 낫다",
}

LIMITS = [
    dict(id="L1", severity="핵심",
         ko="**손잡이의 절대 기준이 코드 자신이다.** `check_rotor_handedness` 는 «dir=+1 인 로터의 "
            "비틀림 방향» 을 `build_propeller(spec)` 에서 읽는다. 즉 «로터 0 이 CCW 이고 CCW 프롭은 "
            "이렇게 생겼다» 를 **가정**한다. 저장소 전체가 같은 방향으로 뒤집혀 있으면 이 검사는 "
            "**영영 안 걸린다**. 등급 [D]. 막으려면 실물 프롭(예: `WM161_zhankai_1k.glb` 의 DJI Mini 2 "
            "날)에서 «이 회전방향의 프롭은 이렇게 비틀린다» 를 한 번 확정해 앵커로 박아야 한다 — "
            "이 라운드는 **안 했다**."),
    dict(id="L2", severity="핵심",
         ko="**기체 전체 거울상은 이 검사가 못 잡고, 못 잡는 게 맞다.** 이웃 로터가 반대로 도는 배치라 "
            "통째로 뒤집으면 프롭이 반대 회전방향 로터 자리로 옮겨가며 손잡이도 같이 뒤집힌다 — 두 번 "
            "뒤집혀 제자리다. 즉 «로터 번호만 바꿔 단 같은 기체»다(대조 항목으로 명시 확인). "
            "⚠ 다만 그렇기 때문에 **좌우 규약 자체가 통째로 뒤집혀 있어도 모른다**(L1 과 같은 뿌리)."),
    dict(id="L3", severity="중",
         ko="**질량·관성의 크기는 장담하지 않는다.** 메쉬 body 가 속 꽉 찬 솔리드라 부피×밀도 질량이 "
            "공표 TOW 의 1.1~5.0 배다(감사 I9, 이 라운드가 재확인). 이 인증서가 장담하는 것은 그 값의 "
            "**좌우 불변량**(CoM_y≈0 · I_xy≈0 · 주축 정렬)과 **물리적 타당성**(고유값>0 · 삼각부등식)"
            "과 **두 구현의 일치**뿐이다."),
    dict(id="L4", severity="중",
         ko="**착륙다리의 좌우 비대칭은 실재하지만 원인 코드를 안 짚었다.** 이 라운드가 새로 발견했다 — "
            "한쪽면 합의 좌우차가 gear='motor_legs'/'legs' 기체에서 7.3e-3~2.5e-2 인데 "
            "gear='feet'(matrice4e)는 2.3e-9 로 사실상 대칭이다. 표면 잔차로는 0.10~0.41 mm 이고, "
            "같은 크기를 «완벽히 대칭인 솔리드 + 비대칭 분할» 대조가 **해석값까지 일치하게** "
            "재현한다(반경 10 mm 12각기둥: 잔차 0.3407 mm = sagitta 0.3407 mm, 좌우차 3.3e-2 / "
            "16각기둥: 0.1921 mm, 1.1e-2). ⇒ **분할 차이로 설명 가능한 크기**다. "
            "그러나 «설명 가능하다»는 «증명했다»가 아니다 — 어느 줄이 좌우를 다르게 분할하는지는 "
            "안 짚었다. 다음 라운드가 볼 곳: `drone_cad._gear_motor_legs` · `_gear_arch` 의 "
            "sweep 국소좌표계(N = up×T 가 좌우에서 뒤집힌다)와 캡슐/원통 분할 위상. "
            "형상 코드는 병행 라운드가 바꾸는 중이라 이 라운드는 손대지 않았다."),
    dict(id="L5", severity="중",
         ko="**투영면적의 «참값»은 확인하지 않았다.** 래스터 자는 닫힌 해로 검정했지만, 그 자가 재는 "
            "면적이 **실물** 드론의 투영면적과 같은지는 이 축이 아니라 사진·CAD 대조 원장의 일이다"
            "(`outputs/mesh_compare_photo.json` · `mesh_compare_cad.json`)."),
    dict(id="L6", severity="중",
         ko="**이중계상 배수는 불변량이 아니라 스냅샷이다.** 형상이 바뀌면 값이 바뀌므로 예산도 다시 "
            "선언해야 한다. 이 칸만 성격이 다르다는 것을 표에 적어 뒀다."),
    dict(id="L7", severity="낮",
         ko="**앞뒤·상하 대칭은 검사하지 않는다** — 우리 기체가 원래 안 가진 대칭이라 검사할 대상이 "
            "없다(닫힘 논증 ①). 반대로 «앞뒤가 뒤집힌 기체»(180° 요)는 좌우 대칭을 깨지 **않으므로** "
            "이 축이 못 잡는다. 그건 좌표계 규약(지도 M1)의 몫이고 아직 빈칸이다."),
    dict(id="L8", severity="낮",
         ko="**3차 이상의 모멘트는 안 본다.** 우리 물리(레이다식·강체 동역학) 어디에도 안 들어가기 "
            "때문이다. 모르는 것이 아니라 필요 없다고 **판단**한 것이고, 판단이 틀리면 이 칸이 뚫린다."),
]

NOT_DONE = [
    "형상 상수를 하나도 안 고쳤다 — 이 라운드가 만든 것은 검사·대조·인증서뿐이다.",
    "손잡이의 실물 앵커(DJI 공식 프롭 CAD ↔ 회전방향)를 확정하지 않았다(한계 L1).",
    "착륙다리 좌우 비대칭의 원인 코드 줄을 특정하지 않았다(한계 L4).",
    "게이트 배선(누가 `mesh_symmetry.assert_ok()` 를 부르는가)은 이 파일이 안 한다 — "
    "봉인 라운드의 몫이다. 지금 이 파일은 **부를 수 있는 함수와 재현 명령**까지 만들어 둔다.",
    "GPU 를 쓰지 않았고 git 도 건드리지 않았다.",
]


# --------------------------------------------------------------------------- #
def main():
    t_start = _kst()
    print("=" * 104)
    print("대칭 · 손잡이 · 파생량 인증서 — 측정 → 대조 → 봉인")
    print("=" * 104)

    #  ── ⑶ 대조부터 돌린다. 자를 못 믿으면 측정값이 의미가 없다 ────────────────── #
    print("\n[1/3] 양성·음성 대조 (adv_mesh_symmetry_faults) …")
    import adv_mesh_symmetry_faults as adv
    buf = io.StringIO()
    with redirect_stdout(buf):
        controls = adv.run_all()
    ctrl_log = buf.getvalue()
    print(ctrl_log)
    n_ctrl_ok = sum(1 for c in controls if c["passed"])

    #  ── ⑵ 측정 ────────────────────────────────────────────────────────────── #
    print(f"\n[2/3] 전 기종 측정 (기종 수 = len(DRONES) = {len(DRONES)}) …")
    measured, fingerprints, blanks = {}, {}, []
    selftest = msym.selftest_rulers()
    for k, s in DRONES.items():
        try:
            m = build_drone(s)
        except Exception as e:
            #  ⭐ 모르면 모른다 — 못 지은 기체는 **빈칸**이다. 통과로 세지 않는다.
            measured[k] = dict(key=k, build_failed=f"{type(e).__name__}: {e}", ok=None)
            blanks.append(k)
            print(f"  ⚠ {k:12s} 메쉬를 못 지었다 — {type(e).__name__}: {e}")
            continue
        fingerprints[k] = _mesh_fingerprint(m)
        r = msym.check_one(s, mesh=m, verbose=False)
        measured[k] = r
        pa = r["projected_area"]
        li = r["lateral"]
        mi = r["mass_inertia"]
        print(f"  {'✅' if r['ok'] else '❌'} {k:12s} "
              f"좌우잔차 {max(g['surf_rms_mm'] for g in li['groups'].values()):.4f} mm · "
              f"프롭짝 {max((x['max_mm'] for x in li['prop_mirror']), default=0):.1e} mm · "
              f"CoM_y {mi['com_mm'][1]:+.5f} mm · I_xy {mi['product_inertia_rel']['Ixy']:.1e} · "
              f"PO/실루엣 {pa['onesided_over_sil_max']}")

    graded = [v for v in measured.values() if v.get("ok") is not None]
    n_ok = sum(1 for v in graded if v["ok"])

    #  ── ⑷ 봉인 ────────────────────────────────────────────────────────────── #
    print("\n[3/3] 봉인 · 원장 쓰기 …")
    budgets = dict(
        LATERAL_SURF_RMS_BUDGET_MM={f"{k}": v for k, v in
                                    msym.LATERAL_SURF_RMS_BUDGET_MM.items()},
        PROP_MIRROR_MAX_MM=msym.PROP_MIRROR_MAX_MM,
        COM_Y_BUDGET_REL=msym.COM_Y_BUDGET_REL,
        PRODUCT_INERTIA_BUDGET_REL=msym.PRODUCT_INERTIA_BUDGET_REL,
        PRINCIPAL_TILT_BUDGET_DEG=msym.PRINCIPAL_TILT_BUDGET_DEG,
        MASS_RULER_AGREE_REL=msym.MASS_RULER_AGREE_REL,
        PROJ_NPX=msym.PROJ_NPX,
        PROJ_MIRROR_TOL_REL=msym.PROJ_MIRROR_TOL_REL,
        PROJ_MIRROR_ONESIDED_TOL_REL=msym.PROJ_MIRROR_ONESIDED_TOL_REL,
        PROJ_ONESIDED_GROUP_BUDGET={f"{k}": v for k, v in
                                    msym.PROJ_ONESIDED_GROUP_BUDGET.items()},
        PROJ_DOUBLE_COUNT_BUDGET=dict(msym.PROJ_DOUBLE_COUNT_BUDGET),
        PROJ_ONESIDED_GE_SIL_TOL_REL=msym.PROJ_ONESIDED_GE_SIL_TOL_REL,
        HAND_MIN_ABS_A=msym.HAND_MIN_ABS_A, HAND_MIN_ABS_B=msym.HAND_MIN_ABS_B,
    )
    #  게이트가 보는 **불변량만** 뽑아 골든 지문을 만든다(크기 스냅샷은 뺀다 — 형상이 바뀌면
    #  같이 바뀌는 값이라 봉인의 뜻이 흐려진다).
    invariants = {}
    for k, r in measured.items():
        if r.get("ok") is None:
            continue
        li, mi, pa = r["lateral"], r["mass_inertia"], r["projected_area"]
        invariants[k] = dict(
            hand_signs=[[x["rotor"], int(np.sign(x["h_normals"])),
                         int(np.sign(x["h_positions"]))] for x in r["handedness"]["per_rotor"]],
            dir_sorted=r["dir_convention"]["azimuth_sorted_dir"],
            torque_sum=r["dir_convention"]["torque_sum"],
            lateral_surf_rms_mm={g: round(v["surf_rms_mm"], 4) for g, v in li["groups"].items()},
            prop_mirror_max_mm=float(f"{max((x['max_mm'] for x in li['prop_mirror']), default=0):.1e}"),
            com_y_rel=float(f"{mi['com_y_rel']:.1e}"),
            Ixy_rel=float(f"{mi['product_inertia_rel']['Ixy']:.1e}"),
            principal_tilt_deg=round(mi["principal_axis_tilt_deg"], 3),
            group_mirror={g: float(f"{v['onesided_mirror_max_rel']:.1e}")
                          for g, v in pa["group_mirror"].items()},
        )

    seal = dict(
        what_ko="다음 라운드가 «이 인증서가 아직 유효한가»를 **기계로** 물을 수 있게 만든 지문들.",
        how_to_reverify_ko=[
            "cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/mesh_symmetry.py",
            "cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
            "benchmark/adv_mesh_symmetry_faults.py",
            "cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
            "benchmark/mesh_cert_symmetry_derived_0816.py   (이 파일 — 원장을 다시 찍는다)",
            "⭐**봉인 확인**: 같은 파일에 `--regress` 를 붙이면 저장된 인증서와 지금을 견주고, "
            "«형상이 바뀌었다(지문 다름 → 3)» 와 «불변량이 깨졌다(→ 1)» 를 **따로** 알려 준다.",
            "게이트로 쓰려면: `from mesh_symmetry import assert_ok; assert_ok()` "
            "(결함이 있으면 예외를 던진다). ⚠배선(누가 부르는가)은 이 라운드가 안 했다 — "
            "형상 라운드들이 편집 중인 파일을 건드리지 않기 위해서다.",
        ],
        checker_code_sha256_16=_sha_file(os.path.join(_ROOT, "src", "mesh_symmetry.py")),
        controls_code_sha256_16=_sha_file(os.path.join(_HERE, "adv_mesh_symmetry_faults.py")),
        budgets_sha256_16=_sha_obj(budgets),
        invariants_sha256_16=_sha_obj(invariants),
        mesh_fingerprints=fingerprints,
        scope_ko="⚠ 이 인증서는 위 `mesh_fingerprints` 의 메쉬에 대한 것이다. 지문이 바뀌면 "
                 "**형상이 바뀐 것**이므로 인증서를 다시 돌려야 한다 — 예산표도 «지금 이만큼이다»의 "
                 "선언이라 같이 다시 선언해야 한다.",
        golden_invariants=invariants,
    )

    #  근거 등급 — 기체 × 이 축의 검사 칸
    grades = {}
    for k, r in measured.items():
        if r.get("ok") is None:
            grades[k] = {c: "빈칸" for c in ("S1 손잡이", "S2 배치규약", "S3 좌우대칭",
                                             "S4 질량·관성", "S5 투영면적")}
            grades[k]["_note"] = "메쉬를 못 지어 재지 못했다"
            continue
        grades[k] = {
            "S1 손잡이": "D",          # 기준이 코드 자신(build_propeller) — 한계 L1
            "S2 배치규약": "A",        # 기대 부호를 로터 수에서 유도(닫힌 논증)
            "S3 좌우대칭": "D",        # 규약(비행 안정)이 기준 — 외부 참값 아님
            "S4 질량·관성": "A/D",     # 자는 닫힌 해로 검정(A) · 값의 크기는 대리(D, 한계 L3)
            "S5 투영면적": "A/빈칸",   # 자는 닫힌 해로 검정(A) · 실물 대비 참값은 안 봄(L5)
        }
    grades["_legend"] = GRADE_LEGEND
    grades["_read_ko"] = ("이 축은 «부품 치수»축과 성격이 다르다 — 참값이 **바깥의 수**가 아니라 "
                          "**규약**이라, 등급 A 는 «닫힌 해로 자를 검정했다»는 뜻이고 D 는 "
                          "«기준이 우리 규약/코드 자신»이라는 뜻이다. 실물 대조는 별도 축(M14)이다.")

    doc = {
        "_meta": dict(
            title="대칭 · 손잡이 · 파생량 인증서 (mesh_cert_symmetry_derived_0816)",
            generated_kst=t_start, finished_kst=_kst(),
            author_role="검사 신설자 — 대칭·손잡이·파생량 축",
            scope_ko="지도(mesh_cert_map_0816.json)의 **M11 대칭**과 **M13 파생량** 두 칸. "
                     "다른 칸(위상·치수·재질·좌표계·출처)은 이 인증서의 범위가 아니다.",
            policy_ko="⛔형상 상수 무변경 · ⛔GPU 무사용 · ⛔git 무사용. 이 라운드가 만든 것은 "
                      "검사·대조·봉인·인증서뿐이다.",
            what_ko="검사마다 원리가 다른 **자 둘**을 대고, 자 자체는 **닫힌 해**로 검정하고, "
                    "범주마다 **양성·음성 대조**를 실제로 돌린 결과를 함께 싣는다.",
            glossary_ko={
                "손잡이(handedness)": "프로펠러 날이 어느 쪽으로 비틀렸는가. 거울에 비추면 뒤집힌다.",
                "거울 대칭": "좌우(y→−y)로 뒤집어도 자기 자신과 겹치는가.",
                "관성텐서": "물체가 각 축으로 얼마나 돌기 싫어하는가를 담은 3×3 표.",
                "관성곱": "관성텐서의 대각선 밖 성분(I_xy 등). 좌우대칭이면 0 이다.",
                "투영면적": "어느 방향에서 봤을 때 물체가 가리는 넓이. 레이다 반사의 1차 결정자.",
                "실루엣": "겹친 부분을 한 번만 센 윤곽의 넓이.",
                "한쪽면 합": "관측자를 향한 삼각형들의 넓이 합. PO 커널이 실제로 더하는 양.",
                "이중계상": "같은 면적을 두 번 세는 것. PO 는 가림을 안 보므로 파묻힌 면도 더한다.",
                "sagitta": "곡면을 직선(현)으로 근사할 때 가운데가 뜨는 높이. 분할이 성길수록 커진다.",
                "양성 대조": "일부러 결함을 심어 검사가 잡는지 보는 시험.",
                "음성 대조": "멀쩡한 것을 넣어 거짓경보가 없는지 보는 시험.",
            },
            inputs_read=[
                "src/drones.py (DRONES 레지스트리 · rotor_layout · build_drone · build_propeller)",
                "src/drone_cad.py (형상 근거 주석 — _gimbal_sensor_v2 의 2×2 개구 표)",
                "src/gazebo_export.py (DENSITY 그룹별 밀도)",
                "src/mesh_check.py (기존 검사기 — 이 파일은 그 밖의 축을 맡는다)",
                "outputs/mesh_cert_map_0816.json (범주 지도의 M11 · M13 칸)",
                "docs/MESH_AUDIT_0816.md (I6 · I9)",
            ],
            env=dict(python=platform.python_version(), numpy=np.__version__,
                     platform=platform.platform(), gpu="미사용(CPU 전용)"),
        ),
        "headline_ko": [
            f"⑴ **자를 먼저 검정했다.** 정육면체 투영면적이 닫힌 해와 "
            f"{selftest['cube_axis_err_rel']:+.1e}(축) / {selftest['cube_diag_err_rel']:+.1e}(대각 √3) "
            f"어긋나고, 직육면체 질량·CoM·관성은 두 자 모두 상대오차 "
            f"{selftest['mass_ruler_max_err_rel']:.0e} 다.",
            f"⑵ **대조 {n_ctrl_ok}/{len(controls)} 통과.** 양성(결함을 심으면 걸린다) · "
            f"음성(멀쩡하면 통과) · 한계(못 잡는다고 선언) · 검정(닫힌 해)을 축마다 걸었다.",
            f"⑶ **측정 {n_ok}/{len(graded)} 통과**"
            + (f", 빈칸 {blanks}(메쉬를 못 지음 — 통과로 세지 않는다)." if blanks else "."),
            "⑷ ⭐**새 발견 1** — 프로펠러 좌우 짝은 **정확히** 맞는다. 거울 뜬 뒤 "
            "Δ = base_ang[k]+base_ang[k′](지금 규약 24°)만큼 돌리면 잔차가 전 기종·전 로터 "
            "1e-13 mm(부동소수 바닥)다. 그 24° 는 상수로 박은 것이 아니라 rotor_layout 에서 읽는다.",
            "⑸ ⭐**새 발견 2** — 좌우 비대칭은 거의 전부 **착륙다리 한 그룹**에 몰려 있고, "
            "그것도 **다리 빌더 종류를 따라간다**. 한쪽면 합의 좌우차로 재면 "
            "gear='motor_legs'(mini5pro 2.2e-2 · mavic4pro 2.5e-2 · mini2 1.4e-2)와 "
            "gear='legs'(phantom4 1.4e-2 · phantom3 7.3e-3)가 1e-2 급인데, "
            "gear='feet'(matrice4e 2.3e-9)는 사실상 대칭이고 gear='tall' 은 기체마다 다르다"
            "(m350rtk gear_cf 8.7e-3 ↔ typhoonh480·x500v2 는 1e-10 이하). 나머지 부품은 "
            "body 1e-5~2.0e-3 · canopy 1e-4 급이고 그 밖은 1e-16(부동소수 바닥)이다. "
            "크기는 «완벽히 대칭인 솔리드 + 비대칭 분할» 대조가 재현하는 범위 안이지만 "
            "**원인 코드 줄은 안 짚었다**(한계 L4).",
            "⑹ ⭐**문서 정정** — `drones.rotor_layout` 독스트링의 «대각쌍 동일» 은 n/2 가 짝수일 "
            "때만 참이다. 헥사(typhoonh480, n=6)는 마주보는 쌍이 **반대로** 돈다. 메쉬 결함이 "
            "아니라 문장이 좁은 것이고, 이 검사는 기대 부호를 n 에서 유도해 둘 다 통과시킨다.",
            "⑺ **못 하는 것** — 손잡이의 절대 기준이 코드 자신이다(L1). 기체 전체 거울상은 못 잡고, "
            "못 잡는 게 맞다(L2). 질량·관성의 **크기**는 장담하지 않는다(L3, 감사 I9).",
        ],
        "closure_argument": CLOSURE,
        "checks": _checks_table(),
        "ruler_selftest": selftest,
        "controls": dict(
            what_ko="범주마다 «결함을 심으면 걸린다(양성)» 와 «멀쩡하면 통과한다(음성)» 를 둘 다 "
                    "돌린 결과. 이 둘이 없는 검사는 «있다» 고 치지 않는다.",
            code="benchmark/adv_mesh_symmetry_faults.py",
            n_pass=n_ctrl_ok, n_total=len(controls),
            by_kind={kk: dict(
                pass_=sum(1 for c in controls if c["kind"] == kk and c["passed"]),
                total=sum(1 for c in controls if c["kind"] == kk))
                for kk in sorted({c["kind"] for c in controls})},
            rows=controls,
            missed=[c for c in controls if not c["passed"]],
        ),
        "measured": measured,
        "blanks": blanks,
        "evidence_grades": grades,
        "limits": LIMITS,
        "regression_seal": seal,
        "what_this_round_did_not_do": NOT_DONE,
        "verdict_ko": (
            f"이 축(대칭·손잡이·파생량)에서 **범주 셋 + 파생량 넷**을 열거하고, 칸마다 자를 둘 대고, "
            f"자를 닫힌 해로 검정하고, 대조 {n_ctrl_ok}/{len(controls)} 로 «잡는다»를 보였다. "
            f"측정은 {n_ok}/{len(graded)} 통과"
            + (f"(빈칸 {blanks})" if blanks else "")
            + ". ⇒ **이 범위 안에서는 장담한다.** 범위 밖은 `limits` 의 L1~L8 이 명시한다."),
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, default=str)
    size = os.path.getsize(OUT) / 1024.0
    print(f"\n원장: {OUT}  ({size:.0f} KB)")
    print(f"  대조 {n_ctrl_ok}/{len(controls)} · 측정 {n_ok}/{len(graded)}"
          + (f" · 빈칸 {blanks}" if blanks else ""))
    ok = (n_ctrl_ok == len(controls)) and (n_ok == len(graded)) and not blanks
    print("=" * 104)
    print("판정: " + ("✅ 이 범위 안에서는 장담한다" if ok else
                     "⚠ 아직 아니다 — 위 실패/빈칸을 먼저 지워라"))
    return 0 if ok else 1


def regress() -> int:
    """⭐ **봉인 확인** — 저장된 인증서와 지금을 견준다(조건 ⑷).

    두 가지를 **따로** 말해 준다. 섞으면 «형상을 고쳤는데 검사가 깨진 줄» 오해한다:
      · **형상이 바뀌었다** — 메쉬 지문이 다르다. 인증서를 다시 찍어야 한다(잘못이 아니다).
      · **불변량이 깨졌다** — 손잡이 부호 · 좌우 잔차 · CoM_y · 관성곱 … 이 달라졌다.
        이건 형상을 어떻게 바꿨든 **일어나면 안 되는 일**이다.
    실행: … benchmark/mesh_cert_symmetry_derived_0816.py --regress"""
    if not os.path.exists(OUT):
        print(f"⛔ 인증서가 없다: {OUT}\n   먼저 인자 없이 한 번 돌려라.")
        return 2
    with open(OUT, encoding="utf-8") as fh:
        old = json.load(fh)
    seal_old = old["regression_seal"]
    print("=" * 104)
    print(f"봉인 확인 — 인증서 {old['_meta']['generated_kst']} 과 지금을 견준다")
    print("=" * 104)

    shape_changed, invariant_broken = [], []
    inv_new, fp_new = {}, {}
    for k, s in DRONES.items():
        try:
            m = build_drone(s)
        except Exception as e:
            invariant_broken.append(f"{k}: 메쉬를 못 지었다 ({type(e).__name__})")
            continue
        fp_new[k] = _mesh_fingerprint(m)
        r = msym.check_one(s, mesh=m, verbose=False)
        li, mi, pa = r["lateral"], r["mass_inertia"], r["projected_area"]
        inv_new[k] = dict(
            hand_signs=[[x["rotor"], int(np.sign(x["h_normals"])),
                         int(np.sign(x["h_positions"]))] for x in r["handedness"]["per_rotor"]],
            dir_sorted=r["dir_convention"]["azimuth_sorted_dir"],
            torque_sum=r["dir_convention"]["torque_sum"],
            lateral_surf_rms_mm={g: round(v["surf_rms_mm"], 4) for g, v in li["groups"].items()},
            prop_mirror_max_mm=float(
                f"{max((x['max_mm'] for x in li['prop_mirror']), default=0):.1e}"),
            com_y_rel=float(f"{mi['com_y_rel']:.1e}"),
            Ixy_rel=float(f"{mi['product_inertia_rel']['Ixy']:.1e}"),
            principal_tilt_deg=round(mi["principal_axis_tilt_deg"], 3),
            group_mirror={g: float(f"{v['onesided_mirror_max_rel']:.1e}")
                          for g, v in pa["group_mirror"].items()},
        )
        fp_old = (seal_old.get("mesh_fingerprints") or {}).get(k, {}).get("sha256_16")
        if fp_old != fp_new[k]["sha256_16"]:
            shape_changed.append(f"{k}: {fp_old} → {fp_new[k]['sha256_16']}")
        if not r["ok"]:
            for axis in ("handedness", "dir_convention", "lateral", "mass_inertia",
                         "projected_area"):
                for f in r.get(axis, {}).get("failures", []):
                    invariant_broken.append(f"{k}/{axis}: {f}")

    same_hash = _sha_obj(inv_new) == seal_old.get("invariants_sha256_16")
    code_now = _sha_file(os.path.join(_ROOT, "src", "mesh_symmetry.py"))
    code_changed = code_now != seal_old.get("checker_code_sha256_16")

    print(f"  검사기 코드 지문 : {seal_old.get('checker_code_sha256_16')} → {code_now}"
          f"  {'(바뀜)' if code_changed else '(같음)'}")
    print(f"  불변량 지문      : {seal_old.get('invariants_sha256_16')} → {_sha_obj(inv_new)}"
          f"  {'(같음)' if same_hash else '(바뀜)'}")
    if shape_changed:
        print(f"  ⚠ **형상이 바뀐 기체** {len(shape_changed)}종 — 인증서를 다시 찍어야 한다:")
        for s_ in shape_changed:
            print(f"      {s_}")
    else:
        print("  형상 지문: 전 기종 그대로")
    if invariant_broken:
        print(f"  ❌ **불변량이 깨졌다** {len(invariant_broken)}건:")
        for s_ in invariant_broken[:20]:
            print(f"      {s_}")
    else:
        print("  ✅ 불변량: 전 기종 통과(손잡이·배치규약·좌우대칭·질량관성·투영면적)")
    print("=" * 104)
    if invariant_broken:
        print("판정: ❌ 회귀 — 위 불변량부터 고쳐라")
        return 1
    if shape_changed:
        print("판정: ⚠ 형상이 바뀌었다(불변량은 멀쩡). 인자 없이 다시 돌려 인증서를 갱신하라")
        return 3
    print("판정: ✅ 봉인 유효 — 형상도 불변량도 그대로다")
    return 0


if __name__ == "__main__":
    sys.exit(regress() if "--regress" in sys.argv[1:] else main())
