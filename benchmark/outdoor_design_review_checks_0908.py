#!/usr/bin/env python
"""Small counterexamples for the outdoor design review; no ray solver is run.

Run:
    CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 /workspace/.venvs/py312/bin/python benchmark/outdoor_design_review_checks_0908.py

Selected source AST nodes execute with synthetic inputs. These checks expose
implementation behavior, not the cause or prevalence of errors in GPU records.
"""
import ast
import glob
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile

os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SWEEP = 'benchmark/elevation_sweep_md.py'
ORIGIN = 'benchmark/outdoor_dip_origin_0908.py'
HAMPEL = 'benchmark/hampel_vs_handrule_0908.py'
OUT = ROOT / 'outputs/outdoor_design_review_checks_0908.json'


def tree(path):
    return ast.parse((ROOT/path).read_text())


def execute(node, namespace):
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, '<selected repository AST>', 'exec'), namespace)


def main():
    source = tree(SWEEP)
    body = next(n for n in ast.walk(source) if isinstance(n, ast.If)
                and ast.unparse(n.test) == 'aa.size')
    amplitudes = np.array([3., 3., 1., 2.], complex)
    dedup = {}
    for det in (False, True):
        ns = dict(np=np, aa=amplitudes.copy(), tau=np.zeros(amplitudes.size),
                  O=np.full((1, amplitudes.size), 7),
                  RP=SimpleNamespace(NO_OBJ=4294967295),
                  a=SimpleNamespace(det=det), fc=0., j=0,
                  p=SimpleNamespace(primitives=np.full((1, 1, 1, amplitudes.size), 2)),
                  E=np.zeros(1, complex), E_dedup=np.zeros(1, complex),
                  npaths=np.zeros(1), nret=np.zeros(1), n_dup=np.zeros(1))
        execute(body, ns)
        dedup[str(det)] = dict(total_real=float(ns['E'][0].real),
                               dedup_real=float(ns['E_dedup'][0].real),
                               duplicate_count=int(ns['n_dup'][0]))
    expected = float(np.unique(amplitudes).real.sum())
    assert dedup['False']['dedup_real'] == expected
    assert dedup['True']['dedup_real'] != expected

    condition = next(n.test for n in ast.walk(source) if isinstance(n, ast.If)
                     and '_envn.startswith' in ast.unparse(n.test)
                     and 'str(_nm)' in ast.unparse(n.test))
    select = compile(ast.Expression(body=condition), '<material selector>', 'eval')
    material = {env: {name: bool(eval(select, dict(_envn=env, _nm=name)))
                     for name in ('env_ground', 'matrice4e_prop')}
                for env in ('outdoor01', 'sionna:munich')}
    assert material['sionna:munich']['matrice4e_prop']
    assert not material['outdoor01']['matrice4e_prop']

    loader = next(n for n in tree(ORIGIN).body
                  if isinstance(n, ast.FunctionDef) and n.name == 'load')
    with tempfile.TemporaryDirectory(prefix='outdoor_review_') as folder:
        prefix = 'sionna_p4000000000_swR0D0E0F1_r15_n8192_'
        tail = 'mfixbatteryi5_blperairframe_d2_el-30_00.npz'
        for tag, idx in (('', [0, 1]), ('envtest_', [0, 2])):
            np.savez(Path(folder)/(prefix+tag+tail), idx=np.array(idx),
                     E=np.ones(len(idx), complex))
        ns = dict(np=np, glob=glob, SHD=folder, MESH='mfixbatteryi5_blperairframe')
        execute(loader, ns)
        free = ns['load']('', -30, 'R0D0E0F1')[0]
        outdoor = ns['load']('envtest_', -30, 'R0D0E0F1')[0]
        loader_result = dict(free_indices=[0, 1], scene_indices=[0, 2],
                             free_length=len(free), scene_length=len(outdoor),
                             accepted_by_equal_length_check=len(free) == len(outdoor))
        assert loader_result['accepted_by_equal_length_check']

    hp = next(n for n in tree(HAMPEL).body
              if isinstance(n, ast.FunctionDef) and n.name == 'hampel_mask')
    ns = dict(np=np)
    execute(hp, ns)
    e = np.ones(101, complex)
    e[e.size//2] = -1
    mask = ns['hampel_mask'](np.abs(e), 31, 3.)
    phase_only = dict(n_poses=len(e), phase_change_index=len(e)//2,
                      n_flagged=int(mask.sum()), caveat='Synthetic constant-amplitude phase jump.')
    assert not mask.any()

    phases = np.arange(8)/8
    moments = {str(k): float(abs(np.exp(2j*np.pi*k*phases).mean()))
               for k in (1, 2, 4, 8)}
    assert max(moments[str(k)] for k in (1, 2, 4)) < 1e-12
    assert moments['8'] > 1-1e-12

    # Compare the existing spectral-band helper with the mesh-aware helper.
    import sys
    sys.path.insert(0, str(ROOT/'src'))
    sys.path.insert(0, str(ROOT/'benchmark'))
    import comb_snr as comb
    from drones import DRONES
    tip_node = next(n for n in source.body
                    if isinstance(n, ast.FunctionDef) and n.name == 'f_tip_at')
    import re
    tip_ns = dict(np=np, re=re, ROOT=str(ROOT), TJ=comb.TJ,
                  carrier_of=comb.carrier_of)
    execute(tip_node, tip_ns)
    tip_comparison = dict(el_deg=-60, carrier_hz=comb.FC0_HZ, cells={})
    for drone in ('matrice4e', 'mini5pro', 'phantom4'):
        arm = f'sionna_{drone}_r15_n8192'
        current = float(comb.f_tip(tip_comparison['el_deg'], arm))
        mesh_aware = float(tip_ns['f_tip_at'](tip_comparison['el_deg'], arm))
        tip_comparison['cells'][drone] = dict(
            prop_dia_mm=DRONES[drone].prop_dia_mm,
            hover_rpm=DRONES[drone].hover_rpm,
            comb_helper_hz=current, mesh_aware_helper_hz=mesh_aware,
            ratio=current/mesh_aware)
    assert abs(tip_comparison['cells']['mini5pro']['ratio']-1) > .1

    out = dict(_meta=dict(generator='benchmark/outdoor_design_review_checks_0908.py',
                          scope='Synthetic inputs; installed solver is not executed.',
                          sources={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                                   for p in (SWEEP, ORIGIN, HAMPEL,
                                             "benchmark/comb_snr.py", "src/drones.py")}),
               sorted_dedup=dict(source_line=body.lineno, input_real=amplitudes.real.tolist(),
                                 expected_unique_sum=expected, observed=dedup),
               material_selector=dict(source_line=condition.lineno, selected=material),
               loader=loader_result, hampel_phase_only=phase_only,
               tip_band_comparison=tip_comparison,
               circular_moments=dict(phases=phases.tolist(), moments=moments,
                                     caveat='Counterexample to excluding periodicity from a '
                                            'small set of low-order circular moments.'))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
