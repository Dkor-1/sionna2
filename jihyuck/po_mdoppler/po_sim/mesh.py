"""
Mesh assembly module ("매쉬 조립").

Loads the triangulated, outward-normal Phantom-4 mesh (drone body + 4 blades)
and places its facets into the world frame for a given pulse:

  - body  :  v_world = R_body @ v_local + pos_body
  - blade :  v_world = R_body @ R_spin(angle) @ v_local + pos_body + R_body @ offset

Per-face vertices (V0/V1/V2) are precomputed once at load so each pulse is a
handful of vectorised matmuls. Facet centres / outward normals / areas are then
derived directly from the world-frame triangle corners.
"""
import os

import numpy as np
from plyfile import PlyData


def load_ply(filepath):
    """Read a triangulated PLY -> (vertices (Nv,3) float64, faces (Nf,3) int)."""
    ply = PlyData.read(filepath)
    v = ply["vertex"]
    verts = np.column_stack([v["x"], v["y"], v["z"]]).astype(np.float64)
    faces = np.array([f[0] for f in ply["face"].data])
    return verts, faces


def facet_geometry(v0, v1, v2):
    """World-frame triangle corners -> (centres, outward normals, areas).

    Normals point outward because the mesh winding order was corrected
    (``Phantom4_Mesh_normals_out``); no per-facet sign flip is applied here.
    """
    centers = (v0 + v1 + v2) / 3.0
    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    normals = cross / (2.0 * areas[:, np.newaxis] + 1e-30)
    return centers, normals, areas


def spin_matrix(angle):
    """Rotation about the local +z axis (blade spin)."""
    ca, sa = np.cos(angle), np.sin(angle)
    return np.array([[ca, -sa, 0.0],
                     [sa,  ca, 0.0],
                     [0.0, 0.0, 1.0]])


class DroneMesh:
    """Static drone mesh with precomputed per-face vertices.

    Load once (``DroneMesh.load(mesh_dir)``) and reuse across every pulse; each
    worker process holds its own copy.
    """

    def __init__(self, body_v, body_f, blade_v_list, blade_f_list):
        self.body_v = body_v
        self.body_f = body_f
        self.blade_v_list = blade_v_list
        self.blade_f_list = blade_f_list

        # precompute face-corner vertex arrays for fast per-pulse transforms
        self.body_v0 = body_v[body_f[:, 0]]
        self.body_v1 = body_v[body_f[:, 1]]
        self.body_v2 = body_v[body_f[:, 2]]
        self.blade_v0_list = [bv[bf[:, 0]] for bv, bf in zip(blade_v_list, blade_f_list)]
        self.blade_v1_list = [bv[bf[:, 1]] for bv, bf in zip(blade_v_list, blade_f_list)]
        self.blade_v2_list = [bv[bf[:, 2]] for bv, bf in zip(blade_v_list, blade_f_list)]

    @classmethod
    def load(cls, mesh_dir):
        """Load ``drone_body.ply`` + ``blade_1..4.ply`` from *mesh_dir*."""
        body_v, body_f = load_ply(os.path.join(mesh_dir, "drone_body.ply"))
        blade_v_list, blade_f_list = [], []
        for i in range(1, 5):
            v, f = load_ply(os.path.join(mesh_dir, f"blade_{i}.ply"))
            blade_v_list.append(v)
            blade_f_list.append(f)
        return cls(body_v, body_f, blade_v_list, blade_f_list)

    @property
    def n_blades(self):
        return len(self.blade_v_list)

    @property
    def total_tris(self):
        return self.body_f.shape[0] + sum(f.shape[0] for f in self.blade_f_list)

    # ---- per-pulse world-frame assembly ----
    def body_facets(self, rot_mat, pos_body):
        """Body facets in the world frame -> (centres, normals, areas)."""
        v0 = (rot_mat @ self.body_v0.T).T + pos_body
        v1 = (rot_mat @ self.body_v1.T).T + pos_body
        v2 = (rot_mat @ self.body_v2.T).T + pos_body
        return facet_geometry(v0, v1, v2)

    def body_vertices_world(self, rot_mat, pos_body):
        """Full body vertex cloud in the world frame (for BVH construction)."""
        return (rot_mat @ self.body_v.T).T + pos_body

    def blade_facets(self, b_idx, angle_signed, rot_mat, pos_body, offset):
        """One rotor's facets in the world frame -> (centres, normals, areas).

        *angle_signed* already includes the per-rotor spin sign.
        """
        combined = rot_mat @ spin_matrix(angle_signed)
        offset_global = rot_mat @ offset
        v0 = (combined @ self.blade_v0_list[b_idx].T).T + pos_body + offset_global
        v1 = (combined @ self.blade_v1_list[b_idx].T).T + pos_body + offset_global
        v2 = (combined @ self.blade_v2_list[b_idx].T).T + pos_body + offset_global
        return facet_geometry(v0, v1, v2)

    def blade_vertices_world(self, b_idx, angle_signed, rot_mat, pos_body, offset):
        """One rotor's full vertex cloud in the world frame.

        Handy for drawing (``verts[mesh.blade_f_list[b_idx]]`` gives the
        per-face triangles) — symmetric with `body_vertices_world`.
        """
        combined = rot_mat @ spin_matrix(angle_signed)
        return (combined @ self.blade_v_list[b_idx].T).T + pos_body + rot_mat @ offset
