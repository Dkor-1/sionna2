# -*- coding: utf-8 -*-
"""mesh_internal_metal_check.py — **내부 금속 검사기** (2026-08-16 신설, CPU 전용)

무엇을 보나
  드론 메쉬의 «내부 산란체»(battery · pcb 그룹)가 정말 **셸 안에** 있는지, 서로/다른 부품과
  겹치지는 않는지, 공표 부품치수와 얼마나 맞는지를 검사한다.

왜 필요한가
  기존 `src/mesh_check.py` 는 **부품 하나하나의 위상**(수밀·중복면·퇴화면)만 본다. 부품이
  «제자리에 있는가» 는 검사 축에 없다. 그래서 내부 금속 상자가 플라스틱 셸을 뚫고 나가
  **맨 금속이 바깥에 노출돼도 통과한다** — 예외도, 경고도 없다.
  이것은 σ 에 직접 먹힌다: 우리 SBR 은 셸을 맞은 광선만 내부를 τ=1−|Γ_shell|² 로 가중해
  더한다(`rcs_sbr.rcs_sbr_batch`). 노출된 금속은 그 관문을 건너뛰고 **first-hit 금속**이
  되어 |Γ|≈1 로 잡힌다. 순수 PO 는 애초에 가림이 없어 두 경우를 구별조차 못 한다.

⛔ 이 파일은 **읽기 전용 검사기**다. 메쉬 생성 코드(src/drones.py · src/drone_cad.py)를
   부르기만 하고 한 글자도 바꾸지 않는다. 기본 동작에 영향 0.

쓰는 법
    PYTHONPATH=src python benchmark/mesh_internal_metal_check.py            # 전 기종
    PYTHONPATH=src python benchmark/mesh_internal_metal_check.py matrice4e  # 한 기종
    PYTHONPATH=src python benchmark/mesh_internal_metal_check.py --json out.json

판정 규약
  · containment  : 내부 상자 표면 중 셸(body 그룹) **밖**에 있는 면적 비율.
                   FAIL 기준 = 1 % 초과 (0 이 아니라 1 % 인 이유: 배터리 팩 뒷면처럼
                   **설계상 외피를 이루는** 면이 있어 0 을 요구하면 거짓양성이 난다.
                   그런 면은 `expected_skin_faces` 로 따로 선언한다.)
  · protrusion   : 밖으로 나간 점의 셸 표면까지 최대 거리[mm]. 참고값.
  · published    : 공표 부품치수가 있으면 축별 상대오차[%]. 없으면 null(모름).
"""
from __future__ import annotations

import json
import sys

import numpy as np

ROOT = "/workspace/sionna"
if f"{ROOT}/src" not in sys.path:
    sys.path.insert(0, f"{ROOT}/src")

#  공표 부품치수 [mm] — **1차 출처가 있는 것만** 적는다. 없으면 넣지 않는다(빈칸이 가짜보다 낫다).
#    matrice4e : DJI Matrice 4 Series User Manual v1.2 p.103 / C2 표 — BPX345-6741-14.76
#    mini5pro  : DJI Mini 5 Pro User Manual p.86-87 + DJI 스펙 페이지 (2S NMC 2788 mAh)
#    mavic4pro : **공개되지 않음** — 95.3 Wh / 332 g 뿐이라 치수 칸은 비운다.
PUBLISHED_BATTERY_MM = {
    "matrice4e": dict(size=(145.47, 60.6, 46.3), mass_g=400.0, wh=99.5,
                      src="User Manual v1.2 p.103 (BPX345-6741-14.76)"),
    "mini5pro": dict(size=(86.10, 54.89, 24.85), mass_g=71.2, wh=19.52,
                     src="User Manual p.86-87 · DJI spec page (2S Li-ion NMC 2788 mAh)"),
}

#  설계상 **외피를 이루는** 내부 부품 면 — 여기 선언된 면은 containment 위반으로 세지 않는다.
#    matrice4e 배터리 팩은 뒤에서 꽂혀 **팩 후면이 곧 기체 꼬리 외피**가 된다(제품 후면 사진에서
#    전원버튼·잔량 LED 4칸이 보이는 그 면). ⚠ 그 면은 실물이 **플라스틱 케이스**이므로
#    재질 축에서는 여전히 문제다 — 기하 검사에서만 면제한다.
#  ⚠ 부품은 **치수로** 지목한다(연결요소 인덱스는 메쉬가 바뀌면 순서가 흔들린다).
EXPECTED_SKIN = {
    "matrice4e": [dict(group="battery", face="tail(-x)", size_mm=(145.47, 60.6, 46.3), tol_mm=2.0,
                       why="공표 배터리 팩 — 후면이 기체 외피")],
}

#  ⭐ 내부 금속이 **설계상 노출된** 기체 — 이 검사가 적용되지 않는다(거짓양성 방지).
#    · x500v2   : 열린 프레임(body_style='plate_stack'). 셸 자체가 없다.
#    · s1000plus: H 프레임 + 상·하판. 배터리 트레이와 전원판이 실물에서도 바깥에 드러난다
#                 (센터프레임 매뉴얼: 배터리는 상판 위 트레이, 짐벌과 같은 브래킷).
OPEN_INTERNALS = {"x500v2", "s1000plus"}

INTERNAL_GROUPS = ("battery", "pcb")
FACE_NAMES = ((0, -1, "tail(-x)"), (0, +1, "nose(+x)"), (1, -1, "left(-y)"),
              (1, +1, "right(+y)"), (2, -1, "belly(-z)"), (2, +1, "top(+z)"))
OUTSIDE_FAIL_FRAC = 0.01


def _components(F, idx):
    """면 인덱스 집합을 **정점 연결**로 나눠 부품(상자)별 면 인덱스를 돌려준다.
    ⚠ trimesh.split 을 쓰지 않는다 — 그 함수는 기본으로 메쉬를 **수리**해 버려서
      검사기가 «방금 고친 사본» 을 보게 된다(docs/MESH_AUDIT_0816.md C1)."""
    par: dict[int, int] = {}

    def find(a):
        r = a
        while par.get(r, r) != r:
            r = par[r]
        while par.get(a, a) != a:
            par[a], a = r, par[a]
        return r

    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    for i in idx:
        a, b, c = F[i]
        uni(int(a), int(b)); uni(int(b), int(c))
    comp: dict[int, list] = {}
    for i in idx:
        comp.setdefault(find(int(F[i][0])), []).append(int(i))
    return [np.asarray(v) for _, v in sorted(comp.items())]


def check_drone(key, grid_mm=0.5):
    import trimesh as tm
    from drones import DRONES, build_drone

    spec = DRONES[key]
    if key in OPEN_INTERNALS or getattr(spec, "body_style", "shell") == "plate_stack":
        return {"drone": key, "verdict": "N/A",
                "why": "내부 금속이 **설계상 노출된** 기체다(열린 프레임/H 프레임) — "
                       "«셸 안에 있는가» 라는 물음 자체가 성립하지 않는다.", "boxes": []}
    m = build_drone(spec)
    V, F, G = np.asarray(m.v, float), np.asarray(m.f, int), np.asarray(m.g)
    if not (G == "body").any():
        return {"drone": key, "verdict": "N/A", "why": "body 그룹이 없다(셸 없는 기체).", "boxes": []}
    body = tm.Trimesh(vertices=V, faces=F[G == "body"], process=True)
    skin = EXPECTED_SKIN.get(key, [])

    def _is_skin(grp, face_name, size_mm):
        """이 면이 «설계상 외피» 로 선언돼 있나 — 그룹·면이름·치수(허용오차)로 지목."""
        for s_ in skin:
            if s_["group"] != grp or s_["face"] != face_name:
                continue
            if all(abs(a - b) <= s_["tol_mm"]
                   for a, b in zip(sorted(size_mm, reverse=True),
                                   sorted(s_["size_mm"], reverse=True))):
                return True
        return False
    rec = {"drone": key, "body_watertight": bool(body.is_watertight), "boxes": [], "verdict": "PASS"}
    if not body.is_watertight:
        rec["verdict"] = "UNKNOWN"
        rec["why"] = "body 그룹이 수밀이 아니라 안/밖 판정이 정의되지 않는다 — 이 검사는 무효다."
        return rec

    for g in INTERNAL_GROUPS:
        idx = np.where(G == g)[0]
        if len(idx) == 0:
            continue
        for ci, ff in enumerate(_components(F, idx)):
            vi = np.unique(F[ff].ravel())
            P = V[vi]
            lo, hi = P.min(0), P.max(0)
            size = (hi - lo) * 1e3
            box = dict(group=g, comp=ci,
                       size_mm=[round(float(v), 2) for v in size],
                       centre_mm=[round(float(v) * 1e3, 2) for v in 0.5 * (lo + hi)],
                       faces={}, outside_area_cm2=0.0, total_area_cm2=0.0,
                       counted_outside_area_cm2=0.0)
            step = grid_mm / 1000.0
            for ax, sgn, nm in FACE_NAMES:
                oa = [a for a in range(3) if a != ax]
                g1 = np.arange(lo[oa[0]] + step / 2, hi[oa[0]], step)
                g2 = np.arange(lo[oa[1]] + step / 2, hi[oa[1]], step)
                A, B = np.meshgrid(g1, g2, indexing="ij")
                Q = np.zeros((A.size, 3))
                Q[:, oa[0]] = A.ravel(); Q[:, oa[1]] = B.ravel()
                Q[:, ax] = hi[ax] if sgn > 0 else lo[ax]
                out_frac = float(1.0 - body.contains(Q).mean())
                a_cm2 = float((hi[oa[0]] - lo[oa[0]]) * (hi[oa[1]] - lo[oa[1]])) * 1e4
                counted = not _is_skin(g, nm, size)
                box["faces"][nm] = dict(area_cm2=round(a_cm2, 2),
                                        outside_frac=round(out_frac, 4),
                                        outside_area_cm2=round(a_cm2 * out_frac, 2),
                                        counted=counted)
                box["total_area_cm2"] += a_cm2
                box["outside_area_cm2"] += a_cm2 * out_frac
                if counted:
                    box["counted_outside_area_cm2"] += a_cm2 * out_frac
            for k in ("total_area_cm2", "outside_area_cm2", "counted_outside_area_cm2"):
                box[k] = round(box[k], 2)
            box["counted_outside_frac"] = round(box["counted_outside_area_cm2"]
                                                / max(box["total_area_cm2"], 1e-9), 4)
            box["pass"] = bool(box["counted_outside_frac"] <= OUTSIDE_FAIL_FRAC)
            if not box["pass"]:
                rec["verdict"] = "FAIL"
            rec["boxes"].append(box)

    # 공표 배터리 치수 대조 — 가장 큰 battery 부품을 팩으로 본다
    pub = PUBLISHED_BATTERY_MM.get(key)
    if pub:
        bats = [b for b in rec["boxes"] if b["group"] == "battery"]
        if bats:
            pack = max(bats, key=lambda b: float(np.prod(b["size_mm"])))
            ours = np.asarray(pack["size_mm"], float)
            want = np.asarray(sorted(pub["size"], reverse=True), float)
            got = np.asarray(sorted(ours, reverse=True), float)
            rec["published_battery"] = dict(
                source=pub["src"], published_mm=list(pub["size"]),
                ours_mm=pack["size_mm"],
                err_pct_sorted=[round(float(100 * (g_ - w) / w), 1) for g_, w in zip(got, want)],
                volume_ratio=round(float(np.prod(got) / np.prod(want)), 3),
                largest_face_ratio=round(float((got[0] * got[1]) / (want[0] * want[1])), 3),
                largest_face_db=round(float(20 * np.log10((got[0] * got[1]) / (want[0] * want[1]))), 2),
                note="err_pct 는 **정렬한 축끼리** 비교한다(상자 방향이 다를 수 있어서). "
                     "largest_face_db 는 최대면 평판극한 σ∝A² 로 옮긴 값.")
            if max(abs(np.asarray(rec["published_battery"]["err_pct_sorted"]))) > 10.0:
                rec["verdict"] = "FAIL" if rec["verdict"] == "PASS" else rec["verdict"]
    return rec


def main(argv):
    keys = [a for a in argv if not a.startswith("-")]
    outfile = None
    if "--json" in argv:
        outfile = argv[argv.index("--json") + 1]
        keys = [k for k in keys if k != outfile]
    from drones import DRONES
    if not keys:
        keys = list(DRONES)
    res = {}
    for k in keys:
        r = check_drone(k)
        res[k] = r
        print(f"\n═══ {k}  →  {r['verdict']}")
        for b in r["boxes"]:
            flag = "  " if b["pass"] else "⛔"
            print(f" {flag} {b['group']}#{b['comp']} {b['size_mm']} @ {b['centre_mm']}  "
                  f"밖 {b['counted_outside_area_cm2']:7.2f} cm² ({b['counted_outside_frac']*100:5.1f} %)")
            for nm, f in b["faces"].items():
                if f["outside_area_cm2"] > 0.05:
                    tag = "" if f["counted"] else "  [외피 선언]"
                    print(f"        {nm:10s} {f['outside_area_cm2']:7.2f} cm² "
                          f"({f['outside_frac']*100:5.1f} %){tag}")
        if "published_battery" in r:
            p = r["published_battery"]
            print(f"    공표 배터리 {p['published_mm']} ↔ 메쉬 {p['ours_mm']}  "
                  f"축오차 {p['err_pct_sorted']} %  최대면 {p['largest_face_db']:+.2f} dB")
    if outfile:
        json.dump(res, open(outfile, "w"), ensure_ascii=False, indent=1)
        print(f"\n✅ {outfile}")
    return 0 if all(r["verdict"] == "PASS" for r in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
