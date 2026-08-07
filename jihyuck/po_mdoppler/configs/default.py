"""
Default configuration for the PO micro-Doppler simulator.

All physical parameters live here so the rest of the package takes a
`SimConfig` object and never hard-codes constants. Values are the validated
defaults carried over verbatim from `sim_ablation.py` (grade_2, RPM x6, X-band).

  - `SimConfig`      : radar + kinematics + occlusion scalars (CLI-overridable)
  - materials        : body (fixed metal) and the blade ablation axis
  - drone geometry   : motor offsets / spin directions (baked into the airframe)
  - paths            : where the mesh, PX4 flight data, and outputs live
"""
import os
from dataclasses import dataclass

import numpy as np

# ==============================================================================
# PATHS
# ==============================================================================
# configs/default.py -> po_mdoppler/  (package root) -> sionna_sim/ (repo root)
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIONNA_SIM_ROOT = os.path.dirname(PKG_ROOT)

# tri + outward-normal Phantom-4 mesh copied into the package
MESH_DIR = os.path.join(PKG_ROOT, "Mesh")

# PX4 flight telemetry (clean_{position,attitude,esc}.csv per grade).
# Prefer the live copy in the surrounding sionna_sim tree (dev machine, all grades
# + groundtruth); fall back to the copy bundled inside the package so a zipped
# hand-off of this folder alone still runs.
_EXTERNAL_DATA = os.path.join(SIONNA_SIM_ROOT, "260115_sim", "sim_data")
_BUNDLED_DATA = os.path.join(PKG_ROOT, "data", "sim_data")
DATA_BASE = _EXTERNAL_DATA if os.path.isdir(_EXTERNAL_DATA) else _BUNDLED_DATA

# where generated windows are written (grade_{G}[tags]/window_XXXXX.npz).
# Use the shared data disk if present; otherwise write into the package so output
# lands somewhere writable on any machine.
_EXTERNAL_OUT = "/data/jihyuckhong/po_ablation"
OUT_BASE = (_EXTERNAL_OUT if os.path.isdir(os.path.dirname(_EXTERNAL_OUT))
            else os.path.join(PKG_ROOT, "output"))

# ==============================================================================
# MATERIALS  (relative_permittivity er, conductivity sigma [S/m])
# ==============================================================================
# Fresnel Gamma at normal incidence = (1 - sqrt(er_c)) / (1 + sqrt(er_c)).
# Body is fixed metal; blade material is the cheap (per-pulse ~free) ablation axis.
BODY_MAT = (1.0, 1e6)                    # metal, FIXED for body -> |Gamma| ~ 1
BLADE_MATS = {
    "nylon": (4.0, 0.0),                 # glass-fibre-reinforced nylon (DJI 9450S)
    "cf":    (8.0, 12.0),                # carbon fibre
    "metal": (1.0, 1e6),                 # metal
}
BLADE_MAT_KEYS = ["nylon", "cf", "metal"]

# ==============================================================================
# DRONE GEOMETRY  (baked into the airframe; not an ablation axis)
# ==============================================================================
MOTOR_OFFSET = 0.175 / np.sqrt(2)        # arm length projected onto x/y
# rotor hub positions in the body frame, order = blade_1..blade_4
BLADE_OFFSETS = np.array([
    [-MOTOR_OFFSET,  MOTOR_OFFSET, 0.072],   # blade_1  FR  CCW
    [ MOTOR_OFFSET, -MOTOR_OFFSET, 0.072],   # blade_2  BL  CCW
    [ MOTOR_OFFSET,  MOTOR_OFFSET, 0.072],   # blade_3  FL  CW
    [-MOTOR_OFFSET, -MOTOR_OFFSET, 0.072],   # blade_4  BR  CW
])
BLADE_DIRS = np.array([-1, -1, 1, 1])        # spin sign per rotor


@dataclass
class SimConfig:
    """Scalar simulation parameters. Derived quantities are properties so a
    single override (e.g. ``prf``) stays internally consistent."""

    # --- radar ---
    f_c: float = 9.85e9                  # carrier [Hz] (X-band)
    c: float = 3e8                       # speed of light [m/s]
    prf: int = 35000                     # pulse repetition frequency [Hz]
    n_pulses: int = 5000                 # pulses per window (= 1 spectrogram)
    t_skip: float = 5.0                  # skip first seconds of the flight [s]

    # --- radar placement relative to flight centre (monostatic ground station) ---
    radar_range_offset: float = 60.0     # horizontal stand-off [m]
    radar_height_offset: float = 20.0    # placed this far below flight centre [m]
    radar_azimuth_deg: float = 0.0       # 0 = behind (-y); rotates the stand-off

    # --- kinematics ---
    rpm_scale: float = 6.0               # PX4 SITL ESC RPM correction (hover ~4500)

    # --- occlusion ---
    bvh_rebuild_every: int = 100         # rebuild body BVH every N pulses (~3cm drift)

    # ---- derived ----
    @property
    def wavelength(self) -> float:
        return self.c / self.f_c

    @property
    def k(self) -> float:
        """Wavenumber 2*pi/lambda."""
        return 2 * np.pi / self.wavelength

    @property
    def dt_radar(self) -> float:
        return 1.0 / self.prf

    @property
    def window_duration(self) -> float:
        return self.n_pulses * self.dt_radar

    @property
    def window_stride(self) -> float:
        # non-overlapping windows (1 window -> 1 spectrogram)
        return self.window_duration
