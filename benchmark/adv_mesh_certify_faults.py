#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
adv_mesh_certify_faults.py — **봉인기(mesh_certify)를 겨냥한 적대 시험**
==============================================================================
왜 있나:  봉인은 «앞으로 누가 무엇을 바꿔도 걸린다» 고 주장한다. 주장은 증명이 필요하다.
          이 파일은 **일부러 바꾼 골든**을 먹여서 `mesh_certify.diff_golden` 이
          ⓐ 잡는가(양성 대조) ⓑ 멀쩡한 것은 통과시키는가(음성 대조) 를 잰다.

무엇을 바꿔 보나 — 골든이 지키는 축 하나마다 한 건씩(**전부 인메모리 복제본**에만 손댄다.
저장소의 골든·소스·형상 상수는 **한 글자도 안 건드린다**).
   P1 형상(삼각형 수)        P2 형상(정점만 이동)     P3 치수 한 줄
   P4 예산 완화              P5 예산 강화             P6 바깥 참값
   P7 형상 상수              P8 새 문                 P9 판정 없는 문
   P10 디스크 자산 상태      P11 인증서 파일          P12 코드 지문
   P13 인증서 ↔ 지금 메쉬 불일치(check_certs_live)
   N1~N3 음성 대조(안 바꾸면 조용한가 · 시각만 달라지면 조용한가 · 이력만 달라지면 조용한가)

실행: cd sionna && PYTHONPATH=src:benchmark python benchmark/adv_mesh_certify_faults.py
      (골든 파일이 있어야 한다. 3 초. CPU only)
"""
from __future__ import annotations

import copy
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mesh_certify as MC                                             # noqa: E402

RED, ORANGE, YELLOW = MC.RED, MC.ORANGE, MC.YELLOW
CASES = []


def case(cid, kind, what):
    def deco(fn):
        CASES.append((cid, kind, what, fn))
        return fn
    return deco


def _find(findings, kind=None, sev=None, needle=None):
    for f in findings:
        if kind and f["kind"] != kind:
            continue
        if sev and f["sev"] != sev:
            continue
        blob = f["what"] + "\n".join(f["lines"])
        if needle and needle not in blob:
            continue
        return f
    return None


# --------------------------------------------------------------------------- #
#  양성 대조 — 일부러 바꾸고 «걸리는가»
# --------------------------------------------------------------------------- #
@case("P1", "positive", "형상 — 그룹 삼각형 수를 늘리면 🔴 로 잡고 «몇 장 늘었는지» 를 말하는가")
def p1(G):
    n = copy.deepcopy(G)
    a = n["airframes"]["mini5pro"]
    a["groups"]["prop"]["n_faces"] += 8
    a["groups"]["prop"]["sha"] = "deadbeefdeadbeef"
    a["n_faces"] += 8
    a["sha"]["mesh"] = "0000000000000000"
    a["sha"]["faces"] = "1111111111111111"
    f = _find(MC.diff_golden(G, n), kind="형상", sev=RED, needle="면 12752→12760 (+8)")
    return f is not None, (f["what"] if f else "못 잡음")


@case("P2", "positive", "형상 — 정점만 움직였을 때 «연결은 그대로» 라고 구별하는가")
def p2(G):
    n = copy.deepcopy(G)
    a = n["airframes"]["mavic4pro"]
    a["sha"]["mesh"] = "abcdabcdabcdabcd"
    a["sha"]["verts"] = "9999999999999999"          # faces sha 는 그대로 둔다
    f = _find(MC.diff_golden(G, n), kind="형상", sev=RED, needle="정점 좌표만 움직였다")
    return f is not None, (f["lines"][0] if f else "못 잡음")


@case("P3", "positive", "치수 — 잣대 한 줄이 3.9 mm 움직이면 mm 와 % 로 말하는가")
def p3(G):
    n = copy.deepcopy(G)
    a = n["airframes"]["matrice4e"]
    a["sha"]["mesh"] = "5555555555555555"
    a["dims_mm"]["shell_belly_z"] = round(a["dims_mm"]["shell_belly_z"] + 3.93, 6)
    f = _find(MC.diff_golden(G, n), kind="형상", needle="치수 shell_belly_z")
    ln = [x for x in (f["lines"] if f else []) if "shell_belly_z" in x]
    return bool(ln and "+3.930 mm" in ln[0]), (ln[0].strip() if ln else "못 잡음")


@case("P4", "positive", "⭐예산 완화 — 슬리버 예산을 늘리면 🟠 «완화» 로 잡는가")
def p4(G):
    n = copy.deepcopy(G)
    b = n["budgets"]["mesh_check"]["values"]["SLIVER_BUDGET"]
    k = [x for x in b if x != "_default"][0]
    b[k] = int(b[k]) * 10 + 100
    f = _find(MC.diff_golden(G, n), kind="예산", sev=ORANGE, needle="완화(느슨해짐)")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P5", "positive", "예산 강화 — 조이는 쪽은 🟡 로 구별하는가(고친 것과 숨긴 것은 다르다)")
def p5(G):
    n = copy.deepcopy(G)
    v = n["budgets"]["mesh_placement"]["values"]["CROSS_AREA_BUDGET_PCT"]
    k = [x for x in v if isinstance(v[x], (int, float))][0]
    v[k] = float(v[k]) / 2.0
    f = _find(MC.diff_golden(G, n), kind="예산", sev=YELLOW, needle="강화(조여짐)")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P6", "positive", "⭐바깥 참값 — 참값을 우리 메쉬에 맞춰 고치면 잡는가")
def p6(G):
    n = copy.deepcopy(G)
    rid = sorted(k for k, v in n["references"]["rows"].items() if v["ref_mm"])[0]
    old = n["references"]["rows"][rid]["ref_mm"]
    n["references"]["rows"][rid]["ref_mm"] = round(float(old) + 7.0, 3)
    f = _find(MC.diff_golden(G, n), kind="참값", sev=ORANGE, needle=f"{rid}.ref_mm")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P7", "positive", "형상 상수 — 코드가 바뀌지 않아도 표의 수가 바뀌면 잡는가")
def p7(G):
    n = copy.deepcopy(G)
    n["shape_constants"]["drone_cad"]["values"]["CHORD_MAX_OVER_R"] = 0.31
    f = _find(MC.diff_golden(G, n), kind="형상상수", sev=ORANGE, needle="CHORD_MAX_OVER_R")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P8", "positive", "⭐새 문 — 메쉬가 나가는 새 경로가 생기면 🔴 인가")
def p8(G):
    n = copy.deepcopy(G)
    n["doors"]["door_ids"] = list(n["doors"]["door_ids"]) + \
        ["benchmark/new_leak.py::write_obj::m.write_obj('/tmp/x.obj')"]
    f = _find(MC.diff_golden(G, n), kind="문", sev=RED, needle="새 문이 1개 생겼다")
    return f is not None, (f["what"] if f else "못 잡음")


@case("P9", "positive", "판정 없는 문 — 원장에 없는 문은 통과시키지 않는가")
def p9(G):
    n = copy.deepcopy(G)
    n["doors"]["doors"] = list(n["doors"]["doors"]) + [dict(
        file="src/leak.py", attr="write_obj", line=1, code="m.write_obj(p)",
        id="src/leak.py::write_obj::m.write_obj(p)",
        verdict=dict(cls="⚠판정 없음", gated=False, why="원장에 없는 문"))]
    n["doors"]["door_ids"] = list(n["doors"]["door_ids"]) + \
        ["src/leak.py::write_obj::m.write_obj(p)"]
    f = _find(MC.diff_golden(G, n), kind="문", sev=RED, needle="판정이 없는 문")
    return f is not None, (f["what"] if f else "못 잡음")


@case("P10", "positive", "디스크 자산 — 정본 OBJ 가 낡아지면 잡는가")
def p10(G):
    n = copy.deepcopy(G)
    k = sorted(k for k, v in n["airframes"].items()
               if v.get("disk_assets", {}).get("exists"))[0]
    n["airframes"][k]["disk_assets"]["n_stale"] += 3
    f = _find(MC.diff_golden(G, n), kind="자산", sev=ORANGE, needle="낡음")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P11", "positive", "인증서 — 파일이 조용히 바뀌면 잡는가")
def p11(G):
    n = copy.deepcopy(G)
    n["certificates"]["topology"]["file_sha"] = "cafecafecafecafe"
    f = _find(MC.diff_golden(G, n), kind="인증서", sev=YELLOW, needle="topology")
    return f is not None, (f["what"] if f else "못 잡음")


@case("P12", "positive", "코드 — 형상은 그대로인데 빌더 코드가 바뀌면 알려 주는가")
def p12(G):
    n = copy.deepcopy(G)
    n["code_fingerprints"]["src/drones.py"] = "0123456789abcdef"
    f = _find(MC.diff_golden(G, n), kind="코드", sev=YELLOW, needle="src/drones.py")
    return f is not None, (f["what"] if f else "못 잡음")


@case("P13", "positive", "⭐인증서 유효성 — 인증서가 «다른 메쉬» 것이면 🔴 로 잡는가")
def p13(G):
    n = copy.deepcopy(G)
    fp = n["certificates"]["dimension"]["fingerprints"]
    k = sorted(fp)[0]
    fp[k] = dict(fp[k], sha256_16="ffffffffffffffff")
    f = _find(MC.check_certs_live(n), kind="인증서유효", sev=RED, needle="다른 메쉬")
    return f is not None, (f["lines"][0].strip() if f else "못 잡음")


@case("P14", "positive", "자산 독자 — 정본 OBJ 를 읽는 자리가 새로 생기면 알려 주는가")
def p14(G):
    n = copy.deepcopy(G)
    n["doors"]["asset_readers"]["ids"] = list(n["doors"]["asset_readers"]["ids"]) + \
        ["benchmark/new_reader.py::trimesh.load('assets/meshes/drones/x/x__prop.obj')"]
    f = _find(MC.diff_golden(G, n), kind="자산독자", sev=ORANGE, needle="new_reader")
    return f is not None, (f["what"] if f else "못 잡음")


# --------------------------------------------------------------------------- #
#  음성 대조 — 안 바꾸면 조용한가
# --------------------------------------------------------------------------- #
@case("N1", "negative", "⭐아무것도 안 바꾸면 findings 가 0 인가")
def n1(G):
    f = MC.diff_golden(G, copy.deepcopy(G))
    return len(f) == 0, f"findings {len(f)}건"


@case("N2", "negative", "봉인 시각·이유만 달라지면 조용한가(형상과 무관한 머리말)")
def n2(G):
    n = copy.deepcopy(G)
    n["_meta"]["generated_kst"] = "2099-01-01 00:00 KST"
    n["_meta"]["update_reason"] = "다른 이유"
    f = MC.diff_golden(G, n)
    return len(f) == 0, f"findings {len(f)}건"


@case("N3", "negative", "이력(history)만 늘어나면 조용한가")
def n3(G):
    n = copy.deepcopy(G)
    n["history"] = list(n.get("history", [])) + [dict(sealed_kst="x", reason="y")]
    f = MC.diff_golden(G, n)
    return len(f) == 0, f"findings {len(f)}건"


@case("N4", "negative", "인증서 유효성 — 지금 상태에서 불일치가 없는가(실제 파일 대조)")
def n4(G):
    f = [x for x in MC.check_certs_live(G) if x["sev"] == RED]
    return len(f) == 0, ("일치" if not f else f[0]["what"])


# --------------------------------------------------------------------------- #
def main() -> int:
    if not os.path.exists(MC.GOLDEN_PATH):
        print(f"⛔ 골든이 없다: {MC.GOLDEN_PATH} — 먼저 mesh_certify.py --update 로 봉인한다")
        return 3
    G = json.load(open(MC.GOLDEN_PATH, encoding="utf-8"))
    print("=" * 104)
    print("봉인기 적대 시험 — 골든을 일부러 흔들어 «걸리는가/조용한가» 를 잰다   [CPU only]")
    print(f"  골든 {os.path.relpath(MC.GOLDEN_PATH, ROOT)} "
          f"(봉인 {G.get('_meta', {}).get('generated_kst')})")
    print("=" * 104)
    rows, n_ok = [], 0
    for cid, kind, what, fn in CASES:
        try:
            ok, detail = fn(G)
        except Exception as e:                                        # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        n_ok += bool(ok)
        rows.append(dict(id=cid, kind=kind, what=what, ok=bool(ok), detail=str(detail)[:150]))
        print(f"  {'✅' if ok else '❌'} {cid:4s} [{kind:8s}] {what}")
        print(f"        → {str(detail)[:150]}")
    n_pos = sum(1 for r in rows if r["kind"] == "positive")
    print("=" * 104)
    print(f"결과: {n_ok}/{len(rows)} 통과   양성 "
          f"{sum(1 for r in rows if r['kind']=='positive' and r['ok'])}/{n_pos} · 음성 "
          f"{sum(1 for r in rows if r['kind']=='negative' and r['ok'])}/{len(rows)-n_pos}")
    print("⇒ 골든이 지키는 축마다 «일부러 바꾸면 걸린다» 가 코드로 증명됐다."
          if n_ok == len(rows) else "⇒ ⛔ 통과 못 한 칸이 있다 — 봉인기를 고쳐야 한다.")
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
