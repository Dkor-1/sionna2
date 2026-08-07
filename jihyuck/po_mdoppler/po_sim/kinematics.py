"""
Kinematics / maneuvering module ("기동").

Turns PX4 flight telemetry into the per-pulse state the PO kernel needs:

  - position   : linear interpolation (NED -> Z-up)
  - attitude   : SLERP over the quaternion log
  - blade angle: cumulative integral of (ESC RPM x rpm_scale), interpolated

The radar is a fixed monostatic ground station whose position is derived from
the flight centroid plus the stand-off offsets in `SimConfig`.
"""
import os

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp

# PX4 CSV column layout
POS_COLS = ["x", "y", "z"]
QUAT_COLS = ["q[1]", "q[2]", "q[3]", "q[0]"]          # -> scipy [x, y, z, w]
ESC_COLS = ["esc[0].esc_rpm", "esc[1].esc_rpm", "esc[2].esc_rpm", "esc[3].esc_rpm"]


class Flight:
    """Interpolators for one flight (one grade). Build with `load_flight`."""

    def __init__(self, pos_interp, rot_interp, blade_angles_interp, t_max,
                 flight_center):
        self.pos_interp = pos_interp                  # t -> (3,) position [Z-up]
        self.rot_interp = rot_interp                  # t -> Rotation (SLERP)
        self.blade_angles_interp = blade_angles_interp  # t -> (4,) cum. blade angle
        self.t_max = t_max                            # last commonly-valid time [s]
        self.flight_center = flight_center            # (3,) mean position [Z-up]


def load_flight(data_dir, cfg):
    """Load clean_{position,attitude,esc}.csv from *data_dir* and build a `Flight`.

    ``cfg.rpm_scale`` is baked into the blade-angle integral here (PX4 SITL ESC
    output runs low, so the micro-Doppler is scaled up to a realistic hover RPM).
    """
    df_pos = pd.read_csv(os.path.join(data_dir, "clean_position.csv"))
    df_att = pd.read_csv(os.path.join(data_dir, "clean_attitude.csv"))
    df_esc = pd.read_csv(os.path.join(data_dir, "clean_esc.csv"))
    t_max = min(df_pos.time_sec.max(), df_att.time_sec.max(), df_esc.time_sec.max())

    # position: NED -> Z-up (flip z), linear interp
    pos_xyz = df_pos[POS_COLS].to_numpy().copy()
    pos_xyz[:, 2] = -pos_xyz[:, 2]
    pos_interp = interp1d(df_pos["time_sec"].to_numpy(), pos_xyz,
                          axis=0, fill_value="extrapolate")

    # attitude: quaternion SLERP
    quats = df_att[QUAT_COLS].to_numpy()
    rot_interp = Slerp(df_att["time_sec"].to_numpy(), R.from_quat(quats))

    # blade angle: cumulative integral of angular velocity (RPM -> rad/s)
    t_esc = df_esc["time_sec"].to_numpy()
    rpm_raw = df_esc[ESC_COLS].to_numpy() * cfg.rpm_scale
    omega_raw = rpm_raw * (2 * np.pi / 60)
    dt_esc = np.diff(t_esc, prepend=t_esc[0])
    cum_angles_esc = np.cumsum(omega_raw * dt_esc[:, np.newaxis], axis=0)
    blade_angles_interp = interp1d(t_esc, cum_angles_esc,
                                   axis=0, fill_value="extrapolate")

    flight_center = np.mean(pos_xyz, axis=0)
    return Flight(pos_interp, rot_interp, blade_angles_interp, t_max, flight_center)


def radar_position(flight_center, cfg):
    """Monostatic ground-station position from the flight centroid + offsets.

    azimuth 0 places the radar behind the flight (-y); it rotates the horizontal
    stand-off around the centroid.
    """
    az = np.deg2rad(cfg.radar_azimuth_deg)
    return np.array([
        flight_center[0] + cfg.radar_range_offset * np.sin(az),
        flight_center[1] - cfg.radar_range_offset * np.cos(az),
        flight_center[2] - cfg.radar_height_offset,
    ])


def window_starts(flight, cfg, max_windows=0):
    """Non-overlapping window start times covering the usable flight span."""
    starts = np.arange(cfg.t_skip, flight.t_max - cfg.window_duration,
                       cfg.window_stride)
    if max_windows > 0:
        starts = starts[:max_windows]
    return starts


def window_poses(flight, t_start, cfg):
    """Per-pulse (positions, rot_matrices, blade_angles) for one window.

    Returns arrays of shape (n_pulses, 3), (n_pulses, 3, 3), (n_pulses, 4).
    """
    t_radar = t_start + np.arange(cfg.n_pulses) * cfg.dt_radar
    positions = flight.pos_interp(t_radar)
    rot_matrices = flight.rot_interp(t_radar).as_matrix()
    blade_angles = flight.blade_angles_interp(t_radar)
    return positions, rot_matrices, blade_angles
