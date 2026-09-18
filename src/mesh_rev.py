# -*- coding: utf-8 -*-
"""mesh_rev.py — the registry of mesh revisions (2026-09-17).

Revision 0 is the mesh that `drones.DRONES` and `drone_cad` build today. It is the frozen
default and is never listed here: `drones.spec_for(key)` returns `DRONES[key]` itself.
Revisions 1, 2, … are added explicitly per (drone key, revision) and are never edited after
release. Any change of geometry after a fingerprint is frozen creates the next revision number.

What this module holds
  * the registry — per (key, rev): spec overrides, the component list with evidence grade and
    sources, the builder functions and the frozen fingerprint (`RevEntry`);
  * `make_spec` — the `drones.DroneSpecRev` object behind `drones.spec_for(key, rev)`;
  * `split_mesh_fix` / `arm_mesh_rev` — read the revision back from an arm name's mfix value
    (`_mfixbatteryi5rev1_blperairframe` → fixes ('battery', 'i5'), revision 1);
  * the gates that `benchmark/elevation_sweep_md.py` calls when `--mesh-rev` is given
    (`run_spec` before FastPoser, `guard_fingerprint` right after it);
  * the merge split that keeps revision arms out of `outputs/elevation_sweep_md.json` and writes
    them to `outputs/elevation_sweep_md_meshrev.json` instead.

When it is loaded
  * A shard worker loads it only when `--mesh-rev` ≥ 1 (elevation_sweep_md.py lines 360, 363, 366).
  * `elevation_sweep_md.py --merge` loads it every time (the merge is not a worker path).
  * Per-drone entries live in `src/mesh_rev_<key>.py` as a module-level list `ENTRIES`. That module
    is imported the first time the key is asked for. When this file was written no such module
    existed, so the registry was empty and `--mesh-rev 1` failed for every key.

Why the revision sits inside the mfix value
  The shard name already carries `_mfix<fix ids>` and the builder skips a shard whose name exists.
  Putting `rev<N>` at the end of that value keeps every revision-0 name unchanged and makes
  revision-N names fail the two literal production-mesh selectors (`_mfixbatteryi5_blperairframe`).
  It does not hide revision shards from readers that glob by solver build or by prefix — those are
  listed in docs/MESH_REV1.md (reader census) and the merge split below handles the main ledger.

⛔ The name is only as good as the geometry behind it. `guard_fingerprint` recomputes the sha256
   of the posed geometry at every launch and stops the run when it differs from the frozen value,
   so a changed builder can never write under an old revision name (the 2026-08-17 mfix accident
   and the solver-build accident were both «same name, different content, skipped as done»).
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import re
from dataclasses import dataclass

#: Evidence grades, strongest first. Only the first two may enter a revision (plan B.0); weaker
#  components exist only as named ablation variants (`rev_drop`) in scratch work.
GRADES = ("high", "medium-high", "medium", "low")
GRADES_ALLOWED_IN_REVISION = ("high", "medium-high")

#: DroneSpec fields a revision may not change (plan B.0: wheelbase, prop diameter, blade count,
#  rotor count, rpm and rotor angles stay as in revision 0).
FORBIDDEN_OVERRIDES = frozenset({
    "key", "diagonal_mm", "prop_dia_mm", "prop_blades", "num_rotors", "coaxial",
    "hover_rpm", "max_rpm", "rotor_deg", "mesh_rev",
})

#: Version string mixed into every fingerprint. Changing how the fingerprint is computed must
#  change this string, which invalidates every frozen value at once instead of silently.
FINGERPRINT_SCHEME = "mesh_rev.fingerprint.v1"


@dataclass(frozen=True)
class Component:
    """One part that a revision adds, removes or reshapes."""
    id: str                     # e.g. "M4E-1"
    change: str                 # one line: what changes
    grade: str                  # one of GRADES
    sources: tuple              # owned sources (file paths, manual pages); at least one
    groups: tuple = ()          # material groups of the parts this component adds (DRONE_GROUP_MAT keys)


@dataclass(frozen=True)
class RevEntry:
    """Registry row for one (drone key, revision)."""
    key: str
    rev: int
    #: (field, value) pairs applied on top of revision 0's DroneSpec values. May also set the
    #  revision-only fields `rotor_dirs` and `rev_drop`. Values must be hashable.
    overrides: tuple = ()
    components: tuple = ()      # of Component
    #: "module:function". Called as fn(spec) and must return a `cadkit.Assembly` whose parts were
    #  added with `Assembly.add`; drone_rev applies revision 0's union semantics afterwards.
    frame_builder: str = ""
    #: "module:function" or "" — "" builds revision 0's propeller from the same spec values.
    prop_builder: str = ""
    #: sha256 from `fingerprint_for(key, rev)` computed with the production venv. None = not
    #  frozen yet: the sweep CLI refuses to run, builders and acceptance tools still work.
    fingerprint: str | None = None
    #: sha256 of docs/mesh_rev1/<key>_acceptance_thresholds.json, committed before the first
    #  acceptance run (plan C, threshold freeze). None = not frozen yet.
    thresholds_sha256: str | None = None
    note: str = ""


# --------------------------------------------------------------------------- #
#  Registry storage
# --------------------------------------------------------------------------- #
_REGISTRY: dict = {}            # (key, rev) -> RevEntry, filled lazily per key
_LOADED_KEYS: set = set()
_TEST_REGISTRY: dict | None = None   # set only inside `registry_for_tests`
_SPEC_CACHE: dict = {}          # (key, rev, id(entry)) -> DroneSpecRev


def _as_rev(rev) -> int:
    import numbers
    if isinstance(rev, bool) or not isinstance(rev, numbers.Integral):
        raise ValueError(f"mesh revision must be an integer, got {rev!r}")
    rev = int(rev)
    if rev < 0:
        raise ValueError(f"mesh revision must be >= 0, got {rev}")
    return rev


def _load_key(key: str) -> None:
    if key in _LOADED_KEYS:
        return
    if not re.fullmatch(r"[a-z0-9]+", str(key)):
        _LOADED_KEYS.add(key)
        return
    modname = f"mesh_rev_{key}"
    try:
        mod = importlib.import_module(modname)
    except ModuleNotFoundError as e:
        if e.name != modname:           # the module exists but one of its imports is missing
            raise
        mod = None
    found = {}
    for entry in (getattr(mod, "ENTRIES", ()) if mod is not None else ()):
        validate_entry(entry)
        if entry.key != key:
            raise ValueError(f"{modname}: entry for key {entry.key!r} does not belong in this file")
        if (entry.key, entry.rev) in found:
            raise ValueError(f"{modname}: revision {entry.rev} is listed twice")
        found[(entry.key, entry.rev)] = entry
    _REGISTRY.update(found)
    _LOADED_KEYS.add(key)


def _table_for(key: str) -> dict:
    if _TEST_REGISTRY is not None:
        return _TEST_REGISTRY
    _load_key(key)
    return _REGISTRY


def is_registered(key: str, rev) -> bool:
    try:
        rev = _as_rev(rev)
    except ValueError:
        return False
    return rev >= 1 and (key, rev) in _table_for(key)


def get_entry(key: str, rev) -> RevEntry:
    rev = _as_rev(rev)
    if rev == 0:
        raise ValueError("revision 0 is DRONES itself and has no registry entry")
    entry = _table_for(key).get((key, rev))
    if entry is None:
        raise ValueError(f"unknown mesh revision (key={key!r}, rev={rev}) — "
                         f"registered: {sorted(k for k in _table_for(key) if k[0] == key)}")
    return entry


def registered_pairs() -> list:
    """Every (key, rev) currently registered (loads every key's module)."""
    if _TEST_REGISTRY is not None:
        return sorted(_TEST_REGISTRY)
    from drones import DRONES
    for k in DRONES:
        _load_key(k)
    return sorted(_REGISTRY)


@contextlib.contextmanager
def registry_for_tests(entries):
    """Tests only: use exactly `entries` as the registry inside the block (validated as usual)."""
    global _TEST_REGISTRY
    table = {}
    for e in entries:
        validate_entry(e)
        table[(e.key, e.rev)] = e
    saved = _TEST_REGISTRY
    _TEST_REGISTRY = table
    try:
        yield table
    finally:
        _TEST_REGISTRY = saved


# --------------------------------------------------------------------------- #
#  Validation and spec construction
# --------------------------------------------------------------------------- #
def _resolve(ref: str):
    mod, _, fn = str(ref).partition(":")
    if not mod or not fn:
        raise ValueError(f"builder reference must be 'module:function', got {ref!r}")
    return getattr(importlib.import_module(mod), fn)


def validate_entry(entry: RevEntry) -> None:
    """Structural checks that do not build geometry (acceptance tests do that)."""
    if not isinstance(entry, RevEntry):
        raise TypeError(f"registry rows must be RevEntry, got {type(entry).__name__}")
    rev = _as_rev(entry.rev)
    if rev < 1:
        raise ValueError(f"({entry.key!r}, {entry.rev}): registered revisions start at 1")
    if not entry.frame_builder or ":" not in entry.frame_builder:
        raise ValueError(f"({entry.key!r}, {rev}): frame_builder must be 'module:function'")
    if entry.prop_builder and ":" not in entry.prop_builder:
        raise ValueError(f"({entry.key!r}, {rev}): prop_builder must be 'module:function' or ''")
    names = [k for k, _ in entry.overrides]
    if len(set(names)) != len(names):
        raise ValueError(f"({entry.key!r}, {rev}): a field is overridden twice: {names}")
    bad = sorted(set(names) & FORBIDDEN_OVERRIDES)
    if bad:
        raise ValueError(f"({entry.key!r}, {rev}): revisions may not change {bad} (plan B.0)")
    for k, v in entry.overrides:
        try:
            hash(v)
        except TypeError:
            raise ValueError(f"({entry.key!r}, {rev}): override {k}={v!r} is not hashable — "
                             f"drones._fit_cache_key needs hashable spec values (use tuples)") from None
    for c in entry.components:
        if not isinstance(c, Component):
            raise TypeError(f"({entry.key!r}, {rev}): components must be Component")
        if c.grade not in GRADES_ALLOWED_IN_REVISION:
            raise ValueError(f"({entry.key!r}, {rev}) component {c.id}: grade {c.grade!r} may not "
                             f"enter a revision (allowed {GRADES_ALLOWED_IN_REVISION}; weaker "
                             f"components are ablation variants only)")
        if not c.sources:
            raise ValueError(f"({entry.key!r}, {rev}) component {c.id}: no source")
    for h in (entry.fingerprint, entry.thresholds_sha256):
        if h is not None and not re.fullmatch(r"[0-9a-f]{64}", str(h)):
            raise ValueError(f"({entry.key!r}, {rev}): hashes must be 64 lowercase hex digits")


def make_spec(key: str, rev):
    """The `drones.DroneSpecRev` for (key, rev ≥ 1). Called by `drones.spec_for`.

    Values start from revision 0's DroneSpec, then the entry's overrides apply. The same object
    is returned for repeated calls with the same registry row."""
    rev = _as_rev(rev)
    entry = get_entry(key, rev)
    ck = (key, rev, id(entry))
    hit = _SPEC_CACHE.get(ck)
    if hit is not None and hit[0] is entry:
        return hit[1]
    import drones
    from drones import DRONES, DRONE_GROUP_MAT, _SPEC_FIELDS
    if not hasattr(drones, "DroneSpecRev"):
        raise ValueError("src/drones.py predates mesh revisions (no DroneSpecRev)")
    if key not in DRONES:
        raise ValueError(f"unknown drone key {key!r}")
    base = DRONES[key]
    kw = {f: getattr(base, f) for f in _SPEC_FIELDS}
    extra = {"rotor_dirs", "rev_drop"}
    for k, v in entry.overrides:
        if k not in kw and k not in extra:
            raise ValueError(f"({key!r}, {rev}): {k!r} is not a DroneSpecRev field")
        kw[k] = v
    kw["mesh_rev"] = rev
    spec = drones.DroneSpecRev(**kw)
    #: plan B.0 — no envelope fit in a revision: the frame is used as built.
    if spec.envelope_mm is not None:
        raise ValueError(f"({key!r}, {rev}): envelope_mm must be None in a revision "
                         f"(official and CAD envelopes are acceptance checks, not a fit)")
    if spec.rotor_dirs is not None:
        dirs = tuple(spec.rotor_dirs)
        if len(dirs) != spec.num_rotors or any(d not in (1, -1) or isinstance(d, bool) for d in dirs):
            raise ValueError(f"({key!r}, {rev}): rotor_dirs must be {spec.num_rotors} values of +1/-1")
    for c in entry.components:
        unknown = [g for g in c.groups if g not in DRONE_GROUP_MAT]
        if unknown:
            raise ValueError(f"({key!r}, {rev}) component {c.id}: unknown groups {unknown} "
                             f"(no new material groups in a revision)")
    hash(drones._fit_cache_key(spec))
    _SPEC_CACHE[ck] = (entry, spec)
    return spec


# --------------------------------------------------------------------------- #
#  Arm names
# --------------------------------------------------------------------------- #
_FIX_IDS_EXTRA = ("all",)
_REV_TAIL = re.compile(r"^(?P<body>[a-z0-9]*?)rev(?P<rev>[0-9]+)$")
_MFIX_TOKEN = re.compile(r"(?:^|_)mfix(?P<val>[A-Za-z0-9]+)(?=_|\.|$)")


def split_mesh_fix(value: str) -> tuple:
    """Read an mfix value back: 'batteryi5rev1' → (('battery', 'i5'), 1); 'batteryi5' → (…, 0).

    The fix part must split into ids from `geom.MESH_FIX_KNOWN` plus 'all', in one way only.
    A trailing `rev<N>` needs N ≥ 1 (revision 0 carries no tag). Raises ValueError otherwise."""
    from geom import MESH_FIX_KNOWN
    s = str(value)
    rev = 0
    m = _REV_TAIL.match(s)
    if m:
        rev = int(m.group("rev"))
        if rev < 1 or m.group("rev") != str(rev):
            raise ValueError(f"mfix value {value!r}: revision tag must be rev<N> with N >= 1")
        s = m.group("body")
    ids = tuple(sorted(set(MESH_FIX_KNOWN) | set(_FIX_IDS_EXTRA), key=len, reverse=True))
    ways: list = []

    def walk(i, acc):
        if len(ways) > 1:
            return
        if i == len(s):
            ways.append(tuple(acc))
            return
        for t in ids:
            if s.startswith(t, i):
                walk(i + len(t), acc + [t])

    walk(0, [])
    if not s:
        raise ValueError(f"mfix value {value!r}: no fix ids")
    if not ways:
        raise ValueError(f"mfix value {value!r}: does not split into known fix ids "
                         f"{sorted(set(MESH_FIX_KNOWN) | set(_FIX_IDS_EXTRA))}")
    if len(ways) > 1:
        raise ValueError(f"mfix value {value!r}: splits in more than one way {ways}")
    return ways[0], rev


def arm_mesh_rev(name: str) -> int:
    """Mesh revision of an arm or shard name (0 when no mfix value carries `rev<N>`).

    Only a trailing `rev<N>` inside an `_mfix…` token counts, so every revision-0 name returns 0
    without being parsed. A revision tag whose fix part does not parse still counts as a revision
    (it is kept out of the main ledger) and the error text is printed."""
    rev = 0
    for m in _MFIX_TOKEN.finditer(os.path.basename(str(name))):
        val = m.group("val")
        t = _REV_TAIL.match(val)
        if not t:
            continue
        try:
            rev = max(rev, split_mesh_fix(val)[1])
        except ValueError as e:
            print(f"  ⚠ {os.path.basename(str(name))}: {e} — kept out of the main ledger", flush=True)
            rev = max(rev, int(t.group("rev")) or 1)
    return rev


# --------------------------------------------------------------------------- #
#  Gates for benchmark/elevation_sweep_md.py
# --------------------------------------------------------------------------- #
def run_spec(drone_key: str, rev):
    """`--mesh-rev` ≥ 1: refuse unless the mesh switches are canonical and (key, rev) is
    registered with a frozen fingerprint; then return `drones.spec_for(key, rev)`.

    Called before FastPoser is built. Every refusal is SystemExit with a ⛔ line, which
    `runners/filter_jobs.sh` prints as the BAD reason."""
    try:
        rev = _as_rev(rev)
    except ValueError as e:
        raise SystemExit(f"⛔ --mesh-rev: {e}") from None
    if rev == 0:
        raise SystemExit("⛔ mesh_rev.run_spec is for --mesh-rev >= 1")
    from geom import mesh_fix_set, MESH_FIX_CANON, blade_law_canon, BLADE_LAW_CANON
    got_fix = sorted(mesh_fix_set())
    if got_fix != sorted(MESH_FIX_CANON):
        raise SystemExit(
            f"⛔ --mesh-rev {rev} needs the canonical mesh repairs {sorted(MESH_FIX_CANON)} but "
            f"MESH_FIX gives {got_fix} ({os.environ.get('MESH_FIX')!r}). A revision is built on top "
            f"of the canonical repairs; any other setting would put a revision name on a mesh "
            f"that is not that revision. Unset MESH_FIX.")
    got_law = blade_law_canon()
    if got_law != BLADE_LAW_CANON:
        raise SystemExit(
            f"⛔ --mesh-rev {rev} needs the canonical blade law {BLADE_LAW_CANON!r} but BLADE_LAW "
            f"gives {got_law!r}. Unset BLADE_LAW.")
    if not is_registered(drone_key, rev):
        raise SystemExit(
            f"⛔ mesh revision {rev} is not registered for drone {drone_key!r} — registered pairs: "
            f"{sorted(p for p in _table_for(drone_key) if p[0] == drone_key)}. "
            f"Revisions are added in src/mesh_rev_<key>.py.")
    entry = get_entry(drone_key, rev)
    if entry.fingerprint is None:
        raise SystemExit(
            f"⛔ mesh revision ({drone_key!r}, {rev}) has no frozen fingerprint — its geometry is "
            f"not fixed yet, so no shard may carry its name. Freeze it after acceptance (plan C.14).")
    import drones
    if not hasattr(drones, "spec_for"):
        raise SystemExit("⛔ src/drones.py predates mesh revisions (no spec_for) — "
                         "--mesh-rev cannot run on this tree.")
    try:
        return drones.spec_for(drone_key, rev)
    except ValueError as e:
        raise SystemExit(f"⛔ --mesh-rev {rev}: {e}") from None


def fingerprint_poser(fp) -> str:
    """sha256 over the geometry a shard worker uses: the FastPoser frame vertices, faces and
    groups, each rotor's propeller vertices (so both the mirrored and unmirrored prop), and the
    JSON of `rotor_layout`. Rotor blocks of `fp.v` are zeros until posed, so the value does not
    depend on any pose."""
    import numpy as np
    h = hashlib.sha256()
    h.update(FINGERPRINT_SCHEME.encode() + b"\0")

    def arr(a, dt):
        a = np.ascontiguousarray(np.asarray(a, dt))
        h.update(repr(a.shape).encode())
        h.update(a.tobytes())

    arr(fp.v, np.float64)
    arr(fp.f, np.int64)
    h.update("|".join(map(str, fp.g)).encode())
    for loc in fp._rotor_local:
        arr(np.asarray(loc)[:, :3], np.float64)
    h.update(json.dumps(fp.rl, sort_keys=True).encode())
    return h.hexdigest()


def fingerprint_for(key: str, rev) -> str:
    """The value to freeze in the registry: fingerprint of `FastPoser(spec_for(key, rev))`."""
    from articulated_fast import FastPoser
    from drones import spec_for
    return fingerprint_poser(FastPoser(spec_for(key, rev)))


def guard_fingerprint(fp, drone_key: str, rev) -> str:
    """Right after FastPoser is built, before any name or dry-run exit: stop the run when the
    geometry differs from the frozen fingerprint of (key, rev)."""
    rev = _as_rev(rev)
    want = get_entry(drone_key, rev).fingerprint
    src = fp
    scaled = any(abs(float(getattr(fp, a, 1.0)) - 1.0) > 1e-12
                 for a in ("prop_scale", "frame_scale", "body_scale"))
    if scaled:
        #  The frozen value is for the unscaled mesh; the scale knobs are separate arm tags.
        from articulated_fast import FastPoser
        src = FastPoser(fp.spec)
    got = fingerprint_poser(src)
    if got != want:
        raise SystemExit(
            f"⛔ mesh revision fingerprint mismatch for ({drone_key!r}, rev {rev}): registry "
            f"{str(want)[:16]}… vs built {got[:16]}…. The geometry behind this revision name "
            f"changed. A changed geometry is a new revision number — never reuse a revision.")
    print(f"  mesh revision {rev} ({drone_key}) fingerprint matches {got[:16]}…", flush=True)
    return got


# --------------------------------------------------------------------------- #
#  Merge split for elevation_sweep_md.analyse()
# --------------------------------------------------------------------------- #
def split_merge_paths(paths, rev_pass: bool = False) -> tuple:
    """(paths for this merge pass, paths left for the other pass).

    The main pass (rev_pass False) keeps revision-0 shards; the revision pass keeps shards whose
    mfix value carries `rev<N>`. The order of `paths` is kept."""
    sel, other = [], []
    for p in paths:
        is_rev = arm_mesh_rev(p) > 0
        (sel if is_rev == bool(rev_pass) else other).append(p)
    return sel, other


def meshrev_ledger_paths(out_json: str, out_npz: str) -> tuple:
    """outputs/elevation_sweep_md.json → outputs/elevation_sweep_md_meshrev.json (same for .npz)."""
    def one(p, ext):
        if not p.endswith(ext):
            raise ValueError(f"ledger path {p!r} does not end with {ext}")
        return p[: -len(ext)] + "_meshrev" + ext
    return one(out_json, ".json"), one(out_npz, ".npz")


def merge_rev_arms(analyse_fn) -> None:
    """Second merge pass over the revision shards only, written to the meshrev ledger.

    `analyse_fn` reads the module globals OUT and OUTN when it writes; they are pointed at the
    meshrev paths for the duration of the pass and restored afterwards. The pass is flagged with
    the function attribute `mesh_rev_pass` (read at elevation_sweep_md.py line 1948), so the
    signature `analyse()` stays as it was."""
    g = analyse_fn.__globals__
    out0, outn0 = g["OUT"], g["OUTN"]
    g["OUT"], g["OUTN"] = meshrev_ledger_paths(out0, outn0)
    print(f"\n═══ mesh-revision arms → {os.path.basename(g['OUT'])} "
          f"(kept out of {os.path.basename(out0)}) ═══", flush=True)
    analyse_fn.mesh_rev_pass = True
    try:
        analyse_fn()
    finally:
        analyse_fn.mesh_rev_pass = False
        g["OUT"], g["OUTN"] = out0, outn0
