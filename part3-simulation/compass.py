"""The compass: race-time slope per surface vertex, and its file (BUILD_SPEC 6, 12.3, 12.8).

Convention: n is the OUTWARD normal of the solid (+ grows the car). For a right-half vertex
i with area A_i at (x_i, z_i), moving it (and its mirror) out by d changes
    drag  by dD_dn[i] * d * A_i      (whole car, N)
    lift  by dL_dn[i] * d * A_i      (whole car, N, + up)
    mass  by 2 * rho * d * A_i       (both halves), at (x_i, z_i)
Part 1 then re-sizes the skin (a uniform outward move over the whole body) to put the mass
back on target. That move costs drag, lift and centre-of-mass position everywhere, so the
whole unconstrained slope is projected:
    g_i = dT/dD dD_dn[i] + dT/dL dL_dn[i]
          + 2 rho (dT/dm + (dT/dx_com x_i + dT/dh_com z_i) / M)
    dT_dn[i] = g_i - <g>_A        (s per m per m^2)
Raw mass and the centre of mass's own position drop out in the projection (constants), so
only the axis directions matter: x rearward and z up, the same in the STL and in Part 2's
mass report. The slopes dT/d... are Part 2's (stopwatch.race dT_d), never typed in.
Part 1 moves along -dT_dn (it treats + as grow).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

QUALITY_KEYS = ("primal_converged", "adjoint_converged", "unmatched_frac", "median_match_m", "method")


def _project(g, A) -> np.ndarray:
    """Constant mass: the skin re-sizing takes the area-weighted mean back off."""
    return g - np.sum(g * A) / np.sum(A)


def mass_slope(points_m, area_m2, rho_kgm3: float, mass_kg: float, dT_d: dict) -> np.ndarray:
    """Constant-mass race-time slope of the mass and centre-of-mass terms, s per m per m^2."""
    P = np.asarray(points_m)
    g = 2.0 * rho_kgm3 * (dT_d["car_weight_kg"]
                          + (dT_d["com_x_m"] * P[:, 0] + dT_d["com_height_m"] * P[:, 2]) / mass_kg)
    return _project(g, np.asarray(area_m2))


def race_slope(dD_dn, dL_dn, dT_d: dict, points_m, area_m2, rho_kgm3: float, mass_kg: float) -> np.ndarray:
    """dT_dn per vertex under the constant-mass rule. The skin re-sizing moves the WHOLE
    surface, so it changes drag and lift too, not only the mass: the aero part is
    projected like the mass part (12.3 states it for the mass part only)."""
    A = np.asarray(area_m2)
    aero = dT_d["drag_20_n"] * np.asarray(dD_dn) + dT_d["lift_20_n"] * np.asarray(dL_dn)
    return _project(aero, A) + mass_slope(points_m, A, rho_kgm3, mass_kg, dT_d)


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
