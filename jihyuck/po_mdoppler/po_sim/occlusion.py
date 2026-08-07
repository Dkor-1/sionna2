"""
Occlusion module (Embree ray-casting).

Normal-visibility (cosθ > 0) alone lets a facet contribute even when another
part of the airframe is between it and the radar. This module resolves true
line-of-sight against the body mesh via an Embree BVH:

  - `self_occlusion_mask` : does the body occlude its own visible facets?
  - `body_block_mask`     : does the body block a visible blade facet?

The BVH is built from the body only (the dominant occluder) and, per the batch
engine, reused for a block of pulses since the drone drifts only ~cm over that span.
"""
import numpy as np
import trimesh
from trimesh.ray.ray_pyembree import RayMeshIntersector

# a hit closer than (facet range - this) counts as blocking [m]
OCCLUSION_EPS = 0.002


def build_body_bvh(mesh, rot_mat, pos_body):
    """Embree intersector over the body mesh placed in the world frame."""
    body_w = mesh.body_vertices_world(rot_mat, pos_body)
    tm = trimesh.Trimesh(vertices=body_w, faces=mesh.body_f, process=False)
    return RayMeshIntersector(tm)


def self_occlusion_mask(bvh, centers, vis_idx, radar_pos):
    """Body self-occlusion.

    For each normal-visible body facet (index into the body mesh given by
    *vis_idx*), cast radar -> facet-centre and keep it only if the first hit is
    that same facet (or nothing). Returns a bool mask aligned with *vis_idx*.
    """
    origins = np.tile(radar_pos, (len(vis_idx), 1))
    dirs = centers[vis_idx] - origins
    td = np.linalg.norm(dirs, axis=1)
    first_hit = bvh.intersects_first(origins, dirs / td[:, np.newaxis])
    return (first_hit == vis_idx) | (first_hit < 0)


def body_block_mask(bvh, centers_b, vb_idx, radar_pos):
    """Blade-by-body occlusion.

    For each normal-visible blade facet (*vb_idx* indexes the blade facets), cast
    radar -> facet-centre and drop it if the body is hit closer than the facet.
    Returns a `keep` bool mask aligned with *vb_idx*.
    """
    origins_b = np.tile(radar_pos, (len(vb_idx), 1))
    dirs_b = centers_b[vb_idx] - origins_b
    td_b = np.linalg.norm(dirs_b, axis=1)
    locs, iray, _ = bvh.intersects_location(
        origins_b, dirs_b / td_b[:, np.newaxis], multiple_hits=False)
    keep = np.ones(len(vb_idx), dtype=bool)
    if len(locs) > 0:
        hit_dist = np.linalg.norm(locs - origins_b[iray], axis=1)
        blocked = hit_dist < (td_b[iray] - OCCLUSION_EPS)
        keep[iray[blocked]] = False
    return keep
