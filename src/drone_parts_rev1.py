# -*- coding: utf-8 -*-
"""drone_parts_rev1.py — shared parametric parts for mesh revision 1 (plan item B.1, P1–P8).

Scope
    Pure geometry. Every function here takes numbers and returns closed meshes. Nothing in this
    file reads a drone key, an environment switch, a registry or a file, and nothing reads or
    writes the repository outside this module. The per-drone builders
    (`src/drone_rev1_<key>.py`, plan E.2) hold the dimensions and the sources; this file holds
    only the shapes those dimensions are poured into.

    ⛔ Revision 0 never reaches this file. It is a new module, imported only by revision builders
    that `drone_rev.build_frame_rev` / `build_propeller_rev` dispatch to, i.e. only when a spec
    carries `mesh_rev >= 1`. `benchmark/test_drone_parts_rev1_0917.py::test_p0_not_on_rev0_path`
    checks that no revision-0 module imports it.

Conventions (plan B.1 and B.0)
    units       Every parameter is in **millimetres** and every angle in degrees. Every returned
                mesh is in **metres**, which is what `cadkit`, `geom` and the RF pipeline use.
                `MM` is the one conversion constant.
    group       Every part declares its material group, and the group must be a key of
                `drones.DRONE_GROUP_MAT` — no new groups in a revision. Plastic parts take the
                group the caller names (that drone's revision-0 plastic convention: body, gear,
                canopy or accent). The P3 motor **pod is plastic and never goes in `motor`**,
                which is metal.
    closed      Every part is watertight, 2-manifold, consistently wound and positively oriented
                (outward normals). `check_part` states it for one part; the builders raise rather
                than hand back an open shell.
    facets      Curved surfaces are sized so the chord sagitta is ≤ `SAGITTA_MAX_MM` (2.58 mm =
                λ/20 at 5.8 GHz), with `SAGITTA_TARGET_MM` (1.0 mm) as the target the builders
                actually aim at. Two numbers are carried for every part:
                  * `Part.sagitta_mm`      — the exact deviation of the discretised curve from
                    the analytic curve it was sampled from (rings, dome profiles, revolves).
                    This is what the builders size against.
                  * `mesh_sagitta_mm(mesh)` — `mesh_topo_check.facet_wavelength`'s whole-mesh
                    estimate (width × dihedral / 8), which is the measure the C.6 acceptance
                    check uses. `check_part` reports it too, so the two never drift apart.
                Flat faces are exact and are not subdivided.
    budgets     `FACE_BUDGET` holds the plan's per-part face budgets. A builder raises when it
                would exceed its budget instead of quietly going over.

API
    P1  section_loft_shell(stations, *, group, …)          → Part
    P2  x_blend_shell(pod_stations, arm_axes, arm_sections, *, group, …)  → Part
    P3  motor_can(…)                                        → list[Part]  (pod, can, adapter)
    P4  straight_arm(root_xyz_mm, tip_xyz_mm, …)            → Part
    P5  attached_leg(path_mm, …, host=…)                    → Part
    P6  blade_rev1(…) / propeller_rev1(spec, …) / blade_orientation(…)
    P7  gimbal_block(…)                                     → list[Part]
    P8  contain(box_mm, shell, …)                           → Part
    checks: check_part, mesh_sagitta_mm, segments_for_sagitta, rings_for_sagitta

Changelog
    2026-09-17  first version (E1).
    2026-09-17  adversarial review (E1-R). Seven fixes. Only C-fix 5 and C-fix 7 change what a
                correctly parameterised part looks like:
                  C-fix 1  P4 `straight_arm` collapsed to **zero volume** on a vertical axis
                           (ez = ex, so ey = 0 and the placement is singular), and `check_part`
                           called the collapsed part ok. The up-reference now falls back to +x,
                           and the placement is checked to preserve volume.
                  C-fix 2  P5/P7 `host=` recorded `cut_against_host=True` when `difference`
                           removed nothing, i.e. when the part never reached its host (152 mm
                           and 15 mm away in the review). A cut that removes no volume is now
                           refused, and `host_removed_mm3` / `host_gap_mm` carry the C.2 number.
                  C-fix 3  P2 `x_blend_shell` declared 1 connected component without looking;
                           arms whose roots miss the pod gave 5 closed shells and passed. The
                           count is measured, the detached arms are named, and it is refused.
                  C-fix 4  P8 `contain` moved an explicitly given `center_mm` by up to the full
                           search radius (60 mm measured) without saying so. A given centre is
                           now pinned unless `search_mm` is also passed, and `center_shift_mm`
                           is always recorded.
                  C-fix 5  P7 sized its fillet by arc-length resampling a dense polygon: a sharp
                           rectangle (`corner_r_mm=0`) ran the search to its 512-point ceiling
                           (2,128 faces against a 2,500 budget), and the cap meant to stop a
                           fillet becoming a chamfer realised 0.493 mm of sagitta on the default
                           2 mm fillet, which **is** that chamfer. The ring is now analytic:
                           4 corner arcs at `corner_seg` segments plus 4 exact flanks.
                  C-fix 6  degenerate inputs that used to reach the mesher: zero-height station,
                           non-positive superellipse exponent, negative chamfer, non-positive
                           pod taper, zero-length leg path, non-positive lens or post diameter,
                           negative clearance.
                  C-fix 7  P2 `root_transition_scale` default was (1.35, 1.15), which puts the
                           **widest** transition ring closest to the root — a collar outside the
                           pod and a waist behind it, the opposite of the docstring. The default
                           is now (1.15, 1.35) and a decreasing sequence is refused.
                  C-fix 8  `drone_cad._boolean` drops degenerate faces after the boolean, and on
                           a leg cut to an arm that drop turned manifold's **closed** 306-face
                           result into 303 faces with 7 boundary edges — a failure that is not
                           there. `_boolean` is a revision-0 file and is untouched; the cut and
                           union paths here go through `_boolean_keep_closed`, which keeps it as
                           the primary path and falls back to the raw boolean only when the
                           cleanup is what opened the mesh.
                Also `declare_components=` on P5, P7 (post) and P8: those parts used to declare
                whatever they measured, which made plan C.1's component check true by
                construction.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import trimesh

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #
MM = 1e-3                       #: millimetre → metre. Parameters are mm, meshes are m.

#: λ/20 at 5.8 GHz — the facet rule of plan B.1. λ(5.8 GHz) = 51.69 mm.
SAGITTA_MAX_MM = 2.58
#: What the builders aim at (plan B.1: "with 1.0 mm as the target").
SAGITTA_TARGET_MM = 1.0

#: Face budgets, plan B.1 table. `None` = "unchanged from revision 0".
FACE_BUDGET = {
    "P1_shell": 9000,
    "P2_pod": 4000,
    "P2_arm": 1500,
    "P2_total": 11000,
    "P3_motor": 600,            # pod + can + adapter together, per motor
    "P4_arm": 800,
    "P5_leg": 800,
    "P6_prop": None,            # "= current (≈3,500 per rotor)"
    "P7_gimbal": 2500,
    "P8_box": 12,
}

#: Groups a plastic part of a revision-1 drone may declare (plan B.1: "that drone's revision-0
#  plastic convention"). Checked against `drones.DRONE_GROUP_MAT` as well.
PLASTIC_GROUPS = ("body", "canopy", "gear", "accent")

#: Largest gap a part cut against its host may still leave, plan C.2 ("leg, gimbal post and
#  motor pod gaps ≤ 0.5 mm; no floating parts"). A host cut is meant to give 0.
ATTACH_GAP_MAX_MM = 0.5

#: Segments per 90° corner of a rounded rectangle (P7). The sagitta rule alone is not a shape
#  rule: a 1.0 mm target on a 2 mm fillet leaves **one** segment per corner, i.e. a chamfer, and
#  that is what the C.4 silhouette sees. A fillet is therefore sized by a segment count.
CORNER_MIN_SEGMENTS = 4

#: Floor on the segment count of a revolved or lofted ring. The sagitta rule alone would allow
#  9 segments on a 28 mm motor can (λ/20 is an RF rule, not a shape rule); that reads as a
#  polygon in a render and in the silhouette checks of C.4, so a floor is applied and the
#  caller may raise it.
MIN_RING_SEGMENTS = 20


# --------------------------------------------------------------------------- #
#  Part container
# --------------------------------------------------------------------------- #
@dataclass
class Part:
    """One closed mesh with its declared material group.

    mesh                 trimesh.Trimesh in **metres**.
    group                key of `drones.DRONE_GROUP_MAT` (plan B.1: every part row declares it).
    name                 short name, used in error messages and render file names.
    plan_item            which plan row built it ("P1" … "P8").
    sagitta_mm           exact deviation of the discretised curve from its analytic curve
                         (0.0 for parts that carry no curved surface).
    declared_components  how many connected components this part is meant to have (C.1).
    info                 free-form record the builder wants carried along (dimensions it
                         realised, clipped volume %, …). Never read by this module.
    """
    mesh: trimesh.Trimesh
    group: str
    name: str
    plan_item: str
    sagitta_mm: float = 0.0
    declared_components: int = 1
    info: dict = field(default_factory=dict)

    @property
    def faces(self) -> int:
        return int(len(self.mesh.faces))

    @property
    def bbox_mm(self) -> tuple:
        lo, hi = self.mesh.bounds
        return tuple(round(float(v) / MM, 4) for v in (hi - lo))


# --------------------------------------------------------------------------- #
#  Facet sizing and measurement
# --------------------------------------------------------------------------- #
def segments_for_sagitta(radius_mm: float, sagitta_mm: float = SAGITTA_TARGET_MM,
                         minimum: int = MIN_RING_SEGMENTS) -> int:
    """Number of straight segments a circle of `radius_mm` needs for chord sagitta ≤ `sagitta_mm`.

    A regular n-gon inscribed in a circle of radius r has sagitta s = r·(1 − cos(π/n)), so
    n = ⌈π / arccos(1 − s/r)⌉. Used by every revolved and circular part here (P3, P5 tubes,
    P7 lens). `minimum` is `MIN_RING_SEGMENTS`; pass a larger one for a part that has to look
    round in a render.
    """
    r = float(radius_mm)
    s = float(sagitta_mm)
    if r <= 0 or s <= 0:
        raise ValueError(f"segments_for_sagitta: radius_mm={radius_mm}, sagitta_mm={sagitta_mm}")
    if s >= r:
        return int(minimum)
    n = math.ceil(math.pi / math.acos(1.0 - s / r))
    return int(max(minimum, n))


def rings_for_sagitta(semi_axis_mm: float, sagitta_mm: float = SAGITTA_TARGET_MM,
                      minimum: int = 3) -> int:
    """Number of rings a 90° dome (quarter ellipse) needs for chord sagitta ≤ `sagitta_mm`.

    The dome is swept in equal angle steps Δ = 90°/(k+1) over k rings plus an apex, so the
    worst sagitta is that of the larger semi-axis: s = a·(1 − cos(Δ/2)). Plan B.1 asks for at
    least 3 rings on every domed end, which is the `minimum`.
    """
    a = float(semi_axis_mm)
    s = float(sagitta_mm)
    if a <= 0 or s <= 0:
        raise ValueError(f"rings_for_sagitta: semi_axis_mm={semi_axis_mm}, sagitta_mm={sagitta_mm}")
    if s >= a:
        return int(minimum)
    d_half = math.acos(1.0 - s / a)                     # Δ/2 in radians
    k = math.ceil((math.pi / 2.0) / (2.0 * d_half) - 1.0)
    return int(max(minimum, k))


def _seg_distance(P: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance from every point of P (n,d) to the segment a–b."""
    ab = b - a
    denom = float(ab @ ab)
    if denom <= 0:
        return np.linalg.norm(P - a, axis=1)
    t = np.clip(((P - a) @ ab) / denom, 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab[None, :]), axis=1)


def curve_sagitta_mm(dense: np.ndarray, poly: np.ndarray, closed: bool = True) -> float:
    """Exact max deviation of the polyline `poly` from the analytic curve sampled as `dense`.

    This is the measure the builders here size against: `dense` is the analytic curve evaluated
    finely (thousands of points), `poly` is the polyline actually put in the mesh. Every dense
    point is measured to the nearest polyline segment and the largest distance is returned, in
    the units of the inputs (mm everywhere in this file).

    It is not the same thing as `mesh_sagitta_mm`, which estimates the same quantity from the
    mesh alone (width × dihedral / 8) and so has no analytic curve to compare with; both are
    reported for every part and the tests check both.
    """
    D = np.asarray(dense, float)
    Q = np.asarray(poly, float)
    n = len(Q)
    idx = list(range(n)) + ([0] if closed else [])
    best = np.full(len(D), np.inf)
    for i in range(len(idx) - 1):
        best = np.minimum(best, _seg_distance(D, Q[idx[i]], Q[idx[i + 1]]))
    return float(best.max())


def mesh_sagitta_mm(mesh: trimesh.Trimesh) -> float:
    """Whole-mesh sagitta, `mesh_topo_check.facet_wavelength`'s measure (width × dihedral / 8).

    This is the number the C.6 acceptance check reads, so it is reported next to the exact
    `Part.sagitta_mm` for every part. Edges whose dihedral is over 30° are design corners and
    are excluded there, by that module's rule.
    """
    from mesh_topo_check import facet_wavelength
    V = np.asarray(mesh.vertices, float)
    F = np.asarray(mesh.faces, np.int64)
    return float(facet_wavelength(V, F, lam=0.0516896551724138)["max_sagitta_mm"])


# --------------------------------------------------------------------------- #
#  Small mesh utilities
# --------------------------------------------------------------------------- #
def _arc_resample(dense: np.ndarray, n: int, closed: bool = True,
                  anchors=None) -> np.ndarray:
    """`n` points spaced by arc length along the polyline `dense`, starting at dense[0].

    Sampling by arc length (not by the curve parameter) is what keeps the facet width — and so
    the sagitta — even on a superellipse, whose corners would otherwise be starved.

    `anchors` are indices into `dense` that must appear in the output exactly. Every section
    here anchors its four cardinal points (widest ±y, crown, keel), so the width, the top z and
    the bottom z a caller declares are the width, top z and bottom z the mesh really has —
    otherwise an arc-length sample lands beside the crown and the part comes out tens of
    nanometres short, which is harmless but makes a dimension check read as approximate.
    """
    D = np.asarray(dense, float)
    P = np.vstack([D, D[:1]]) if closed else D
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    total = float(d[-1])
    if anchors is None:
        want = np.linspace(0.0, total, n, endpoint=False) if closed else np.linspace(0.0, total, n)
    else:
        if not closed:
            raise ValueError("_arc_resample: anchors are only defined for a closed ring")
        a, cnt = anchors
        if len(a) != len(cnt) or sum(cnt) != n:
            raise ValueError(f"_arc_resample: {len(a)} anchors and counts {cnt} do not make {n}")
        s = [d[i] for i in a] + [d[a[0]] + total]
        want = np.concatenate([s[i] + (s[i + 1] - s[i]) * np.arange(cnt[i]) / cnt[i]
                               for i in range(len(a))])
    out = np.empty((len(want), P.shape[1]), float)
    for k in range(P.shape[1]):
        out[:, k] = np.interp(want, d, P[:, k])
    return out


def _alloc_anchor_counts(dense: np.ndarray, n: int, anchor_idx) -> tuple:
    """Split `n` ring points between the arcs between `anchor_idx`, in proportion to arc length.

    The **same** split is then used for every section of one loft, so the rings stay aligned and
    the bands do not twist. Computing it per section would put different point counts in the
    same quadrant of neighbouring sections and shear the surface.
    """
    D = np.asarray(dense, float)
    P = np.vstack([D, D[:1]])
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    total = float(d[-1])
    a = sorted({int(i) % len(D) for i in anchor_idx})
    if len(a) > n:
        raise ValueError(f"_alloc_anchor_counts: {len(a)} anchors do not fit in {n} points")
    s = [d[i] for i in a] + [d[a[0]] + total]
    raw = [(s[i + 1] - s[i]) / total * n for i in range(len(a))]
    cnt = [max(1, int(math.floor(r))) for r in raw]
    while sum(cnt) < n:                        # hand out what rounding left over, biggest first
        cnt[int(np.argmax([raw[i] - cnt[i] for i in range(len(cnt))]))] += 1
    while sum(cnt) > n:
        cnt[int(np.argmax([cnt[i] - raw[i] if cnt[i] > 1 else -np.inf
                           for i in range(len(cnt))]))] -= 1
    return tuple(a), tuple(cnt)


def _fit_rings(dense_list, sagitta_mm: float, n_pts: int | None = None,
               n_min: int = MIN_RING_SEGMENTS, n_max: int = 512, anchor_idx=None):
    """Smallest ring point count whose polyline stays within `sagitta_mm` of every analytic
    section in `dense_list`, and the rings at that count.

    Sizing a superellipse ring by `segments_for_sagitta` of its largest half-axis is wrong:
    the flat flanks have a huge radius of curvature and the corners a small one, and it is the
    corners that set the error. So the count is **measured**: the rings are resampled by arc
    length and compared with the analytic curve until the target is met. Passing `n_pts`
    explicitly skips the search and only measures.

    `anchor_idx` are indices into every dense section that must end up as ring vertices (the
    four cardinal points of a shell section). The arc split between them is computed once, on
    the section with the longest perimeter, and reused for all of them, so the rings align.
    """
    ref = max(range(len(dense_list)),
              key=lambda i: float(np.linalg.norm(np.diff(np.vstack(
                  [dense_list[i], dense_list[i][:1]]), axis=0), axis=1).sum()))

    def build(n):
        anc = None if anchor_idx is None else _alloc_anchor_counts(dense_list[ref], n, anchor_idx)
        rings = [_arc_resample(d, n, closed=True, anchors=anc) for d in dense_list]
        sag = max(curve_sagitta_mm(d, r, closed=True) for d, r in zip(dense_list, rings))
        return rings, sag

    if n_pts is not None:
        rings, sag = build(int(n_pts))
        return int(n_pts), rings, sag
    n = int(n_min)
    while True:
        rings, sag = build(n)
        if sag <= float(sagitta_mm) or n >= int(n_max):
            return n, rings, sag
        n = min(int(n_max), max(n + 4, int(round(n * 1.4))))


def _require_sagitta(mesh, curve_sag: float, what: str, hint: str = "") -> float:
    """Raise unless both sagitta measures are within `SAGITTA_MAX_MM`; return the mesh measure.

    The two numbers answer different questions and both have to hold.
      * the analytic-curve one covers the **section rings and the dome profiles**, which this
        module samples from curves it knows;
      * the whole-mesh one also covers the **station-to-station direction**, where there is no
        analytic curve — the stations are the measured data. A whole-mesh sagitta that is far
        larger than the analytic one therefore means the stations are too far apart for the rule,
        and the answer is more measured stations, not a finer ring.
    """
    ms = mesh_sagitta_mm(mesh)
    worst = max(float(curve_sag), ms)
    if worst > SAGITTA_MAX_MM:
        raise ValueError(
            f"{what}: sagitta {worst:.4f} mm is over the {SAGITTA_MAX_MM} mm facet rule "
            f"(section rings and domes {curve_sag:.4f} mm, whole mesh {ms:.4f} mm)."
            + (f" {hint}" if hint else ""))
    return ms


def _boolean_keep_closed(op: str, meshes, what: str) -> trimesh.Trimesh:
    """`drone_cad._boolean`, but never trading watertightness for a tidier face list.

    `_boolean` drops degenerate faces **after** the boolean (`nondegenerate_faces`, then
    `merge_vertices`). Where the boolean produced slivers, dropping them opens the mesh, and the
    caller then reports a failure that is not there: a leg cut to its arm came back from
    manifold **closed** at 306 faces and left `_boolean` at 303 faces with 7 boundary edges
    (adversarial review 2026-09-17, C-fix 8). `_boolean` is a revision-0 file and is not
    touched; this wrapper keeps it as the primary path and falls back to the raw boolean only
    when the cleanup is what opened the mesh, so nothing that already worked changes.
    """
    from drone_cad import _boolean
    r = _boolean(op, meshes, what)
    if r.is_watertight:
        return r
    fn = trimesh.boolean.union if op == "union" else trimesh.boolean.difference
    raw = fn(meshes, engine="manifold")
    if raw is None or len(raw.faces) == 0 or not raw.is_watertight:
        raise RuntimeError(
            f"{what}: the boolean {op} did not close. `_boolean`'s cleaned result has "
            f"{len(r.faces)} faces and is open; the raw result is "
            f"{'missing' if raw is None else ('open at %d faces' % len(raw.faces))}.")
    trimesh.repair.fix_normals(raw)
    if raw.volume < 0:
        raw.invert()
    return raw


def _cut_to_host(part_mesh: trimesh.Trimesh, host_mesh: trimesh.Trimesh, what: str,
                 max_gap_mm: float = ATTACH_GAP_MAX_MM) -> tuple:
    """`difference(part, host)`, **measuring the gap it leaves**, and refusing a floating part.

    Why the guard (adversarial review 2026-09-17, C-fix 2). `difference` of two meshes that do
    not overlap is a no-op: it returns the part unchanged and raises nothing. The callers then
    recorded `cut_against_host=True` and the docstrings promised "gap 0 by construction", while
    a leg 152.599 mm clear of its host and a post 15.000 mm short of it both came back marked
    as cut. Plan C.2 scores exactly that gap, so it is measured here.

    ⚠ The **removed volume is not the test.** The boolean retriangulates even when it removes
    nothing, so a post 15 mm clear of its host still reports 3.31e−4 mm³ of "removed" volume.
    The gap is what C.2 asks for and what is decided on; the removed volume is reported beside
    it because a cut that removed nothing and a cut that removed a sliver read differently.

    Returns (mesh, removed_mm3, gap_mm), with `gap_mm` the smallest distance from the cut part's
    vertices to the host surface — 0 for a part that now ends on the host.
    """
    v0 = float(part_mesh.volume)
    out = _boolean_keep_closed("difference", [part_mesh, host_mesh], what)
    removed = (v0 - float(out.volume)) / MM ** 3
    gap = float(np.asarray(trimesh.proximity.closest_point(
        host_mesh, np.asarray(out.vertices, float))[1], float).min()) / MM
    if gap > float(max_gap_mm):
        raise ValueError(
            f"{what}: after the cut the part's nearest point is still {gap:.3f} mm from the "
            f"host, over the {float(max_gap_mm)} mm of plan C.2 — it does not reach its host and "
            f"is a floating part. `difference` of two meshes that do not overlap returns the "
            f"first one unchanged and raises nothing, so the cut is not evidence of attachment "
            f"(it removed {removed:.6g} mm³, which is boolean retriangulation, not geometry). "
            f"Move the part onto the host, or pass host=None and state the gap from your own "
            f"source.")
    return out, removed, gap


def _tri_from(V, F, name: str) -> trimesh.Trimesh:
    """Build, weld, orient outward and require a closed 2-manifold."""
    m = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, np.int64), process=True)
    m.merge_vertices()
    m.remove_unreferenced_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    if m.is_watertight and m.volume < 0:
        m.invert()
    if not m.is_watertight:
        n_b = int((np.bincount(trimesh.grouping.unique_rows(m.edges_sorted)[1]) == 1).sum())
        raise RuntimeError(f"drone_parts_rev1: {name} is not closed "
                           f"({len(m.faces)} faces, {n_b} boundary edges)")
    if not m.is_winding_consistent:
        raise RuntimeError(f"drone_parts_rev1: {name} has inconsistent winding")
    return m


def _ring_loft(rings: list[np.ndarray], xs: list[float],
               apex_lo=None, apex_hi=None, name: str = "loft") -> trimesh.Trimesh:
    """Loft equal-length rings along x, closing each end with an apex point or a flat fan cap.

    rings    list of (n,2) arrays of (y, z), all the same length and the same start point, so
             the bands do not twist.
    xs       the x of each ring.
    apex_lo / apex_hi
             (y, z) of an apex vertex to close that end with, or None for a flat fan cap.
             An apex is one vertex, as in `cadkit.revolve`: a ring of coincident points would
             pour degenerate triangles into the mesh.
    """
    n = len(rings[0])
    if any(len(r) != n for r in rings):
        raise ValueError(f"_ring_loft({name}): rings have different point counts")
    V, F = [], []
    for x, r in zip(xs, rings):
        V.append(np.c_[np.full(n, float(x)), np.asarray(r, float)])
    V = np.vstack(V)
    for i in range(len(xs) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            F.append([a + k, b + k, b + k2])
            F.append([a + k, b + k2, a + k2])
    for end, apex, sgn in ((0, apex_lo, -1), (len(xs) - 1, apex_hi, +1)):
        base = end * n
        c = len(V)
        if apex is None:                                   # flat fan cap at the ring centroid
            V = np.vstack([V, np.r_[xs[end], np.asarray(rings[end], float).mean(0)][None, :]])
        else:                                              # dome apex, given by the caller
            V = np.vstack([V, np.r_[apex[0], apex[1], apex[2]][None, :]])
        for k in range(n):
            k2 = (k + 1) % n
            F.append([c, base + k, base + k2][::sgn])
    return _tri_from(V, F, name)


def _rounded_rect_ring(w_mm: float, h_mm: float, r_mm: float,
                       sagitta_mm: float = SAGITTA_TARGET_MM,
                       corner_seg: int = CORNER_MIN_SEGMENTS) -> tuple:
    """A rounded-rectangle ring built **analytically**: 4 corner arcs, 4 exact straight flanks.

    Same shape as `cadkit.rounded_rect` (shapely's offset of the inner core rectangle), but the
    vertices are placed where they belong instead of being arc-length-resampled from a dense
    polygon (adversarial review 2026-09-17, C-fix 5). Two things went wrong with the resample:

      * a **sharp** rectangle (`corner_r_mm = 0`) has no curve to converge to, so the sagitta
        search ran all the way to its 512-point ceiling — 2,128 faces on a plain box, against a
        2,500-face budget that also has to hold the lenses;
      * the cap that was meant to keep a fillet from collapsing into a chamfer (a quarter of the
        fillet radius) is itself about one segment per corner: at the default 2 mm fillet it
        realised 0.493 mm of sagitta, which is the chamfer it was there to prevent.

    So the corner is sized by a **segment count** (`corner_seg`, at least 1 and enough for
    `sagitta_mm`) and the flanks are single segments, because they are flat.
    Returns (ring (n,2) in mm, exact sagitta in mm).
    """
    w, h, r = float(w_mm), float(h_mm), float(r_mm)
    a, b = 0.5 * w - r, 0.5 * h - r
    if r <= 1e-9:                                    # a sharp rectangle is exact at 4 points
        return np.array([[+0.5 * w, +0.5 * h], [-0.5 * w, +0.5 * h],
                         [-0.5 * w, -0.5 * h], [+0.5 * w, -0.5 * h]]), 0.0
    k = int(max(1, int(corner_seg)))
    if float(sagitta_mm) < r:                        # also honour the facet target on a big fillet
        k = max(k, int(math.ceil((math.pi / 2.0) / (2.0 * math.acos(1.0 - float(sagitta_mm) / r)))))
    th = np.linspace(0.0, np.pi / 2.0, k + 1)
    arcs = []
    for cxx, cyy, t0 in ((a, b, 0.0), (-a, b, np.pi / 2.0), (-a, -b, np.pi), (a, -b, 1.5 * np.pi)):
        arcs.append(np.c_[cxx + r * np.cos(t0 + th), cyy + r * np.sin(t0 + th)])
    return np.vstack(arcs), float(r * (1.0 - math.cos(0.5 * (np.pi / 2.0) / k)))


def _check_group(group: str, what: str, plastic_only: bool = False) -> str:
    from drones import DRONE_GROUP_MAT
    g = str(group)
    if g not in DRONE_GROUP_MAT:
        raise ValueError(f"{what}: group {g!r} is not a key of drones.DRONE_GROUP_MAT "
                         f"(a revision adds no material groups). Known: {sorted(DRONE_GROUP_MAT)}")
    if plastic_only and g not in PLASTIC_GROUPS:
        raise ValueError(f"{what}: group {g!r} is not a plastic group. This part is plastic and "
                         f"must take that drone's revision-0 plastic convention, one of "
                         f"{list(PLASTIC_GROUPS)}. In particular it must not go in 'motor', "
                         f"which is metal.")
    return g


def _budget(part_faces: int, key: str, what: str, max_faces=None) -> None:
    lim = FACE_BUDGET[key] if max_faces is None else max_faces
    if lim is not None and part_faces > lim:
        raise ValueError(f"{what}: {part_faces} faces is over the {key} budget of {lim}. "
                         f"Raise `sagitta_mm` toward {SAGITTA_MAX_MM} mm, lower `n_pts`, or pass "
                         f"an explicit `max_faces` with a reason.")


def check_part(part: Part, sagitta_max_mm: float = SAGITTA_MAX_MM) -> dict:
    """Topology, orientation, component count and both sagitta numbers for one part (C.1, C.6)."""
    m = part.mesh
    comp = int(len(m.split(only_watertight=False)))
    lo, hi = m.bounds
    out = dict(
        name=part.name, plan_item=part.plan_item, group=part.group,
        faces=int(len(m.faces)), vertices=int(len(m.vertices)),
        watertight=bool(m.is_watertight),
        winding_consistent=bool(m.is_winding_consistent),
        volume_positive=bool(m.volume > 0),
        volume_mm3=round(float(m.volume) / MM ** 3, 3),
        area_mm2=round(float(m.area) / MM ** 2, 3),
        components=comp,
        declared_components=int(part.declared_components),
        components_match=bool(comp == int(part.declared_components)),
        euler_number=int(m.euler_number),
        bbox_mm=[round(float(v) / MM, 4) for v in (hi - lo)],
        curve_sagitta_mm=round(float(part.sagitta_mm), 5),
        mesh_sagitta_mm=round(mesh_sagitta_mm(m), 5),
    )
    out["sagitta_ok"] = bool(max(out["curve_sagitta_mm"], out["mesh_sagitta_mm"]) <= sagitta_max_mm)
    #  ⭐ A part flattened onto a line or a plane is still watertight, still consistently wound,
    #  and `volume > 0` still passes on a volume of 1e-20 m³ — that is how a collapsed P4 arm
    #  came through this function marked ok (adversarial review 2026-09-17, C-fix 1). The bounding
    #  box says it plainly: a solid has three positive extents.
    out["degenerate"] = bool(min(out["bbox_mm"]) <= 0.0 or float(m.volume) <= 0.0)
    out["ok"] = bool(out["watertight"] and out["winding_consistent"] and out["volume_positive"]
                     and out["components_match"] and out["sagitta_ok"]
                     and not out["degenerate"])
    return out


# --------------------------------------------------------------------------- #
#  P1 — section loft shell
# --------------------------------------------------------------------------- #
#: how finely a shell section's analytic curve is evaluated, and the four cardinal points of
#  that sampling (t = 0, π/2, π, 3π/2 = widest +y, crown, widest −y, keel). Anchoring the ring
#  on them is what makes a declared width, top z and bottom z come back out of the mesh exactly.
_SHELL_DENSE = 4000
_SHELL_ANCHORS = (0, _SHELL_DENSE // 4, _SHELL_DENSE // 2, 3 * _SHELL_DENSE // 4)


def _shell_ring_dense(half_w, z_mid, z_top, z_bot, n_up, n_dn, n_dense=_SHELL_DENSE) -> np.ndarray:
    """The analytic section curve: two superellipse halves sharing the widest line at `z_mid`.

    y(t) = half_w · sgn(cos t)·|cos t|^(2/n),  z(t) = z_mid + (z_top−z_mid)·|sin t|^(2/n_up)
    above the widest line and z_mid − (z_mid−z_bot)·|sin t|^(2/n_dn) below it. n = 2 is an
    ellipse and larger n is boxier, the same convention as `cadkit.superellipse`.
    """
    t = np.linspace(0.0, 2.0 * np.pi, int(n_dense), endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    up = st >= 0
    n_pow = np.where(up, float(n_up), float(n_dn))
    y = half_w * np.sign(ct) * np.abs(ct) ** (2.0 / n_pow)
    zz = np.where(up,
                  z_mid + (z_top - z_mid) * np.abs(st) ** (2.0 / float(n_up)),
                  z_mid - (z_mid - z_bot) * np.abs(st) ** (2.0 / float(n_dn)))
    return np.c_[y, zz]


def section_loft_shell(stations, *, group: str, name: str = "shell",
                       n_pts: int | None = None, sagitta_mm: float = SAGITTA_TARGET_MM,
                       cap=("dome", "dome"), dome_len_mm=(None, None), dome_rings=None,
                       max_faces=None) -> Part:
    """**P1** — a lofted shell from measured cross sections.

    stations : sequence of dicts, front to back along +x, each with
                 x        [mm] station position;
                 width    [mm] full width (y), so the half width is width/2;
                 z_top    [mm] top of the section;
                 z_bot    [mm] bottom of the section;
                 n_up     superellipse exponent of the upper half (2 = ellipse, larger = boxier);
                 n_dn     superellipse exponent of the lower half;
                 z_mid    [mm] optional, the height of the widest line. Default (z_top+z_bot)/2.
               At least two stations. Plan B.3/B.4 fill this from CAD or photo sections every
               10 mm; nothing is interpolated between them beyond the straight ruled band, so no
               dimension is invented between two measured stations.
    group    : material group of the shell (plan B.1: declared, and one of DRONE_GROUP_MAT).
    n_pts    : points per section ring. Default: sized from `sagitta_mm` and the largest
               section, floored at MIN_RING_SEGMENTS.
    cap      : ("dome"|"flat", "dome"|"flat") for the −x and +x ends. Plan B.1: ends are domed;
               **a flat cap is allowed only where CAD or photos show a flat face**, so asking
               for one is an explicit act by the caller.
    dome_len_mm : (front, back) dome length along x. Default: half the end section's height.
    dome_rings  : rings per dome. Default: sized from `sagitta_mm`, at least 3 (plan B.1).
    sagitta_mm  : facet target. The hard ceiling is SAGITTA_MAX_MM.

    Returns one closed Part. Serves plan rows M4E-2, M4E-3, M4E-5 (Matrice 4E body),
    M5P-2, M5P-6 (Mini 5 Pro shell) and the pod of P2.
    """
    st = [dict(s) for s in stations]
    if len(st) < 2:
        raise ValueError("section_loft_shell: at least two stations are needed")
    xs0 = [float(s["x"]) for s in st]
    if any(b <= a for a, b in zip(xs0, xs0[1:])):
        raise ValueError(f"section_loft_shell: stations must increase in x, got {xs0}")
    for s in st:
        s.setdefault("z_mid", 0.5 * (float(s["z_top"]) + float(s["z_bot"])))
        if not (float(s["z_bot"]) <= float(s["z_mid"]) <= float(s["z_top"])):
            raise ValueError(f"section_loft_shell: station x={s['x']} has z_mid outside "
                             f"[z_bot, z_top]")
        if float(s["width"]) <= 0:
            raise ValueError(f"section_loft_shell: station x={s['x']} has width {s['width']}")
        #  A station of zero height is a flat ribbon, not a section: the loft then has zero
        #  volume and the first thing to complain is the dome length, which sends the caller
        #  looking in the wrong place (adversarial review 2026-09-17, C-fix 6).
        if float(s["z_top"]) - float(s["z_bot"]) <= 0:
            raise ValueError(f"section_loft_shell: station x={s['x']} has z_top "
                             f"{s['z_top']} not above z_bot {s['z_bot']}")
        for kk in ("n_up", "n_dn"):
            if float(s[kk]) <= 0:
                raise ValueError(f"section_loft_shell: station x={s['x']} has {kk}={s[kk]}; the "
                                 f"superellipse exponent must be positive (2 = ellipse)")

    dense = [_shell_ring_dense(0.5 * float(s["width"]), float(s["z_mid"]), float(s["z_top"]),
                               float(s["z_bot"]), float(s["n_up"]), float(s["n_dn"])) for s in st]
    n_pts, rings, sag = _fit_rings(dense, sagitta_mm, n_pts, anchor_idx=_SHELL_ANCHORS)

    xs = list(xs0)
    rings0 = list(rings)                 # the original stations, before any dome is prepended
    apex_lo = apex_hi = None
    for side, which in ((0, cap[0]), (1, cap[1])):
        if which not in ("dome", "flat"):
            raise ValueError(f"section_loft_shell: cap must be 'dome' or 'flat', got {which!r}")
        if which == "flat":
            continue
        i = 0 if side == 0 else len(st) - 1
        sgn = -1.0 if side == 0 else +1.0
        s = st[i]
        h_half = 0.5 * (float(s["z_top"]) - float(s["z_bot"]))
        w_half = 0.5 * float(s["width"])
        dl = dome_len_mm[side]
        dl = float(h_half if dl is None else dl)
        if dl <= 0:
            raise ValueError(f"section_loft_shell: dome length {dl} at side {side}")
        k = dome_rings if dome_rings is not None else rings_for_sagitta(max(dl, w_half, h_half),
                                                                       sagitta_mm)
        k = int(max(3, k))
        th = (np.pi / 2.0) * np.arange(1, k + 1) / (k + 1.0)
        zc = float(s["z_mid"])
        new_x, new_rings, dome_dense, dome_poly = [], [], [], []
        for a in th:
            sc = float(np.cos(a))
            new_x.append(xs0[i] + sgn * dl * float(np.sin(a)))
            r = rings0[i].copy()
            r[:, 0] *= sc
            r[:, 1] = zc + (r[:, 1] - zc) * sc
            new_rings.append(r)
        # the dome profile itself (x, half width), for the sagitta of the dome direction
        a_dense = np.linspace(0.0, np.pi / 2.0, 2000)
        dome_dense = np.c_[xs0[i] + sgn * dl * np.sin(a_dense), w_half * np.cos(a_dense)]
        a_poly = np.r_[0.0, th, np.pi / 2.0]
        dome_poly = np.c_[xs0[i] + sgn * dl * np.sin(a_poly), w_half * np.cos(a_poly)]
        sag = max(sag, curve_sagitta_mm(dome_dense, dome_poly, closed=False))
        apex = (xs0[i] + sgn * dl, 0.0, zc)
        if side == 0:
            xs = [x for x in reversed(new_x)] + xs
            rings = [r for r in reversed(new_rings)] + rings
            apex_lo = apex
        else:
            xs = xs + new_x
            rings = rings + new_rings
            apex_hi = apex

    m = _ring_loft([r * MM for r in rings], [x * MM for x in xs],
                   apex_lo=None if apex_lo is None else tuple(v * MM for v in apex_lo),
                   apex_hi=None if apex_hi is None else tuple(v * MM for v in apex_hi),
                   name=f"P1 {name}")
    _budget(len(m.faces), "P1_shell", f"section_loft_shell({name!r})", max_faces)
    step = max(b - a for a, b in zip(xs0, xs0[1:]))
    ms = _require_sagitta(
        m, sag, f"section_loft_shell({name!r})",
        hint=(f"The widest station gap is {step:.1f} mm. If the whole-mesh number is the larger "
              f"one, that gap is what sets it: give the measured sections closer together (plan "
              f"B.3/B.4 read CAD or scan sections every 10 mm). Otherwise lower `sagitta_mm` or "
              f"raise `n_pts`/`dome_rings`."))
    return Part(mesh=m, group=_check_group(group, f"section_loft_shell({name!r})"),
                name=name, plan_item="P1", sagitta_mm=sag, declared_components=1,
                info=dict(n_stations=len(st), n_pts=n_pts, cap=list(cap),
                          mesh_sagitta_mm=round(ms, 5),
                          max_station_step_mm=round(step, 4),
                          x_span_mm=[round(xs[0], 4), round(xs[-1], 4)]))


# --------------------------------------------------------------------------- #
#  P2 — X-blend shell (pod + four arm fairings)
# --------------------------------------------------------------------------- #
def x_blend_shell(pod_stations, arm_axes, arm_sections, *, group: str, name: str = "xblend",
                  n_pts: int | None = None, sagitta_mm: float = SAGITTA_TARGET_MM,
                  root_transition_mm: float = 12.0, root_transition_scale=(1.15, 1.35),
                  pod_cap=("dome", "dome"), pod_dome_len_mm=(None, None),
                  max_faces=None) -> Part:
    """**P2** — an X-shaped fairing: one pod loft unioned with four arm fairing lofts.

    pod_stations  : as `section_loft_shell`'s `stations` (the centre pod).
    arm_axes      : one entry per arm, `dict(heading_deg=…, root_mm=(x, y), length_mm=…,
                    z_mm=…)`. `heading_deg` is measured from +x toward +y, `root_mm` is where
                    the arm leaves the pod, `z_mm` is the height of the arm section's widest
                    line at the root.
    arm_sections  : one list per arm (or a single list used for all four), of stations along the
                    arm: `dict(s=…, width=…, z_top=…, z_bot=…, n_up=…, n_dn=…, z_mid=…)` with
                    `s` the distance from the root in mm. The keel depth of plan P2 is simply a
                    `z_bot` that reaches lower than the pod's — it is a dimension, not a switch.
    root_transition_mm / root_transition_scale
                  : the **2 transition sections at each root** of plan P2. Entry j sits inboard
                    of the root at s = −(j+1)·d with d = root_transition_mm/2, scaled by
                    `root_transition_scale[j]`, so the arm grows into the pod and the union is
                    clean. The sequence must start at 1.0 or more and not decrease, or the
                    widest ring lands closest to the root — a collar outside the pod followed by
                    a waist. No smoothing pass is run anywhere here: smoothing moves dimensions.

    Returns one closed Part (pod ∪ arms). Serves plan row P4-2 (Phantom 4 oval pod → X fairing).
    """
    pod = section_loft_shell(pod_stations, group=group, name=f"{name}_pod", n_pts=n_pts,
                             sagitta_mm=sagitta_mm, cap=pod_cap, dome_len_mm=pod_dome_len_mm,
                             max_faces=FACE_BUDGET["P2_pod"])
    axes = list(arm_axes)
    secs = list(arm_sections)
    if len(secs) == 1:
        secs = secs * len(axes)
    if len(secs) != len(axes):
        raise ValueError(f"x_blend_shell: {len(axes)} arm axes but {len(secs)} section lists")
    scales = tuple(float(s) for s in root_transition_scale)
    if scales and (min(scales) < 1.0 or any(b < a for a, b in zip(scales, scales[1:]))):
        raise ValueError(
            f"x_blend_shell({name!r}): root_transition_scale={root_transition_scale} must start at "
            f"1.0 or more and not decrease. Entry j sits at s = −(j+1)·root_transition_mm/2, i.e. "
            f"deeper inside the pod, and the fairing is meant to **grow** into the pod. A "
            f"decreasing sequence puts the widest ring closest to the root, which is a collar "
            f"outside the pod and a waist behind it (adversarial review 2026-09-17, C-fix 7).")
    sag = pod.sagitta_mm
    meshes = [pod.mesh]
    arm_faces = []
    detached = []
    d = float(root_transition_mm) / 2.0
    for i, (ax, sec) in enumerate(zip(axes, secs)):
        rows = [dict(s) for s in sec]
        if not rows or min(float(r["s"]) for r in rows) != 0.0:
            raise ValueError(f"x_blend_shell: arm {i} sections must start at s=0 (the root)")
        rows.sort(key=lambda r: float(r["s"]))
        root = rows[0]
        for j, sc in enumerate(scales):                           # the 2 transition sections
            t = dict(root)
            t["s"] = -float(d) * (j + 1)
            zc = float(root.get("z_mid", 0.5 * (float(root["z_top"]) + float(root["z_bot"]))))
            t["z_mid"] = zc
            t["width"] = float(root["width"]) * float(sc)
            t["z_top"] = zc + (float(root["z_top"]) - zc) * float(sc)
            t["z_bot"] = zc - (zc - float(root["z_bot"])) * float(sc)
            rows.insert(0, t)
        stations = [dict(x=float(r["s"]), width=float(r["width"]), z_top=float(r["z_top"]),
                         z_bot=float(r["z_bot"]), n_up=float(r["n_up"]), n_dn=float(r["n_dn"]),
                         z_mid=float(r.get("z_mid",
                                           0.5 * (float(r["z_top"]) + float(r["z_bot"])))))
                    for r in rows]
        arm = section_loft_shell(stations, group=group, name=f"{name}_arm{i}", n_pts=n_pts,
                                 sagitta_mm=sagitta_mm, cap=("flat", "dome"),
                                 max_faces=FACE_BUDGET["P2_arm"])
        sag = max(sag, arm.sagitta_mm)
        arm_faces.append(len(arm.mesh.faces))
        M = trimesh.transformations.rotation_matrix(
            math.radians(float(ax["heading_deg"])), [0, 0, 1])
        mm_ = arm.mesh.copy().apply_transform(M)
        mm_.apply_translation([float(ax["root_mm"][0]) * MM, float(ax["root_mm"][1]) * MM,
                               float(ax.get("z_mm", 0.0)) * MM])
        meshes.append(mm_)
        if not bool(pod.mesh.contains(np.array(
                [[float(ax["root_mm"][0]) * MM, float(ax["root_mm"][1]) * MM,
                  float(ax.get("z_mm", 0.0)) * MM]]))[0]):
            detached.append(i)
    u = _boolean_keep_closed("union", meshes, f"P2 x_blend_shell({name!r})")
    if not u.is_watertight:
        raise RuntimeError(f"x_blend_shell({name!r}): the union is not closed")
    if u.volume < 0:
        u.invert()
    #  ⭐ The X fairing is one solid. A union of a pod with arms whose roots miss it is still
    #  watertight and still consistently wound — it is simply five separate closed shells, and
    #  the part used to declare 1 component without looking (adversarial review 2026-09-17,
    #  C-fix 3). Plan C.1 counts components per group and C.2 forbids floating parts, so the
    #  count is measured here and a fairing in pieces is refused, naming the arms at fault.
    comp = int(len(u.split(only_watertight=False)))
    if comp != 1:
        raise ValueError(
            f"x_blend_shell({name!r}): the union came out as {comp} separate closed shells, not "
            f"one X fairing. Arm root(s) {detached if detached else '(none)'} are outside the "
            f"pod: `arm_axes[i]['root_mm']`/`z_mm` must lie inside the pod loft, deep enough "
            f"that the transition sections at s = −{d:.1f} and −{2 * d:.1f} mm are buried.")
    _budget(len(u.faces), "P2_total", f"x_blend_shell({name!r})", max_faces)
    #  The boolean retriangulates the blend, so the whole-mesh measure is checked as well as the
    #  analytic one: a seam that the union leaves coarse shows up only there.
    ms = _require_sagitta(u, sag, f"x_blend_shell({name!r})")
    return Part(mesh=u, group=_check_group(group, f"x_blend_shell({name!r})"), name=name,
                plan_item="P2", sagitta_mm=sag, declared_components=1,
                info=dict(pod_faces=int(len(pod.mesh.faces)), arm_faces=arm_faces,
                          mesh_sagitta_mm=round(ms, 5),
                          n_arms=len(axes), transitions_per_root=len(root_transition_scale)))


# --------------------------------------------------------------------------- #
#  P3 — motor can on a plastic pod, plus adapter
# --------------------------------------------------------------------------- #
def _revolve_profile(profile_rz_mm, seg: int, center_mm=(0.0, 0.0, 0.0),
                     name: str = "revolve") -> tuple[trimesh.Trimesh, float]:
    """Revolve an (r, z) profile in mm about +z, returning the mesh (m) and the ring sagitta (mm).

    r = 0 rows become a single apex vertex, as `cadkit.revolve` does, so no degenerate fan
    appears on the axis.
    """
    pr = np.asarray(profile_rz_mm, float)
    a = np.linspace(0.0, 2.0 * np.pi, int(seg), endpoint=False)
    V, F, idx = [], [], []
    for r, z in pr:
        if r <= 1e-9:
            idx.append(("apex", len(V)))
            V.append([0.0, 0.0, z])
        else:
            idx.append(("ring", len(V)))
            for k in range(int(seg)):
                V.append([r * np.cos(a[k]), r * np.sin(a[k]), z])
    for i in range(len(pr) - 1):
        (t0, b0), (t1, b1) = idx[i], idx[i + 1]
        if t0 == "ring" and t1 == "ring":
            for k in range(int(seg)):
                k2 = (k + 1) % int(seg)
                F.append([b0 + k, b1 + k, b1 + k2])
                F.append([b0 + k, b1 + k2, b0 + k2])
        elif t0 == "apex" and t1 == "ring":
            for k in range(int(seg)):
                F.append([b0, b1 + (k + 1) % int(seg), b1 + k])
        elif t0 == "ring" and t1 == "apex":
            for k in range(int(seg)):
                F.append([b1, b0 + k, b0 + (k + 1) % int(seg)])
    for end, sgn in ((0, -1), (len(pr) - 1, +1)):
        t, b = idx[end]
        if t == "ring":
            c = len(V)
            V.append([0.0, 0.0, float(pr[end, 1])])
            for k in range(int(seg)):
                F.append([c, b + k, b + (k + 1) % int(seg)][::sgn])
    V = np.asarray(V, float) * MM + np.asarray(center_mm, float)[None, :] * MM
    m = _tri_from(V, F, name)
    r_big = float(pr[:, 0].max())
    sag = r_big * (1.0 - math.cos(math.pi / float(seg)))
    return m, sag


def motor_can(d_can_mm: float, h_can_mm: float, d_pod_mm: float, h_pod_mm: float,
              adapter_d_mm: float, adapter_h_mm: float, *, pod_group: str,
              center_xy_mm=(0.0, 0.0), base_z_mm: float = 0.0,
              can_group: str = "motor", adapter_group: str = "motor",
              chamfer_mm: float = 0.8, pod_taper: float = 0.92,
              pod_profile_rz_mm=None,
              name: str = "motor", seg: int | None = None,
              sagitta_mm: float = SAGITTA_TARGET_MM, max_faces=None) -> list[Part]:
    """**P3** — a metal can standing on a plastic pod, with a prop adapter on top.

    Replaces revision 0's flat disc `drone_cad._motor_bell`. Three parts are returned, bottom
    to top, and **each declares its own group**:

      pod      Ø `d_pod_mm` × `h_pod_mm`, slightly tapered (`pod_taper` = top/bottom radius),
               or — when `pod_profile_rz_mm` is given — a revolved profile of measured radii.
               It is **plastic and goes into the body**, so `pod_group` is required and must be
               one of `PLASTIC_GROUPS` — plan B.1: "The P3 motor pod never goes in `motor`,
               which is metal."
      can      Ø `d_can_mm` × `h_can_mm` straight wall with a `chamfer_mm` break top and bottom,
               group `can_group` (metal).
      adapter  Ø `adapter_d_mm` × `adapter_h_mm` on top of the can, group `adapter_group`.
               Its top face is the surface a propeller hub seats on, so it is the reference for
               `rotor_z_mm` in plan B.0: rotor_z = target mount z − bell top − standoff.

    base_z_mm is the bottom of the pod; the parts stack upward from there. `center_xy_mm` is the
    rotor centre, which plan C.3 requires to stay at revision 0's realized xy.

    pod_profile_rz_mm
        Optional (r, z) rows for the pod's own meridian, z measured **from the bottom of the
        pod**, i.e. 0 … `h_pod_mm`. Given, they replace the single linear taper and `pod_taper`
        is then only recorded in `info`. Why it exists (adversarial review fix 2026-09-18,
        Phantom 4 R8): a cone is widest at one of its two ends, and a scanned motor pod is a
        **barrel** — the owned Phantom 4 scan reads r50 17.6 mm at the pod's bottom, 19.05 mm in
        the middle and 14.7 mm where it meets the can. Fitting a cone to those three numbers
        misses the middle by 1.8 mm whichever pair of ends it is anchored to, and the Phantom 4
        pod came out 3.6 mm narrower than its source. Rows must have r > 0, z strictly
        increasing, and must start at z = 0 and end at z = `h_pod_mm`; the caps at both ends are
        added here, as for the cone. `d_pod_mm` is then only the nominal diameter used to size
        the ring segment count and to record the part, so pass it as twice the largest r.
        ⚠ Leave it None and the pod is built exactly as before — every existing caller keeps its
        geometry bit for bit.

    Serves plan rows M4E-6 (Matrice 4E motor stack), M5P-3 (Mini 5 Pro motor) and P4-4
    (Phantom 4 disc motors → cans).
    """
    what = f"motor_can({name!r})"
    for label, v in (("d_can_mm", d_can_mm), ("h_can_mm", h_can_mm), ("d_pod_mm", d_pod_mm),
                     ("h_pod_mm", h_pod_mm), ("adapter_d_mm", adapter_d_mm),
                     ("adapter_h_mm", adapter_h_mm)):
        if float(v) <= 0:
            raise ValueError(f"{what}: {label}={v} must be positive")
    ch = float(chamfer_mm)
    if ch < 0:
        raise ValueError(f"{what}: chamfer_mm={chamfer_mm} must be 0 or more; a negative one "
                         f"builds an outward lip around the can, not a break edge")
    if ch >= 0.5 * min(float(h_can_mm), float(d_can_mm)):
        raise ValueError(f"{what}: chamfer_mm={chamfer_mm} is too large for the can")
    if not (0.0 < float(pod_taper)):
        raise ValueError(f"{what}: pod_taper={pod_taper} must be positive (it is the ratio of "
                         f"the pod's top radius to its bottom radius); 0 or less silently makes "
                         f"a cone")
    r_can, r_pod, r_ad = 0.5 * float(d_can_mm), 0.5 * float(d_pod_mm), 0.5 * float(adapter_d_mm)
    seg_pod = int(seg or segments_for_sagitta(r_pod, sagitta_mm))
    seg_can = int(seg or segments_for_sagitta(r_can, sagitta_mm))
    seg_ad = int(seg or segments_for_sagitta(r_ad, sagitta_mm))
    cx, cy = float(center_xy_mm[0]), float(center_xy_mm[1])
    z0 = float(base_z_mm)

    if pod_profile_rz_mm is None:
        pod_rows = [[r_pod, 0.0], [r_pod * float(pod_taper), float(h_pod_mm)]]
    else:
        pod_rows = [[float(r), float(z)] for r, z in pod_profile_rz_mm]
        if len(pod_rows) < 2:
            raise ValueError(f"{what}: pod_profile_rz_mm needs at least 2 (r, z) rows")
        if min(r for r, _ in pod_rows) <= 0.0:
            raise ValueError(f"{what}: pod_profile_rz_mm has a row with r <= 0; the end caps are "
                             f"added here, so give the wall only")
        zs_ = [z for _, z in pod_rows]
        if any(b <= a for a, b in zip(zs_, zs_[1:])):
            raise ValueError(f"{what}: pod_profile_rz_mm must increase in z, got {zs_}")
        if abs(zs_[0]) > 1e-9 or abs(zs_[-1] - float(h_pod_mm)) > 1e-9:
            raise ValueError(f"{what}: pod_profile_rz_mm must run from z=0 to z=h_pod_mm="
                             f"{float(h_pod_mm)}, got {zs_[0]} … {zs_[-1]}")
    pod_m, sag_pod = _revolve_profile(
        [[0.0, 0.0]] + pod_rows + [[0.0, float(h_pod_mm)]],
        seg_pod, center_mm=(cx, cy, z0), name=f"P3 {name} pod")
    z1 = z0 + float(h_pod_mm)
    can_m, sag_can = _revolve_profile(
        [[0.0, 0.0], [r_can - ch, 0.0], [r_can, ch], [r_can, float(h_can_mm) - ch],
         [r_can - ch, float(h_can_mm)], [0.0, float(h_can_mm)]],
        seg_can, center_mm=(cx, cy, z1), name=f"P3 {name} can")
    z2 = z1 + float(h_can_mm)
    ad_m, sag_ad = _revolve_profile(
        [[0.0, 0.0], [r_ad, 0.0], [r_ad, float(adapter_h_mm)], [0.0, float(adapter_h_mm)]],
        seg_ad, center_mm=(cx, cy, z2), name=f"P3 {name} adapter")

    total = len(pod_m.faces) + len(can_m.faces) + len(ad_m.faces)
    _budget(total, "P3_motor", what, max_faces)
    top_z = z2 + float(adapter_h_mm)
    info = dict(pod_top_z_mm=round(z1, 4), can_top_z_mm=round(z2, 4),
                adapter_top_z_mm=round(top_z, 4), center_xy_mm=[cx, cy],
                seg=[seg_pod, seg_can, seg_ad], faces_total=total,
                pod_shape="cone" if pod_profile_rz_mm is None else "profile",
                pod_taper=float(pod_taper) if pod_profile_rz_mm is None else None,
                pod_profile_rz_mm=None if pod_profile_rz_mm is None else
                [[round(r, 4), round(z, 4)] for r, z in pod_rows],
                pod_max_radius_mm=round(max(r for r, _ in pod_rows), 4))
    return [
        Part(pod_m, _check_group(pod_group, f"{what} pod", plastic_only=True),
             f"{name}_pod", "P3", sag_pod, 1, dict(info, role="pod")),
        Part(can_m, _check_group(can_group, f"{what} can"),
             f"{name}_can", "P3", sag_can, 1, dict(info, role="can")),
        Part(ad_m, _check_group(adapter_group, f"{what} adapter"),
             f"{name}_adapter", "P3", sag_ad, 1, dict(info, role="adapter")),
    ]


# --------------------------------------------------------------------------- #
#  P4 — straight arm
# --------------------------------------------------------------------------- #
def straight_arm(root_xyz_mm, tip_xyz_mm, root_section_mm, tip_section_mm, *, group: str,
                 name: str = "arm", n_up: float = 3.0, n_dn: float = 3.0,
                 n_pts: int | None = None, n_sec: int = 6,
                 sagitta_mm: float = SAGITTA_TARGET_MM, max_faces=None) -> Part:
    """**P4** — a straight arm from a root on the body side to the motor, with a tapering section.

    root_xyz_mm / tip_xyz_mm : the arm axis end points, in mm. The arm is straight: it replaces
        revision 0's radial `drone_cad._arm_folding`, which starts at `hub_r` and bends, and it
        is what plan row M4E-4 asks for ("root x +85 ±5, heading 66–68°, bow ≤ 1 mm").
    root_section_mm / tip_section_mm : (width, height) of the section, in mm, in the plane normal
        to the axis. Width is measured horizontally, height vertically (the arm axis may rise).
    n_up / n_dn : superellipse exponents of the section's upper and lower halves.
    n_sec : stations along the arm; the section is interpolated linearly between root and tip,
        so no dimension appears between the two measured ends.

    The heading and the bow follow from the two end points, so the acceptance check of C.3 reads
    them straight off the part: `info["heading_deg"]`, `info["bow_mm"]` (0.0 by construction).

    Serves plan rows M4E-4 (Matrice 4E front arms) and M5P-2 (Mini 5 Pro front arm heading).
    """
    a = np.asarray(root_xyz_mm, float)
    b = np.asarray(tip_xyz_mm, float)
    L = float(np.linalg.norm(b - a))
    if L <= 0:
        raise ValueError(f"straight_arm({name!r}): root and tip coincide")
    if int(n_sec) < 2:
        raise ValueError(f"straight_arm({name!r}): n_sec must be at least 2")
    w0, h0 = float(root_section_mm[0]), float(root_section_mm[1])
    w1, h1 = float(tip_section_mm[0]), float(tip_section_mm[1])
    if min(w0, h0, w1, h1) <= 0:
        raise ValueError(f"straight_arm({name!r}): sections must be positive")
    ts = np.linspace(0.0, 1.0, int(n_sec))
    dense = [_shell_ring_dense(0.5 * (w0 + (w1 - w0) * t), 0.0,
                               +0.5 * (h0 + (h1 - h0) * t), -0.5 * (h0 + (h1 - h0) * t),
                               n_up, n_dn) for t in ts]
    n_pts, rings, sag = _fit_rings(dense, sagitta_mm, n_pts, anchor_idx=_SHELL_ANCHORS)
    m = _ring_loft([r * MM for r in rings], [t * L * MM for t in ts], name=f"P4 {name}")

    #  place: local +x along the axis, local +z as close to world +z as the axis allows.
    #  ⚠ The reference for "up" must not be parallel to the axis. A vertical arm has no
    #  component of world +z left after the projection, and taking +z anyway gives ez = ex,
    #  ey = ez × ex = 0 and a **singular** transform: the arm collapses onto its own axis with
    #  zero volume, watertight and consistently wound, so nothing downstream notices
    #  (adversarial review 2026-09-17, C-fix 1). +x is used as the reference instead, so the
    #  section's local +z points along world +x for an exactly vertical arm.
    ex = (b - a) / L
    ref = np.array([0.0, 0.0, 1.0])
    if abs(float(ex[2])) > 1.0 - 1e-9:
        ref = np.array([1.0, 0.0, 0.0])
    ez = ref - ex * float(ref @ ex)
    nz = float(np.linalg.norm(ez))
    if nz < 1e-9:
        raise ValueError(f"straight_arm({name!r}): cannot build a frame on the axis "
                         f"{tuple(round(float(v), 6) for v in ex)}")
    ez = ez / nz
    ey = np.cross(ez, ex)
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2] = ex, ey, ez
    T[:3, 3] = a * MM
    v_local = float(m.volume)
    m = m.apply_transform(T)
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    #  T is a rigid motion, so it preserves volume exactly up to float error. Checking it is
    #  what turns any future frame bug into a refusal instead of a silently flat arm.
    if v_local <= 0 or abs(float(m.volume) - v_local) > 1e-6 * v_local:
        raise RuntimeError(f"straight_arm({name!r}): placing the arm changed its volume from "
                           f"{v_local / MM ** 3:.6g} to {float(m.volume) / MM ** 3:.6g} mm³ — "
                           f"the placement frame is degenerate.")
    _budget(len(m.faces), "P4_arm", f"straight_arm({name!r})", max_faces)
    ms = _require_sagitta(m, sag, f"straight_arm({name!r})")
    heading = math.degrees(math.atan2(float(b[1] - a[1]), float(b[0] - a[0])))
    return Part(m, _check_group(group, f"straight_arm({name!r})"), name, "P4", sag, 1,
                dict(length_mm=round(L, 4), heading_deg=round(heading, 4), bow_mm=0.0,
                     mesh_sagitta_mm=round(ms, 5),
                     root_mm=[round(float(v), 4) for v in a],
                     tip_mm=[round(float(v), 4) for v in b],
                     root_section_mm=[w0, h0], tip_section_mm=[w1, h1], n_pts=n_pts))


# --------------------------------------------------------------------------- #
#  P5 — attached leg
# --------------------------------------------------------------------------- #
def attached_leg(path_mm, root_section_mm, tip_section_mm, *, group: str, host=None,
                 name: str = "leg", shape: str = "bar", n_up: float = 3.0, n_dn: float = 3.0,
                 n_pts: int | None = None, n_sec: int | None = None,
                 declare_components: int | None = None,
                 sagitta_mm: float = SAGITTA_TARGET_MM, max_faces=None) -> Part:
    """**P5** — a leg swept along a path, then cut against its host so it touches with no gap.

    path_mm  : (N,3) polyline of the leg axis in mm, from the host end to the foot. Three or
               more points make an arch; two make a straight strut.
    root_section_mm / tip_section_mm : (width, height) in mm at the first and last path point.
    shape    : "bar" (a superellipse section, the default) or "tube" (a circular section, i.e.
               n_up = n_dn = 2 and width = height = the given width).
    host     : the mesh the leg hangs from, in **metres** (a `Part.mesh` or a raw trimesh), or
               None. When given, `difference(leg, host)` removes the part of the leg inside the
               host, so the leg meets the host surface exactly: gap 0, which is inside the
               ≤ 0.5 mm of plan C.2, and no buried leg area is left behind. ⚠ The cut is only
               evidence of attachment when it **removed** volume; a leg that misses its host
               comes back unchanged from `difference`, so that case is refused here and
               `info["host_removed_mm3"]` / `info["host_gap_mm"]` carry the measured numbers.
    declare_components
             : how many pieces the caller means this leg to be. Given, the builder refuses any
               other count. Leave it None only for a leg whose piece count is not part of the
               acceptance claim — `Part.declared_components` is otherwise just the measured
               value, which makes plan C.1's component check true by construction.

    The path is swept with parallel transport, the same frame `cadkit.sweep` uses, so the
    section does not spin along a curved path.

    Serves plan rows P4-5 (Phantom 4 legs attached), M5P-4 (Mini 5 Pro one leg per front motor)
    and the Phantom 3 / Mavic 4 Pro legs of plan B.6.
    """
    P = np.asarray(path_mm, float)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 2:
        raise ValueError(f"attached_leg({name!r}): path_mm must be (N,3) with N ≥ 2")
    if shape not in ("bar", "tube"):
        raise ValueError(f"attached_leg({name!r}): shape must be 'bar' or 'tube'")
    w0, h0 = float(root_section_mm[0]), float(root_section_mm[1])
    w1, h1 = float(tip_section_mm[0]), float(tip_section_mm[1])
    if shape == "tube":
        h0, h1, n_up, n_dn = w0, w1, 2.0, 2.0
    if min(w0, h0, w1, h1) <= 0:
        raise ValueError(f"attached_leg({name!r}): sections must be positive")
    #  size the ring on the two end sections (the worst of the two sets the count)
    _end_dense = [_shell_ring_dense(0.5 * w0, 0.0, 0.5 * h0, -0.5 * h0, n_up, n_dn),
                  _shell_ring_dense(0.5 * w1, 0.0, 0.5 * h1, -0.5 * h1, n_up, n_dn)]
    n_pts, _, _ = _fit_rings(_end_dense, sagitta_mm, n_pts, anchor_idx=_SHELL_ANCHORS)
    _leg_anchors = _alloc_anchor_counts(_end_dense[0], n_pts, _SHELL_ANCHORS)

    #  resample the path so the bands are even, then parallel-transport a frame along it
    seglen = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if float(seglen[-1]) <= 0.0:
        raise ValueError(f"attached_leg({name!r}): the path has zero length — all "
                         f"{len(P)} points coincide")
    n_sec = int(n_sec or 2 * len(P))
    want = np.linspace(0.0, float(seglen[-1]), n_sec)
    Q = np.c_[tuple(np.interp(want, seglen, P[:, k]) for k in range(3))]
    T = np.gradient(Q, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    up = np.array([0.0, 0.0, 1.0])
    N = np.cross(up, T[0])
    if np.linalg.norm(N) < 1e-9:
        N = np.cross(np.array([1.0, 0.0, 0.0]), T[0])
    N /= np.linalg.norm(N) + 1e-12
    V, F, sag = [], [], 0.0
    for i in range(len(Q)):
        if i > 0:
            v = np.cross(T[i - 1], T[i])
            s = float(np.linalg.norm(v))
            if s > 1e-9:
                ax = v / s
                ang = math.atan2(s, float(np.dot(T[i - 1], T[i])))
                R = trimesh.transformations.rotation_matrix(ang, ax)[:3, :3]
                N = R @ N
            N -= float(np.dot(N, T[i])) * T[i]
            N /= np.linalg.norm(N) + 1e-12
        B = np.cross(T[i], N)
        t = i / max(1, len(Q) - 1)
        w, h = w0 + (w1 - w0) * t, h0 + (h1 - h0) * t
        dense = _shell_ring_dense(0.5 * w, 0.0, 0.5 * h, -0.5 * h, n_up, n_dn)
        ring = _arc_resample(dense, n_pts, closed=True, anchors=_leg_anchors)
        sag = max(sag, curve_sagitta_mm(dense, ring, closed=True))
        V.append(Q[i][None, :] * MM + ring[:, 0:1] * MM * N[None, :]
                 + ring[:, 1:2] * MM * B[None, :])
    V = np.vstack(V)
    for i in range(len(Q) - 1):
        a, b = i * n_pts, (i + 1) * n_pts
        for k in range(n_pts):
            k2 = (k + 1) % n_pts
            F.append([a + k, b + k, b + k2])
            F.append([a + k, b + k2, a + k2])
    for end, sgn in ((0, -1), (len(Q) - 1, +1)):
        base = end * n_pts
        c = len(V)
        V = np.vstack([V, V[base:base + n_pts].mean(0)[None, :]])
        for k in range(n_pts):
            F.append([c, base + k, base + (k + 1) % n_pts][::sgn])
    m = _tri_from(V, F, f"P5 {name}")

    cut, removed, gap = False, None, None
    if host is not None:
        hm = host.mesh if isinstance(host, Part) else host
        m, removed, gap = _cut_to_host(m, hm, f"attached_leg({name!r}) vs host")
        cut = True
        if not m.is_watertight:
            raise RuntimeError(f"attached_leg({name!r}): the leg is not closed after the host cut")
    _budget(len(m.faces), "P5_leg", f"attached_leg({name!r})", max_faces)
    ms = _require_sagitta(m, sag, f"attached_leg({name!r})")
    comp = int(len(m.split(only_watertight=False)))
    if declare_components is not None and comp != int(declare_components):
        raise ValueError(f"attached_leg({name!r}): the leg is {comp} piece(s), not the "
                         f"{int(declare_components)} the caller declared. A leg that pierces its "
                         f"host comes back in two pieces; declare what you meant (plan C.1).")
    return Part(m, _check_group(group, f"attached_leg({name!r})"), name, "P5", sag, comp,
                dict(shape=shape, n_pts=n_pts, n_sec=int(n_sec), cut_against_host=cut,
                     host_removed_mm3=None if removed is None else round(removed, 6),
                     host_gap_mm=None if gap is None else round(gap, 6),
                     components_declared_by_caller=declare_components is not None,
                     mesh_sagitta_mm=round(ms, 5),
                     path_len_mm=round(float(seglen[-1]), 4),
                     root_section_mm=[w0, h0], tip_section_mm=[w1, h1]))


# --------------------------------------------------------------------------- #
#  P6 — blade orientation against each rotor's own rotation
# --------------------------------------------------------------------------- #
#  Why this exists (plan B.1 P6, and sourcing note S2)
#    Revision 0 builds one blade section with `drone_cad._airfoil`, whose leading edge — the
#    thick, rounded one — sits at chord coordinate −0.30·c, i.e. on −y, and then pitches the
#    section by +θ about the span axis. That puts the thick edge **low**, and the thin trailing
#    edge **high and on +y**. `drones.rotor_layout` gives dir=+1 to the unmirrored propeller and
#    `pose_articulated` spins it about +z, so a blade lying on +x moves toward +y. Revision 0
#    therefore meets the air with its thin, raised edge: the blade flies backwards.
#
#    What a real blade does, measured on the one owned reference that has whole rotors in place:
#    `assets/meshes/reference/WM161_zhankai_1k.glb` (DJI's own Mini 2 model, 4 rotors × 2 blades).
#    Each of the 8 blades was measured on its own geometry — no file name and no label was read,
#    because plan S2 records that `solo_prop_ccw.stl` and `1345_prop_cw.stl` disagree about which
#    label goes with which shape. Result at 0.7 span (producer:
#    scratch .../impl/e1/work/ref_mini2_blades.py, ledger ref_mini2_blades.json):
#        thick edge is the raised edge   8 / 8 blades
#        chord 13.18–13.20 mm, pitch of the chord line 10.5–17.9° against the rotor plane
#        implied rotations 4 CCW / 4 CW, and the two blades of each rotor always agree
#    So: **the thick rounded edge is the leading edge; it is raised, and it faces the motion.**
#    Both cues are the same statement, because a blade that leads with a raised thick edge is a
#    blade at a positive angle of attack, which is what pushes air down.
#
#  What P6 changes, and what it leaves alone
#    * the chord coordinate of the section is mirrored, so the thick rounded edge lands on the
#      side the blade moves toward, and the same +θ pitch then raises it;
#    * the planform sweep is mirrored with it, so the tip still sweeps **aft** (away from the
#      motion) rather than forward;
#    * chord law, blade-angle law, radius, root fraction, thickness taper, camber and hub are
#      untouched — plan P6: "Chord law, blade-angle law, radius and hub stay the same."
#    The section is mirrored about its own thickness axis, so its thickness and camber
#    distributions as functions of distance-from-the-leading-edge are unchanged: it is the same
#    aerofoil, pointed the other way.
def _check_spin(spin, where: str) -> int:
    """`spin` is a rotor's rotation, +1 counter-clockwise seen from +z or −1 clockwise — the
    same value `drones.rotor_layout` puts in `dir`. It is required to be a real int: `True` and
    `"+1"` both survive `int()` and would silently mean +1."""
    if isinstance(spin, bool) or not isinstance(spin, (int, np.integer)) or int(spin) not in (1, -1):
        raise ValueError(f"{where}: spin must be the int +1 (counter-clockwise seen from +z) "
                         f"or -1 (clockwise), got {spin!r}")
    return int(spin)


def blade_rev1(R_mm: float, *, spin: int = +1, root_frac: float = 0.070,
               chord_max_over_r: float = 0.25, pitch_mm: float | None = None,
               pitch_deg: float = 20.0, twist_deg: float = 13.0, sweep_frac: float = 0.10,
               n_sec: int = 22, n_pts: int = 36, law: str = "legacy", pitch_law=None,
               tip_refine=None, chord_rr=None, chord_frac=None) -> trimesh.Trimesh:
    """**P6** — one blade, span along +x, oriented for a rotor turning `spin` about +z.

    spin  : +1 for a rotor turning counter-clockwise seen from +z (which is what
            `drones.rotor_layout` calls dir=+1 and what `drones.build_propeller(mirror=False)`
            is used for), −1 for clockwise. The −1 blade is the exact y-mirror of the +1 blade,
            which is what a real opposite-hand propeller is, and is the same operation
            `drones._mirror_y` applies to the whole propeller.
    R_mm  : blade radius (half the swept-disc diameter), in mm.
    Everything else is passed through to `drone_cad._blade`'s laws unchanged; `pitch_mm` is the
    geometric pitch in mm (revision 0 passes `prop_pitch_in · 25.4`).

    The blade comes back in **metres**, hub at the origin, span +x, and satisfies both cues of
    P6 for its `spin`: thick rounded edge raised, and facing the motion. `blade_orientation`
    measures it.
    """
    from shapely import affinity as aff
    from shapely.geometry import Polygon
    from drone_cad import BLADE_LAWS, PITCH_LAWS, _airfoil, TC_ROOT, TC_TIP
    from cadkit import loft

    _check_spin(spin, "blade_rev1")
    R = float(R_mm) * MM
    lw = BLADE_LAWS[law]
    pw = PITCH_LAWS[pitch_law or lw["pitch_default"]]
    n_ref = int(lw["tip_refine"] if tip_refine is None else tip_refine)
    c_rr = lw["chord_rr"] if chord_rr is None else tuple(chord_rr)
    c_fr = lw["chord_frac"] if chord_frac is None else tuple(chord_frac)

    r0 = float(root_frac) * R
    xs = np.linspace(r0, R, int(n_sec))
    if n_ref > 1:
        step = xs[-1] - xs[-2]
        extra = xs[-2] + step * np.arange(1, n_ref) / n_ref
        xs = np.concatenate([xs[:-1], extra, xs[-1:]])
    tt = (xs - r0) / (R - r0)
    rr = xs / R
    c = np.interp(rr, c_rr, c_fr) * float(chord_max_over_r) * R
    if pitch_mm is not None:
        k = np.interp(rr, pw["rr"], pw["k"])
        th = np.arctan(k * (float(pitch_mm) * MM) / (2.0 * np.pi * xs))
    else:
        th = np.radians(float(pitch_deg) - float(twist_deg) * tt)
    yc = float(sweep_frac) * R * np.sin(np.pi / 2.0 * tt)

    rings = []
    for x, ci, ti, yi, rri in zip(xs, c, th, yc, rr):
        f = np.clip((rri - float(root_frac)) / max(1e-9, 1.0 - float(root_frac)), 0.0, 1.0)
        p = _airfoil(max(ci, 1e-4), thick_ratio=TC_TIP + (TC_ROOT - TC_TIP) * (1 - f))
        #  ⭐ P6, cue 1: mirror the chord coordinate so the thick rounded edge leads. The same
        #     +θ pitch below then raises it, which is the second cue.
        p = Polygon(np.c_[-np.asarray(p.exterior.coords)[:-1, 0],
                          np.asarray(p.exterior.coords)[:-1, 1]])
        p = aff.rotate(p, np.degrees(ti), origin=(0, 0), use_radians=False)
        #  ⭐ P6, cue 2: the tip sweeps aft, which after the mirror is −y, not +y.
        p = aff.translate(p, -yi, 0.0)
        rings.append((float(x), p))
    m = loft(rings, n_pts=int(n_pts), cap=True)
    m.merge_vertices()
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    if m.is_watertight and m.volume < 0:
        m.invert()
    if int(spin) < 0:
        V = np.asarray(m.vertices, float).copy()
        V[:, 1] *= -1.0
        F = np.asarray(m.faces, np.int64)[:, [0, 2, 1]]        # a reflection flips the winding
        m = trimesh.Trimesh(vertices=V, faces=F, process=False)
        trimesh.repair.fix_normals(m)
        if m.is_watertight and m.volume < 0:
            m.invert()
    return m


def propeller_rev1(spec, n_sec: int = 22, blade_law=None, pitch_law=None, max_edge_m=None,
                   lambda_m=None, edge_over_lambda: float = 10.0):
    """**P6** — the revision-1 propeller, with `drone_cad.build_propeller_cad`'s exact contract.

    This is what a registry entry's `prop_builder` points at: `drone_rev.build_propeller_rev`
    calls it with the arguments already resolved (`blade_law` is the canonical law, `max_edge_m`
    already folds in `lambda_m`). It returns a `cadkit.Assembly` with one 'prop' group.

    It is the **dir=+1 (counter-clockwise)** propeller, because that is what
    `drones.build_propeller` mirrors for the clockwise rotors. Everything except the two
    orientation cues is revision 0's propeller: the same hub, the same chord and pitch laws for
    that airframe, the same root overlap into the hub, and the same swept-disc normalisation
    that makes the realized tip radius equal `prop_dia_mm/2`.
    """
    from cadkit import Assembly, rot_z
    from drone_cad import (_prop_hub, refine_to_max_edge, resolve_chord_max_over_r,
                           resolve_chord_profile)
    from geom import blade_law_canon as _blc

    R_mm = float(spec.prop_dia_mm) / 2.0
    P_mm = float(spec.prop_pitch_in or 5.0) * 25.4
    hub_r = R_mm * 0.085 * MM
    blade_law = blade_law or _blc()
    chord_max, chord_max_src = resolve_chord_max_over_r(spec, blade_law)
    c_rr, c_fr, profile_src = resolve_chord_profile(spec, blade_law)
    if max_edge_m is None and lambda_m is not None:
        max_edge_m = float(lambda_m) / float(edge_over_lambda)

    def _one(R_mm_):
        return blade_rev1(R_mm_, spin=+1, root_frac=0.070, chord_max_over_r=chord_max,
                          pitch_mm=P_mm, n_sec=n_sec, law=blade_law, pitch_law=pitch_law,
                          chord_rr=c_rr, chord_frac=c_fr)

    probe = _one(R_mm)
    V = np.asarray(probe.vertices)
    r_max = float(np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2).max())
    scale = (R_mm * MM) / max(r_max, 1e-12)

    A = Assembly()
    A.add(_prop_hub(hub_r, R_mm * MM * 0.09), "prop")
    for b in range(int(spec.prop_blades)):
        A.add(rot_z(_one(R_mm * scale), (360.0 / int(spec.prop_blades)) * b), "prop")
    A.union_group("prop")
    if max_edge_m:
        A.parts["prop"] = [refine_to_max_edge(m, max_edge_m) for m in A.parts.get("prop", [])]
    A.mesh_rev1_prop = dict(chord_max_over_r=chord_max, chord_max_source=chord_max_src,
                            chord_profile_source=profile_src, blade_law=blade_law,
                            swept_disc_scale=round(float(scale), 9))
    return A


def blade_orientation(mesh, spin: int, n_blades: int, r_over_R: float = 0.7,
                      n_sample: int = 200_000, band: float = 0.02) -> dict:
    """**P6 check** — do this propeller's blades lead with the raised, thick edge?

    mesh      : a whole propeller, hub at the origin, rotor axis +z, in metres (a trimesh, a
                `cadkit.Assembly` part, or a `geom.Mesh`).
    spin      : the rotation of the rotor this propeller is mounted on, +1 = counter-clockwise
                seen from +z (`rotor_layout`'s dir), −1 = clockwise.
    n_blades  : blade count, used to split the cylindrical section into blades.
    r_over_R  : where to take the section. Plan C.7 asks for 0.3 / 0.5 / 0.7 / 0.9 R.

    Each row also carries two readings of the blade angle, `angle_hull_deg` and
    `angle_inertia_deg`; the inertia one is the one to score plan C.7's ±0.2° with (see below).

    The cylindrical section at radius r is taken, projected on (tangential, z), the chord is the
    longest diagonal of that section's convex hull, and the thick end is the chord end carrying
    more thickness. The motion direction at that section is `spin · (ẑ × r̂)`. Returns per-blade
    rows and a summary with `all_ok` true when every blade has the thick edge both raised and
    leading — the same two cues measured on the DJI Mini 2 reference (8/8 blades).
    """
    from scipy.spatial import ConvexHull
    m = _as_trimesh(mesh)
    _check_spin(spin, "blade_orientation")
    P = trimesh.sample.sample_surface(m, int(n_sample), seed=0)[0]
    rad = np.hypot(P[:, 0], P[:, 1])
    R = float(rad.max())
    r0 = float(r_over_R) * R
    sel = np.abs(rad - r0) <= float(band) * R
    Q = P[sel]
    if len(Q) < 50 * int(n_blades):
        raise RuntimeError(f"blade_orientation: only {len(Q)} points in the r/R={r_over_R} band")
    phi = np.arctan2(Q[:, 1], Q[:, 0])
    rows = []
    for b in range(int(n_blades)):
        #  rotate the band so blade b sits near φ = 0, then keep a wedge around it
        off = 2.0 * np.pi * b / int(n_blades)
        d = (phi - off + np.pi) % (2.0 * np.pi) - np.pi
        keep = np.abs(d) <= np.pi / int(n_blades)
        if int(keep.sum()) < 50:
            continue
        S = Q[keep]
        phi_c = float(np.arctan2(np.sin(phi[keep]).mean(), np.cos(phi[keep]).mean()))
        #  ẑ × r̂ at this azimuth = the direction a counter-clockwise rotor moves the blade
        t_hat = np.array([-math.sin(phi_c), math.cos(phi_c), 0.0])
        A = np.c_[S @ t_hat, S[:, 2]] / MM                            # (tangential, z) in mm
        H = A[ConvexHull(A).vertices]
        D = H[:, None, :] - H[None, :, :]
        d2 = (D ** 2).sum(-1)
        i, j = np.unravel_index(np.argmax(d2), d2.shape)
        chord = float(np.sqrt(d2[i, j]))
        ev = (H[j] - H[i]) / chord
        nv = np.array([-ev[1], ev[0]])
        s = (A - H[i]) @ ev
        h = (A - H[i]) @ nv

        def thick(a, b_):
            k = (s >= a * chord) & (s <= b_ * chord)
            return float(np.ptp(h[k])) if k.sum() >= 10 else float("nan")

        #  Two readings of the blade angle, because they do not agree and plan C.7 scores it:
        #    hull    — from the convex hull's longest diagonal, the usual quick chord line. It
        #              moves by up to ~0.6° when a cambered section is mirrored chordwise, since
        #              the hull ends land at different places relative to the camber.
        #    inertia — the first principal axis of the section's surface samples. It does not
        #              care which end the camber sits at, and it is the one to score ±0.2° with.
        C = A - A.mean(0)
        v = np.linalg.svd(C, full_matrices=False)[2][0]
        angle_inertia = math.degrees(math.atan2(abs(float(v[1])), abs(float(v[0]))))
        ti, tj = thick(0.05, 0.25), thick(0.75, 0.95)
        thick_pt, thin_pt = (H[i], H[j]) if ti > tj else (H[j], H[i])
        d_tan = float(thick_pt[0] - thin_pt[0])
        d_up = float(thick_pt[1] - thin_pt[1])
        leads = bool(d_tan * int(spin) > 0)
        raised = bool(d_up > 0)
        rows.append(dict(blade=b, phi_deg=round(math.degrees(phi_c), 3),
                         chord_mm=round(chord, 4),
                         t_near_thick_mm=round(max(ti, tj), 4),
                         t_near_thin_mm=round(min(ti, tj), 4),
                         thick_over_thin=round(max(ti, tj) / max(min(ti, tj), 1e-9), 4),
                         d_tangential_thick_minus_thin_mm=round(d_tan, 4),
                         d_up_thick_minus_thin_mm=round(d_up, 4),
                         angle_hull_deg=round(math.degrees(math.asin(
                             min(1.0, abs(d_up) / max(chord, 1e-9)))), 4),
                         angle_inertia_deg=round(angle_inertia, 4),
                         thick_edge_leads=leads, thick_edge_is_raised=raised,
                         ok=bool(leads and raised), r_over_R=float(r_over_R),
                         radius_mm=round(r0 / MM, 4)))
    n_ok = sum(r["ok"] for r in rows)
    return dict(spin=int(spin), r_over_R=float(r_over_R), n_blades=len(rows),
                n_leading=sum(r["thick_edge_leads"] for r in rows),
                n_raised=sum(r["thick_edge_is_raised"] for r in rows),
                n_ok=n_ok, all_ok=bool(rows and n_ok == len(rows)), blades=rows)


def blade_angle_deg(blade_mesh, r_over_R: float, R_mm: float) -> float:
    """**P6 check** — blade angle of one blade at r/R, on the plane normal to its span.

    blade_mesh : one blade with its span along +x and its root at the origin, in metres — what
                 `blade_rev1` and `drone_cad._blade` both return.
    Returns the angle in degrees between the section's long axis and the rotor plane, always
    positive: this compares revision 1 with revision 0, where the sign is the whole point and is
    settled by `blade_orientation` instead.

    Why a plane and not a cylinder: the cylindrical section of plan C.7 is the right place to
    read the leading/raised cues, but it mixes a band of radii whose blade angles differ, and a
    chord-mirrored section shifts the weight inside that band. On revision 0 against revision 1
    that reads about 0.4° where the plane reads 0.07°. Why the section's principal axis and not
    the chord line: the hull's longest diagonal lands somewhere else once the camber sits at the
    other end of the chord, which moves it by about 0.6°.

    ⚠ Even the principal axis is not exactly the chord line of a **cambered** section — the
    camber tilts it by about half the residual seen here (CAMBER_M = 0.05 in `drone_cad`). So a
    0.07° difference between a section and its chordwise mirror is this measure, not the blade
    angle law, which is the same code with the same sign in both revisions.
    """
    m = _as_trimesh(blade_mesh)
    x = float(r_over_R) * float(R_mm) * MM
    sec = m.section(plane_origin=[x, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    if sec is None:
        raise RuntimeError(f"blade_angle_deg: no section at r/R={r_over_R}")
    V = np.asarray(sec.vertices, float)[:, 1:]          # (y, z), the rotor plane and up
    V = V - V.mean(0)
    u = np.linalg.svd(V, full_matrices=False)[2][0]
    return float(math.degrees(math.atan2(abs(float(u[1])), abs(float(u[0])))))


def _as_trimesh(mesh) -> trimesh.Trimesh:
    """Accept a trimesh, a `Part`, a `cadkit.Assembly` or a `geom.Mesh`."""
    if isinstance(mesh, Part):
        return mesh.mesh
    if isinstance(mesh, trimesh.Trimesh):
        return mesh
    parts = getattr(mesh, "parts", None)
    if isinstance(parts, dict):                      # cadkit.Assembly
        ms = [m for lst in parts.values() for m in lst]
        return ms[0] if len(ms) == 1 else trimesh.util.concatenate(ms)
    v, f = getattr(mesh, "v", None), getattr(mesh, "f", None)
    if v is not None and f is not None:              # geom.Mesh
        return trimesh.Trimesh(vertices=np.asarray(v, float),
                               faces=np.asarray(f, np.int64), process=False)
    raise TypeError(f"blade_orientation: cannot read a mesh out of {type(mesh).__name__}")


# --------------------------------------------------------------------------- #
#  P7 — gimbal block on a yaw post
# --------------------------------------------------------------------------- #
def gimbal_block(w_mm: float, h_mm: float, d_mm: float, lens_d_mm: float, lens_len_mm: float,
                 *, group: str, center_xyz_mm=(0.0, 0.0, 0.0), yaw_post=None, host=None,
                 post_group: str | None = None, name: str = "gimbal",
                 corner_r_mm: float = 2.0, corner_seg: int = CORNER_MIN_SEGMENTS,
                 lens_axis: str = "+x", n_lens: int = 1,
                 lens_spacing_mm: float = 0.0, declare_post_components: int | None = None,
                 sagitta_mm: float = SAGITTA_TARGET_MM,
                 max_faces=None) -> list[Part]:
    """**P7** — a camera block hanging under the airframe on a yaw post.

    w_mm, h_mm, d_mm : block width (y), height (z) and depth (x), at `center_xyz_mm`.
    lens_d_mm, lens_len_mm : the lens barrel(s) standing out of the block along `lens_axis`
        ("+x" forward is the usual one). `n_lens` and `lens_spacing_mm` place several barrels
        side by side in y for a multi-camera head.
    yaw_post : `dict(d_mm=…, top_z_mm=…)`, the post the block hangs from. Its bottom meets the
        block's top; its top is `top_z_mm`, normally inside the airframe.
    host : the airframe mesh in **metres**, or None. When given, the post is cut with
        `difference(post, host)` so it stops exactly at the host surface: plan C.2 wants a gap
        ≤ 0.5 mm and no floating part, and the cut gives 0.
    group / post_group : the block's group (`camera` for a real camera head) and the post's.
        The post defaults to the block's group.

    Returns [block(+lenses), post] — two parts, or one when no post is asked for.
    Serves plan rows M4E-7 (Matrice 4E gimbal width), P4-3 (Phantom 4 camera position and
    burial) and the Mavic 4 Pro gimbal of plan B.6.
    """
    what = f"gimbal_block({name!r})"
    if min(float(w_mm), float(h_mm), float(d_mm)) <= 0:
        raise ValueError(f"{what}: block dimensions must be positive")
    if lens_axis not in ("+x", "-x"):
        raise ValueError(f"{what}: lens_axis must be '+x' or '-x'")
    if int(n_lens) < 0:
        raise ValueError(f"{what}: n_lens={n_lens} must be 0 or more")
    if int(n_lens) > 0 and (float(lens_d_mm) <= 0 or float(lens_len_mm) <= 0):
        raise ValueError(f"{what}: lens_d_mm={lens_d_mm} and lens_len_mm={lens_len_mm} must be "
                         f"positive when n_lens={n_lens}. A non-positive length used to build a "
                         f"stub that the block simply swallowed, so the head came out with no "
                         f"lens and nothing said so.")
    if float(corner_r_mm) < 0:
        raise ValueError(f"{what}: corner_r_mm={corner_r_mm} must be 0 or more")
    cx, cy, cz = (float(v) for v in center_xyz_mm)

    r = min(float(corner_r_mm), 0.49 * min(float(w_mm), float(h_mm)))
    ring, sag = _rounded_rect_ring(float(w_mm), float(h_mm), r, float(sagitta_mm), int(corner_seg))
    xs = [cx - 0.5 * float(d_mm), cx + 0.5 * float(d_mm)]
    rings = [np.c_[ring[:, 0] + cy, ring[:, 1] + cz]] * 2
    block = _ring_loft([q * MM for q in rings], [x * MM for x in xs], name=f"P7 {name} block")

    meshes = [block]
    sgn = +1.0 if lens_axis == "+x" else -1.0
    seg = segments_for_sagitta(0.5 * float(lens_d_mm), sagitta_mm)
    for i in range(int(n_lens)):
        y = cy + (i - (int(n_lens) - 1) / 2.0) * float(lens_spacing_mm)
        z0 = cx + sgn * 0.5 * float(d_mm) - sgn * 0.5          # 0.5 mm of overlap into the block
        lens, s_l = _revolve_profile(
            [[0.0, 0.0], [0.5 * float(lens_d_mm), 0.0],
             [0.5 * float(lens_d_mm), float(lens_len_mm) + 0.5], [0.0, float(lens_len_mm) + 0.5]],
            seg, center_mm=(0.0, 0.0, 0.0), name=f"P7 {name} lens{i}")
        M = trimesh.transformations.rotation_matrix(sgn * math.pi / 2.0, [0, 1, 0])
        lens = lens.copy().apply_transform(M)
        lens.apply_translation([z0 * MM, y * MM, cz * MM])
        meshes.append(lens)
        sag = max(sag, s_l)
    body = (_boolean_keep_closed("union", meshes, f"{what} block ∪ lenses")
            if len(meshes) > 1 else block)
    _budget(len(body.faces), "P7_gimbal", what, max_faces)
    ms = _require_sagitta(body, sag, what)
    out = [Part(body, _check_group(group, f"{what} block"), name, "P7", sag, 1,
                dict(center_xyz_mm=[cx, cy, cz], w_mm=float(w_mm), h_mm=float(h_mm),
                     d_mm=float(d_mm), n_lens=int(n_lens), mesh_sagitta_mm=round(ms, 5)))]

    if yaw_post is not None:
        pd = float(yaw_post["d_mm"])
        z_top = float(yaw_post["top_z_mm"])
        z_bot = cz + 0.5 * float(h_mm) - 0.5                   # 0.5 mm of overlap into the block
        if z_top <= z_bot:
            raise ValueError(f"{what}: yaw post top z {z_top} is not above the block top {z_bot}")
        if pd <= 0:
            raise ValueError(f"{what}: yaw post d_mm={pd} must be positive")
        seg_p = segments_for_sagitta(0.5 * pd, sagitta_mm)
        post, s_p = _revolve_profile([[0.0, 0.0], [0.5 * pd, 0.0], [0.5 * pd, z_top - z_bot],
                                      [0.0, z_top - z_bot]],
                                     seg_p, center_mm=(cx, cy, z_bot), name=f"P7 {name} post")
        cut, removed, gap = False, None, None
        if host is not None:
            hm = host.mesh if isinstance(host, Part) else host
            post, removed, gap = _cut_to_host(post, hm, f"{what} post vs host")
            cut = True
        comp = int(len(post.split(only_watertight=False)))
        if declare_post_components is not None and comp != int(declare_post_components):
            raise ValueError(f"{what}: the post is {comp} piece(s), not the "
                             f"{int(declare_post_components)} the caller declared (plan C.1).")
        out.append(Part(post, _check_group(post_group or group, f"{what} post"),
                        f"{name}_post", "P7", s_p, comp,
                        dict(d_mm=pd, top_z_mm=z_top, bottom_z_mm=z_bot,
                             cut_against_host=cut,
                             host_removed_mm3=None if removed is None else round(removed, 6),
                             host_gap_mm=None if gap is None else round(gap, 6))))
    return out


# --------------------------------------------------------------------------- #
#  P8 — contain an internal box inside the shell
# --------------------------------------------------------------------------- #
def contain(box_mm, shell, *, group: str, clearance_mm: float = 1.0, name: str = "box",
            center_mm=None, search_mm: float | None = None, search_steps: int = 9,
            declare_components: int | None = None, max_faces=None) -> Part:
    """**P8** — place an internal box of its **official size** inside a shell, with clearance.

    box_mm       : (L, W, H) in mm, the official dimensions. They are never changed: plan B.0
                   forbids inventing a dimension, and a battery's catalogue size is a source.
    shell        : the shell mesh in **metres** (a `Part` or a trimesh), closed.
    clearance_mm : how far the box must stay from the shell on every side (plan C.2: internal
                   metal 100 % inside the shell with ≥ 1 mm clearance).
    center_mm    : the box centre. Default: the centre of the shell's bounding box, **and only
                   then is it searched**. Giving a centre pins the box there, because a centre
                   from a source is a measured dimension and plan B.0 forbids inventing one; the
                   search used to move an explicitly given centre by the full search radius
                   (60 mm was measured) without saying so (adversarial review 2026-09-17,
                   C-fix 4). Pass `search_mm` as well to search from a given start on purpose.
    search_mm / search_steps : the box is translated on a coordinate-descent search over a cube
                   of ±`search_mm`, refined `search_steps` times, looking for a placement where
                   the box grown by `clearance_mm` on every side is wholly inside the shell.
                   Default: 60 mm with no `center_mm`, 0 mm (pinned) with one.
    declare_components : how many pieces the caller means the result to be. Given, any other
                   count is refused; a clipped box can come back in several pieces.

    If a placement is found, the part is the plain 12-triangle box at that position and
    `info["clipped_volume_pct"]` is 0.0. If none is found, the box is intersected with the
    shell at the best placement and the clipped volume is logged — plan P8: "If it cannot fit,
    intersect it with the shell and log the clipped volume %."

    Serves plan rows M4E-3 (Matrice 4E battery), M5P-5 (Mini 5 Pro battery) and P4-7
    (Phantom 4 internals).
    """
    sm = shell.mesh if isinstance(shell, Part) else shell
    if not sm.is_watertight:
        raise ValueError(f"contain({name!r}): the shell must be closed to test containment")
    L, W, H = (float(v) for v in box_mm)
    if min(L, W, H) <= 0:
        raise ValueError(f"contain({name!r}): box_mm must be positive, got {box_mm}")
    cl = float(clearance_mm)
    if cl < 0:
        raise ValueError(f"contain({name!r}): clearance_mm={clearance_mm} must be 0 or more")
    search = float((0.0 if center_mm is not None else 60.0) if search_mm is None else search_mm)
    if search < 0:
        raise ValueError(f"contain({name!r}): search_mm={search_mm} must be 0 or more")
    grown = np.array([L + 2 * cl, W + 2 * cl, H + 2 * cl]) * MM
    lo, hi = sm.bounds
    c0 = np.asarray(center_mm, float) * MM if center_mm is not None else 0.5 * (lo + hi)

    #  probe points of the grown box: corners, edge midpoints, face centres and a light grid
    g = []
    for a in (-0.5, 0.0, 0.5):
        for b in (-0.5, 0.0, 0.5):
            for c in (-0.5, 0.0, 0.5):
                g.append([a, b, c])
    for a in (-0.5, -0.25, 0.0, 0.25, 0.5):
        for b in (-0.5, -0.25, 0.0, 0.25, 0.5):
            g += [[a, b, -0.5], [a, b, 0.5], [a, -0.5, b], [a, 0.5, b],
                  [-0.5, a, b], [0.5, a, b]]
    G = np.unique(np.asarray(g, float), axis=0) * grown[None, :]

    def inside_frac(c):
        return float(sm.contains(G + np.asarray(c, float)[None, :]).mean())

    best_c, best_f = np.asarray(c0, float), inside_frac(c0)
    if center_mm is None and search > 0 and best_f < 1.0 - 1e-12:
        #  A coordinate descent from one start can sit down in a local maximum — a battery that
        #  would fit further forward stays where the first few steps left it. So the shell's
        #  bounding box is scanned coarsely first and the descent starts from the best cell.
        for fx in np.linspace(0.2, 0.8, 7):
            for fy in (0.35, 0.5, 0.65):
                for fz in (0.3, 0.5, 0.7):
                    c = lo + np.array([fx, fy, fz]) * (hi - lo)
                    f = inside_frac(c)
                    if f > best_f + 1e-12:
                        best_c, best_f = c, f
    step = search * MM
    for _ in range(int(search_steps) if search > 0 else 0):
        moved = False
        for ax in range(3):
            for sgn in (+1.0, -1.0):
                c = best_c.copy()
                c[ax] += sgn * step
                f = inside_frac(c)
                if f > best_f + 1e-12:
                    best_c, best_f, moved = c, f, True
        if not moved:
            step *= 0.5
            if step < 0.05 * MM:
                break

    box = trimesh.creation.box(extents=[L * MM, W * MM, H * MM])
    box.apply_translation(best_c)
    v_full = float(box.volume)
    if best_f >= 1.0 - 1e-12:
        m, clipped = box, 0.0
    else:
        m = trimesh.boolean.intersection([box, sm], engine="manifold")
        if m is None or len(m.faces) == 0:
            raise RuntimeError(f"contain({name!r}): the box does not meet the shell at all")
        m.update_faces(m.nondegenerate_faces())
        m.merge_vertices()
        m.remove_unreferenced_vertices()
        trimesh.repair.fix_normals(m)
        if m.is_watertight and m.volume < 0:
            m.invert()
        clipped = 100.0 * (1.0 - float(m.volume) / max(v_full, 1e-30))
    if max_faces is not None or best_f >= 1.0 - 1e-12:
        _budget(len(m.faces), "P8_box", f"contain({name!r})", max_faces)
    comp = int(len(m.split(only_watertight=False)))
    if declare_components is not None and comp != int(declare_components):
        raise ValueError(f"contain({name!r}): the box is {comp} piece(s), not the "
                         f"{int(declare_components)} the caller declared (plan C.1).")
    return Part(m, _check_group(group, f"contain({name!r})"), name, "P8", 0.0, comp,
                dict(box_mm=[L, W, H], clearance_mm=cl,
                     center_mm=[round(float(v) / MM, 4) for v in best_c],
                     center_asked_mm=None if center_mm is None
                     else [round(float(v), 4) for v in center_mm],
                     center_shift_mm=round(float(np.linalg.norm(best_c - np.asarray(c0, float)))
                                           / MM, 6),
                     search_mm=search,
                     fits_with_clearance=bool(best_f >= 1.0 - 1e-12),
                     probe_inside_frac=round(best_f, 6),
                     clipped_volume_pct=round(clipped, 6)))
