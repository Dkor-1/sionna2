"""
CLI: generate decomposed PO micro-Doppler windows for one flight (grade).

This is the refactored entry point that replaces the monolithic
`sionna_sim/sim_ablation.py`. It wires `configs/default.py` defaults (+ CLI
overrides) into the pure `po_sim` library and runs the windowed generator.

Examples
--------
  # subset smoke test (2 windows) into a scratch dir
  python scripts/generate_ablation.py --grade 2 --max-windows 2 --workers 2 \
      --out /tmp/po_test

  # full grade_2 with the standard RPM x5.73 and rpm augmentation sweep
  python scripts/generate_ablation.py --grade 2 --rpm-scale 5.73 \
      --rpm-sweep 5.16,6.30

Output: <out>/grade_{G}[tags]/window_XXXXX.npz  (+ metadata.npz, MANIFEST.txt)
Reconstruct the 9 ablation combos post-hoc — see MANIFEST.txt.
"""
# --- cap BLAS/embree threads to 1 per worker BEFORE importing numpy ---
# Otherwise each of N worker processes spawns a full BLAS thread pool -> load
# ~800 and ~7x slower. Must be set before numpy loads its backend.
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import argparse
from multiprocessing import cpu_count

# make `configs` and `po_sim` importable (project root = po_mdoppler/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from configs.default import (
    SimConfig, MESH_DIR, DATA_BASE, OUT_BASE,
    BODY_MAT, BLADE_MATS, BLADE_MAT_KEYS, BLADE_OFFSETS, BLADE_DIRS,
)
from po_sim.engine import run_generation, SceneSpec


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grade", type=int, default=2)
    ap.add_argument("--workers", type=int,
                    default=int(os.environ.get("PO_WORKERS", min(24, cpu_count()))))
    ap.add_argument("--max-windows", type=int, default=0,
                    help="0 = all; >0 = first N windows (subset test)")
    ap.add_argument("--out", type=str, default=OUT_BASE)
    ap.add_argument("--rpm-scale", type=float, default=6.0,
                    help="블레이드 RPM 스케일 (기본 6.0)")
    ap.add_argument("--blade-cf-eps", type=float, default=None,
                    help="cf 블레이드 상대유전율 εr override (RCS 물리보정)")
    ap.add_argument("--blade-cf-sigma", type=float, default=None,
                    help="cf 블레이드 전도율 σ override (RCS 물리보정)")
    ap.add_argument("--radar-azimuth", type=float, default=0.0,
                    help="레이더 방위각(deg). 0=현재(-y)")
    ap.add_argument("--radar-range", type=float, default=None,
                    help="레이더 수평거리 m (기본 60)")
    ap.add_argument("--radar-height", type=float, default=None,
                    help="레이더 고도오프셋 m (기본 20)")
    ap.add_argument("--rpm-sweep", type=str, default=None,
                    help="per-window RPM 연속 스윕 'lo,hi' (윈도우별 고유 RPM)")
    ap.add_argument("--per-rotor", action="store_true",
                    help="per-rotor cf 블레이드 신호 분리저장 (1D 컴포넌트 refine용)")
    return ap.parse_args()


def build_config(args):
    """SimConfig from CLI (radar geometry + RPM scale)."""
    kw = dict(rpm_scale=args.rpm_scale, radar_azimuth_deg=args.radar_azimuth)
    if args.radar_range is not None:
        kw["radar_range_offset"] = args.radar_range
    if args.radar_height is not None:
        kw["radar_height_offset"] = args.radar_height
    return SimConfig(**kw)


def build_spec(args):
    """SceneSpec = materials (+ cf override) + airframe geometry."""
    blade_mats = dict(BLADE_MATS)
    cf_er, cf_sg = blade_mats["cf"]
    if args.blade_cf_eps is not None:
        cf_er = args.blade_cf_eps
    if args.blade_cf_sigma is not None:
        cf_sg = args.blade_cf_sigma
    blade_mats["cf"] = (cf_er, cf_sg)
    return SceneSpec(body_mat=BODY_MAT, blade_mats=blade_mats,
                     blade_mat_keys=list(BLADE_MAT_KEYS),
                     blade_offsets=BLADE_OFFSETS, blade_dirs=BLADE_DIRS,
                     per_rotor=args.per_rotor)


def output_tag(args, cfg, spec):
    """Reproduce the sim_ablation.py out_dir naming so runs stay distinguishable."""
    tag = "" if abs(cfg.rpm_scale - 6.0) < 1e-6 else f"_rpm{cfg.rpm_scale:g}"
    if args.blade_cf_eps is not None or args.blade_cf_sigma is not None:
        er, sg = spec.blade_mats["cf"]
        tag += f"_cf{er:g}-{sg:g}"
    if (abs(args.radar_azimuth) > 1e-6 or args.radar_range is not None
            or args.radar_height is not None):
        tag += (f"_az{args.radar_azimuth:g}_r{cfg.radar_range_offset:g}"
                f"_h{cfg.radar_height_offset:g}")
    if args.rpm_sweep:
        lo, hi = [float(x) for x in args.rpm_sweep.split(",")]
        tag += f"_rpmsweep{lo:g}-{hi:g}"
    if spec.per_rotor:
        tag += "_perrotor"
    return tag


def main():
    args = parse_args()
    cfg = build_config(args)
    spec = build_spec(args)

    rpm_sweep = None
    if args.rpm_sweep:
        lo, hi = [float(x) for x in args.rpm_sweep.split(",")]
        rpm_sweep = (lo, hi)

    data_dir = os.path.join(DATA_BASE, f"grade_{args.grade}")
    out_dir = os.path.join(args.out, f"grade_{args.grade}{output_tag(args, cfg, spec)}")

    run_generation(cfg, spec, grade=args.grade, data_dir=data_dir, out_dir=out_dir,
                   mesh_dir=MESH_DIR, workers=args.workers,
                   max_windows=args.max_windows, rpm_sweep=rpm_sweep)


if __name__ == "__main__":
    main()
