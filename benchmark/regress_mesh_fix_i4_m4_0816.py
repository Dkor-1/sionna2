# -*- coding: utf-8 -*-
"""
regress_mesh_fix_i4_m4_0816.py — **«수리를 안 켜면 아무것도 안 바뀐다» 를 증명한다**
                                 (2026-08-16, 감사 §⑤ 2층 I4 · m4)
============================================================================================

왜 이 파일이 필요한가
  지금까지의 모든 σ 원장·리포트·덱은 **수리 없는 메쉬**로 나온 값이다. 그러니 이 라운드의
  제1 조건은 «스위치를 안 켜면 메쉬가 **비트 단위로** 예전 그대로일 것» 이다.
  그런데 이 저장소에는 오늘 이전의 **프레임 지문 원장이 없고**, 오늘 다른 수리자들이 같은
  파일을 동시에 고치고 있다. 그래서 «오늘 아침 트리와 비교» 는 성립하지 않는다.
  ⇒ 대신 **내 편집만 되돌린 사본**을 만들어 비교한다. 다른 수리자의 변경은 양쪽 사본에
    똑같이 들어 있으므로 상쇄되고, 남는 차이는 **내 편집뿐**이다.

검사 넷
  A. **비트동일(핵심)** — `src` 를 두 벌 뜬다: `src_now`(지금 그대로) 와 `src_pre`(내가 넣은
     세 덩어리를 문자열로 정확히 도로 뺀 것). 두 트리에서 10기종 `build_drone()` 을 지어
     정점(float64)·면(int64)·그룹 문자열의 **바이트 SHA-256** 을 비교한다. 전부 같아야 한다.
     ⚠ 되돌릴 문자열이 하나라도 안 맞으면 **즉시 실패**한다(조용한 통과 금지).
  B. **경로 동치** — 스위치 없음 == `mesh_fix=False` == `mesh_fix=()` 가 같은 지문인가.
  C. **양성 대조** — 켜면 **달라져야** 한다. A 만 있으면 «아무것도 안 하는 수리» 도 통과한다.
     i4 는 셸형 7기체에서, m4 는 x500v2 에서 지문이 바뀌어야 하고, **해당 없는 기체는
     그대로여야** 한다(i4 는 열린 프레임 2기체·m4 는 나머지 9기체).
  D. **오타는 죽는다** — 아무도 모르는 id 를 명시로 주면 ValueError.

실행: cd sionna && PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/regress_mesh_fix_i4_m4_0816.py
종료코드 0 = 통과. GPU 미사용.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

KEYS = ("mavic4pro", "phantom3", "phantom4", "mini2", "mini5pro", "typhoonh480",
        "matrice4e", "m350rtk", "s1000plus", "x500v2")
SHELL = ("mavic4pro", "phantom3", "phantom4", "mini2", "mini5pro", "typhoonh480", "matrice4e")

#  ── 내가 `src/drone_cad.py` 에 넣은 덩어리 셋. 되돌리기(=제거)용 **정확한 표식**. ─────── #
#  (시작표식, 끝표식) → [시작, 끝) 을 지운다. 끝표식은 **원래 있던 줄**이라 남겨야 한다.
#  ⚠ 셋 다 파일에 **정확히 한 번**만 나오는 문자열이다(regress 가 개수까지 확인한다).
MY_BLOCKS = [
    ('    "i4": (\n', '}\n\n\ndef normalize_mesh_fix'),            # MESH_FIX_TOKENS 두 항목
    ('#  ⭐⭐ 2026-08-16 — 2층 메쉬 수리 (감사 §⑤ 2층 I4 · m4)',
     '#  프레임 (프로펠러 제외) — 기종별'),                          # _boolean + 수리 함수 둘
    ('    #  ⭐⭐ 2026-08-16 (감사 §⑤ 2층) — **그룹 사이** 수리.',
     '    return A'),                                              # build_frame_cad 안의 호출
]

_SNIPPET_MARKS = ('_fix_i4_canopy', '_fix_m4_arm_clamp', 'A.mesh_fix_log',
                  '"i4": (', '"m4": (')

CHILD = r'''
import hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.environ["TREE"], "src"))
import numpy as np
from drones import DRONES, build_drone

def fp(m):
    v = np.asarray(m.v, float); f = np.asarray(m.f, np.int64)
    g = "|".join(m.g).encode()
    return hashlib.sha256(v.tobytes() + f.tobytes() + g).hexdigest()

mode = os.environ.get("MODE", "off")
out = {}
for k in json.loads(os.environ["KEYS"]):
    spec = DRONES[k]
    if mode == "off":
        out[k] = fp(build_drone(spec))
    elif mode == "false":
        out[k] = fp(build_drone(spec, mesh_fix=False))
    elif mode == "empty":
        out[k] = fp(build_drone(spec, mesh_fix=()))
    else:                                   # 전역 스위치로 켠다(cadkit·drone_cad 가 같이 본다)
        from geom import set_mesh_fix
        set_mesh_fix(*mode.split("+"))
        try:
            out[k] = fp(build_drone(spec))
        finally:
            set_mesh_fix()
print(json.dumps(out))
'''


def make_pre_tree(dst: str, seed: str) -> dict:
    """`seed`(= 이미 떠 둔 사본)를 복사하고 **내 편집만** 문자열로 도로 뺀다. 못 찾으면 예외.

    ⚠ 원본 `src/` 가 아니라 **사본**에서 복사한다 — 오늘은 다른 수리자들이 같은 파일을
    동시에 고치고 있어서, 두 사본을 각각 원본에서 뜨면 그 사이의 남의 편집이 차이로 섞인다."""
    shutil.copytree(seed, os.path.join(dst, "src"))
    p = os.path.join(dst, "src", "drone_cad.py")
    s = open(p, encoding="utf-8").read()
    n0 = len(s)
    removed = []
    for start, end in MY_BLOCKS:
        #  ⚠ **시작표식**은 파일에 한 번만 나와야 한다(내 덩어리를 정확히 집는다).
        #    끝표식은 원래 코드의 흔한 줄일 수 있으므로 **시작 뒤 첫 번째**를 쓴다.
        if s.count(start) != 1:
            raise RuntimeError(f"되돌리기 실패: 시작표식이 유일하지 않다 "
                               f"({start[:30]!r}: {s.count(start)}개). "
                               f"⛔«내 편집만 뺀 사본» 을 못 만들면 이 시험은 무의미하다.")
        i = s.find(start)
        j = s.find(end, i)
        if not 0 <= i < j:
            raise RuntimeError(f"되돌리기 실패: 끝표식 {end[:30]!r} 을 시작 뒤에서 못 찾았다.")
        removed.append(j - i)
        s = s[:i] + s[j:]
    for mark in _SNIPPET_MARKS:
        if mark in s:
            raise RuntimeError(f"되돌리기 실패: 사본에 아직 {mark!r} 이 남아 있다.")
    open(p, "w", encoding="utf-8").write(s)
    return dict(bytes_before=n0, bytes_after=len(s), removed_blocks=removed)


def digests(tree: str, mode: str, keys=KEYS) -> dict:
    env = dict(os.environ, TREE=tree, MODE=mode, KEYS=json.dumps(list(keys)),
               PYTHONPATH=os.path.join(tree, "src"), MESH_FIX="")
    r = subprocess.run([sys.executable, "-c", CHILD], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"자식 프로세스 실패(tree={tree}, mode={mode}):\n{r.stderr[-3000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="regress_i4m4_")
    now, pre = os.path.join(tmp, "now"), os.path.join(tmp, "pre")
    shutil.copytree(os.path.join(_ROOT, "src"), os.path.join(now, "src"))
    info = make_pre_tree(pre, os.path.join(now, "src"))
    ok = True
    report = {"되돌린_사본": info}

    #  A. 비트동일 — 내 편집 전 ↔ 후 (스위치 꺼짐)
    d_now = digests(now, "off")
    d_pre = digests(pre, "off")
    same = {k: d_now[k] == d_pre[k] for k in KEYS}
    report["A_비트동일_내편집_전후"] = dict(all_same=all(same.values()), per_key=same,
                                     digest_now=d_now)
    ok &= all(same.values())

    #  B. 경로 동치 — 스위치 없음 == mesh_fix=False == mesh_fix=()
    d_false = digests(now, "false")
    d_empty = digests(now, "empty")
    b = {k: (d_now[k] == d_false[k] == d_empty[k]) for k in KEYS}
    report["B_경로동치"] = dict(all_same=all(b.values()), per_key=b)
    ok &= all(b.values())

    #  C. 양성 대조 — 켜면 달라지고, 해당 없는 기체는 그대로다
    d_i4 = digests(now, "i5+i4")
    d_m4 = digests(now, "m4")
    #    ⚠ i4 시험은 i5 를 같이 켠다(mini2 body 가 비수밀이라 불리언이 못 돈다).
    #      i5 는 mini2 **하나만** 건드리므로 다른 기체의 «달라짐» 은 전부 i4 의 몫이다.
    d_i5 = digests(now, "i5")
    changed_i4 = {k: d_i4[k] != d_i5[k] for k in KEYS}
    changed_m4 = {k: d_m4[k] != d_now[k] for k in KEYS}
    want_i4 = {k: (k in SHELL) for k in KEYS}
    want_m4 = {k: (k == "x500v2") for k in KEYS}
    report["C_양성대조"] = dict(
        i4=dict(changed=changed_i4, expected=want_i4, ok=changed_i4 == want_i4),
        m4=dict(changed=changed_m4, expected=want_m4, ok=changed_m4 == want_m4))
    ok &= (changed_i4 == want_i4) and (changed_m4 == want_m4)

    #  D. 오타는 죽는다
    from drone_cad import normalize_mesh_fix
    try:
        normalize_mesh_fix("i4x")
        typo_ok = False
    except ValueError:
        typo_ok = True
    report["D_오타는_죽는다"] = typo_ok
    ok &= typo_ok

    shutil.rmtree(tmp, ignore_errors=True)
    report["ok"] = bool(ok)
    out = os.path.join(_ROOT, "outputs", "regress_mesh_fix_i4_m4_0816.json")
    json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "A_비트동일_내편집_전후"},
                     ensure_ascii=False, indent=1))
    print("A 비트동일:", report["A_비트동일_내편집_전후"]["all_same"],
          "· 원장:", out)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
