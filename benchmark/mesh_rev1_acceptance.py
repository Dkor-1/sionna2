# -*- coding: utf-8 -*-
"""mesh_rev1_acceptance.py — plan C acceptance for one (drone key, mesh revision).

    python benchmark/mesh_rev1_acceptance.py --drone <key> [--rev 1] [--out <ledger.json>] ...

Exit code 0 when every **gate** row passes, 1 otherwise. Report rows never change the exit code.

Why this file is a dispatcher (merge, 2026-09-18)
------------------------------------------------
Four units each delivered a file called `benchmark/mesh_rev1_acceptance.py`, and they are not
four versions of one script — they are three independent implementations that happen to share a
name, because each aircraft is scored against a different kind of reference:

    matrice4e   the M4T STEP CAD: true plane sections, CAD-to-ours distance percentiles, a
                z-buffer renderer for per-view visibility, facing areas as ratios to CAD values.
                Signatures c1..c13(T, b0, b1, th, cad).
    phantom4    the owned CC-BY scan in the datum frame: scan sample clouds, region-wise distance,
                mesh_topo_check / mesh_buried. Signatures c1..c13(T, gm, thr, ...).
    mini5pro    owned FCC external photos: one `run(key, rev, thr, variant)`.
    mavic4pro   forked from the mini5pro file and generalised to both photo-scored aircraft.

Merging them line by line would have meant rewriting three scoring implementations into one, and
every number in the four accepted tables would then rest on code no unit had run. Instead each
implementation is kept **byte for byte** as `mesh_rev1_acceptance_<impl>.py`, and this file is
the single entry point the plan's C section names. The one exception is the two photo-scored
aircraft, whose two files really were one lineage; they are reconciled into
`mesh_rev1_acceptance_photo.py` (see the merge note in docs/MESH_REV1.md).

Adding a drone: add its key to `_IMPL`. A key that is not listed is refused here rather than
scored by whichever implementation happened to be imported.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
#  MERGE FIX 2026-09-18: two of the three implementations import `drones`, `mesh_check` and the
#  rest straight off sys.path and were run with PYTHONPATH set by hand in their unit's env.sh;
#  the other two configure sys.path themselves. The entry point sets it for all of them, so how
#  the tree is laid out is not something the caller has to know.
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: drone key -> (module, entry point). "argv" takes the remaining argv, "main" re-parses sys.argv.
_IMPL = {
    "matrice4e": ("mesh_rev1_acceptance_matrice4e", "argv"),
    "phantom4":  ("mesh_rev1_acceptance_phantom4", "main"),
    "mini5pro":  ("mesh_rev1_acceptance_photo", "main"),
    "mavic4pro": ("mesh_rev1_acceptance_photo", "main"),
}


def _drone_of(argv) -> str | None:
    for i, a in enumerate(argv):
        if a == "--drone" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--drone="):
            return a.split("=", 1)[1]
    return None


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    key = _drone_of(argv)
    if key is None:
        raise SystemExit(
            "usage: mesh_rev1_acceptance.py --drone <key> [--rev 1] [--out ledger.json]\n"
            f"       keys with a revision-1 acceptance: {', '.join(sorted(_IMPL))}")
    if key not in _IMPL:
        raise SystemExit(
            f"⛔ no revision-1 acceptance is implemented for drone {key!r}. "
            f"Implemented: {', '.join(sorted(_IMPL))}.\n"
            "   Scoring a drone with another drone's implementation would print a full table of "
            "numbers measured against the wrong reference, so this is a refusal, not a fallback.")

    mod_name, how = _IMPL[key]
    mod = __import__(mod_name)
    print(f"[mesh_rev1_acceptance] {key} -> {mod_name}.py", flush=True)
    #  ⚠ The implementations report failure differently: the matrice4e one RETURNS 1 and relies on
    #  its own `sys.exit(main())`, the other two call `sys.exit()` inside `main`. Dispatching
    #  without propagating the return value made a 7-failure matrice4e run exit 0 — a driver or a
    #  shell `&&` would have read that as a pass. Both shapes end the process here.
    if how == "argv":
        raise SystemExit(mod.main(argv) or 0)
    sys.argv = [f"{mod_name}.py"] + argv
    raise SystemExit(mod.main() or 0)


if __name__ == "__main__":
    main()
