"""
Physical-optics scattering module ("PO 전용").

The radar return of one pulse is the coherent sum over visible facets:

    S = Σ_i  Γ_i(θ_i; er, σ) · A_i·cosθ_i / R_i² · exp(-j·2k·R_i)

This module provides the three reusable primitives that make up that sum:

  - `fresnel_te_vec` : angle-dependent reflection coefficient Γ(θ; er, σ)
  - `visible_facets` : normal-visibility test (cosθ > 0) + range/incidence
  - `geometry_term`  : the material-free factor  A·cosθ/R² · exp(-j·2k·R)

Splitting Γ from the geometry lets one geometry pass serve every blade material
(Γ is a cheap per-facet reweighting), which is why the ablation axis is nearly free.
"""
import numpy as np

EPS0 = 8.854e-12  # vacuum permittivity [F/m]


def fresnel_te_vec(cos_i, er, sigma, f_c):
    """TE Fresnel reflection coefficient Γ for an array of incidence cosines.

    Conductors (large σ) approach |Γ| = 1; dielectrics (σ ~ 0) follow the
    standard formula. *er* is the relative permittivity, *sigma* the conductivity.
    """
    omega = 2 * np.pi * f_c
    er_c = er - 1j * sigma / (omega * EPS0)          # complex permittivity
    ci = np.clip(cos_i, 0, 1)
    sq = np.sqrt(er_c - (1.0 - ci ** 2))
    return (ci - sq) / (ci + sq)


def visible_facets(centers, normals, radar_pos):
    """Normal-visibility of facets toward the radar.

    Returns (visible, dist, cos_theta):
      - visible   : bool mask, cosθ > 0 (facet faces the radar)
      - dist      : facet-centre -> radar range R
      - cos_theta : incidence cosine (also the projected-area factor)
    """
    to_radar = radar_pos - centers
    dist = np.linalg.norm(to_radar, axis=1)
    cos_theta = np.sum(normals * (to_radar / dist[:, np.newaxis]), axis=1)
    visible = cos_theta > 0
    return visible, dist, cos_theta


def geometry_term(areas, cos_theta, dist, k):
    """Material-free PO factor  A·cosθ / R² · exp(-j·2k·R).

    Multiply by a facet's Fresnel Γ to get its complex contribution. Inputs are
    expected to be already sliced to the facets of interest (e.g. visible ones).
    """
    return areas * cos_theta / (dist ** 2) * np.exp(-1j * 2 * k * dist)
