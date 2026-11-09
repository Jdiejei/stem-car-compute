"""The compass: race-time slope per surface vertex, and its file (BUILD_SPEC 6, 12.3, 12.8).

Convention: n is the OUTWARD normal of the solid (+ grows the car). For a right-half vertex
i with area A_i at (x_i, z_i), moving it (and its mirror) out by d changes
    drag  by dD_dn[i] * d * A_i      (whole car, N)
    lift  by dL_dn[i] * d * A_i      (whole car, N, + up)
    mass  by 2 * rho * d * A_i       (both halves), at (x_i, z_i)
Part 1 then re-sizes the skin to put the mass back on target: one offset u of the field,
which moves vertex i out by w_i * u. w_i is 1 on the free surface and about 0 where a rule
zone or a block face holds the surface (Part 1, 2026-11-09: param_body.make offsets the
field, then the rule masks, milling and stamps act on it). Constant mass gives
u = -sum(d A) / sum(w A), so the whole unconstrained slope is projected with weights w:
    g_i = dT/dD dD_dn[i] + dT/dL dL_dn[i]
          + 2 rho (dT/dm + (dT/dx_com x_i + dT/dh_com z_i) / M)
    dT_dn[i] = g_i - <g>_wA,   <g>_wA = sum(g w A) / sum(w A)      (s per m per m^2)
Raw mass and the centre of mass's own position drop out (constants), so only the axis
directions matter: x rearward and z up, the same in Part 1's STL and Part 2's mass report.
The slopes dT/d... are Part 2's (stopwatch.race dT_d) and rho is Part 1's
(geometry_contract.get_density("main_body")); never typed in. w is measured from Part 1's
own sizing (two skins, per-vertex move / skin change); w = 1 everywhere is the free-surface
idealisation. Part 1 moves along -dT_dn (cutter.cut negates it).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

QUALITY_KEYS = ("primal_converged", "adjoint_converged", "unmatched_frac", "median_match_m", "method")


def _project(g, A, w=None) -> np.ndarray:
    """Constant mass: the skin re-sizing takes the (skin-weighted) area mean back off."""
    wA = np.asarray(A) * (1.0 if w is None else np.asarray(w))
    return g - np.sum(g * wA) / np.sum(wA)


def mass_slope(points_m, area_m2, rho_kgm3: float, mass_kg: float, dT_d: dict, skin_weight=None) -> np.ndarray:
    """Constant-mass race-time slope of the mass and centre-of-mass terms, s per m per m^2."""
    P = np.asarray(points_m)
    g = 2.0 * rho_kgm3 * (dT_d["car_weight_kg"]
                          + (dT_d["com_x_m"] * P[:, 0] + dT_d["com_height_m"] * P[:, 2]) / mass_kg)
    return _project(g, area_m2, skin_weight)


def race_slope(dD_dn, dL_dn, dT_d: dict, points_m, area_m2, rho_kgm3: float, mass_kg: float,
               skin_weight=None) -> np.ndarray:
    """dT_dn per vertex under the constant-mass rule. The skin re-sizing moves the surface,
    so it changes drag and lift too, not only the mass: the aero part is projected like the
    mass part (12.3 states it for the mass part only)."""
    aero = dT_d["drag_20_n"] * np.asarray(dD_dn) + dT_d["lift_20_n"] * np.asarray(dL_dn)
    return (_project(aero, area_m2, skin_weight)
            + mass_slope(points_m, area_m2, rho_kgm3, mass_kg, dT_d, skin_weight))


def body_density_kgm3() -> float:
    import geometry_contract
    return float(geometry_contract.get_density("main_body"))


def save(path, points, normals, area, dD_dn, dL_dn, dT_dn, quality: dict) -> None:
    n = len(points)
    assert all(len(v) == n for v in (normals, area, dD_dn, dL_dn, dT_dn)), "every field needs one value a vertex"
    assert set(QUALITY_KEYS) <= set(quality) and quality["method"] in ("adjoint", "measured"), quality
    nn = np.linalg.norm(normals, axis=1)
    assert np.allclose(nn, 1.0, atol=1e-6), "normals must be unit vectors"
    np.savez(Path(path), points=np.asarray(points, float), normals=np.asarray(normals, float),
             area=np.asarray(area, float), dD_dn=np.asarray(dD_dn, float), dL_dn=np.asarray(dL_dn, float),
             dT_dn=np.asarray(dT_dn, float), quality=np.array(quality, dtype=object))


def load(path) -> dict:
    z = np.load(Path(path), allow_pickle=True)
    out = {k: z[k] for k in z.files}
    out["quality"] = out["quality"].item()
    return out
