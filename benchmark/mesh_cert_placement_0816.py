# -*- coding: utf-8 -*-
"""
mesh_cert_placement_0816.py — **배치·겹침·묻힘 인증서**를 발급한다
==============================================================================
이 스크립트가 하는 일 (순서대로)
  ① **범주 지도** — 이 영역에서 메쉬가 틀릴 수 있는 자리를 열거하고, 그 목록이 왜 빠짐없는지
     («두 껍질의 관계는 네 칸뿐» 이라는 논증)를 인증서에 싣는다.
  ② **대조 시험** — `benchmark/adv_mesh_placement_0816.py` 를 그대로 돌려, 범주마다
     **양성 대조(결함을 심으면 걸린다) + 음성 대조(멀쩡하면 통과)** 결과를 인증서에 싣는다.
  ③ **전 기종 실측** — 관계표·자기교차·동일평면·뜬 부품을 재고 예산과 대조한다.
  ④ **교차검증** — 같은 수를 **독립된 다른 엔진**(`mesh_buried`)이 내는지 맞춰 본다.
  ⑤ **봉인** — 기체마다 (형상 지문 mesh_sha1, 관계 지문 relation_sha1)를 박는다.
     형상이 바뀌면 인증서가 **스스로 무효를 선언**한다(재발급 필요).
  ⑥ **한계** — 못 하는 것을 조목조목 적는다. «전부 완벽» 은 장담이 아니다.

산출: outputs/mesh_cert_placement_overlap_0816.json
나가는 값: 0 = 인증 · 1 = 예산 초과/대조 실패 · 2 = 형상이 바뀌어 재발급 필요

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/mesh_cert_placement_0816.py [--verify]
      --verify 를 주면 **기존 인증서의 봉인만** 확인한다(다시 재지 않는다).
⛔ GPU 안 쓴다.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from contextlib import redirect_stdout

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _HERE)

import mesh_placement as mp                                   # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "mesh_cert_placement_overlap_0816.json")


def _kst() -> str:
    os.environ["TZ"] = "Asia/Seoul"
    try:
        time.tzset()
    except AttributeError:
        pass
    return time.strftime("%Y-%m-%d %H:%M KST")


# --------------------------------------------------------------------------- #
#  ① 범주 지도 — «이 영역에서 틀릴 수 있는 자리» 와 그 목록이 닫혀 있다는 논증
# --------------------------------------------------------------------------- #
CLOSURE = dict(
    scope_ko="부품들이 **서로** 어떻게 놓여 있는가. 부품 하나하나의 위상·치수·재질은 다른 범주다.",
    one_line_ko="닫힌 껍질 두 개 사이에 성립할 수 있는 관계는 **넷뿐**이고, 한 껍질 안에서만 "
                "따로 생기는 것이 자기교차 하나다 ⇒ 이 영역의 검사 항목은 **다섯**이다.",
    derivation_ko=[
        "두 부품 A, B 는 각각 삼각형의 모음이고, 우리 조립에서는 서로 다른 연결요소다(면을 공유하지 않는다).",
        "① 두 표면이 **만나는가**로 먼저 갈린다. 만나면 = 서로를 가로지르는 삼각형 쌍이 있다 → **R2 관통**.",
        "② 안 만나면 두 내부(부피)는 «서로소» 이거나 «하나가 다른 하나를 포함» 한다 — 위상적으로 그 둘뿐이다"
        "(경계가 안 만나는데 부분적으로 겹칠 수는 없다). 포함이면 → **R3 완전매몰**.",
        "②-b ⚠ 다만 «만난다» 를 **가로지름**으로만 재면 빠지는 자리가 있다 — 두 껍질이 **같은 평면에서** "
        "맞물리면(옆면이 딱 맞는 두 상자) 가로지름이 하나도 없는데 부피는 겹친다. 그래서 «안에 든 "
        "면적이 1 % 이상이고 그 깊이가 10 µm 를 넘으면» 도 R2 로 친다. 이 가지가 없으면 합성 대조 "
        "B4(맞물린 상자)가 통째로 빠져나간다 — 실제로 첫 판에서 빠져나갔고, 대조가 그걸 잡았다.",
        "③ 서로소이면 남는 자유도는 **거리 하나**뿐이다. 접촉허용(10 µm) 안이면 → **R1 접촉**, 밖이면 → **R0 떨어짐**.",
        "④ R1 중에서 두 표면이 **같은 자리에 나란히** 겹친 것이 «동일평면» 이다(별도 계량: 겹친 면적).",
        "⑤ R0 중에서 «붙어 있어야 하는데 떨어진 것» 이 «뜬 부품» 이다(별도 계량: 최근접 이격).",
        "⑥ A = B 인 경우, 즉 **한 부품이 자기 자신과** 만나는 것이 «자기교차» 다. 위 네 칸과 독립이다.",
        "⇒ (R0, R1, R2, R3) 는 서로 배타적이고 빠짐이 없다. 동일평면·뜬 부품은 그 안의 **부분집합**이며, "
        "자기교차는 «쌍» 이 아니라 «한 부품» 의 성질이라 따로 센다. 이 여섯 말고 다른 관계는 없다.",
    ],
    what_this_does_not_prove_ko=[
        "⛔ **절대 배치는 안 본다** — «부품이 있어야 할 자리에 있는가»(원점 대비 좌표·각도)는 이 영역 밖이다. "
        "두 부품을 통째로 100 mm 옮겨도 관계표는 한 글자도 안 변한다(대조 C3 가 그걸 실제로 보인다).",
        "⛔ **관계가 옳은지는 안 본다** — «이 두 부품이 붙어야 하는가 떨어져야 하는가» 는 **의도**이고, "
        "의도는 메쉬 안에 없다. 그래서 예산표(FLOAT_BUDGET_MM)에 사람이 근거와 함께 적는다.",
        "⛔ **1 µm 보다 얕은 파고듦은 «관통» 으로 안 센다** — 그 척도에서는 독립 구현끼리도 답이 갈린다.",
        "⛔ 내부판정의 알갱이는 **면 중심 한 점**이다 — 면의 절반만 들어간 것은 반올림된다.",
    ],
)

CATEGORIES = [
    dict(
        id="P1", name="자기 겹침 — 한 부품이 자기 자신을 뚫는다",
        what_can_go_wrong=[
            "로프트/스윕이 급하게 휘면서 껍질이 자기를 통과한다(날 비틀림·팔 굽힘)",
            "정점 하나가 잘못된 좌표로 밀려 반대쪽 면 너머로 나간다",
            "CSG 합집합 산출물이 씨접합에서 자기를 스친다",
        ],
        check="mesh_placement.self_intersection — 정점을 공유하지 않는 삼각형 쌍의 가로지름 "
              "(Möller 구간겹침, 파고든 깊이 ≥ 1 µm)",
        positive_control="B3 — 상자의 꼭짓점 하나를 반대면 너머로 밀어 넣는다",
        negative_control="B3 — 멀쩡한 상자 · 전 기종 실측 0",
        budget="SELF_INTERSECT_BUDGET (전부 0 — 예외 없음)",
    ),
    dict(
        id="P2", name="부품 간 관통 — 두 부품이 서로 파고든다",
        what_can_go_wrong=[
            "그룹끼리 불리언 합집합을 안 하므로 겹친 자리의 면이 **둘 다 살아** PO 가 이중계상한다",
            "값을 바꾸다가(모터 z·축간거리) 부품이 서로 더 깊이 박힌다",
        ],
        check="mesh_placement.pair_relation → R2_관통 (삼각형 교차. **수밀을 요구하지 않는다**)",
        positive_control="B4 — 80 % 겹친 두 상자 · B2a — 봉이 상자를 꿰뚫음",
        negative_control="B4 — 멀리 떨어진 두 상자 · B2c — 5 mm 떨어진 봉",
        budget="CROSS_AREA_BUDGET_PCT (기종별 실측 + 10 %)",
    ),
    dict(
        id="P3", name="묻힘 — 부품이 다른 부품 **안**에 있다",
        what_can_go_wrong=[
            "셸 안의 배터리·기판처럼 **설계로** 묻힌 것과, 캐노피가 동체에 통째로 잠긴 **결함**이 섞인다",
            "표면이 안 만나므로 **교차 검사만으로는 절대 못 본다** — 내부판정이 있어야 한다",
        ],
        check="mesh_placement.pair_relation → R3_완전매몰 + inside_faces (양방향 내부판정)",
        positive_control="B4 — 상자 안의 상자 · B2b — 상자 안에 통째로 든 봉(교차쌍 0)",
        negative_control="B4 — 떨어진 두 상자(매몰 0)",
        budget="ENGULFED_PAIRS_BUDGET (기종별 쌍 개수 못 박음)",
    ),
    dict(
        id="P4", name="간극·뜬 부품 — 붙어 있어야 할 것이 떨어졌다",
        what_can_go_wrong=[
            "다리·기판·캐노피가 아무 것에도 안 닿는다(실물이라면 공중에 뜬 부품)",
            "⭐**측정법이 틀려서** 거짓양성이 난다 — 큰 상자가 가는 봉을 감쌀 때 한 방향 잣대는 «멀다» 고 한다",
        ],
        check="mesh_placement.placement_census → floating. 최근접 **부호간극**: "
              "양방향 정점↔면 + 내부판정(부호) + 삼각형 교차(0 판정)",
        positive_control="B1 — 5 mm 띄운 부품 · ⭐B2 — 큰 상자↔가는 봉 3종(관통/완전매몰/진짜 떨어짐)",
        negative_control="B1 — 붙어 있는 두 부품 · B2c",
        budget="FLOAT_BUDGET_MM (기종×그룹. 칸마다 «설계» 인지 «의심» 인지 FLOAT_NOTE 에 적었다)",
    ),
    dict(
        id="P5", name="동일평면 — 같은 자리에 두 껍질이 겹쳐 있다",
        what_can_go_wrong=[
            "PO 가 같은 물리적 면을 **두 재질로 두 번** 더한다",
            "SBR 은 first-hit 이라 둘 중 **어느 쪽이 이길지 광선 순서가 정한다**(답이 흔들린다)",
            "그 자리에서는 교차 판정 자체가 부호 잡음에 흔들린다 — 그래서 «교차» 가 아니라 별도 항목이다",
        ],
        check="mesh_placement.pair_relation → coplanar_* (면 중심이 상대 표면 10 µm 안 + 법선 5° 안)",
        positive_control="B5 — 면이 정확히 포개진 두 판(면적이 맞는지까지 확인)",
        negative_control="B5 — 1 mm 띄운 두 판",
        budget="COPLANAR_AREA_BUDGET_PCT (기종별 실측 + 10 %)",
    ),
]

#  ⭐ 근거 등급 — **어디에 등급이 붙는가**를 먼저 못 박는다.
#     이 영역의 «측정» 은 외부 참값이 필요 없다(메쉬 스스로의 관계를 재는 것이라 등급이 무의미하다).
#     외부 근거가 필요한 것은 딱 하나 — «이 둘이 붙어야 하는가 떨어져야 하는가» 라는 **의도**다.
#     그래서 등급은 예산표의 «뜬 부품 선언» 칸에만 붙인다. 그 밖의 칸에 등급을 붙이면 거짓말이 된다.
EVIDENCE_GRADES = dict(
    ladder=dict(
        A="공식 CAD 직접(제조사 STEP/GLB 를 열어 잰 것)",
        B="사진 계측·관측(공식 렌더/분해 사진)",
        C="계열 유추(같은 제조사·같은 급 기체에서 미룸)",
        D="대리(짐작. 확인 안 함)",
        P="⭐물리적 필연 — 사다리 밖. 외부 자료가 아니라 «그럴 수밖에 없다» 로 정해지는 칸",
    ),
    scope_ko="측정에는 등급이 없다(자기무결성). 등급은 **의도**에만 붙는다.",
    rows=[
        dict(key="prop 스탠드오프(mini5pro·x500v2·phantom3·s1000plus)", grade="P",
             intent="프롭은 모터 벨에 **닿으면 안 된다**(돌아가는 부품이 정지 부품에 닿을 수 없다)",
             source="물리적 필연 + 우리 코드 상수 drones.PROP_STANDOFF_M(근거는 그 자리에 기록)",
             mesh_says="0.63~1.94 mm 떠 있다", verdict="설계와 일치 — 결함 아님"),
        dict(key="phantom4 gear(다리)", grade="B",
             intent="착륙 다리는 동체 밑면에 **붙는다**",
             source="assets/photos/phantom4/'Phantom 4 pro + V2_1.png' — 공식 3/4 렌더에서 다리가 "
                    "셸 밑면에서 곧바로 뻗어 나온다(틈 없음). ⚠정성 관측이지 치수 계측이 아니다",
             mesh_says="8.05 mm 떠 있다", verdict="⚠⚠형상 결함 의심 — 형상 라운드로 넘김"),
        dict(key="phantom3 gear(다리)", grade="B",
             intent="같음",
             source="assets/photos/phantom3/phantom3_d02_official_front.png(공식 정면) + "
                    "phantom3_c06_ifixit_std_landing_gear_pair.jpg(분해 사진)",
             mesh_says="13.84 mm 떠 있다", verdict="⚠⚠형상 결함 의심 — 함대 최대 이격"),
        dict(key="phantom4 canopy 조각", grade="D",
             intent="캐노피는 동체에 붙는다(추정)", source="확인 안 함",
             mesh_says="4.52 mm 떠 있다", verdict="⚠의심 — 근거를 안 봤으므로 단정 안 함"),
        dict(key="phantom3 camera 조각", grade="D",
             intent="짐벌 부품끼리 이어진다(추정)", source="확인 안 함",
             mesh_says="8.18 mm 떠 있다", verdict="⚠의심 — 근거를 안 봤으므로 단정 안 함"),
        dict(key="x500v2 pcb", grade="D",
             intent="비행제어 기판은 스탠드오프로 띄워 단다(추정)",
             source="⚠제조사 STEP(assets/meshes/reference/x500v2-frame.step)이 **있는데 안 열었다** — "
                    "열면 [A] 로 올릴 수 있다. 이 라운드의 미결 항목",
             mesh_says="5.00 mm 떠 있다", verdict="판단 보류(등급이 낮다고 결함인 것은 아니다)"),
        dict(key="s1000plus pcb", grade="D",
             intent="같음", source="확인 안 함",
             mesh_says="5.93 mm 떠 있다", verdict="판단 보류"),
    ],
    coverage_ko="뜬 부품 선언 10칸 중 등급 P 4칸 · B 2칸 · D 4칸. **D 4칸은 «모른다» 는 뜻이고, "
                "그 칸에 대해서는 장담하지 않는다.**",
)

LIMITS = [
    dict(id="L1", what="1 µm 보다 얕은 파고듦", why="그 척도에서는 독립 구현끼리도 답이 갈린다"
         "(실제 메쉬에서 32 % 불일치). 잡음의 열 배인 1 µm 를 바닥으로 선언했다.",
         control="C1 — 0.1 µm 파고듦은 «접촉», 10 µm 는 «관통» 으로 답하는지 확인"),
    dict(id="L2", what="면의 절반만 들어간 부분 매몰의 정확한 면적",
         why="내부판정 질의점이 **면 중심 한 점**이라 면 단위로 반올림된다(매몰면 검사와 같은 규약).",
         control="C2 — 절반만 들어간 봉으로 확인"),
    dict(id="L3", what="절대 배치(부품이 있어야 할 자리에 있는가)",
         why="이 영역은 **상대 관계**만 본다. 절대 좌표·자세는 다른 범주(M8)의 몫이다.",
         control="C3 — 통째로 100 mm 옮겨도 관계지문이 같음을 확인"),
    dict(id="L4", what="«붙어야 하는가 떨어져야 하는가» 라는 의도",
         why="메쉬 안에 없다. 사람이 예산표에 근거와 함께 적어야 한다 — 그래서 FLOAT_NOTE 가 있다.",
         control="없음(원리적으로 메쉬만으로는 불가능)"),
    dict(id="L5", what="간극의 참값(모서리↔모서리 최근접)",
         why="간극은 **정점↔면**을 양방향으로 재므로, 두 모서리가 서로를 스치는 배치에서는 "
             "참값보다 **크게** 나올 수 있다(상한). 접촉/관통 판정은 교차·내부판정이 따로 하므로 "
             "판정은 안 흔들리고, 흔들리는 것은 «떨어진 거리의 값» 뿐이다.",
         control="없음(선언만) — 실제 함대에서 R0 로 판정된 쌍의 값에만 영향"),
    dict(id="L7", what="완전히 같은 자리에 복제된 부품 — **부품이라는 구분 자체가 사라진다**",
         why="좌표가 같으면 웰딩이 두 껍질의 정점을 합쳐서 «둘» 이 아니게 된다. 그래도 통째로 "
             "빠져나가지는 않는다 — 모서리를 네 삼각형이 쓰게 되어(비다양체) 부품 분해가 삼각형 "
             "단위로 쪼개지고, 그 조각들이 서로 **동일평면 100 %** 로 잡힌다. 같은 자리를 "
             "`mesh_check` 의 비다양체 모서리 검사도 따로 본다(두 겹으로 막혀 있다).",
         control="C4 — 완전 복제 상자로 확인(동일평면 100 %)"),
    dict(id="L6", what="비수밀 부품의 내부판정",
         why="구멍 난 껍질은 «안/밖» 이 정의되지 않는다. **못 봤다고 보고**하고(blind_parts), "
             "그 자리는 수밀을 요구하지 않는 **교차 검사**가 대신 본다.",
         control="B6 — 구멍 낸 상자 + 관통하는 봉"),
]


# --------------------------------------------------------------------------- #
#  ② 대조 시험 — 적대 스크립트를 그대로 돌려 결과를 싣는다
# --------------------------------------------------------------------------- #
def run_controls() -> dict:
    import adv_mesh_placement_0816 as adv
    buf = io.StringIO()
    argv = list(sys.argv)
    sys.argv = [argv[0], "--fleet"]      # 실제 기체 대조(D2·D3)까지 인증서에 싣는다
    try:
        with redirect_stdout(buf):
            rc = adv.main()
    finally:
        sys.argv = argv
    rows = [dict(tag=t, passed=bool(p), detail=d) for t, p, d in adv.RESULTS]
    return dict(exit_code=int(rc), n=len(rows), n_passed=sum(1 for r in rows if r["passed"]),
                rows=rows, stdout_tail=buf.getvalue().strip().splitlines()[-3:])


# --------------------------------------------------------------------------- #
#  ④ 교차검증 — 독립 엔진(mesh_buried)이 같은 수를 내는가
# --------------------------------------------------------------------------- #
def cross_validate(name, mesh, census) -> dict:
    """매몰 면적을 **독립된 다른 코드**로 다시 재서 맞춰 본다.

    ⚠ 두 엔진은 부품 분해·후보 짝짓기·내부판정 호출이 전부 따로 짜여 있다. 차이가 나야 하는
      곳은 딱 하나 — `mesh_buried` 는 **구멍을 메운 사본**으로 내부판정을 하고(patch_holes=True),
      우리는 안 메우고 «못 봄» 으로 남긴다. 그래서 비수밀 부품이 있는 기체만 값이 다르고,
      그 기체도 patch_holes=False 로 맞추면 같아야 한다."""
    try:
        from mesh_buried import buried_census
    except Exception as e:                                    # noqa: BLE001
        return dict(available=False, why=f"{type(e).__name__}: {e}")
    a = buried_census(mesh, name, patch_holes=True)["buried_pct"]
    b = buried_census(mesh, name, patch_holes=False)["buried_pct"]
    ours = census["inside_faces"]["area_pct"]
    d_patch = round(abs(ours - a), 4)
    d_raw = round(abs(ours - b), 4)
    return dict(available=True, ours_inside_pct=ours,
                mesh_buried_patched_pct=a, mesh_buried_unpatched_pct=b,
                diff_vs_patched=d_patch, diff_vs_unpatched=d_raw,
                agree=bool(d_raw <= 0.02),
                read_ko="구멍을 안 메운 판(unpatched)과 맞으면 두 엔진이 같은 답이다. "
                        "메운 판과의 차이는 비수밀 부품이 감춘 면적이다.")


# --------------------------------------------------------------------------- #
#  ③⑤ 본체
# --------------------------------------------------------------------------- #
def build_certificate() -> dict:
    from drones import DRONES, build_drone
    print("=" * 100)
    print("배치·겹침·묻힘 인증서 발급 — 범주지도 · 대조시험 · 전기종 실측 · 교차검증 · 봉인")
    print("=" * 100)

    print("\n[1/3] 대조 시험(양성·음성)")
    controls = run_controls()
    print(f"      {controls['n_passed']}/{controls['n']} 통과")

    print("\n[2/3] 전 기종 실측")
    fleet, seals, xval, suspects = {}, {}, {}, []
    for k, s in DRONES.items():
        t0 = time.time()
        try:
            m = build_drone(s)
        except Exception as e:                                # noqa: BLE001
            fleet[k] = dict(name=k, measured=False,
                            build_failed=f"{type(e).__name__}: {e}",
                            read_ko="⛔ 이 기체는 **재지 못했다**. 빈칸으로 남긴다 — 가짜 통과 금지.")
            print(f"      {k:12s} ⛔ 빌드 실패 {type(e).__name__}: {e}")
            continue
        c = mp.placement_census(m, k)
        v = mp.check_placement(c)
        c["verdict"] = v
        c["_sec"] = round(time.time() - t0, 1)
        fleet[k] = c
        seals[k] = dict(mesh_sha1=c["mesh_sha1"], relation_sha1=c["relation_sha1"],
                        n_faces=c["n_faces"], n_parts=c["n_parts"])
        xval[k] = cross_validate(k, m, c)
        for f in c["floating"]:
            note = mp.FLOAT_NOTE.get((k, f["group"]), "")
            if "의심" in note:
                suspects.append(dict(drone=k, part=f["pid"], gap_mm=f["gap_mm"],
                                     nearest=f["nearest"], note=note))
        print(f"      {k:12s} {c['_sec']:5.1f}s {'✅' if v['ok'] else '❌'} "
              f"관계 {c['relations']} 자기교차 {c['self_intersection']['n_pairs']} "
              f"동일평면 {c['coplanar']['area_pct']:.3f} % 뜬부품 {len(c['floating'])} "
              f"{'· 교차검증 ' + ('일치' if xval[k].get('agree') else '차이') if xval[k]['available'] else ''}")

    print("\n[3/3] 인증서 조립")
    measured = [k for k, c in fleet.items() if c.get("measured", True) and "verdict" in c]
    passed = [k for k in measured if fleet[k]["verdict"]["ok"]]
    cert = dict(
        _meta=dict(
            title="메쉬 인증서 — 배치·겹침·묻힘 (부품 사이의 관계)",
            generated_kst=_kst(),
            author_role="검사 신설자 — 배치·겹침·묻힘",
            policy="⛔이 라운드는 형상 상수를 한 글자도 안 바꿨다. 만든 것은 검사·대조·봉인·인증서뿐이다.",
            what_ko="부품들이 서로 어떻게 놓여 있는가(떨어짐/접촉/관통/완전매몰) + 자기교차 + "
                    "동일평면 + 뜬 부품을 전 기종에서 재고, 검사가 실제로 결함을 잡는다는 것을 "
                    "양성·음성 대조로 증명한 기록.",
            how_to_read_ko="① closure_argument 로 «빠진 칸이 없다» 를 확인하고 ② categories 의 "
                           "positive/negative control 이 controls.rows 에서 실제로 통과했는지 보고 "
                           "③ fleet 의 수와 verdict 를 보고 ④ limits 에서 **못 하는 것**을 확인하라.",
            engine="src/mesh_placement.py",
            controls_script="benchmark/adv_mesh_placement_0816.py",
            env=dict(python=sys.version.split()[0], numpy=np.__version__,
                     trimesh=__import__("trimesh").__version__, gpu="사용 안 함(CPU)"),
            tolerances=dict(plane_eps_m=mp.PLANE_EPS_M, cross_pen_min_m=mp.CROSS_PEN_MIN_M,
                            touch_tol_m=mp.TOUCH_TOL_M, coplanar_gap_m=mp.COPLANAR_GAP_M,
                            coplanar_ang_deg=mp.COPLANAR_ANG_DEG),
            glossary_ko={
                "부품": "삼각형이 모서리로 이어진 덩어리 하나(연결요소). 그룹 안에서 센다.",
                "수밀": "껍질에 구멍이 없어 «안/밖» 이 정의되는 상태.",
                "내부판정": "점이 껍질 안인지 밖인지 가리는 것. 수밀이어야 성립한다.",
                "교차": "두 삼각형이 서로를 뚫고 지나가는 것. 같은 평면에 얹힌 것은 교차가 아니다.",
                "간극": "두 부품 표면 사이의 최단거리. 안에 들어가 있으면 음수로 적는다.",
                "동일평면": "두 껍질이 같은 자리에 같은 방향으로 겹친 것(PO 가 두 번 더한다).",
                "PO": "우리 산란 커널 하나. 가림(그림자)을 안 보므로 겹친 면적을 그대로 더한다.",
                "SBR": "다른 커널(기본). 광선이 처음 맞은 곳만 세므로 매몰면 오차는 구조적으로 0.",
            }),
        closure_argument=CLOSURE,
        categories=CATEGORIES,
        controls=controls,
        fleet=fleet,
        cross_validation=dict(
            what_ko="같은 양(부품 안에 든 면적)을 **독립된 다른 엔진**(src/mesh_buried.py)이 "
                    "다시 재게 해서 맞춰 본다. 두 코드는 부품 분해·후보 짝짓기·판정이 전부 따로다.",
            per_drone=xval,
            n_agree=sum(1 for v in xval.values() if v.get("agree")),
            n_total=len(xval)),
        suspected_defects=dict(
            what_ko="예산 **안**이라 통과했지만 «설계로 보기 어렵다» 고 표시해 둔 자리. "
                    "형상 라운드의 할 일 목록이다(이 라운드는 형상을 안 고친다).",
            rows=suspects),
        evidence_grades=EVIDENCE_GRADES,
        limits=LIMITS,
        seal=dict(
            what_ko="기체마다 (형상 지문, 관계 지문) 두 개를 박는다.",
            how_ko="`--verify` 로 다시 돌리면 ① 형상 지문이 다르면 **인증서 무효(재발급 필요, 나가는 값 2)** "
                   "② 형상 지문은 같은데 관계 지문이 다르면 **검사기/환경이 흔들린 것(실패, 1)** "
                   "③ 둘 다 같으면 인증 유지. 즉 누가 무엇을 바꿔도 자동으로 걸린다.",
            per_drone=seals),
        gate=dict(
            command="PYTHONPATH=src:benchmark python benchmark/mesh_cert_placement_0816.py",
            api="mesh_placement.assert_placement_ok()",
            wiring_todo="⚠ 아직 `src/drones.py` 내보내기 게이트(mesh_check.assert_ok)에는 "
                        "**안 걸려 있다** — 그 파일은 지금 다른 라운드가 고치는 중이라 "
                        "이 라운드가 건드리지 않았다. 배선은 한 줄이다: "
                        "`from mesh_placement import assert_placement_ok; assert_placement_ok()`.",
            budgets_meaning="예산값은 «지금 이만큼이다» 라는 **선언**이지 «이만큼이 옳다» 가 아니다"
                            "(이 저장소의 기존 규약 — PROP_BELL_* · BURIED_FACE_BUDGET_PCT 와 같은 뜻).",
        ),
        summary=dict(
            n_drones=len(DRONES), n_measured=len(measured), n_passed=len(passed),
            not_measured=[k for k in fleet if k not in measured],
            controls_passed=f"{controls['n_passed']}/{controls['n']}",
            self_intersection_fleet_total=sum(
                fleet[k]["self_intersection"]["n_pairs"] for k in measured),
            #  ⭐ 측정법이 왜 중요한지 한 수로 — 순진한 잣대(한 방향·정점↔정점)였다면
            #     함대 전체에서 이만큼의 쌍을 «떨어짐(뜬 부품)» 이라고 잘못 답했을 것이다.
            one_way_ruler_false_verdicts_fleet_total=sum(
                fleet[k]["one_way_ruler_false_verdicts"]["n"] for k in measured),
            coplanar_worst=sorted(
                ((fleet[k]["coplanar"]["area_pct"], k) for k in measured), reverse=True)[:3],
            floating_total=sum(len(fleet[k]["floating"]) for k in measured),
            headline_ko=None),
    )
    ok = (controls["exit_code"] == 0 and len(passed) == len(measured)
          and len(measured) == len(DRONES))
    cert["summary"]["headline_ko"] = (
        f"대조 {controls['n_passed']}/{controls['n']} 통과 · 실측 {len(measured)}/{len(DRONES)} 기체 · "
        f"예산 통과 {len(passed)}/{len(measured)} · 자기교차 함대 합계 "
        f"{cert['summary']['self_intersection_fleet_total']} · "
        f"교차검증 일치 {cert['cross_validation']['n_agree']}/{cert['cross_validation']['n_total']} · "
        f"⭐순진한 잣대였다면 잘못 판정했을 쌍 "
        f"{cert['summary']['one_way_ruler_false_verdicts_fleet_total']}개")
    cert["summary"]["certified"] = bool(ok)
    return cert


def _clean(o):
    """numpy·비직렬화 키를 걷어낸다(`_gf_*` 는 면 번호 배열이라 인증서에 안 싣는다)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if not k.startswith("_gf")}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def verify_seal() -> int:
    """인증서의 봉인만 확인한다 — 다시 재지 않고 지문만 맞춰 본다."""
    from drones import DRONES, build_drone
    if not os.path.exists(OUT):
        print(f"⛔ 인증서가 없다: {OUT}")
        return 1
    cert = json.load(open(OUT, encoding="utf-8"))
    seals = cert["seal"]["per_drone"]
    stale, broken = [], []
    for k, s in DRONES.items():
        if k not in seals:
            stale.append(f"{k}(인증서에 없음)")
            continue
        try:
            m = build_drone(s)
        except Exception as e:                                # noqa: BLE001
            broken.append(f"{k}(빌드 실패 {type(e).__name__})")
            continue
        if mp.fingerprint(m) != seals[k]["mesh_sha1"]:
            stale.append(k)
            continue
        if mp.placement_census(m, k)["relation_sha1"] != seals[k]["relation_sha1"]:
            broken.append(f"{k}(형상은 같은데 관계가 달라졌다 — 검사기/환경 변화)")
    print(f"봉인 확인 — 무효(형상 바뀜) {stale} · 깨짐(비결정성) {broken}")
    if broken:
        return 1
    if stale:
        print("⇒ 형상이 바뀌었다. 인증서를 **다시 발급**하라(이 스크립트를 인자 없이 실행).")
        return 2
    print("⇒ 봉인 유효 — 인증서가 가리키는 형상이 지금 형상과 같다.")
    return 0


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(verify_seal())
    cert = build_certificate()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(_clean(cert), f, ensure_ascii=False, indent=1)
    s = cert["summary"]
    print("\n" + "=" * 100)
    print(f"인증서: {OUT}")
    print(f"  {s['headline_ko']}")
    print(f"  판정: {'✅ 인증' if s['certified'] else '❌ 미인증'}")
    if cert["suspected_defects"]["rows"]:
        print(f"  ⚠ 형상 라운드로 넘기는 의심 {len(cert['suspected_defects']['rows'])}건:")
        for r in cert["suspected_defects"]["rows"]:
            print(f"      {r['drone']:12s} {r['part']:12s} {r['gap_mm']:7.3f} mm  {r['note']}")
    sys.exit(0 if s["certified"] else 1)
