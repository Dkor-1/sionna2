"""
po_sim — Physical-Optics micro-Doppler simulator for a quad-rotor drone.

Modules
-------
  mesh        : PLY load + body/blade world-frame assembly   ("매쉬 조립")
  kinematics  : PX4 telemetry -> per-pulse pose + blade angle ("기동")
  physics     : Fresnel Γ + PO facet scattering primitives    ("PO 전용")
  occlusion   : Embree ray-casting visibility masks
  engine      : pulse decomposition + windowed multiprocessing driver

`mesh`, `kinematics`, and `physics` are light. `engine`/`occlusion` pull in
trimesh + pyembree, so import those explicitly when you need them:

    from po_sim.engine import run_generation, SceneSpec
"""
from . import physics, mesh, kinematics  # noqa: F401

__all__ = ["physics", "mesh", "kinematics"]
