# -*- coding: utf-8 -*-
"""
regress_mesh_fix_battery_0816.py — 수리 스위치 'battery' 의 **회귀 시험**
==========================================================================

이 시험이 증명하는 것 (두 방향)
-------------------------------
R1 ⭐**인자를 안 주면 비트동일** — 하드코딩한 해시와 견주지 **않는다**. 시험이 스스로
   ① 지금 `src/` 를 임시 폴더에 복사하고 ② 거기서 **battery 합집합 배선만** 잘라낸 뒤
   (union 목록을 옛 10-튜플 리터럴로 되돌리고 합집합 실패 가드를 지운다 — 스위치가 꺼졌을 때
   기본 동작을 바꿀 수 있는 조각은 그 둘뿐이다) ③ 그 트리를 PYTHONPATH 로 건 **별도 프로세스**로
   10기종 메쉬 지문을 뜬다. 지금 트리(스위치 끔)의 지문과 **10/10 같아야** 한다.
   ⚠이 방식이라야 **다른 라인이 기본 형상을 바꿔도** 이 시험이 여전히 «내 수정은 무해» 만
   가려낸다(하드코딩 해시는 남의 변경에 같이 빨개진다 — 실제로 2026-08-16 B6/B7 적용에서 그랬다).
R2 **켜면 달라진다(의도된 것)** — 배터리 부품이 2개인 7기종에서 메쉬가 바뀌고,
   그중 겹침이 있던 4기종은 면 수가 +20 장(24→44) 늘고 겹침이 0 이 된다.
R3 **환경변수와 인자가 같은 결과** — `MESH_FIX=battery` 와 `mesh_fix='battery'` 가 비트동일.
R4 **오타는 죽는다** — 아무도 모르는 id 는 ValueError (조용한 무시 금지).
R5 **켠 뒤에도 검사기 통과** — 'battery' 그룹 겹침이 예산(수리판 0.1 %) 밑.
R6 (참고, 판정 아님) 수리 코드가 없던 시점의 기준선 원장과 대조 — 어긋나면 **다른 라인이
   기본 메쉬를 바꿨다는 뜻**이다. 내 수정 때문인지 아닌지는 R1 이 가른다.

실행: PYTHONPATH=src:benchmark python benchmark/regress_mesh_fix_battery_0816.py
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⭐ 참고 기록 — 2026-08-16 15:20 KST+9 시점의 기본(스위치 끔) 지문. **판정에 안 쓴다**
#    (그 뒤 다른 라인이 셸 스무딩·외형강제를 바꿔 셸형 6종의 기본 지문이 정당하게 달라졌다).
#    남겨 두는 이유는 «그때 무엇이었나» 를 되짚기 위해서다.
FINGERPRINT_20260816_1520 = {
    "mini5pro":     "c6b9213d8a4ba901e8ec5836e3e88959ae31bf141d7e17d99375b4736140a7ea",
    "mavic4pro":    "7138f0c4971b70193be1c3ff1985dbee066f251cb0bf5f14f92f7e0947047adf",
    "matrice4e":    "2e18fb0f0c971853870029a350be77d38f1b7da0fe4799ef68cafea6a6db0159",
    "s1000plus":    "a412b9aa5a5db47fb1c5a04f73e9a0c4315d38651d534ff6e49ced5cf40c6edf",
    "phantom4":     "0deb8b1205f969159186d7015127670e9b4312c26990b5802b8ea7f067595c43",
    "typhoonh480":  "7bab2947e31239a1f9e4ced923c9214b4fd1c3ba8598081f3be16de8f8a75d23",
    "x500v2":       "2e4b749b31f19f5f3a18950edf7c71542c15597999c59ac507342969f8844d32",
    "phantom3":     "3978428bacf2c3f2f83a8193ded01fcc9e594d997635bce48e6580821e10ed2a",
    "m350rtk":      "83ebc0bb2e68c4ec8be80ee76f77c3c77881b4f830e66b3e7c8736cccc598a35",
    "mini2":        "e227579861e1b058c32984ecba954da717fe8e8f6508df4b8b5c772e4e1d0c5b",
}

BASELINE_LEDGER = "outputs/mesh_layer2_baseline_0816.json"
BASELINE_CHECKS = {                    # 기종 → (그룹내 겹침 %, σ 방위평균 dBsm @mono el0)
    "mini2":     (49.958, -24.586),
    "phantom4":  (49.4624, -18.268),
    "mavic4pro": (48.1201, -16.183),
    "mini5pro":  (47.8868, -19.484),
}


def fingerprint(m) -> str:
    """메쉬 지문 — 꼭짓점 float **바이트** + 면 인덱스 + 면별 그룹 이름."""
    h = hashlib.sha256()
    h.update(np.asarray(m.v, float).tobytes())
    h.update(np.asarray(m.f, np.int64).tobytes())
    h.update("\n".join(m.g).encode("utf-8"))
    return h.hexdigest()


FP_DUMP = r"""
import json, hashlib
import numpy as np
from drones import DRONES, build_drone
def fp(m):
    h = hashlib.sha256(); h.update(np.asarray(m.v, float).tobytes())
    h.update(np.asarray(m.f, np.int64).tobytes()); h.update("\n".join(m.g).encode())
    return h.hexdigest()
print("@@" + json.dumps({k: fp(build_drone(s)) for k, s in DRONES.items()}))
"""

#  ⭐ «수정 전» 트리를 만드는 잘라내기 — 이 두 조각만이 스위치가 꺼졌을 때의 동작을 건드릴 수 있다.
CUT_FROM = '    union_groups = ["body", "arm", "motor", "camera", "gear", "canopy", "accent",'
CUT_TO = "    #  ⭐⭐ 2026-08-16 (감사 §⑤ 2층) — **그룹 사이** 수리."
CUT_REPLACEMENT = '''    for g in ("body", "arm", "motor", "camera", "gear", "canopy", "accent",
              "deck", "gear_cf", "fc"):
        A.union_group(g)

'''


def fingerprints_without_battery_wiring():
    """지금 src/ 를 복사해 **battery 배선만** 잘라낸 트리에서 10기종 지문을 뜬다(별도 프로세스)."""
    import json
    import shutil
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp(prefix="regress_battery_")
    src = os.path.join(tmp, "src")
    shutil.copytree(os.path.join(ROOT, "src"), src,
                    ignore=shutil.ignore_patterns("__pycache__"))
    p = os.path.join(src, "drone_cad.py")
    t = open(p, encoding="utf-8").read()
    i = t.index(CUT_FROM)
    j = t.index(CUT_TO, i)
    t = t[:i] + CUT_REPLACEMENT + t[j:]
    assert '"battery" in fix' not in t, "잘라내기 실패 — 수리 배선이 남았다"
    open(p, "w", encoding="utf-8").write(t)
    env = dict(os.environ)
    env["PYTHONPATH"] = src
    env.pop("MESH_FIX", None)
    r = subprocess.run([sys.executable, "-c", FP_DUMP], capture_output=True, text=True, env=env)
    shutil.rmtree(tmp, ignore_errors=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("@@")]
    if not line:
        raise RuntimeError(f"수정 전 트리 지문 실패:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return json.loads(line[0][2:])


def main():
    import drone_cad
    from drones import DRONES, build_drone

    ok = True
    print("=" * 96)
    print("R1  인자 없음 = **수정 전 소스와 비트동일** (지금 트리에서 battery 배선만 잘라내 비교)")
    print("=" * 96)
    before = fingerprints_without_battery_wiring()
    for k in DRONES:
        got = fingerprint(build_drone(DRONES[k]))
        exp = before.get(k)
        good = (got == exp)
        ok &= good
        print(f"  {'✅' if good else '❌'} {k:12s} {got[:32]}  "
              f"{'==' if good else '!='}  {(exp or '')[:32]}")

    print("\n" + "=" * 96)
    print("R6 (참고, 판정 아님) 수리 코드가 없던 시점의 기준선 원장과 대조")
    print("=" * 96)
    import mesh_check as mc
    from rcs_po import mesh_to_points, rcs_from_points, C0
    from mesh_fix_battery_union_0816 import GAMMA, SPACING, AZ, FC, BW, N_F
    for k, (ov_exp, sig_exp) in BASELINE_CHECKS.items():
        m = build_drone(DRONES[k])
        r = mc.check_mesh(m, k)["groups"]["battery"]
        P, N, dA, w = mesh_to_points(m, SPACING, gamma=GAMMA)
        acc = 0.0
        for f in np.linspace(FC - BW / 2, FC + BW / 2, N_F):
            acc = acc + rcs_from_points(P, N, dA, f, AZ, 0.0, w=w)
        sig = float(10 * np.log10((acc / N_F).mean()))
        same = abs(r["overlap_pct"] - ov_exp) < 1e-3 and abs(sig - sig_exp) < 5e-3
        print(f"  {'=' if same else '≠'} {k:12s} 겹침 {r['overlap_pct']} % (원장 {ov_exp}) · "
              f"σ {sig:.4f} dBsm (원장 {sig_exp})"
              + ("" if same else "  ← 다른 라인이 기본 메쉬를 바꿨다는 뜻(R1 이 무죄를 가린다)"))

    print("\n" + "=" * 96)
    print("R2  켜면 달라진다(의도된 것) · R3  환경변수 == 인자")
    print("=" * 96)
    for k in DRONES:
        spec = DRONES[k]
        m_off = build_drone(spec)
        m_kw = build_drone(spec, mesh_fix="battery")
        os.environ["MESH_FIX"] = "battery"
        try:
            m_env = build_drone(spec)
        finally:
            os.environ.pop("MESH_FIX", None)
        n_parts = len(drone_cad.build_frame_cad(spec).parts.get("battery", []))
        same_env = fingerprint(m_kw) == fingerprint(m_env)
        changed = fingerprint(m_off) != fingerprint(m_kw)
        want_changed = n_parts > 1
        good = (changed == want_changed) and same_env
        ok &= good
        print(f"  {'✅' if good else '❌'} {k:12s} battery부품 {n_parts} · "
              f"면 {len(m_off.f)}→{len(m_kw.f)} · 바뀜={changed}(기대 {want_changed}) · "
              f"env==인자 {same_env}")

    print("\n" + "=" * 96)
    print("R4  아무도 모르는 id 는 죽는다")
    print("=" * 96)
    for bad in ("battry", "battery_union", "nope"):
        try:
            drone_cad.normalize_mesh_fix(bad)
            print(f"  ❌ {bad!r} 가 조용히 통과했다")
            ok = False
        except ValueError:
            print(f"  ✅ {bad!r} → ValueError")
    for other in ("i5", "m6", "i3"):          # 다른 파일 담당 id — 여기선 조용히 지나가야 한다
        got = drone_cad.normalize_mesh_fix(other)
        good = (got == frozenset())
        ok &= good
        print(f"  {'✅' if good else '❌'} {other!r} → {set(got) or '{}'} (다른 수리자 담당, 예외 아님)")

    print("\n" + "=" * 96)
    print("R5  켠 뒤에도 검사기 통과 — 'battery' 그룹")
    print("=" * 96)
    import mesh_check as mc
    from geom import set_mesh_fix
    set_mesh_fix("battery")
    try:
        for k in ("mini2", "phantom4", "mavic4pro", "mini5pro"):
            r = mc.check_mesh(build_drone(DRONES[k], mesh_fix="battery"), k)["groups"]["battery"]
            good = r["ok"] and r["overlap_pct"] <= r["overlap_budget_pct"]
            ok &= good
            print(f"  {'✅' if good else '❌'} {k:12s} 겹침 {r['overlap_pct']} % "
                  f"(예산 {r['overlap_budget_pct']} %) · 경계모서리 {r['boundary_edges']} · "
                  f"비다양체 {r['nonmanifold_edges']} · 법선안쪽 {r['inward_normals']}")
    finally:
        set_mesh_fix()

    print("\n" + "=" * 96)
    print("결과: " + ("✅ 전부 통과" if ok else "❌ 실패 있음"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
