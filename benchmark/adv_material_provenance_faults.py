# -*- coding: utf-8 -*-
"""
adv_material_provenance_faults.py — **재질·출처 검사기를 검사한다**: 일부러 틀린 것을 먹인다
==================================================================================================
왜 필요한가
  «검사기를 만들면 **양성 대조**부터 통과시켜야 한다. 음성 대조만으로는
   «0 이 나오는 검사기» 와 «0 이 맞는 대상» 을 구별할 수 없다.» (메쉬 감사 I6 의 교훈)

  그리고 이 라운드가 맡은 축은 특히 그렇다 — 메쉬 인증 범주 지도가 실측으로 이렇게 적었다:
    · **M12(그룹 라벨·재질 배정)** : «그룹 이름 바꾸기»와 «camera↔gear 라벨 뒤바꾸기»를
      심었더니 **전 검사 통과**. 상태 «없음».
    · **M15(출처·등급)** : 기체 × 부품 등급 행렬이 **아예 없음**. 상태 «부분».

무엇을 하나 — 결함·대조 **39 건**을 실제로 지어 `src/material_provenance.py` 에 먹인다.
  · 음성 대조: 손대지 않은 것은 **통과해야** 한다(거짓경보가 아님을 보인다)
  · 양성 대조: 결함을 넣으면 **걸려야** 한다(실제로 본다는 것을 보인다)
  · 한계 선언: 못 잡는 것은 **못 잡는다고** 적는다(가짜 통과보다 빈칸이 낫다)

실행: cd sionna && CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
        ~/.venvs/py312/bin/python benchmark/adv_material_provenance_faults.py
      ⛔GPU 안 쓴다 · 파일도 안 쓴다(읽기 + 화면 출력) · 저장소 상태를 안 바꾼다
        (원장·표를 건드리는 시험은 전부 **사본**이거나 `try/finally` 로 되돌린다).
      나가는 값: 전부 잡으면 0, 하나라도 놓치면 1.
"""
from __future__ import annotations

import contextlib
import copy
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")      # ⛔GPU 금지 — 임포트 전에 못 박는다

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

import numpy as np                                     # noqa: E402

import material_provenance as MP                       # noqa: E402
from drones import DRONES, build_drone                 # noqa: E402
import drones as DR                                    # noqa: E402
from materials import MATERIALS                        # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def _say(tag: str, passed: bool, detail: str):
    RESULTS.append((tag, passed, detail))
    print(f"  {'✅' if passed else '❌'} {tag:38s} {detail}")


def _hit(res: dict, needle: str) -> bool:
    """실패 목록에 그 규칙의 표식이 들어 있나 — «걸리기는 했는데 다른 이유로» 를 막는다."""
    return any(needle in f for f in res.get("failures", []))


@contextlib.contextmanager
def _patch(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


_MESH_CACHE: dict = {}


def _mesh(key: str):
    if key not in _MESH_CACHE:
        _MESH_CACHE[key] = build_drone(DRONES[key])
    return _MESH_CACHE[key]


def _all_meshes() -> dict:
    return {k: _mesh(k) for k in DRONES}


def _relabel(mesh, mapping: dict):
    """그룹 라벨만 바꾼 **사본** — 정점·면은 한 글자도 안 건드린다."""
    m = copy.deepcopy(mesh)
    m.g = [mapping.get(g, g) for g in m.g]
    return m


# =========================================================================== #
#  A. 재질 배정 — 라벨이 표에 있나, 조용한 폴백이 어디 있나 (범주 M12)
# =========================================================================== #
def test_group_table():
    """A1·A2 — 미등록 그룹 이름과 미등록 재질 키."""
    ok = MP.check_group_table_closure(_all_meshes())
    _say("A0 음성대조: 10기체 원본 라벨", ok["ok"],
         f"그룹 {len(ok['used_groups'])}종 전부 세 표에 등록 · 죽은 항목 {ok['unused_table_entries']}")

    #  A1 — 그룹 이름을 바꾼다(범주 지도가 «놓침»으로 기록한 결함 O 그대로)
    meshes = dict(_all_meshes())
    meshes["mini2"] = _relabel(meshes["mini2"], {"gear": "landing_skid"})
    bad = MP.check_group_table_closure(meshes)
    _say("A1 양성대조: 그룹 이름 gear→landing_skid", (not bad["ok"]) and _hit(bad, "landing_skid"),
         f"실패 {len(bad['failures'])}건 — {bad['failures'][0][:76] if bad['failures'] else ''}")

    #  A2 — 재질 키 오타(표에 없는 재질)
    gm = dict(DR.DRONE_GROUP_MAT)
    gm["prop"] = ("nylon", "프로펠러")
    with _patch(DR, "DRONE_GROUP_MAT", gm):
        bad2 = MP.check_group_table_closure(_all_meshes())
    _say("A2 양성대조: 재질 키 오타 'nylon'", (not bad2["ok"]) and _hit(bad2, "MATERIALS 에 없다"),
         f"실패 {len(bad2['failures'])}건(기체 수만큼)")


def test_silent_fallback_live():
    """A3 — **살아 있는 폴백을 실제로 돌려서** 잰다. 소스 읽기가 아니라 실행이다."""
    from geom import Mesh
    from rcs_po import mesh_to_points
    from materials import gamma_po

    m = Mesh("t")
    #  아주 작은 두 삼각형 — 하나는 등록된 그룹, 하나는 미등록 그룹
    a = m.add_vertex(0, 0, 0); b = m.add_vertex(0.05, 0, 0); c = m.add_vertex(0, 0.05, 0)
    m.add_tri(a, b, c, group="body")
    d = m.add_vertex(0, 0, 0.1); e = m.add_vertex(0.05, 0, 0.1); f = m.add_vertex(0, 0.05, 0.1)
    m.add_tri(d, e, f, group="unobtainium")

    gmap = {"body": gamma_po("plastic")}                  # 미등록 그룹은 일부러 뺀다
    P, N, dA, w = mesh_to_points(m, spacing=0.01, gamma=gmap)
    w_body = float(np.median(w[:len(w) // 2]))
    w_unk = float(np.median(w[len(w) // 2:]))
    gap = MP.db(w_unk) - MP.db(w_body)
    _say("A3 양성대조: PO 가 미등록 그룹을 PEC 로 흘린다",
         abs(w_unk - 1.0) < 1e-9 and abs(w_body - 0.28) < 1e-6,
         f"등록 |Γ|={w_body:.3f} · **미등록 |Γ|={w_unk:.3f}** (진폭 {gap:+.2f} dB, σ 로는 그 두 배)")

    src = MP.check_fallback_sites()
    sbr = [s for s in src["sites"] if "rcs_sbr" in s["file"]]
    _say("A3b 대조: 같은 오타가 SBR 에선 반대로 흐른다",
         bool(sbr) and sbr[0]["falls_to"] == "plastic" and src["ok"],
         f"SBR→{sbr[0]['falls_to'] if sbr else '?'} · PO→PEC · 두 엔진 차 "
         f"{src['two_engine_gap_db']:+.2f} dB")


def test_fallback_scanner():
    """A4 — 새로 생긴 조용한 폴백을 잡나(표류 감지)."""
    good = MP.check_fallback_sites()
    _say("A4 음성대조: 현행 소스", good["ok"],
         f"선언된 자리 {len(good['sites'])}곳 전부 그대로 · 미선언 {len(good['undeclared'])}곳")

    fake = {"src/microdoppler.py": 'x = gamma.get(grp, "carbon")   # 새로 생긴 폴백\n'}
    bad = MP.check_fallback_sites(sources=fake)
    _say("A4 양성대조: 새 폴백 한 줄 심기", (not bad["ok"]) and _hit(bad, "선언 안 된 조용한 폴백"),
         f"미선언 {len(bad['undeclared'])}곳 적발 — {bad['undeclared'][0]['code'] if bad['undeclared'] else ''}")

    #  선언된 자리가 **사라져도** 걸려야 한다(고쳐 놓고 원장을 안 고치는 경우)
    gone = {"src/rcs_po.py": "def mesh_to_points(): pass\n"}
    bad2 = MP.check_fallback_sites(sources=gone)
    _say("A4b 양성대조: 선언된 폴백이 사라짐", (not bad2["ok"]) and _hit(bad2, "선언된 폴백"),
         "코드를 고치면 원장도 같이 고치라고 잡는다")


# =========================================================================== #
#  B. 라벨 ↔ 형상 — 이름이 그 자리에 맞나 (범주 지도가 «놓침» 으로 적은 자리)
# =========================================================================== #
def test_label_geometry():
    for key in DRONES:
        r = MP.check_label_geometry(DRONES[key], mesh=_mesh(key))
        if not r["ok"]:
            _say(f"B0 음성대조: {key}", False, f"{r['failures']}")
            return
    _say("B0 음성대조: 10기체 전부 원본", True, "L1~L5 잣대 전부 통과(거짓경보 0)")

    #  B1 — camera ↔ gear 뒤바꾸기. 범주 지도 F2 가 «전 검사 통과» 라고 기록한 결함.
    key = "matrice4e"
    sw = _relabel(_mesh(key), {"camera": "gear", "gear": "camera"})
    r = MP.check_label_geometry(DRONES[key], mesh=sw)
    _say("B1 양성대조: camera ↔ gear 라벨 뒤바꾸기",
         (not r["ok"]) and (any("L1" in f for f in r["failures"])
                            or any("L3" in f for f in r["failures"])),
         f"{len(r['failures'])}건 — {r['failures'][0][:70]}")

    #  B1b — 위상·치수 검사로는 못 본다는 대조(왜 이 검사가 따로 필요한가)
    import mesh_check
    topo = mesh_check.check_mesh(sw, name=key)
    dim = mesh_check.check_dimensions(DRONES[key], mesh=sw)
    _say("B1b 참고: 위상·치수로는 못 본다", topo["ok"] and dim["ok"],
         "수밀·법선·구멍·치수는 라벨을 안 본다 — 그래서 이 검사가 따로 있어야 한다")

    #  B2 — motor ↔ pcb 뒤바꾸기(회전부가 로터 중심을 떠난다)
    sw2 = _relabel(_mesh(key), {"motor": "pcb", "pcb": "motor"})
    r2 = MP.check_label_geometry(DRONES[key], mesh=sw2)
    _say("B2 양성대조: motor ↔ pcb 뒤바꾸기",
         (not r2["ok"]) and any("L4" in f for f in r2["failures"]),
         f"{r2['failures'][0][:76]}")

    #  B3 — prop ↔ motor 뒤바꾸기(위아래가 뒤집힌다)
    sw3 = _relabel(_mesh(key), {"prop": "motor", "motor": "prop"})
    r3 = MP.check_label_geometry(DRONES[key], mesh=sw3)
    _say("B3 양성대조: prop ↔ motor 뒤바꾸기",
         (not r3["ok"]) and any("L2" in f for f in r3["failures"]),
         f"{r3['failures'][0][:76]}")

    #  B4 — 한계 선언: **이름만** 바꾸면 형상 검사는 통과한다(형상이 그대로니까).
    #      그래서 A1(표 닫힘)이 따로 필요하다. 두 검사는 서로의 사각지대를 덮는다.
    ren = _relabel(_mesh(key), {"gear": "landing_skid"})
    r4 = MP.check_label_geometry(DRONES[key], mesh=ren)
    tbl = MP.check_group_table_closure({key: ren})
    _say("B4 한계선언: 이름만 바꾸면 형상 검사는 통과",
         r4["ok"] and (not tbl["ok"]),
         "형상은 그대로라 L1~L5 는 통과한다 — 그 자리는 A1(표 닫힘)이 잡는다")


# =========================================================================== #
#  C. 재질 상수 — 출처·문헌구간·ITU·표피깊이·두 엔진
# =========================================================================== #
def test_constants():
    good = MP.check_constants()
    _say("C0 음성대조: 현행 재질표", good["ok"],
         f"상수 {len(good['declarations'])}개 선언 · ITU 교차검증 "
         f"{good['itu_crosscheck']['n']}행 중 어긋남 {good['itu_crosscheck']['mismatches']}")

    #  C1 — 문헌을 주장했는데 그 구간 밖(=재질판 «등급 인플레»)
    bad = copy.deepcopy(MATERIALS)
    bad["plastic"]["eps_r"] = 4.0
    r = MP.check_constants(materials_table=bad)
    _say("C1 양성대조: plastic εr 2.7→4.0 (문헌 밖)", (not r["ok"]) and _hit(r, "C2 plastic.eps_r"),
         f"{[f for f in r['failures'] if 'C2' in f][0][:80]}")

    #  C2 — 출처 선언이 없는 새 상수
    bad2 = copy.deepcopy(MATERIALS)
    bad2["unobtainium"] = dict(eps_r=9.9, sigma=0.5, S=0.1, note="지어낸 재질")
    r2 = MP.check_constants(materials_table=bad2)
    _say("C2 양성대조: 출처 없는 새 재질 추가", (not r2["ok"]) and _hit(r2, "출처 선언이 없다"),
         f"{len([f for f in r2['failures'] if 'C1' in f])}개 필드가 미선언으로 걸림")

    #  C3 — ITU 이름 오타
    bad3 = copy.deepcopy(MATERIALS)
    bad3["metal"]["itu"] = "metall"
    r3 = MP.check_constants(materials_table=bad3)
    _say("C3 양성대조: ITU 이름 오타 'metall'", (not r3["ok"]) and _hit(r3, "ITU 표에 없다"),
         "설치본 Sionna 표를 정적으로 읽어 대조한다(임포트 없음 = GPU 없음)")

    #  C4 — 우리 대역이 ITU 유효구간 밖
    with _patch(MP, "BANDS", {"저주파 0.5 GHz": 0.5e9}):
        r4 = MP.check_constants()
    _say("C4 양성대조: 0.5 GHz (ITU metal 유효구간 1~100 GHz 밖)",
         (not r4["ok"]) and _hit(r4, "유효구간 밖"),
         "Sionna 도 여기서 예외를 던진다 — 계획 단계에서 미리 걸러 준다")

    #  C5 — «금속으로 본다» 가 물리로 안 서는 경우
    thin = [dict(name="배터리 포일(0.5 µm 가정)", sigma=3.5e7, thickness_m=0.5e-6,
                 evidence="lit.battery_foil", why_ko="양성 대조용")]
    with _patch(MP, "METAL_OPACITY_CASES", thin):
        r5 = MP.check_constants()
    _say("C5 양성대조: 포일 15 µm → 0.5 µm", (not r5["ok"]) and _hit(r5, "C4 «배터리 포일"),
         f"{[f for f in r5['failures'] if 'C4' in f][0][:88]}")
    ok_case = [c for c in good["metal_opacity"] if "파우치" in c["name"]][0]
    _say("C5b 음성대조: 문헌 하한 15 µm 는 통과", ok_case["ok"],
         f"표피깊이 {ok_case['skin_depth_um']} µm · 두께가 그 {ok_case['skin_depths']}배 "
         f"(기준 {MP.SKIN_DEPTH_MARGIN}배)")

    #  C6 — 2026-07-14 «카메라 10.9 dB» 버그를 되살린다
    bug = copy.deepcopy(MATERIALS)
    bug["camera_assembly"].pop("itu")
    bug["camera_assembly"].update(eps_r=2.7, sigma=0.02)      # Sionna 쪽만 plastic 으로
    with _patch(MP, "CONSTANT_SOURCES", dict(MP.CONSTANT_SOURCES)):
        MP.CONSTANT_SOURCES[("camera_assembly", "eps_r")] = dict(kind="modeling_choice", why_ko="시험")
        MP.CONSTANT_SOURCES[("camera_assembly", "sigma")] = dict(kind="modeling_choice", why_ko="시험")
        r6 = MP.check_constants(materials_table=bug)
    row = [x for x in r6["engine_agreement"] if x["material"] == "camera_assembly"][0]
    _say("C6 양성대조: 옛 카메라 버그(두 엔진 10.9 dB)",
         (not r6["ok"]) and _hit(r6, "경보선"),
         f"Sionna 벌크 |Γ|={row['gamma_bulk']} ↔ PO {row['gamma_po']} = {row['gap_db']:+.2f} dB")
    now = [x for x in good["engine_agreement"] if x["material"] == "camera_assembly"][0]
    _say("C6b 음성대조: 지금은 같은 표에서 나온다", good["ok"],
         f"현행 차이 {now['gap_db']:+.2f} dB (선언됨={now['declared']}) — 경보선 6 dB 안")


# =========================================================================== #
#  D. 출처 등급 — 죽은 링크·죽은 인용·인플레·대리·판 규칙
# =========================================================================== #
def _led():
    return copy.deepcopy(MP.PART_PROVENANCE)


def _ev():
    return copy.deepcopy(MP.EVIDENCE)


def test_provenance():
    meshes = _all_meshes()
    good = MP.check_provenance(meshes=meshes)
    _say("D0 음성대조: 현행 원장", good["ok"],
         f"기체 × 부품 {len(good['cells'])}칸 · 등급 분포 {good['grade_distribution']}")

    #  D1 — 죽은 링크
    ev = _ev()
    ev["mini2.shell"]["path"] = "assets/photos/mini2/없는파일.jpg"
    r = MP.check_provenance(meshes=meshes, evidence_table=ev)
    _say("D1 양성대조: 근거 파일이 사라짐", (not r["ok"]) and _hit(r, "죽은 링크"),
         f"{[f for f in r['failures'] if '죽은 링크' in f][0][:80]}")

    #  D2 — 죽은 인용(파일은 있는데 그 문장이 없다)
    ev2 = _ev()
    ev2["dji.prop_material_1158F"]["quote"] = "Carbon Fiber Propeller"
    r2 = MP.check_provenance(meshes=meshes, evidence_table=ev2)
    _say("D2 양성대조: 인용문이 그 파일에 없음", (not r2["ok"]) and _hit(r2, "죽은 인용"),
         "«문서가 그렇게 말한다» 를 글자 단위로 확인한다")

    #  D3 — 등급 인플레(사진뿐인데 [A])
    led = _led()
    led["mini5pro"]["body"]["grade"] = "A"
    r3 = MP.check_provenance(meshes=meshes, ledger=led)
    _say("D3 양성대조: 렌더뿐인데 [A]", (not r3["ok"]) and _hit(r3, "등급 인플레"),
         f"{[f for f in r3['failures'] if '인플레' in f][0][:86]}")

    #  D4 — 남의 기체 사진을 자기 근거로(=대리인데 [B])
    ev4 = _ev()
    ev4["borrowed"] = dict(kind="own_teardown", owner="mini2",
                           path=MP.EVIDENCE["mini2.shell"]["path"], what_ko="시험용")
    led4 = _led()
    led4["mini5pro"]["body"]["evidence"] = ["borrowed"]
    led4["mini5pro"]["body"]["grade"] = "B"
    r4 = MP.check_provenance(meshes=meshes, ledger=led4, evidence_table=ev4)
    _say("D4 양성대조: 남의 기체 사진을 [B] 근거로", (not r4["ok"]) and _hit(r4, "P5"),
         f"{[f for f in r4['failures'] if 'P5' in f][0][:86]}")

    #  D5 — [D] 인데 대리 대상 미표시 / [C] 인데 유추 출처 미표시
    led5 = _led()
    led5["x500v2"]["prop"]["proxy_of"] = None
    led5["typhoonh480"]["motor"]["inferred_from"] = None
    r5 = MP.check_provenance(meshes=meshes, ledger=led5)
    _say("D5 양성대조: [D]·[C] 의 근거 대상 미표시",
         (not r5["ok"]) and _hit(r5, "`proxy_of` 가 없다") and _hit(r5, "`inferred_from` 이 없다"),
         "대리는 «누구의 것을 빌렸는지» 를 반드시 적어야 한다")

    #  D6 — 판(variant) 규칙: 4T 짐벌 자료를 4E 짐벌 칸에
    led6 = _led()
    led6["matrice4e"]["camera"]["evidence"] = ["matrice4e.gimbal_4t"]
    r6 = MP.check_provenance(meshes=meshes, ledger=led6)
    _say("D6 양성대조: 4T 판 짐벌 근거를 4E 칸에", (not r6["ok"]) and _hit(r6, "P7"),
         "사용자 상시 규칙 — 그 CAD·분해사진은 M4T 판이다")

    #  D7 — 덮개: 메쉬에 있는 그룹인데 칸이 없다
    led7 = _led()
    led7["mini2"].pop("motor")
    r7 = MP.check_provenance(meshes=meshes, ledger=led7)
    _say("D7 양성대조: 칸 하나 삭제", (not r7["ok"]) and _hit(r7, "P1"),
         "새 부품이 생겼는데 출처 칸을 안 만들면 걸린다")

    #  D8 — 원장 재질과 실제 배정표가 어긋남
    led8 = _led()
    led8["mini2"]["body"]["model_key"] = "carbon"
    r8 = MP.check_provenance(meshes=meshes, ledger=led8)
    _say("D8 양성대조: 원장 재질 ≠ DRONE_GROUP_MAT", (not r8["ok"]) and _hit(r8, "P2"),
         "원장이 배정표와 따로 놀면 «세 갈래 기록» 사고가 다시 난다")

    #  D9 — 빈칸인데 이유가 없다
    led9 = _led()
    led9["phantom3"]["prop"]["unknown_reason"] = None
    r9 = MP.check_provenance(meshes=meshes, ledger=led9)
    _say("D9 양성대조: 빈칸에 이유가 없음", (not r9["ok"]) and _hit(r9, "unknown_reason"),
         "«모른다» 도 왜 모르는지 적어야 통과한다")

    #  D10 — 실물 재질이 모델 키와 다른데 대체 선언이 없다
    led10 = _led()
    led10["mavic4pro"]["prop"]["substitution"] = None
    r10 = MP.check_provenance(meshes=meshes, ledger=led10)
    _say("D10 양성대조: 나일론을 ABS/PC 로 쓰면서 선언 없음",
         (not r10["ok"]) and _hit(r10, "P8"),
         "DJI 공식 문서가 «나일론 복합» 이라고 적는 자리 — 바꿔 쓰면 그 사실과 크기를 적어야 한다")


# =========================================================================== #
#  E. 공용 «구조판» — 메쉬를 재서 찾고 선언을 요구한다
# =========================================================================== #
def test_shared_plate():
    meshes = _all_meshes()
    good = MP.check_shared_plate(meshes)
    _say("E0 음성대조: 현행 원장", good["ok"],
         "얇은 판 " + " · ".join(f"{p['airframe']}({p['pct_of_metal_area']} %)" for p in good["plates"]))

    led = _led()
    led["mini2"]["battery"]["declared_shared_plate"] = False
    bad = MP.check_shared_plate(meshes, ledger=led)
    _say("E1 양성대조: 선언을 지움", (not bad["ok"]) and _hit(bad, "mini2"),
         f"{bad['failures'][0][:88]}")


# =========================================================================== #
#  F. 회귀 봉인 — 조용히 바뀌면 지문이 달라진다
# =========================================================================== #
def test_seal():
    base = MP.seal_fingerprint()
    _say("F0 음성대조: 같은 상태", MP.check_seal(base)["ok"],
         " · ".join(f"{k}={v[:8]}" for k, v in base.items()))

    tweak = copy.deepcopy(MATERIALS)
    tweak["prop_plastic"]["gamma_po"] = 0.26              # 0.25 → 0.26 (0.34 dB)
    moved = MP.seal_fingerprint(materials_table=tweak)
    r = MP.check_seal(base) if moved["materials"] == base["materials"] else \
        dict(ok=False, failures=[f"봉인 깨짐 — materials: {base['materials']} → {moved['materials']}"])
    _say("F1 양성대조: |Γ| 0.25→0.26 만 바꿔도 지문이 움직인다", not r["ok"],
         f"{base['materials'][:8]} → {moved['materials'][:8]}")

    led = _led()
    led["mini5pro"]["prop"]["grade"] = "B"
    with _patch(MP, "PART_PROVENANCE", led):
        moved2 = MP.seal_fingerprint()
    _say("F2 양성대조: 등급 하나만 바꿔도 지문이 움직인다",
         moved2["provenance"] != base["provenance"],
         f"provenance {base['provenance'][:8]} → {moved2['provenance'][:8]}")


def run_all() -> list[tuple[str, bool, str]]:
    print("=" * 100)
    print("재질·출처 검사기 적대 시험 — 일부러 틀린 것을 지어 먹인다")
    print("=" * 100)
    print("\n[A. 재질 배정 — 라벨 등록 · 조용한 폴백]")
    test_group_table()
    test_silent_fallback_live()
    test_fallback_scanner()
    print("\n[B. 라벨 ↔ 형상 — 이름이 그 자리에 맞나]")
    test_label_geometry()
    print("\n[C. 재질 상수 — 출처 · 문헌구간 · ITU · 표피깊이 · 두 엔진]")
    test_constants()
    print("\n[D. 출처 등급 — 죽은 링크 · 죽은 인용 · 인플레 · 대리 · 판]")
    test_provenance()
    print("\n[E. 공용 구조판]")
    test_shared_plate()
    print("\n[F. 회귀 봉인]")
    test_seal()
    return list(RESULTS)


def main() -> int:
    run_all()
    n_ok = sum(1 for _, p, _ in RESULTS if p)
    print("\n" + "=" * 100)
    print(f"결과: {n_ok}/{len(RESULTS)} 통과")
    if n_ok < len(RESULTS):
        print("놓친 항목:")
        for tag, p, d in RESULTS:
            if not p:
                print(f"  ❌ {tag} — {d}")
        return 1
    print("⇒ 범주 지도가 «놓침» 으로 적었던 라벨 뒤바꿈·그룹 이름 변경이 지금은 전부 걸린다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
