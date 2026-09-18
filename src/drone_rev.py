# -*- coding: utf-8 -*-
"""drone_rev.py — builders for mesh revisions ≥ 1, dispatched by (drone key, revision).

drone_cad reaches this module through two hooks that test `getattr(spec, "mesh_rev", 0)`:
  * `drone_cad.build_frame_cad`     → `build_frame_rev(spec, mesh_fix=…)`
  * `drone_cad.build_propeller_cad` → `build_propeller_rev(spec, n_sec=…, blade_law=…, …)`
Revision-0 specs (`DRONES[key]`, plain `DroneSpec`) never reach this file.

Rules this module enforces for every revision
  1. **Canonical mesh switches only.** A revision is defined on top of the canonical repairs
     (`geom.MESH_FIX_CANON`) and the canonical blade law (`geom.BLADE_LAW_CANON`). Any other
     `MESH_FIX`, `BLADE_LAW` or explicit `mesh_fix`/`blade_law` argument raises ValueError. The
     sweep CLI checks the same thing before it builds anything; this check covers CPU drivers
     and tools that call `drones.spec_for` directly (plan M3).
  2. **Revision 0's union semantics.** The per-revision frame builder only places parts (with
     `cadkit.Assembly.add`, which applies the i5 degenerate-face collapse under the canonical
     switches exactly as for revision 0). `finish_frame_assembly` then does what the end of
     `build_frame_cad` does: boolean union inside each group of `UNION_GROUPS_REV0`, plus
     'battery' when the battery repair is on, and it refuses a battery group that stayed in
     more than one piece or a body that is not closed. The union-parity item of
     `benchmark/regress_mesh_rev0_bitidentical_0917.py` replays revision 0's own pre-union parts
     through this function and requires the same bytes for all drones.
  3. **No new material groups.** Every group must be a key of `drones.DRONE_GROUP_MAT`.

Revision builders may import private helpers from drone_cad but never edit them. To reuse a
revision-0 builder for an unchanged part, call it with `base_spec(spec)` — a plain DroneSpec with
the same field values — so the hooks above are not re-entered.
"""
from __future__ import annotations

#: The group list at the end of `drone_cad.build_frame_cad` (revision 0), in the same order.
#  The regression script compares this tuple with the source of build_frame_cad.
UNION_GROUPS_REV0 = ("body", "arm", "motor", "camera", "gear", "canopy", "accent",
                     "deck", "gear_cf", "fc")


def _rev_of(spec) -> int:
    rev = getattr(spec, "mesh_rev", 0)
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
        raise ValueError(f"drone_rev: spec {getattr(spec, 'key', '?')!r} has mesh_rev={rev!r}; "
                         f"revision builders are for mesh_rev >= 1")
    return rev


def require_canonical(where: str, mesh_fix=None, blade_law=None) -> None:
    """Raise ValueError unless the mesh switches are the canonical ones (rule 1)."""
    from geom import mesh_fix_set, MESH_FIX_CANON, blade_law_canon, BLADE_LAW_CANON
    got = sorted(mesh_fix_set())
    if got != sorted(MESH_FIX_CANON):
        raise ValueError(f"{where}: mesh revisions are built only with the canonical repairs "
                         f"{sorted(MESH_FIX_CANON)}; MESH_FIX gives {got}")
    if blade_law_canon() != BLADE_LAW_CANON:
        raise ValueError(f"{where}: mesh revisions are built only with blade law "
                         f"{BLADE_LAW_CANON!r}; BLADE_LAW gives {blade_law_canon()!r}")
    if mesh_fix is not None:
        from drone_cad import normalize_mesh_fix
        if normalize_mesh_fix(mesh_fix) != normalize_mesh_fix(None):
            raise ValueError(f"{where}: mesh_fix={mesh_fix!r} differs from the canonical repairs")
    if blade_law is not None and str(blade_law).strip().lower() != BLADE_LAW_CANON:
        raise ValueError(f"{where}: blade_law={blade_law!r} differs from {BLADE_LAW_CANON!r}")


def base_spec(spec):
    """A plain `drones.DroneSpec` with the same values for every DroneSpec field (the
    revision-only fields are dropped). Revision-0 builders called with it do not re-enter the
    drone_cad hooks."""
    from drones import DroneSpec, _SPEC_FIELDS
    return DroneSpec(**{f: getattr(spec, f) for f in _SPEC_FIELDS})


def finish_frame_assembly(A, spec):
    """Apply revision 0's end-of-`build_frame_cad` union semantics to an Assembly (rule 2)."""
    from cadkit import Assembly
    from drone_cad import normalize_mesh_fix
    from drones import DRONE_GROUP_MAT
    if not isinstance(A, Assembly):
        raise TypeError(f"frame builder for {spec.key!r} must return cadkit.Assembly, "
                        f"got {type(A).__name__}")
    unknown = sorted(g for g in A.parts if g not in DRONE_GROUP_MAT)
    if unknown:
        raise ValueError(f"frame builder for {spec.key!r} used unknown groups {unknown} "
                         f"(no new material groups in a revision)")
    fix = normalize_mesh_fix(None)
    groups = list(UNION_GROUPS_REV0)
    if "battery" in fix:
        groups.append("battery")
    for g in groups:
        A.union_group(g)
    if "battery" in fix and len(A.parts.get("battery", ())) > 1:
        raise RuntimeError(
            f"drone_rev.finish_frame_assembly(key={spec.key!r}, rev={getattr(spec, 'mesh_rev', '?')}): "
            f"the 'battery' union failed — {len(A.parts['battery'])} parts are left "
            f"(see cadkit.Assembly.UNION_FAILURES)")
    #  i5: under the canonical switches revision 0 ends with a closed body for every drone that has
    #  one (10/10 keys, benchmark/regress_mesh_rev0_bitidentical_0917.py union-parity). A revision
    #  must keep it closed — an open shell breaks the containment checks i5 exists for.
    body = A.parts.get("body", [])
    if body and not all(bool(m.is_watertight) for m in body):
        raise RuntimeError(
            f"drone_rev.finish_frame_assembly(key={spec.key!r}, rev={getattr(spec, 'mesh_rev', '?')}): "
            f"the body is not closed (watertight parts {sum(bool(m.is_watertight) for m in body)}/{len(body)})")
    #  i4 and m4 are not canonical repairs, and require_canonical has already refused them.
    A.mesh_fix_log = {}
    return A


def build_frame_rev(spec, mesh_fix=None):
    """drone_cad.build_frame_cad for mesh_rev ≥ 1 → cadkit.Assembly (same contract)."""
    import mesh_rev
    rev = _rev_of(spec)
    require_canonical(f"build_frame_rev({spec.key!r}, rev {rev})", mesh_fix=mesh_fix)
    entry = mesh_rev.get_entry(spec.key, rev)
    builder = mesh_rev._resolve(entry.frame_builder)
    return finish_frame_assembly(builder(spec), spec)


def build_propeller_rev(spec, n_sec=22, blade_law=None, pitch_law=None, max_edge_m=None,
                        lambda_m=None, edge_over_lambda: float = 10.0):
    """drone_cad.build_propeller_cad for mesh_rev ≥ 1 → cadkit.Assembly (same contract).

    ⚠ The hook sits after build_propeller_cad has resolved its arguments, so `blade_law`
      arrives resolved (None → canonical) and `max_edge_m` already includes `lambda_m`.
    An entry without `prop_builder` builds revision 0's propeller from `base_spec(spec)`."""
    import mesh_rev
    from drone_cad import build_propeller_cad
    rev = _rev_of(spec)
    require_canonical(f"build_propeller_rev({spec.key!r}, rev {rev})", blade_law=blade_law)
    entry = mesh_rev.get_entry(spec.key, rev)
    kw = dict(n_sec=n_sec, blade_law=blade_law, pitch_law=pitch_law, max_edge_m=max_edge_m,
              lambda_m=lambda_m, edge_over_lambda=edge_over_lambda)
    if not entry.prop_builder:
        return build_propeller_cad(base_spec(spec), **kw)
    return mesh_rev._resolve(entry.prop_builder)(spec, **kw)
