#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regress_mesh_rev0_bitidentical_0917.py — proof that adding mesh revisions changes nothing by default.

Plan: docs/MESH_REV1.md §A.2 (the corrected plan of 2026-09-17). The mesh-revision mechanism edits
three files that shard workers load (src/drones.py, src/drone_cad.py, benchmark/elevation_sweep_md.py)
and adds src/mesh_rev.py and src/drone_rev.py. This script compares a tree WITH the change (the tree
this file sits in, or --new-root) against a tree WITHOUT it (--old-root, e.g. `git archive` of the
commit before) and exits nonzero on any failure.

Items (each is a subcommand; each writes its results under --work and exits nonzero on failure):
  hashes          A.2(i)   mesh bytes: 10 keys × 4 switch states, fresh process per state
  names           A.2(ii)  dry-run shard names for queue lines (CLI, same command as runners/filter_jobs.sh)
  namespaces      A.2(ii)  argparse Namespace per line (identical apart from mesh_rev=0)
  abbrev          A.2(ii)  search for `--me` abbreviations (ambiguous once --mesh-rev exists)
  grammar         A.2(iii) arm_grammar parse of every shard stem and ledger engine; check_arm_names.py
  merge           A.2(iv)  analyse() with SHD → a shard folder (read only), OUT/OUTN → scratch
  existing        A.2(v)   exit codes of the existing mesh regression scripts and checkers
  citations       A.2(vi)  scripts that cite the edited files by line number or quote them; runs two checkers
  quotes          A.2(vi)  static evaluation of every literal Q("<edited file>", "needle") call
  controls        A.2(vii) positive controls with a test-only in-memory registry
  union-parity    drone_rev.finish_frame_assembly replays revision 0's own parts → same bytes
  combos          E.3      all 8 old/new mixes of the three worker-loaded files

Inputs that are not in git (pass them explicitly): a tree without the change (--old-root), a read-only
snapshot of outputs/elev_sweep_shards (--shd, --shd-src), and for `existing`/`citations` a folder with frozen
copies of outputs/*.json, docs/, assets/meshes (--inputs). The queue lines are passed as files (--lines).

Run (CPU only, two cores):
  CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 MPLBACKEND=Agg nice -n 19 taskset -c 14-15 \
    /workspace/.venvs/py312/bin/python benchmark/regress_mesh_rev0_bitidentical_0917.py <item> \
    --old-root <tree without the change> --work <scratch dir> [item options]

Hash definition (A.2(i)): sha256 over float64 vertex bytes, int64 face bytes (with shapes) and
'|'.join(groups) — the last part only where the mesh has groups.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

STATES = {
    "unset": {},
    "mesh_fix_none": {"MESH_FIX": "none"},
    "blade_law_legacy": {"BLADE_LAW": "legacy"},
    "mesh_fix_all": {"MESH_FIX": "all"},
}
PHASES = (0.0, 17.0, 41.5, 123.0)
SCALE_KNOBS = (("body_scale", 0.4), ("frame_scale", 1.3), ("prop_scale", 0.8))
#: the three files shard workers load and this change edits (E.3)
WORKER_FILES = ("src/drones.py", "src/drone_cad.py", "benchmark/elevation_sweep_md.py")
#: new modules (present in every combination: the swap installs them first)
NEW_MODULES = ("src/mesh_rev.py", "src/drone_rev.py")


def child_env(state: str = "unset", extra: dict | None = None) -> dict:
    env = dict(os.environ)
    for k in ("MESH_FIX", "BLADE_LAW", "PYTHONPATH"):
        env.pop(k, None)
    env.update(CUDA_VISIBLE_DEVICES="", SIONNA2_ALLOW_CPU="1", MPLBACKEND="Agg")
    env.update(STATES[state])
    env.update(extra or {})
    return env


def use_tree(root: str) -> None:
    """Import src/ and benchmark/ from `root` first, and prove it."""
    for p in (os.path.join(root, "benchmark"), os.path.join(root, "src")):
        while p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)


def assert_from(mod, root: str) -> None:
    f = os.path.realpath(mod.__file__)
    if not f.startswith(os.path.realpath(root) + os.sep):
        raise SystemExit(f"⛔ {mod.__name__} imported from {f}, not from {root}")


def dump(obj, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    os.replace(tmp, path)


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ═══ A.2(i) mesh bytes ═════════════════════════════════════════════════════════
def mesh_hash(v, f, g=None) -> str:
    import numpy as np
    h = hashlib.sha256()
    for a, dt in ((v, np.float64), (f, np.int64)):
        a = np.ascontiguousarray(np.asarray(a, dt))
        h.update(repr(a.shape).encode())
        h.update(a.tobytes())
    if g is not None:
        h.update("|".join(map(str, g)).encode())
    return h.hexdigest()


def text_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=repr).encode()).hexdigest()


def hash_worker(root: str, keys: list, out: str) -> None:
    use_tree(root)
    import drones
    import articulated_fast
    assert_from(drones, root)
    assert_from(articulated_fast, root)
    from drones import (DRONES, build_frame, build_propeller, build_drone, rotor_layout,
                        frame_fit_scale, frame_envelope_mm)
    from articulated_fast import FastPoser
    res = {"_meta": dict(root=root, MESH_FIX=os.environ.get("MESH_FIX"),
                         BLADE_LAW=os.environ.get("BLADE_LAW"), python=sys.version.split()[0],
                         drones_py=hashlib.sha256(open(drones.__file__, "rb").read()).hexdigest())}
    for key in keys:
        t0 = time.time()
        sp = DRONES[key]
        r = {}
        m = build_frame(sp); r["build_frame"] = mesh_hash(m.v, m.f, m.g)
        m = build_propeller(sp); r["build_propeller"] = mesh_hash(m.v, m.f, m.g)
        m = build_propeller(sp, mirror=True); r["build_propeller_mirror"] = mesh_hash(m.v, m.f, m.g)
        m = build_drone(sp); r["build_drone"] = mesh_hash(m.v, m.f, m.g)
        rl = rotor_layout(sp)
        r["rotor_layout_json"] = json.dumps(rl, sort_keys=True)
        r["frame_fit_scale"] = repr(tuple(frame_fit_scale(sp)))
        env = frame_envelope_mm(sp)
        r["frame_envelope_mm"] = json.dumps(env, sort_keys=True, default=repr)
        fp = FastPoser(sp)
        r["fastposer_vfg"] = mesh_hash(fp.v, fp.f, fp.g)
        r["fastposer_rotor_local"] = [mesh_hash(loc[:, :3], []) for loc in fp._rotor_local]
        r["fastposer_pose"] = {repr(ph): mesh_hash(*(lambda mv: (mv.v, mv.f, mv.g))(
            fp.pose([d * ph for d in fp.dirs]))) for ph in PHASES}
        #  pose_articulated at the same phases: recorded while FastPoser.verify() calls it
        seen = []
        orig = drones.pose_articulated

        def rec(spec, *a, **k):
            mm = orig(spec, *a, **k)
            seen.append(mesh_hash(mm.v, mm.f, mm.g))
            return mm
        drones.pose_articulated = rec
        try:
            ver = fp.verify(phases=PHASES)
        finally:
            drones.pose_articulated = orig
        r["pose_articulated"] = dict(zip(map(repr, PHASES), seen))
        r["fastposer_verify"] = json.dumps(ver, sort_keys=True)
        for knob, val in SCALE_KNOBS:
            f2 = FastPoser(sp, **{knob: val})
            mv = f2.pose([d * 17.0 for d in f2.dirs])
            r[f"fastposer_{knob}_{val:g}"] = mesh_hash(mv.v, mv.f, mv.g)
        #  facts that exist only on the new tree (reported, not compared)
        extra = {}
        if hasattr(drones, "spec_for"):
            extra["spec_for_rev0_is_DRONES_object"] = drones.spec_for(key) is sp
            extra["spec_for_rev0_twice_same"] = drones.spec_for(key, 0) is drones.spec_for(key)
        r["_new_tree_only"] = extra
        r["_seconds"] = round(time.time() - t0, 2)
        res[key] = r
        print(f"  {key:12s} {r['build_drone'][:12]} {r['_seconds']:6.1f}s", flush=True)
    dump(res, out)


def cmd_hashes(a) -> int:
    """A.2(i): for each tree and state, a fresh process builds and hashes every key."""
    trees = [("new", a.new_root)] + ([("old", a.old_root)] if a.old_root else [])
    states = a.states.split(",")
    keys = a.keys.split(",") if a.keys else None
    if keys is None:
        use_tree(a.new_root)
        from drones import DRONES
        keys = sorted(DRONES)
    jobs = []
    for tag, root in trees:
        for st in states:
            out = os.path.join(a.work, "hashes", f"{tag}_{st}.json")
            if os.path.exists(out) and not a.redo:
                continue
            jobs.append((tag, root, st, out))

    def run(job):
        tag, root, st, out = job
        log = out.replace(".json", ".log")
        t0 = time.time()
        with open(log, "w") as fh:
            r = subprocess.run([PY, os.path.abspath(__file__), "hash-worker", "--root", root,
                                "--keys", ",".join(keys), "--out", out],
                               env=child_env(st), stdout=fh, stderr=subprocess.STDOUT, cwd=root)
        print(f"[hashes] {tag} {st} rc={r.returncode} {time.time()-t0:.0f}s", flush=True)
        return r.returncode

    os.makedirs(os.path.join(a.work, "hashes"), exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        rcs = list(ex.map(run, jobs))
    if any(rcs):
        print("⛔ a hash worker failed — see the .log next to the json")
        return 1
    if not a.old_root:
        return 0
    return compare_hash_sets(a.work, states, keys)


def compare_hash_sets(work: str, states, keys, old_tag="old", new_tag="new", label="A.2(i)") -> int:
    n_ok = n_bad = 0
    rows = []
    for st in states:
        A = load(os.path.join(work, "hashes", f"{old_tag}_{st}.json"))
        B = load(os.path.join(work, "hashes", f"{new_tag}_{st}.json"))
        for k in keys:
            for item in sorted(set(A[k]) | set(B[k])):
                if item.startswith("_"):
                    continue
                same = A[k].get(item) == B[k].get(item)
                n_ok += same
                n_bad += (not same)
                if not same:
                    rows.append((st, k, item))
            if "_new_tree_only" in B[k] and B[k]["_new_tree_only"]:
                for fact, val in B[k]["_new_tree_only"].items():
                    n_ok += bool(val)
                    n_bad += (not val)
                    if not val:
                        rows.append((st, k, fact))
    print(f"[{label}] {old_tag} vs {new_tag}: {n_ok} equal, {n_bad} different "
          f"({len(states)} states × {len(keys)} keys)")
    for r in rows[:40]:
        print("   ⛔", r)
    return 1 if n_bad else 0


# ═══ A.2(ii) names ═════════════════════════════════════════════════════════════
DRY_CMD = 'cd "$1" && L="$2" && exec "$3" benchmark/elevation_sweep_md.py $L --dry-run </dev/null'


def queue_lines(files) -> list:
    out = []
    for fn in files:
        with open(fn, encoding="utf-8") as fh:
            for i, ln in enumerate(fh, 1):
                s = ln.rstrip("\n")
                if re.match(r"^\s*(#|$)", s):
                    continue
                out.append(dict(file=os.path.basename(fn), lineno=i, line=s))
    return out


def dry_one(root: str, line: str, state: str, timeout: int = 300) -> dict:
    """Same command as runners/filter_jobs.sh (bash word splitting of an unquoted $L)."""
    if re.search(r"[*?\[]", line):
        return dict(rc=-1, names=[], why="line contains glob characters; not reproduced")
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", DRY_CMD, "_", root, line, PY], env=child_env(state),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                           timeout=timeout)
        raw, rc = r.stdout, r.returncode
    except subprocess.TimeoutExpired as e:
        raw, rc = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), 124
    dry = [ln for ln in raw.splitlines() if re.match(r"^\s*\[dry\]", ln)]
    names = [m.group(0) for ln in dry for m in [re.search(r"[A-Za-z0-9_.+-]+\.npz", ln)] if m]
    why = ""
    if not names:
        bad = [ln for ln in raw.splitlines() if "⛔" in ln]
        tail = [ln for ln in raw.splitlines() if ln.strip()]
        why = (bad[0] if bad else (tail[-1] if tail else f"no output rc={rc}"))[:300]
    return dict(rc=rc, names=names, why=why, seconds=round(time.time() - t0, 2))


def cmd_names(a) -> int:
    files = sorted(a.lines)
    items = queue_lines(files)
    if a.unique:
        seen, uniq = set(), []
        for it in items:
            if it["line"] not in seen:
                seen.add(it["line"])
                uniq.append(it)
        items = uniq
    trees = [("new", a.new_root)] + ([("old", a.old_root)] if a.old_root else [])
    rc = 0
    for st in a.states.split(","):
        results = {}
        for tag, root in trees:
            out = os.path.join(a.work, "names", f"{a.label}_{tag}_{st}.json")
            if os.path.exists(out) and not a.redo:
                results[tag] = load(out)
                continue
            t0 = time.time()
            with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
                got = list(ex.map(lambda it: dict(it, **dry_one(root, it["line"], st)), items))
            dump(dict(root=root, state=st, n_lines=len(items), rows=got), out)
            results[tag] = load(out)
            nb = sum(1 for g in got if not g["names"])
            print(f"[names] {a.label} {tag} {st}: {len(got)} lines, {nb} BAD, "
                  f"{time.time()-t0:.0f}s", flush=True)
        rc |= compare_names(results, st, a.label)
    return rc


def compare_names(results: dict, st: str, label: str) -> int:
    new = results["new"]["rows"]
    n_lines = len(new)
    n_names_new = sum(1 for r in new if r["names"])
    bad_new = [r for r in new if not r["names"] or r["rc"] != 0]
    fails = []
    if bad_new:
        fails.append(f"{len(bad_new)} BAD lines in the new tree")
    if "old" in results:
        old = results["old"]["rows"]
        bad_old = [r for r in old if not r["names"] or r["rc"] != 0]
        if bad_old:
            fails.append(f"{len(bad_old)} BAD lines in the old tree")
        diff = [(o, n) for o, n in zip(old, new) if o["names"] != n["names"] or o["line"] != n["line"]]
        if len(old) != len(new):
            fails.append("line counts differ")
        if diff:
            fails.append(f"{len(diff)} lines give different names")
        for o, n in diff[:10]:
            print("   ⛔", n["file"], n["lineno"], o["names"], "→", n["names"])
    for r in bad_new[:10]:
        print("   ⛔ BAD", r["file"], r["lineno"], r["why"])
    n_total_names = sum(len(r["names"]) for r in new)
    print(f"[A.2(ii) names] {label} state={st}: lines {n_lines}, lines with a name {n_names_new}, "
          f"names {n_total_names}, identical old/new "
          f"{'n/a' if 'old' not in results else sum(1 for o, n in zip(results['old']['rows'], new) if o['names'] == n['names'])}"
          f" → {'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}", flush=True)
    return 1 if fails else 0


def namespace_worker(root: str, lines_json: str, out: str) -> None:
    use_tree(root)
    os.chdir(root)
    import elevation_sweep_md as M
    assert_from(M, root)
    got = {}
    M.run = lambda a: got.__setitem__("ns", dict(vars(a)))
    M.analyse = lambda *x, **k: got.__setitem__("ns", "merge")
    rows = []
    for it in load(lines_json):
        sys.argv = ["elevation_sweep_md.py"] + it["line"].split() + ["--dry-run"]
        try:
            M.main()
            ns = got.pop("ns", None)
        except SystemExit as e:
            ns = f"SystemExit({e.code})"
        rows.append(dict(it, ns=ns))
    dump(rows, out)


def cmd_namespaces(a) -> int:
    items = queue_lines(sorted(a.lines))
    seen, uniq = set(), []
    for it in items:
        if it["line"] not in seen:
            seen.add(it["line"]); uniq.append(it)
    lj = os.path.join(a.work, "names", "namespace_lines.json")
    dump(uniq, lj)
    outs = {}
    for tag, root in (("old", a.old_root), ("new", a.new_root)):
        out = os.path.join(a.work, "names", f"namespaces_{tag}.json")
        r = subprocess.run([PY, os.path.abspath(__file__), "namespace-worker", "--root", root,
                            "--lines-json", lj, "--out", out], env=child_env("unset"), cwd=root,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if r.returncode:
            print(r.stdout[-3000:])
            return 1
        outs[tag] = load(out)
    n_same = n_diff = 0
    for o, n in zip(outs["old"], outs["new"]):
        on, nn = o["ns"], n["ns"]
        ok = isinstance(on, dict) and isinstance(nn, dict) and nn.get("mesh_rev") == 0 \
            and {k: v for k, v in nn.items() if k != "mesh_rev"} == on and "mesh_rev" not in on
        n_same += ok
        n_diff += (not ok)
        if not ok and n_diff <= 10:
            print("   ⛔", n["file"], n["lineno"], str(on)[:200], "→", str(nn)[:200])
    print(f"[A.2(ii) namespaces] {len(uniq)} unique lines: {n_same} identical apart from mesh_rev=0, "
          f"{n_diff} different → {'PASS' if not n_diff else 'FAIL'}")
    return 1 if n_diff else 0


def cmd_abbrev(a) -> int:
    """`--me` was an abbreviation of --merge; with --mesh-rev it becomes ambiguous (argparse error)."""
    rx = re.compile(r"(?<![\w-])--me(?![\w-])")
    hits = []
    for sub in ("runners", "benchmark", "docs", "src"):
        base = os.path.join(a.live_root, sub)
        for dp, dn, fns in os.walk(base):
            dn[:] = [d for d in dn if d not in ("__pycache__", "logs", ".git")]
            for fn in fns:
                if not fn.endswith((".txt", ".py", ".sh", ".md", ".ipynb", ".json")):
                    continue
                p = os.path.join(dp, fn)
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        for i, ln in enumerate(fh, 1):
                            if rx.search(ln):
                                hits.append(f"{os.path.relpath(p, a.live_root)}:{i}: {ln.strip()[:160]}")
                except OSError:
                    pass
    #  a hit is an invocation when the line runs the sweep (or is a queue line); anything else is prose
    inv = [h for h in hits if "elevation_sweep_md" in h or re.match(r"^runners/jobs_[^:]*\.txt:", h)]
    for h in hits:
        print("   ", "INVOCATION" if h in inv else "prose     ", h)
    print(f"[A.2(ii) abbrev] `--me` occurrences in runners/ benchmark/ docs/ src/: {len(hits)} "
          f"(invocations {len(inv)}, prose {len(hits) - len(inv)}) → {'PASS' if not inv else 'FAIL'}")
    return 1 if inv else 0


# ═══ A.2(vii) positive controls (test-only in-memory registry) ═══════════════════
def _test_frame_builder(spec):
    """TEST ONLY: revision-0 frame parts with the camera group moved 2 mm up."""
    import drone_cad
    import drone_rev
    from cadkit import Assembly
    A = drone_cad.build_frame_cad(drone_rev.base_spec(spec))
    B = Assembly()
    for g, ms in A.parts.items():
        for m in ms:
            m2 = m.copy()
            if g == "camera":
                m2.apply_translation([0.0, 0.0, 0.002])
            B.parts.setdefault(g, []).append(m2)
    return B


class _Checks:
    def __init__(self):
        self.rows = []

    def __call__(self, name, ok, detail=""):
        ok = bool(ok)
        self.rows.append(dict(check=name, ok=ok, detail=str(detail)[:600]))
        print(f"  {'✅' if ok else '⛔'} {name}" + (f" — {str(detail)[:200]}" if detail and not ok else ""),
              flush=True)
        return ok

    def expect_raises(self, name, exc, fn, needle=""):
        try:
            fn()
        except exc as e:
            return self(name, needle.lower() in str(e).lower(), f"{type(e).__name__}: {e}")
        except Exception as e:                                    # noqa: BLE001
            return self(name, False, f"wrong exception {type(e).__name__}: {e}")
        return self(name, False, "no exception")


def controls_worker(root: str, out: str, line: str, ours_line: str, shd_src: str, work: str) -> None:
    use_tree(root)
    os.chdir(root)
    import contextlib
    import dataclasses
    import io
    import articulated_fast
    import drones
    import mesh_rev
    import elevation_sweep_md as M
    for mod in (drones, mesh_rev, articulated_fast, M):
        assert_from(mod, root)
    from arm_grammar import parse, unparse
    from drones import DRONES, build_frame, build_drone, build_propeller, rotor_layout, spec_for
    from mesh_rev import RevEntry, Component
    C = _Checks()

    def cli(argv, env=None, forbid_fastposer=False):
        saved = {k: os.environ.get(k) for k in ("MESH_FIX", "BLADE_LAW")}
        for k in saved:
            os.environ.pop(k, None)
        os.environ.update(env or {})
        orig = articulated_fast.FastPoser
        built = []
        if forbid_fastposer:
            def sentinel(*a, **k):
                built.append(1)
                raise AssertionError("FastPoser was built")
            articulated_fast.FastPoser = sentinel
        buf = io.StringIO()
        sys.argv = ["elevation_sweep_md.py"] + argv
        code = "0"
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                M.main()
        except SystemExit as e:
            code = str(e.code)
        except AssertionError as e:
            code = f"AssertionError: {e}"
        finally:
            articulated_fast.FastPoser = orig
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v
        txt = buf.getvalue()
        names = [m.group(1) for m in re.finditer(r"\[dry\]\s+\S+\s+([A-Za-z0-9_.+-]+\.npz)", txt)]
        return dict(code=code, out=txt, names=names, fastposer_built=bool(built))

    key = "matrice4e"
    base_argv = line.split() + ["--dry-run"]
    r0 = cli(base_argv)
    C("rev-0 line gives one name", r0["code"] == "0" and len(r0["names"]) >= 1, r0)
    name0 = r0["names"][0] if r0["names"] else ""

    # (0) the live registry is empty: --mesh-rev 1 fails for every key, before FastPoser
    C("live registry is empty", mesh_rev.registered_pairs() == [], mesh_rev.registered_pairs())
    for k in sorted(DRONES):
        C.expect_raises(f"spec_for({k!r}, 1) raises ValueError (empty registry)", ValueError,
                        lambda k=k: spec_for(k, 1), "unknown mesh revision")
        r = cli(["--engine", "ours", "--drone", k, "--els", "0", "--n-poses", "64", "--mesh-rev", "1",
                 "--dry-run"], forbid_fastposer=True)
        C(f"CLI --mesh-rev 1 --drone {k} stops: not registered, no FastPoser, no name",
          "not registered" in r["code"] and not r["fastposer_built"] and not r["names"], r["code"])

    entry = RevEntry(key=key, rev=1, overrides=(("envelope_mm", None),),
                     components=(Component(id="TEST-1", change="test only: camera group 2 mm up",
                                           grade="high", sources=("test fixture",), groups=("camera",)),),
                     frame_builder="regress_mesh_rev0_bitidentical_0917:_test_frame_builder",
                     note="test fixture of benchmark/regress_mesh_rev0_bitidentical_0917.py")
    ref = DRONES[key]
    h0 = {"frame": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_frame(ref))),
          "drone": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_drone(ref))),
          "prop": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_propeller(ref)))}

    # (1) rev 1 builds a different mesh; fingerprint not frozen → the CLI refuses
    with mesh_rev.registry_for_tests([entry]):
        sp = spec_for(key, 1)
        C("spec_for(key, 1) is a DroneSpecRev with mesh_rev 1",
          type(sp).__name__ == "DroneSpecRev" and sp.mesh_rev == 1 and sp.envelope_mm is None)
        C("spec_for(key, 1) returns the same object twice", spec_for(key, 1) is sp)
        C("spec_for(key, 0) is DRONES[key]", spec_for(key, 0) is ref and spec_for(key) is ref)
        C("DRONES[key] untouched (plain DroneSpec)", type(ref).__name__ == "DroneSpec")
        h1 = {"frame": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_frame(sp))),
              "drone": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_drone(sp))),
              "prop": mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_propeller(sp)))}
        C("rev 1 frame differs from rev 0", h1["frame"] != h0["frame"])
        C("rev 1 drone differs from rev 0", h1["drone"] != h0["drone"])
        C("rev 1 prop without prop_builder equals rev 0 prop", h1["prop"] == h0["prop"])
        C("rev 0 frame unchanged after building rev 1",
          mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_frame(ref))) == h0["frame"])
        fpo = articulated_fast.FastPoser(sp)
        ver = fpo.verify()
        C("FastPoser(spec_for(key, 1)).verify() ok", ver["ok"], ver)
        r = cli(base_argv + ["--mesh-rev", "1"], forbid_fastposer=True)
        C("CLI refuses a revision without frozen fingerprint, before FastPoser",
          "no frozen fingerprint" in r["code"] and not r["fastposer_built"] and not r["names"], r["code"])
        fp_value = mesh_rev.fingerprint_for(key, 1)
        C("fingerprint_for is 64 hex", re.fullmatch(r"[0-9a-f]{64}", fp_value) is not None, fp_value)
        C("fingerprint_for is stable in-process", mesh_rev.fingerprint_for(key, 1) == fp_value)

    frozen = dataclasses.replace(entry, fingerprint=fp_value)
    with mesh_rev.registry_for_tests([frozen]):
        r1 = cli(base_argv + ["--mesh-rev", "1"])
        name1 = r1["names"][0] if r1["names"] else ""
        C("CLI rev 1 dry-run gives a name", r1["code"] == "0" and bool(name1), r1["code"])
        C("rev 1 name carries _mfixbatteryi5rev1_blperairframe", "_mfixbatteryi5rev1_blperairframe" in name1,
          name1)
        C("rev 1 name = rev 0 name with rev1 after the mfix value",
          name1 == name0.replace("_mfixbatteryi5_", "_mfixbatteryi5rev1_", 1) and name1 != name0,
          f"{name0} | {name1}")
        C("guard printed a fingerprint match", "fingerprint matches" in r1["out"])
        stem = re.sub(r"_el[+-]\d+(?:\.\d+)?_\d+\.npz$", "", name1)
        try:
            f = parse(stem)
            C("arm_grammar parses the rev 1 stem (mesh_fix = batteryi5rev1) and unparse round-trips",
              f.get("mesh_fix") == "batteryi5rev1" and unparse(f) == stem, f)
        except Exception as e:                                    # noqa: BLE001
            C("arm_grammar parses the rev 1 stem", False, e)
        C("mesh_rev.arm_mesh_rev(rev 1 name) == 1 and (rev 0 name) == 0",
          mesh_rev.arm_mesh_rev(name1) == 1 and mesh_rev.arm_mesh_rev(name0) == 0)
        ro = cli(ours_line.split() + ["--dry-run", "--mesh-rev", "1"])
        C("ours-engine rev 1 dry-run name carries the tag",
          ro["code"] == "0" and ro["names"] and all("_mfixbatteryi5rev1_blperairframe" in n for n in ro["names"]),
          ro["names"] or ro["code"])
        rs = cli(base_argv + ["--mesh-rev", "1", "--body-scale", "0.4"])
        C("scale knob with rev 1: guard fingerprints the unscaled mesh; name has _bs0.4 and rev1",
          rs["code"] == "0" and rs["names"] and "_bs0.4" in rs["names"][0] and "rev1" in rs["names"][0],
          rs["code"])
        for env in ({"MESH_FIX": "none"}, {"MESH_FIX": "all"}, {"MESH_FIX": "battery"}, {"BLADE_LAW": "legacy"}):
            r = cli(base_argv + ["--mesh-rev", "1"], env=env, forbid_fastposer=True)
            kind = "MESH_FIX" if "MESH_FIX" in env else "BLADE_LAW"
            C(f"{env} --mesh-rev 1 stops before FastPoser with a {kind} message",
              kind in r["code"] and not r["fastposer_built"] and not r["names"], r["code"])
        os.environ["MESH_FIX"] = "none"
        try:
            C.expect_raises("drone_rev refuses MESH_FIX=none when building a rev spec directly",
                            ValueError, lambda: build_frame(spec_for(key, 1)), "canonical")
        finally:
            os.environ.pop("MESH_FIX", None)
        C.expect_raises("drone_rev refuses mesh_fix=False", ValueError,
                        lambda: build_frame(spec_for(key, 1), mesh_fix=False), "canonical")
        C.expect_raises("drone_rev refuses blade_law='legacy'", ValueError,
                        lambda: build_propeller(spec_for(key, 1), blade_law="legacy"), "blade_law")
        C("rev 1 mesh still builds with explicit canonical mesh_fix='battery'",
          mesh_hash(*(lambda m: (m.v, m.f, m.g))(build_frame(spec_for(key, 1), mesh_fix="battery"))) == h1["frame"])
        C("fingerprint_for equals the value the CLI checked", mesh_rev.fingerprint_for(key, 1) == fp_value)

    # (2) a tampered fingerprint stops the dry-run
    tampered = dataclasses.replace(entry, fingerprint="0" * 64)
    with mesh_rev.registry_for_tests([tampered]):
        r = cli(base_argv + ["--mesh-rev", "1"])
        C("tampered fingerprint stops the dry-run with no name",
          "fingerprint mismatch" in r["code"] and not r["names"], r["code"])
        rs = cli(base_argv + ["--mesh-rev", "1", "--frame-scale", "1.3"])
        C("tampered fingerprint also stops a scaled run", "fingerprint mismatch" in rs["code"] and not rs["names"],
          rs["code"])

    # (3) unknown (key, rev) raises ValueError; CLI refuses
    with mesh_rev.registry_for_tests([frozen]):
        C.expect_raises("spec_for(key, 2) raises ValueError", ValueError, lambda: spec_for(key, 2), "unknown")
        C.expect_raises("spec_for('mini2', 1) raises ValueError", ValueError, lambda: spec_for("mini2", 1), "unknown")
        C.expect_raises("spec_for('nokey', 0) raises ValueError", ValueError, lambda: spec_for("nokey"), "unknown")
        C.expect_raises("spec_for(key, -1) raises ValueError", ValueError, lambda: spec_for(key, -1), "integer")
        C.expect_raises("spec_for(key, True) raises ValueError", ValueError, lambda: spec_for(key, True), "integer")
        C.expect_raises("spec_for(key, 1.0) raises ValueError", ValueError, lambda: spec_for(key, 1.0), "integer")
        r = cli(base_argv + ["--mesh-rev", "2"], forbid_fastposer=True)
        C("CLI --mesh-rev 2 stops: not registered", "not registered" in r["code"] and not r["fastposer_built"],
          r["code"])
        r = cli(base_argv + ["--mesh-rev", "-1"], forbid_fastposer=True)
        C("CLI --mesh-rev -1 stops before FastPoser", ">= 0" in r["code"] and not r["fastposer_built"], r["code"])

    # (4) rotor_dirs is honoured; revision 0 is not
    flipped = dataclasses.replace(frozen, overrides=(("envelope_mm", None), ("rotor_dirs", (-1, 1, -1, 1))),
                                  fingerprint=None)
    with mesh_rev.registry_for_tests([flipped]):
        spf = spec_for(key, 1)
        C("rotor_layout follows rotor_dirs", [r_["dir"] for r_ in rotor_layout(spf)] == [-1, 1, -1, 1])
        C("revision 0 rotor dirs unchanged", [r_["dir"] for r_ in rotor_layout(ref)] == [1, -1, 1, -1])
        fpf = articulated_fast.FastPoser(spf)
        C("FastPoser with flipped dirs verifies", fpf.verify()["ok"] and fpf.dirs == [-1, 1, -1, 1])

    # (5) registry validation rejects what plan B.0 forbids
    bad = [
        ("forbidden override prop_dia_mm", dict(overrides=(("prop_dia_mm", 300.0),)), "may not change"),
        ("unhashable override", dict(overrides=(("rotor_z_mm", [1.0, 2.0, 3.0, 4.0]),)), "hashable"),
        ("component grade medium", dict(components=(Component("X", "x", "medium", ("s",)),)), "grade"),
        ("component without source", dict(components=(Component("X", "x", "high", ()),)), "no source"),
        ("builder reference without colon", dict(frame_builder="nofn"), "module:function"),
        ("fingerprint not hex", dict(fingerprint="xyz"), "hex"),
        ("revision 0 entry", dict(rev=0), "start at 1"),
    ]
    for label, kw, needle in bad:
        C.expect_raises(f"validate_entry rejects {label}", (ValueError, TypeError),
                        lambda kw=kw: mesh_rev.validate_entry(dataclasses.replace(entry, **kw)), needle)
    with mesh_rev.registry_for_tests([dataclasses.replace(entry, overrides=())]):
        C.expect_raises("make_spec rejects a revision that keeps envelope_mm", ValueError,
                        lambda: spec_for(key, 1), "envelope_mm")
    with mesh_rev.registry_for_tests([dataclasses.replace(entry, overrides=(("envelope_mm", None), ("rotor_dirs", (1, 1, 1))))]):
        C.expect_raises("make_spec rejects rotor_dirs of the wrong length", ValueError,
                        lambda: spec_for(key, 1), "rotor_dirs")
    with mesh_rev.registry_for_tests([dataclasses.replace(entry, components=(Component("X", "x", "high", ("s",), ("newgroup",)),))]):
        C.expect_raises("make_spec rejects an unknown material group", ValueError,
                        lambda: spec_for(key, 1), "unknown groups")

    # (6) split_mesh_fix table
    table = [("batteryi5", (("battery", "i5"), 0)), ("batteryi5rev1", (("battery", "i5"), 1)),
             ("all", (("all",), 0)), ("i3i4m4", (("i3", "i4", "m4"), 0)), ("batteryi5rev12", (("battery", "i5"), 12))]
    for val, want in table:
        try:
            got = mesh_rev.split_mesh_fix(val)
        except Exception as e:                                    # noqa: BLE001
            got = repr(e)
        C(f"split_mesh_fix({val!r}) == {want}", got == want, got)
    for val in ("batteryi5rev0", "foo", "batteryi5rev", "rev1", "batteryi5rev01"):
        C.expect_raises(f"split_mesh_fix({val!r}) raises", ValueError, lambda v=val: mesh_rev.split_mesh_fix(v))

    # (7) merge routing on a tiny synthetic shard folder
    import glob as _glob
    import numpy as np
    shd = os.path.join(work, "controls_shards"); shd0 = os.path.join(work, "controls_shards_rev0only")
    for d in (shd, shd0):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    pick = sorted(_glob.glob(os.path.join(shd_src, "*_mfixbatteryi5_blperairframe_*_el-30_0[01].npz")),
                  key=os.path.getsize)[:1]
    if pick:
        stem = re.sub(r"_0[01]\.npz$", "", os.path.basename(pick[0]))
        cell = sorted(_glob.glob(os.path.join(shd_src, stem + "_[0-9][0-9].npz")))
        for fsrc in cell:
            b = os.path.basename(fsrc)
            shutil.copy2(fsrc, os.path.join(shd, b)); shutil.copy2(fsrc, os.path.join(shd0, b))
            shutil.copy2(fsrc, os.path.join(shd, b.replace("_mfixbatteryi5_", "_mfixbatteryi5rev1_", 1)))
        outs = {}
        for tag, d in (("with_rev", shd), ("rev0_only", shd0)):
            M.SHD = d
            M.OUT = os.path.join(work, f"controls_merge_{tag}.json")
            M.OUTN = os.path.join(work, f"controls_merge_{tag}.npz")
            for pth in (M.OUT, M.OUTN) + mesh_rev.meshrev_ledger_paths(M.OUT, M.OUTN):
                if os.path.exists(pth):
                    os.remove(pth)
            with contextlib.redirect_stdout(io.StringIO()):
                M.analyse()
            outs[tag] = (load(M.OUT), mesh_rev.meshrev_ledger_paths(M.OUT, M.OUTN))
        main_w, (rj, rn) = outs["with_rev"]
        main_0, (rj0, rn0) = outs["rev0_only"]
        C("merge: main ledger has no revision arm", all(mesh_rev.arm_mesh_rev(r_["engine"]) == 0 for r_ in main_w["rows"]))
        C("merge: main ledger identical with or without the revision shards", main_w == main_0)
        C("merge: meshrev ledger written only when revision shards exist", os.path.exists(rj) and not os.path.exists(rj0))
        if os.path.exists(rj):
            R = load(rj)
            C("merge: meshrev ledger holds only revision arms",
              len(R["rows"]) >= 1 and all(mesh_rev.arm_mesh_rev(r_["engine"]) == 1 for r_ in R["rows"]))
            strip = lambda rows: [{k: v for k, v in r_.items() if k != "engine"} for r_ in rows]
            C("merge: revision rows equal the rev 0 rows apart from the engine name",
              strip(R["rows"]) == strip(main_0["rows"]))
            Z1, Z0 = np.load(rn), np.load(M.OUTN.replace("with_rev", "rev0_only"))
            C("merge: meshrev npz series equal", sorted(k.replace("rev1", "") for k in Z1.files) == sorted(Z0.files)
              and all(np.array_equal(Z1[k], Z0[k.replace("rev1", "")]) for k in Z1.files))
        C("merge: module globals restored after the revision pass", M.OUT.endswith("controls_merge_rev0_only.json"))
    else:
        C("merge control found a small shard cell", False, shd_src)

    n_fail = sum(1 for r_ in C.rows if not r_["ok"])
    dump(dict(n_checks=len(C.rows), n_fail=n_fail, rows=C.rows), out)
    print(f"[A.2(vii) controls] {len(C.rows)} checks, {n_fail} failed")


def cmd_controls(a) -> int:
    out = os.path.join(a.work, "controls.json")
    r = subprocess.run([PY, os.path.abspath(__file__), "controls-worker", "--root", a.new_root, "--out", out,
                        "--line", a.line, "--ours-line", a.ours_line, "--shd-src", a.shd_src,
                        "--work", a.work], env=child_env("unset"), cwd=a.new_root)
    if r.returncode or not os.path.exists(out):
        print("⛔ controls worker failed")
        return 1
    return 1 if load(out)["n_fail"] else 0


# ═══ drone_rev union parity ════════════════════════════════════════════════════
def union_parity_worker(root: str, out: str) -> None:
    use_tree(root)
    import inspect
    import cadkit
    import drone_cad
    import drone_rev
    import drones
    for mod in (cadkit, drone_cad, drone_rev, drones):
        assert_from(mod, root)
    from drones import DRONES
    C = _Checks()
    src = inspect.getsource(drone_cad.build_frame_cad)
    m = re.search(r"union_groups = \[(.*?)\]", src, re.S)
    lst = tuple(re.findall(r'"([a-z_]+)"', m.group(1))) if m else ()
    C("drone_rev.UNION_GROUPS_REV0 equals the list in drone_cad.build_frame_cad", lst == drone_rev.UNION_GROUPS_REV0,
      lst)
    orig = cadkit.Assembly.union_group
    for key in sorted(DRONES):
        sp = DRONES[key]
        snap, order = {}, []

        def spy(self, group, _snap=snap, _order=order):
            if not _order:
                _snap["parts"] = {g: [mm.copy() for mm in ms] for g, ms in self.parts.items()}
            _order.append(group)
            return orig(self, group)
        cadkit.Assembly.union_group = spy
        try:
            A = drone_cad.build_frame_cad(sp)
        finally:
            cadkit.Assembly.union_group = orig
        ref = A.to_geom()
        B = cadkit.Assembly()
        B.parts = snap["parts"]
        order2 = []

        def spy2(self, group, _o=order2):
            _o.append(group)
            return orig(self, group)
        cadkit.Assembly.union_group = spy2
        try:
            drone_rev.finish_frame_assembly(B, sp)
        finally:
            cadkit.Assembly.union_group = orig
        got = B.to_geom()
        C(f"{key}: finish_frame_assembly replays revision 0's union calls", order2 == order, (order, order2))
        C(f"{key}: finish_frame_assembly on revision 0's own parts gives the same bytes",
          mesh_hash(ref.v, ref.f, ref.g) == mesh_hash(got.v, got.f, got.g))
        body = B.parts.get("body", [])
        C.rows.append(dict(check=f"{key}: body parts watertight (information)", ok=True,
                           detail=f"{sum(bool(x.is_watertight) for x in body)}/{len(body)}"))
    #  negative control: a revision builder that leaves the body open must be refused
    sp = DRONES["mini2"]
    A = drone_cad.build_frame_cad(sp)
    B = cadkit.Assembly()
    B.parts = {g: [mm.copy() for mm in ms] for g, ms in A.parts.items()}
    body0 = B.parts["body"][0]
    body0.update_faces([i for i in range(len(body0.faces)) if i != 0])
    C("negative control: the opened body is not watertight", not body0.is_watertight)
    C.expect_raises("finish_frame_assembly refuses a body that is not closed", RuntimeError,
                    lambda: drone_rev.finish_frame_assembly(B, sp), "closed")
    n_fail = sum(1 for r_ in C.rows if not r_["ok"])
    dump(dict(n_checks=len(C.rows), n_fail=n_fail, rows=C.rows), out)
    print(f"[union parity] {len(C.rows)} checks, {n_fail} failed")


def cmd_union_parity(a) -> int:
    out = os.path.join(a.work, "union_parity.json")
    r = subprocess.run([PY, os.path.abspath(__file__), "union-parity-worker", "--root", a.new_root, "--out", out],
                       env=child_env("unset"), cwd=a.new_root)
    return 1 if (r.returncode or load(out)["n_fail"]) else 0


# ═══ A.2(iii) grammar ══════════════════════════════════════════════════════════
def grammar_worker(root: str, shard_list: str, ledger: str, out: str) -> None:
    use_tree(root)
    import arm_grammar
    assert_from(arm_grammar, root)
    arms = set()
    with open(shard_list) as fh:
        for ln in fh:
            m = re.match(r"^(.*)_el([+-]\d+(?:\.\d+)?)_\d+\.npz$", ln.strip())
            if m:
                arms.add(m.group(1))
    led = {r["engine"] for r in load(ledger)["rows"]}
    res = {}
    for arm in sorted(arms | led):
        try:
            f = arm_grammar.parse(arm)
            res[arm] = dict(fields={k: (v if isinstance(v, (str, int, float, bool)) or v is None else repr(v))
                                    for k, v in f.items()}, roundtrip=(arm_grammar.unparse(f) == arm))
        except Exception as e:                                    # noqa: BLE001
            res[arm] = dict(error=f"{type(e).__name__}: {e}")
    dump(dict(n_shard_arms=len(arms), n_ledger_arms=len(led), arms=res), out)


def cmd_grammar(a) -> int:
    lst = os.path.join(a.work, "grammar", "shard_names.txt")
    os.makedirs(os.path.dirname(lst), exist_ok=True)
    with open(lst, "w") as fh:
        fh.write("\n".join(sorted(os.listdir(a.shd))) + "\n")
    rc = 0
    res = {}
    for tag, root in (("old", a.old_root), ("new", a.new_root)):
        out = os.path.join(a.work, "grammar", f"parse_{tag}.json")
        r = subprocess.run([PY, os.path.abspath(__file__), "grammar-worker", "--root", root, "--shard-list", lst,
                            "--ledger", a.ledger, "--out", out], env=child_env("unset"))
        rc |= r.returncode
        res[tag] = load(out)
    same = res["old"] == res["new"]
    arms = res["new"]["arms"]
    n_err = sum(1 for v in arms.values() if "error" in v)
    n_rt = sum(1 for v in arms.values() if v.get("roundtrip"))
    print(f"[A.2(iii) parse] {len(arms)} arms (shards {res['new']['n_shard_arms']}, ledger "
          f"{res['new']['n_ledger_arms']}): parsed {len(arms)-n_err}, round-trip {n_rt}, errors {n_err}; "
          f"old == new: {same}")
    rc |= (not same)
    # check_arm_names.py in both trees, on a view that has the frozen ledger and the shard snapshot
    ex = {}
    for tag, root in (("old", a.old_root), ("new", a.new_root)):
        view = os.path.join(a.work, "grammar", f"view_{tag}")
        shutil.rmtree(view, ignore_errors=True)
        os.makedirs(os.path.join(view, "outputs", "elev_sweep_shards"))
        for sub in ("src", "benchmark"):
            os.symlink(os.path.join(root, sub), os.path.join(view, sub))
        shutil.copy2(a.ledger, os.path.join(view, "outputs", "elevation_sweep_md.json"))
        for fn in os.listdir(a.shd):
            os.link(os.path.join(a.shd, fn), os.path.join(view, "outputs", "elev_sweep_shards", fn))
        r = subprocess.run([PY, os.path.join(view, "benchmark", "check_arm_names.py"), "--shards"],
                           env=child_env("unset"), cwd=view, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        with open(os.path.join(a.work, "grammar", f"check_arm_names_{tag}.log"), "w") as fh:
            fh.write(r.stdout)
        ex[tag] = (r.returncode, [ln for ln in r.stdout.splitlines() if ln.strip()])
        shutil.rmtree(os.path.join(view, "outputs", "elev_sweep_shards"), ignore_errors=True)
    same_cn = ex["old"] == ex["new"]
    print(f"[A.2(iii) check_arm_names --shards] exit old {ex['old'][0]} new {ex['new'][0]}; "
          f"output identical: {same_cn}; last line: {ex['new'][1][-1][:160] if ex['new'][1] else ''}")
    rc |= (not same_cn)
    return 1 if rc else 0


# ═══ A.2(iv) merge ═════════════════════════════════════════════════════════════
def merge_worker(root: str, shd: str, out_json: str, out_npz: str) -> None:
    use_tree(root)
    import elevation_sweep_md as M
    assert_from(M, root)
    M.SHD, M.OUT, M.OUTN = shd, out_json, out_npz
    t0 = time.time()
    M.analyse()
    dump(dict(seconds=round(time.time() - t0, 1), n_shards=len(os.listdir(shd))), out_json + ".time.json")


def cmd_merge(a) -> int:
    d = os.path.join(a.work, "merge", a.label)
    os.makedirs(d, exist_ok=True)
    shd = a.shd
    if a.subset:
        shd = os.path.join(d, "shards")
        if not os.path.isdir(shd):
            cells = {}
            for fn in sorted(os.listdir(a.shd)):
                m = re.match(r"^(.*_el[+-]\d+(?:\.\d+)?)_\d+\.npz$", fn)
                if m:
                    cells.setdefault(m.group(1), []).append(fn)
            order = sorted(cells, key=lambda c: hashlib.sha256(c.encode()).hexdigest())
            chosen, n = [], 0
            for c in order:
                if n >= a.subset:
                    break
                chosen.append(c); n += len(cells[c])
            os.makedirs(shd)
            for c in chosen:
                for fn in cells[c]:
                    os.link(os.path.join(a.shd, fn), os.path.join(shd, fn))
            dump(dict(rule="whole cells in sha256(cell) order until >= subset shards", subset=a.subset,
                      n_cells=len(chosen), n_shards=n, cells=chosen), os.path.join(d, "subset.json"))
    procs = {}
    for tag, root in (("old", a.old_root), ("new", a.new_root)):
        oj, on = os.path.join(d, f"ledger_{tag}.json"), os.path.join(d, f"ledger_{tag}.npz")
        if os.path.exists(oj) and not a.redo:
            continue
        log = open(os.path.join(d, f"merge_{tag}.log"), "w")
        procs[tag] = subprocess.Popen([PY, os.path.abspath(__file__), "merge-worker", "--root", root, "--shd", shd,
                                       "--out-json", oj, "--out-npz", on], env=child_env("unset"), stdout=log,
                                      stderr=subprocess.STDOUT)
    for tag, p in procs.items():
        p.wait()
        print(f"[merge] {a.label} {tag} rc={p.returncode}", flush=True)
        if p.returncode:
            return 1
    import numpy as np
    J = {t: load(os.path.join(d, f"ledger_{t}.json")) for t in ("old", "new")}
    T = {t: load(os.path.join(d, f"ledger_{t}.json.time.json")) for t in ("old", "new")}
    fails = []
    if J["old"] != J["new"]:
        ko, kn = J["old"].get("rows", []), J["new"].get("rows", [])
        nd = sum(1 for x, y in zip(ko, kn) if x != y) + abs(len(ko) - len(kn))
        fails.append(f"json differs ({nd} rows differ; meta equal: {J['old'].get('_meta') == J['new'].get('_meta')})")
    Zo, Zn = np.load(os.path.join(d, "ledger_old.npz")), np.load(os.path.join(d, "ledger_new.npz"))
    if sorted(Zo.files) != sorted(Zn.files):
        fails.append("npz keys differ")
    else:
        nd = sum(1 for k in Zo.files if not np.array_equal(Zo[k], Zn[k]))
        if nd:
            fails.append(f"{nd} npz arrays differ")
    extra = [f for f in os.listdir(d) if "meshrev" in f]
    if extra:
        fails.append(f"meshrev ledger written without revision shards: {extra}")
    print(f"[A.2(iv) merge] {a.label}: shards {T['new']['n_shards']}, rows {len(J['new'].get('rows', []))}, "
          f"npz series {len(Zn.files)}; seconds old {T['old']['seconds']} new {T['new']['seconds']} → "
          f"{'PASS' if not fails else 'FAIL: ' + '; '.join(fails)}")
    return 1 if fails else 0


# ═══ views: a tree's code + frozen copies of the inputs the checkers read ═══════════
def make_view(work: str, label: str, root: str, inputs: str, shards: str | None = None) -> str:
    """work/views/<label>: src/ and benchmark/ link to `root`; outputs/, docs/, runners/ are real
    copies (checkers write there); assets/ links to the frozen inputs (read only);
    outputs/elev_sweep_shards holds hard links to the shard snapshot when `shards` is given."""
    view = os.path.join(work, "views", label)
    if os.path.isdir(view):
        return view
    os.makedirs(view)
    for sub in ("src", "benchmark"):
        os.symlink(os.path.join(root, sub), os.path.join(view, sub))
    shutil.copytree(os.path.join(inputs, "outputs"), os.path.join(view, "outputs"))
    shutil.copytree(os.path.join(inputs, "docs"), os.path.join(view, "docs"))
    shutil.copytree(os.path.join(root, "runners"), os.path.join(view, "runners"))
    os.makedirs(os.path.join(view, "assets"))
    os.symlink(os.path.join(inputs, "assets", "meshes"), os.path.join(view, "assets", "meshes"))
    if shards:
        d = os.path.join(view, "outputs", "elev_sweep_shards")
        os.makedirs(d, exist_ok=True)
        for fn in os.listdir(shards):
            os.link(os.path.join(shards, fn), os.path.join(d, fn))
    return view


def run_logged(cmd, cwd, log, env, timeout=7200) -> dict:
    t0 = time.time()
    with open(log, "w") as fh:
        try:
            r = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
            rc = r.returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    return dict(rc=rc, seconds=round(time.time() - t0, 1), log=log)


# ═══ A.2(v) existing checks ════════════════════════════════════════════════════
EXISTING = (
    ("regress_blade_law_bitidentical", ["benchmark/regress_blade_law_bitidentical.py"]),
    ("regress_mesh_fix_battery_0816", ["benchmark/regress_mesh_fix_battery_0816.py"]),
    ("regress_mesh_fix_i4_m4_0816", ["benchmark/regress_mesh_fix_i4_m4_0816.py"]),
    ("mesh_check", ["src/mesh_check.py"]),
    ("mesh_topo_check", ["src/mesh_topo_check.py"]),
    ("mesh_topo_check_seal", ["src/mesh_topo_check.py", "--check-seal"]),
    ("mesh_certify", ["benchmark/mesh_certify.py"]),
)


def cmd_existing(a) -> int:
    only = set(a.only.split(",")) if a.only else None
    res_path = os.path.join(a.work, "existing", "existing.json")
    res = load(res_path) if os.path.exists(res_path) else {}
    views = {t: make_view(a.work, f"existing_{t}", r, a.inputs) for t, r in (("old", a.old_root), ("new", a.new_root))}
    tmp = os.path.join(a.work, "existing", "tmp")
    os.makedirs(tmp, exist_ok=True)
    for name, rel in EXISTING:
        if only and name not in only:
            continue
        if name in res and not a.redo:
            continue
        jobs = {}

        def one(tag):
            v = views[tag]
            env = child_env("unset", dict(TMPDIR=tmp, PYTHONPATH=f"{v}/src:{v}/benchmark"))
            return run_logged([PY, os.path.join(v, rel[0])] + rel[1:], v,
                              os.path.join(a.work, "existing", f"{name}_{tag}.log"), env)
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for tag in ("old", "new"):
                jobs[tag] = ex.submit(one, tag)
            res[name] = {t: f.result() for t, f in jobs.items()}
        print(f"[A.2(v)] {name}: exit old {res[name]['old']['rc']} ({res[name]['old']['seconds']}s) "
              f"new {res[name]['new']['rc']} ({res[name]['new']['seconds']}s)", flush=True)
        dump(res, res_path)
    bad = [n for n, r in res.items() if r["old"]["rc"] != r["new"]["rc"] and n != "mesh_certify"]
    print(f"[A.2(v)] {len(res)} checks; exit codes equal old/new for {len(res) - len(bad)}"
          f"{'' if 'mesh_certify' not in res else ' (mesh_certify judged from its log)'}; different: {bad}")
    return 1 if bad else 0


# ═══ A.2(vi) citations ═════════════════════════════════════════════════════════
def edited_lines(old_root: str, new_root: str) -> dict:
    out = {}
    for rel in WORKER_FILES:
        o = open(os.path.join(old_root, rel), encoding="utf-8").read().split("\n")
        n = open(os.path.join(new_root, rel), encoding="utf-8").read().split("\n")
        ch = [i + 1 for i in range(min(len(o), len(n))) if o[i] != n[i]]
        out[rel] = dict(changed=ch, old={i: o[i - 1] for i in ch}, new={i: n[i - 1] for i in ch},
                        n_old=len(o), n_new=len(n), appended=max(0, len(n) - len(o)),
                        removed=max(0, len(o) - len(n)))
    return out


def cmd_citations(a) -> int:
    ed = edited_lines(a.old_root, a.new_root)
    fails = []
    for rel, e in ed.items():
        if e["removed"]:
            fails.append(f"{rel}: lines removed")
        print(f"[A.2(vi)] {rel}: changed lines {e['changed']}, appended {e['appended']}, removed {e['removed']}")
    hits = []
    skip_dirs = {".git", "__pycache__", "elev_sweep_shards", "figures", "renders", "jihyuck_po", "photos",
                 "reference", "partial", "prefreeze", "meshes", "logs", "figs", "archive"}
    for dp, dn, fns in os.walk(a.live_root):
        dn[:] = [d for d in dn if d not in skip_dirs]
        for fn in fns:
            if not fn.endswith((".py", ".md", ".ipynb", ".json", ".txt", ".sh")):
                continue
            pth = os.path.join(dp, fn)
            rel_p = os.path.relpath(pth, a.live_root)
            if rel_p in WORKER_FILES:
                continue
            try:
                if os.path.getsize(pth) > 20_000_000:
                    continue
                txt = open(pth, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for rel, e in ed.items():
                b = os.path.basename(rel)
                if b not in txt:
                    continue
                for m in re.finditer(re.escape(b) + r"[\"']?\s*[:,]\s*(\d{2,4})(?:\s*[-–~]\s*(\d{2,4}))?", txt):
                    lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
                    for ln in e["changed"]:
                        if lo <= ln <= hi:
                            hits.append(dict(file=rel_p, target=rel, line=ln, kind="line number", text=m.group(0)))
                for ln in e["changed"]:
                    q = e["old"][ln].strip()
                    if len(q) > 12 and q in txt:
                        hits.append(dict(file=rel_p, target=rel, line=ln, kind="quote", text=q[:120],
                                         still_substring_of_new_line=q in e["new"][ln]))
    runnable = sorted({h["file"] for h in hits if h["file"].startswith(("benchmark/", "src/")) and h["file"].endswith(".py")})
    for h in hits:
        print(f"   {h['file']}: {h['target']}:{h['line']} {h['kind']}"
              + (f" (quote still a substring: {h['still_substring_of_new_line']})" if h["kind"] == "quote" else ""))
    #  (line, text) anchor lists checked at import time by scripts that copy code from the sweep
    anchors = {}
    import ast
    for script in ("benchmark/dropout_paths_0916.py",):
        src = open(os.path.join(a.live_root, script), encoding="utf-8").read()
        node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign)
                    and any(getattr(t, "id", "") == "ANCHORS" for t in n.targets))
        pairs = ast.literal_eval(node.value)
        res_a = {}
        for tag, root in (("old", a.old_root), ("new", a.new_root)):
            L = open(os.path.join(root, "benchmark", "elevation_sweep_md.py"), encoding="utf-8").read().splitlines()
            res_a[tag] = [ln for ln, txt in pairs if ln > len(L) or txt not in L[ln - 1]]
        anchors[script] = dict(n=len(pairs), failing_old=res_a["old"], failing_new=res_a["new"])
        print(f"[A.2(vi)] {script}: {len(pairs)} (line, text) anchors into elevation_sweep_md.py — failing old "
              f"{res_a['old']} new {res_a['new']}")
        if res_a["new"] != res_a["old"]:
            fails.append(f"{script}: anchors changed")
    runs = {}
    for script, extra in (("benchmark/isac_plan_link_budget_0915.py", []),
                          ("benchmark/isac_plan_kernel_match_0915.py", [])):
        runs[script] = {}
        for tag, root in (("old", a.old_root), ("new", a.new_root)):
            v = make_view(a.work, f"citations_{tag}", root, a.inputs, shards=a.shd)
            outp = os.path.join(a.work, "citations", f"{os.path.basename(script)[:-3]}_{tag}.json")
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            env = child_env("unset", dict(PYTHONPATH=f"{v}/src:{v}/benchmark"))
            r = run_logged([PY, os.path.join(v, script), "--root", v, "--out", outp] + extra, v,
                           outp.replace(".json", ".log"), env)
            r["ledger_exists"] = os.path.exists(outp)
            runs[script][tag] = r
        o, n = runs[script]["old"], runs[script]["new"]
        diff_paths = []
        if o["ledger_exists"] and n["ledger_exists"]:
            diff_paths = json_diff(load(os.path.join(a.work, "citations", f"{os.path.basename(script)[:-3]}_old.json")),
                                   load(os.path.join(a.work, "citations", f"{os.path.basename(script)[:-3]}_new.json")))
        runs[script]["diff_paths"] = diff_paths[:200]
        print(f"[A.2(vi)] {script}: exit old {o['rc']} new {n['rc']}; ledgers {o['ledger_exists']}/{n['ledger_exists']}; "
              f"differing JSON paths {len(diff_paths)}")
        for dpth in diff_paths[:30]:
            print("      ", dpth)
        if o["rc"] != n["rc"]:
            fails.append(f"{script}: exit code changed")
    dump(dict(edited=ed, hits=hits, runnable_citing_scripts=runnable, anchors=anchors, runs=runs, fails=fails),
         os.path.join(a.work, "citations", "citations.json"))
    print(f"[A.2(vi)] citations hitting edited lines: {len(hits)} "
          f"(quotes no longer found: {sum(1 for h in hits if h['kind'] == 'quote' and not h['still_substring_of_new_line'])}); "
          f"fails: {fails}")
    return 1 if fails else 0


def json_diff(x, y, path="$") -> list:
    if type(x) is not type(y):
        return [path]
    if isinstance(x, dict):
        out = []
        for k in sorted(set(x) | set(y), key=str):
            if k not in x or k not in y:
                out.append(f"{path}.{k}")
            else:
                out += json_diff(x[k], y[k], f"{path}.{k}")
        return out
    if isinstance(x, list):
        if len(x) != len(y):
            return [f"{path}[len {len(x)}→{len(y)}]"]
        out = []
        for i, (u, v) in enumerate(zip(x, y)):
            out += json_diff(u, v, f"{path}[{i}]")
        return out
    return [] if x == y else [path]


def cmd_quotes(a) -> int:
    """A.2(vi), static: every call like Q("<edited file>", "needle"[, after]) or X.quote("<edited file>", …)
    in src/ and benchmark/ of the live repo (read only) is evaluated with the semantics of
    isac_plan_kernel_match_0915.Ledger.quote (needle is a substring of some line at or after the first
    line containing `after`) against the old and the new text. Only string-literal arguments are read."""
    import ast
    texts = {t: {rel: open(os.path.join(r, rel), encoding="utf-8").read().splitlines() for rel in WORKER_FILES}
             for t, r in (("old", a.old_root), ("new", a.new_root))}
    rows = []
    for sub in ("src", "benchmark"):
        for dp, dn, fns in os.walk(os.path.join(a.live_root, sub)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for fn in fns:
                if not fn.endswith(".py"):
                    continue
                pth = os.path.join(dp, fn)
                rel_p = os.path.relpath(pth, a.live_root)
                try:
                    src = open(pth, encoding="utf-8", errors="replace").read()
                    if not any(os.path.basename(w) in src for w in WORKER_FILES):
                        continue
                    tree = ast.parse(src)
                except (OSError, SyntaxError):
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call) or len(node.args) < 2:
                        continue
                    f0, f1 = node.args[0], node.args[1]
                    if not (isinstance(f0, ast.Constant) and isinstance(f0.value, str) and f0.value in WORKER_FILES
                            and isinstance(f1, ast.Constant) and isinstance(f1.value, str)):
                        continue
                    after = None
                    if len(node.args) > 2 and isinstance(node.args[2], ast.Constant) and isinstance(node.args[2].value, str):
                        after = node.args[2].value
                    for kw in node.keywords:
                        if kw.arg == "after" and isinstance(kw.value, ast.Constant):
                            after = kw.value.value
                    res = {}
                    for t in ("old", "new"):
                        L = texts[t][f0.value]
                        start = 0
                        if after is not None:
                            hit = [i for i, row in enumerate(L) if after in row]
                            if not hit:
                                res[t] = None
                                continue
                            start = hit[0] + 1
                        hit = [i + 1 for i in range(start, len(L)) if f1.value in L[i]]
                        res[t] = hit[0] if hit else None
                    rows.append(dict(file=rel_p, line=node.lineno, target=f0.value, needle=f1.value[:100],
                                     after=after, old=res["old"], new=res["new"]))
    changed = [r for r in rows if r["old"] != r["new"]]
    lost = [r for r in rows if r["old"] is not None and r["new"] is None]
    for r in changed:
        print(f"   ⛔ {r['file']}:{r['line']} {r['target']} {r['needle']!r}: old line {r['old']} → new {r['new']}")
    dump(dict(rows=rows, changed=changed), os.path.join(a.work, "citations", "quote_calls.json"))
    print(f"[A.2(vi) quote calls] {len(rows)} literal quote calls into the edited files in "
          f"{len({r['file'] for r in rows})} scripts: found in old {sum(r['old'] is not None for r in rows)}, "
          f"found in new {sum(r['new'] is not None for r in rows)}, resolved line changed {len(changed)}, "
          f"lost {len(lost)} → {'PASS' if not changed else 'FAIL'}")
    return 1 if changed else 0


# ═══ E.3 the 8 old/new combinations ═══════════════════════════════════════════
def cmd_combos(a) -> int:
    base_h = load(os.path.join(a.work, "hashes", "old_unset.json"))
    base_n = load(os.path.join(a.work, "names", f"{a.names_label}_old_unset.json"))
    keys = sorted(k for k in base_h if not k.startswith("_"))
    items = queue_lines(sorted(a.lines))
    summary = []
    rc = 0
    for mask in range(8):
        pick = {f: bool(mask >> i & 1) for i, f in enumerate(WORKER_FILES)}
        tag = "c" + "".join("N" if pick[f] else "o" for f in WORKER_FILES)
        tree = os.path.join(a.work, "combos", tag, "sionna")
        if not os.path.isdir(tree):
            shutil.copytree(a.old_root, tree, ignore=shutil.ignore_patterns("__pycache__", "elev_sweep_shards"))
            for f in NEW_MODULES:
                shutil.copy2(os.path.join(a.new_root, f), os.path.join(tree, f))
            for f, new in pick.items():
                shutil.copy2(os.path.join(a.new_root if new else a.old_root, f), os.path.join(tree, f))
        hout = os.path.join(a.work, "combos", tag, "hashes_unset.json")
        nout = os.path.join(a.work, "combos", tag, "names_unset.json")

        def do_hash():
            if os.path.exists(hout) and not a.redo:
                return 0
            with open(hout + ".log", "w") as fh:
                return subprocess.run([PY, os.path.abspath(__file__), "hash-worker", "--root", tree, "--keys",
                                       ",".join(keys), "--out", hout], env=child_env("unset"), cwd=tree,
                                      stdout=fh, stderr=subprocess.STDOUT).returncode

        def do_names():
            if os.path.exists(nout) and not a.redo:
                return 0
            got = [dict(it, **dry_one(tree, it["line"], "unset")) for it in items]
            dump(dict(root=tree, rows=got), nout)
            return 0
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            fh_, fn_ = ex.submit(do_hash), ex.submit(do_names)
            hrc, nrc = fh_.result(), fn_.result()
        H = load(hout) if os.path.exists(hout) else {}
        N = load(nout)["rows"]
        n_eq = n_ne = 0
        for k in keys:
            for item, val in base_h[k].items():
                if item.startswith("_"):
                    continue
                same = H.get(k, {}).get(item) == val
                n_eq += same; n_ne += (not same)
        names_same = sum(1 for o, n in zip(base_n["rows"], N) if o["names"] == n["names"] and n["names"])
        n_bad = sum(1 for n in N if not n["names"] or n["rc"] != 0)
        ok = hrc == 0 and n_ne == 0 and names_same == len(N) == len(base_n["rows"]) and n_bad == 0
        rc |= (not ok)
        row = dict(combo=tag, files={f: ("new" if v else "old") for f, v in pick.items()}, hash_items_equal=n_eq,
                   hash_items_different=n_ne, lines=len(N), names_identical=names_same, bad_lines=n_bad, ok=ok)
        summary.append(row)
        print(f"[E.3] {tag} drones={row['files'][WORKER_FILES[0]]} drone_cad={row['files'][WORKER_FILES[1]]} "
              f"esm={row['files'][WORKER_FILES[2]]}: hash items {n_eq} equal / {n_ne} different; "
              f"names {names_same}/{len(N)} identical, BAD {n_bad} → {'PASS' if ok else 'FAIL'}", flush=True)
    dump(summary, os.path.join(a.work, "combos", "summary.json"))
    print(f"[E.3] {sum(r['ok'] for r in summary)}/8 combinations pass")
    return rc


# ═══ main ═══════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, old=True):
        p.add_argument("--new-root", default=ROOT)
        if old:
            p.add_argument("--old-root", default=None)
        p.add_argument("--work", required=True, help="scratch folder for results")
        p.add_argument("--jobs", type=int, default=2)
        p.add_argument("--redo", action="store_true")

    p = sub.add_parser("hash-worker"); p.add_argument("--root"); p.add_argument("--keys"); p.add_argument("--out")
    p = sub.add_parser("hashes"); common(p)
    p.add_argument("--states", default=",".join(STATES)); p.add_argument("--keys", default="")
    p = sub.add_parser("names"); common(p)
    p.add_argument("--lines", nargs="+", required=True); p.add_argument("--states", default="unset")
    p.add_argument("--label", required=True); p.add_argument("--unique", action="store_true")
    p = sub.add_parser("namespace-worker"); p.add_argument("--root"); p.add_argument("--lines-json"); p.add_argument("--out")
    p = sub.add_parser("namespaces"); common(p); p.add_argument("--lines", nargs="+", required=True)
    p = sub.add_parser("abbrev"); p.add_argument("--live-root", default=ROOT)
    p = sub.add_parser("controls-worker")
    for o in ("--root", "--out", "--line", "--ours-line", "--shd-src", "--work"):
        p.add_argument(o)
    p = sub.add_parser("controls"); common(p)
    p.add_argument("--line", required=True, help="a revision-0 queue line (PathSolver engine)")
    p.add_argument("--ours-line", required=True, help="a small ours-engine line")
    p.add_argument("--shd-src", required=True, help="shard folder to copy one small cell from (read only)")
    p = sub.add_parser("union-parity-worker"); p.add_argument("--root"); p.add_argument("--out")
    p = sub.add_parser("union-parity"); common(p)
    p = sub.add_parser("grammar-worker")
    for o in ("--root", "--shard-list", "--ledger", "--out"):
        p.add_argument(o)
    p = sub.add_parser("grammar"); common(p)
    p.add_argument("--shd", required=True); p.add_argument("--ledger", required=True)
    p = sub.add_parser("merge-worker")
    for o in ("--root", "--shd", "--out-json", "--out-npz"):
        p.add_argument(o)
    p = sub.add_parser("merge"); common(p)
    p.add_argument("--shd", required=True); p.add_argument("--label", required=True)
    p.add_argument("--subset", type=int, default=0)
    p = sub.add_parser("existing"); common(p)
    p.add_argument("--inputs", required=True); p.add_argument("--only", default="")
    p = sub.add_parser("citations"); common(p)
    p.add_argument("--inputs", required=True); p.add_argument("--shd", required=True)
    p.add_argument("--live-root", default=ROOT)
    p = sub.add_parser("quotes"); common(p); p.add_argument("--live-root", default=ROOT)
    p = sub.add_parser("combos"); common(p)
    p.add_argument("--lines", nargs="+", required=True); p.add_argument("--names-label", required=True)

    a = ap.parse_args()
    if a.cmd == "hash-worker":
        hash_worker(a.root, a.keys.split(","), a.out); return 0
    if a.cmd == "namespace-worker":
        namespace_worker(a.root, a.lines_json, a.out); return 0
    if a.cmd == "controls-worker":
        controls_worker(a.root, a.out, a.line, a.ours_line, a.shd_src, a.work); return 0
    if a.cmd == "union-parity-worker":
        union_parity_worker(a.root, a.out); return 0
    if a.cmd == "grammar-worker":
        grammar_worker(a.root, a.shard_list, a.ledger, a.out); return 0
    if a.cmd == "merge-worker":
        merge_worker(a.root, a.shd, a.out_json, a.out_npz); return 0
    for need in ("old_root",):
        if a.cmd in ("names", "namespaces", "grammar", "merge", "existing", "citations", "quotes", "combos") \
                and not getattr(a, need, None):
            ap.error(f"{a.cmd} needs --old-root")
    return {"hashes": cmd_hashes, "names": cmd_names, "namespaces": cmd_namespaces, "abbrev": cmd_abbrev,
            "controls": cmd_controls, "union-parity": cmd_union_parity, "grammar": cmd_grammar,
            "merge": cmd_merge, "existing": cmd_existing, "citations": cmd_citations, "quotes": cmd_quotes,
            "combos": cmd_combos}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
