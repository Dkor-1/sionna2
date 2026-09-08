#!/usr/bin/env python
"""Recheck scene comparison from complete shards and direct geometry queries.

Run from the repository root:
    CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 /workspace/.venvs/py312/bin/python benchmark/builtin_scene_diagnosis_0908.py

This reads existing GPU records. Geometry queries run on CPU; they do not
reproduce GPU path-candidate generation. The difference between outdoor and
free-space fields includes environment-induced changes to drone paths, and is
not by itself a list of static paths or proof of a missing ground reflection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/builtin_scene_diagnosis_0908.json'
SHARDS = ROOT / 'outputs/elev_sweep_shards'
THRESHOLDS = (.001, .003, .01, .03, .1, .2, .3, .5, 1.)
ELS = (-30, -60)
SCENES = ('outdoor01', 'sionna-simple_street_canyon', 'sionna-munich')


def load(tag, el):
    import numpy as np
    prefix = 'sionna_p4000000000_swR0D0E0F1_r15_n8192_'
    pattern = f'{prefix}{tag}mfixbatteryi5_blperairframe_d2_el{el}_*.npz'
    files = sorted(SHARDS.glob(pattern))
    if not files:
        raise ValueError(f'No input for {pattern}')
    rows, sources = [], []
    for path in files:
        raw = path.read_bytes()
        with np.load(path) as z:
            rows.append({k: z[k].copy() for k in z.files})
        sources.append(dict(path=str(path.relative_to(ROOT)),
                            sha256=hashlib.sha256(raw).hexdigest()))
    idx = np.concatenate([z['idx'] for z in rows])
    order = np.argsort(idx)
    expected = int(rows[0]['meta'][3])
    assert np.array_equal(idx[order], np.arange(expected)), 'Incomplete or duplicate poses'
    assert all(np.array_equal(z['cfg'], rows[0]['cfg']) for z in rows)
    return (np.concatenate([z['E'] for z in rows])[order],
            np.concatenate([z['npaths'] for z in rows])[order],
            rows[0]['cfg'].tolist(), sources)


def shard_comparison():
    import numpy as np
    result = {}
    for el in ELS:
        free, _, cfg_free, sources_free = load('', el)
        for scene in SCENES:
            field, npaths, cfg, sources = load(f'env{scene}_', el)
            assert cfg == cfg_free, 'Solver settings differ'
            delta = field - free
            center = complex(np.median(delta.real), np.median(delta.imag))
            assert abs(center) > 0
            relative = np.abs(delta - center) / abs(center)
            amp = np.abs(field)
            base = float(np.median(amp))
            event = relative > .5
            drops = amp < .1 * base
            entry = dict(
                scene=scene, el_deg=el, n_poses=len(field), cfg=cfg,
                sources=sources, free_sources=sources_free,
                delta_center_re=center.real, delta_center_im=center.imag,
                npaths_min=int(npaths.min()), npaths_max=int(npaths.max()),
                npaths_median=float(np.median(npaths)),
                thresholds={str(t): int((relative > t).sum()) for t in THRESHOLDS},
                relative_deviation_quantiles=dict(zip(
                    ('p50', 'p90', 'p99', 'p999', 'max'),
                    np.quantile(relative, [.5, .9, .99, .999, 1]).tolist())),
                old_deviation_events=int(event.sum()), old_amplitude_drops=int(drops.sum()),
                events_caught_by_drop=int((event & drops).sum()),
                event_pose_indices=np.flatnonzero(event).tolist(),
                amplitude_step_db_at_events=(float(20*np.log10(np.median(amp[event])/base))
                                             if event.any() else None),
                caveat='Field-difference events are not direct path-identity counts. '
                       'The relative-deviation criterion has an explicit threshold.')
            result[f'{scene}/el{el}'] = entry
    return result


def geometry_queries():
    import numpy as np
    import sionna.rt as rt
    import mitsuba as mi
    from importlib.metadata import version

    def trace(sc, origin, direction):
        si = sc.mi_scene.ray_intersect(mi.Ray3f(
            mi.Point3f(*map(float, origin)), mi.Vector3f(*map(float, direction))))
        valid = bool(si.is_valid()[0])
        return dict(hit=valid, distance_m=float(si.t[0]) if valid else None,
                    point_m=np.asarray(si.p).ravel().tolist() if valid else None,
                    shape=si.shape[0].id() if valid else None)

    def triangle_distance(sc, origin, direction):
        # Independent intersection arithmetic on the loaded mesh vertices.
        # This shares the geometry with Mitsuba, not its intersection routine.
        nearest = None
        for shape in sc.mi_scene.shapes():
            params = mi.traverse(shape)
            if 'faces' not in params:
                continue
            vertices = np.asarray(params['vertex_positions']).reshape(-1, 3).astype(float)
            faces = np.asarray(params['faces']).reshape(-1, 3)
            tri = vertices[faces]
            e1, e2 = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
            p = np.cross(np.broadcast_to(direction, e2.shape), e2)
            determinant = np.einsum('ij,ij->i', e1, p)
            ok = np.abs(determinant) > 1e-12
            inv = np.divide(1., determinant, out=np.zeros_like(determinant), where=ok)
            tv = origin-tri[:, 0]
            u = np.einsum('ij,ij->i', tv, p)*inv
            q = np.cross(tv, e1)
            v = q @ direction*inv
            t = np.einsum('ij,ij->i', e2, q)*inv
            ok &= (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8) & (t > 1e-6)
            if ok.any():
                distance = float(t[ok].min())
                if nearest is None or distance < nearest['distance_m']:
                    nearest = dict(distance_m=distance, shape=shape.id())
        return nearest

    results = {}
    for name in ('simple_street_canyon', 'munich'):
        sc = rt.load_scene(getattr(rt.scene, name))
        center = np.array([0., 0., 25.])
        cells = {}
        for el in ELS:
            radar = center+15*np.array([np.cos(np.radians(el)), 0., np.sin(np.radians(el))])
            direction = (center-radar)/15
            hit = trace(sc, radar, direction)
            independent = triangle_distance(sc, radar, direction)
            if hit['hit']:
                assert independent is not None
                assert abs(hit['distance_m']-independent['distance_m']) < 1e-3
            else:
                assert independent is None
            cells[str(el)] = dict(
                drone_center_m=center.tolist(), radar_m=radar.tolist(), range_m=15.,
                to_drone=hit, numpy_intersection=independent,
                blocked_before_drone=hit['hit'] and hit['distance_m'] < 15.,
                radar_down=trace(sc, radar, np.array([0., 0., -1.])))
        # Find a candidate offset for a future matched-placement experiment.
        # These are visibility checks, not a new field simulation.
        candidate = None
        offsets = sorted(((x, y) for x in range(-40, 41, 10)
                          for y in range(-40, 41, 10)), key=lambda xy: xy[0]**2+xy[1]**2)
        for x, y in offsets:
            c = center+np.array([x, y, 0.])
            checks = []
            for el in ELS:
                radar = c+15*np.array([np.cos(np.radians(el)), 0., np.sin(np.radians(el))])
                ray = trace(sc, radar, (c-radar)/15)
                down = trace(sc, radar, np.array([0., 0., -1.]))
                clear = not ray['hit'] or ray['distance_m'] > 15.
                ground = down['hit'] and abs(down['point_m'][2]) < .1
                checks.append(dict(el_deg=el, clear=clear, ground_below=ground))
            if all(row['clear'] and row['ground_below'] for row in checks):
                candidate = dict(drone_center_m=c.tolist(), checks=checks,
                                 caveat='Center-ray visibility only; full drone clearance '
                                        'and new GPU field simulations remain to be checked.')
                break
        results[name] = dict(cells=cells, candidate_clear_placement=candidate)
    return dict(variant=mi.variant(), sionna_rt_version=version('sionna-rt'), scenes=results,
                caveat='CPU geometry checks in the unmodified built-in environment; '
                       'the drone center is queried without inserting drone geometry. '
                       'This establishes line-of-sight obstruction, not the cause of '
                       'a missing path in the GPU candidate generator.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--max-cores', type=int, default=1)
    args = ap.parse_args()
    if hasattr(os, 'sched_setaffinity'):
        allowed = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, set(allowed[:max(1, args.max_cores)]))
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    out = dict(_meta=dict(generator='benchmark/builtin_scene_diagnosis_0908.py',
                          question='Why can built-in scenes appear free of the observed drops?',
                          method='Complete index-aligned GPU shards; threshold sweep; '
                                 'CPU ray intersections checked with NumPy triangle arithmetic.'),
               shard_comparison=shard_comparison(), geometry=geometry_queries())
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    for key, row in out['shard_comparison'].items():
        print(key, row['old_deviation_events'], row['amplitude_step_db_at_events'],
              row['npaths_min'], row['npaths_max'])
    for scene, row in out['geometry']['scenes'].items():
        print(scene, {el: c['blocked_before_drone'] for el, c in row['cells'].items()},
              row['candidate_clear_placement'])
    print(OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
