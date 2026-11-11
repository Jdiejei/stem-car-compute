"""p1_mill_lab: where in the fixed-grid milling does the 0.75 mm body gain mass?

    python ../.github/lab/p1_mill_lab.py <seed> <k> [mode]     (same arguments as p1_grid_lab)

Runs p1_grid_lab with param_body._mill_on traced: solid volume (sub-cell, mm3) after every
stage, on the car's grid and on the 0.5 mm mill grid.
"""
import copy
import runpy
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402

import machining  # noqa: E402
import param_body as pb  # noqa: E402
import unified_phi as up  # noqa: E402
from phi_updater import reinitialise_sdf  # noqa: E402


def vol(tag, geom, d):
    g = geom.phi.grid.astype(np.float64)
    v = np.clip(0.5 - g / d, 0.0, 1.0).sum() * (d * 1e3) ** 3
    print(f"LAB stage {tag:12s} d {d * 1e3:.2f} vol_mm3 {v:.1f} cells {int((g < 0).sum())} "
          f"origin_mm {np.round(np.asarray(geom.region.origin_m) * 1e3, 4).tolist()} shape {list(g.shape)}", flush=True)


def traced(g, fine_base):
    d, f = up.GRID_SPACING_M, pb.MILL_SPACING_MM / 1e3
    vol("in", g, d)
    with pb._spacing(pb.MILL_SPACING_MM):
        h = copy.deepcopy(fine_base)
        h.phi.grid = pb._resample(g.phi.grid, g.region, d, h.region, f)
        vol("up", h, f)
        h.phi.apply_hard_constraints()
        vol("up_hard", h, f)
        reinitialise_sdf(h.phi)
        h.phi.apply_hard_constraints()
        vol("up_reinit", h, f)
        mill_diag(h)
        rep = machining.make_machinable(h)
        rep["mill_spacing_mm"] = pb.MILL_SPACING_MM
        vol("milled", h, f)
        print(f"LAB rep {rep}", flush=True)
    g.phi.grid = pb._resample(h.phi.grid, h.region, f, g.region, d)
    vol("down", g, d)
    g.phi.apply_hard_constraints()
    vol("down_hard", g, d)
    reinitialise_sdf(g.phi)
    g.phi.apply_hard_constraints()
    vol("down_reinit", g, d)
    return rep


_mm = machining.make_machinable


def traced_mm(geom, *a, **k):          # the 0.5 mm car mills on its own grid: trace that too
    d = up.GRID_SPACING_M
    vol("mm_in", geom, d)
    mill_diag(geom)
    rep = _mm(geom, *a, **k)
    vol("mm_out", geom, d)
    return rep



def _wrap(name):
    f = getattr(pb, name)

    def w(geom, *a, **k):
        d = up.GRID_SPACING_M
        vol(name + "_in", geom, d)
        out = f(geom, *a, **k)
        vol(name + "_out", geom, d)
        print(f"LAB {name} returned {out} mass_g {sum(c.mass_kg for c in up.compute_mass_com(geom)) * 1e3:.4f}", flush=True)
        return out
    setattr(pb, name, w)


_wrap("_drop_islands")
_wrap("_close_pinches")


def profile(tag, geom):
    """Solid volume (mm3) on smooth hat nodes in x (20 mm), |y| (6.5 mm), z (10 mm): no bin-edge noise."""
    import json
    d, r = up.GRID_SPACING_M, geom.region
    fill = np.clip(0.5 - geom.phi.grid.astype(np.float64) / d, 0.0, 1.0) * (d * 1e3) ** 3
    W = []
    for ax, h, n in ((0, 20.0, 13), (1, 6.5, 6), (2, 10.0, 6)):
        c = (r.origin_m[ax] + np.arange(r.shape[ax]) * d) * 1e3
        c = np.abs(c) if ax == 1 else c
        W.append(np.clip(1.0 - np.abs(c[None, :] - (np.arange(n) * h)[:, None]) / h, 0.0, 1.0))
    T = np.einsum("ai,bj,ck,ijk->abc", W[0], W[1], W[2], fill)
    print(f"LAB prof {tag} d {d * 1e3:.2f} tot {fill.sum():.1f} T {json.dumps(np.round(T, 1).tolist())}", flush=True)


def _prof_wrap(mod, name):
    f = getattr(mod, name)

    def w(geom, *a, **k):
        profile(name + "_in", geom)
        out = f(geom, *a, **k)
        profile(name + "_out", geom)
        return out
    setattr(mod, name, w)


import exact_zones  # noqa: E402


def _bins(tag, mask, geom, d_mm, top=10):
    """Largest (x 10 mm, |y| 6.5 mm, z 10 mm) bins of a cell mask, as mm3."""
    ijk = np.argwhere(mask)
    if not len(ijk):
        print(f"LAB {tag} none", flush=True)
        return
    o = np.asarray(geom.region.origin_m) * 1e3
    P = o + ijk * d_mm
    key = (P[:, 0] // 10).astype(int) * 10000 + (np.abs(P[:, 1]) // 6.5).astype(int) * 100 + (P[:, 2] // 10).astype(int)
    u, c = np.unique(key, return_counts=True)
    best = np.argsort(-c)[:top]
    out = [(int(u[i] // 10000) * 10, round((int(u[i]) // 100 % 100) * 6.5, 1), int(u[i] % 100) * 10, round(float(c[i]) * d_mm ** 3, 1))
           for i in best]
    print(f"LAB {tag} total_mm3 {mask.sum() * d_mm ** 3:.1f} top(x,|y|,z,mm3) {out}", flush=True)


def mill_diag(geom):
    """machining.make_machinable's zone-growth loop, replayed without changing geom: which
    required-air cells the ball misses (and by how much), and where the zone is grown."""
    from scipy.ndimage import distance_transform_edt as edt
    phi = geom.phi
    d_mm = up.GRID_SPACING_M * 1e3
    r = machining.TOOL_R_MM / d_mm
    S = phi.grid < 0
    H = phi.hard_mask_air.copy()
    drilled = np.zeros_like(H)
    fh = getattr(geom, "fixed_hardware", None)
    if fh is not None and getattr(fh, "canister_void_mask", None) is not None:
        drilled = fh.canister_void_mask.astype(bool)
    drilled = drilled | up.model_block_slot_mask(geom.region)
    border = np.zeros_like(H)
    border[0, :, :] = border[-1, :, :] = True
    border[:, 0, :] = border[:, -1, :] = True
    border[:, :, 0] = border[:, :, -1] = True
    pocket = np.zeros_like(H)
    if fh is not None and getattr(fh, "halo_void_mask", None) is not None:
        pocket = fh.halo_void_mask.astype(bool)
    Hm = H & ~drilled & ~border & ~pocket
    A = ~S | H
    p = int(np.ceil(r)) + 2
    for it in range(4):
        Ap = np.pad(A, p, constant_values=True)
        C = edt(Ap) > r
        usable = np.zeros_like(C)
        for _n, axis, hi in machining.DIRECTIONS:
            usable |= machining._visible(C, axis, hi)
        dist = edt(~usable)[p:-p, p:-p, p:-p]          # cells, to the nearest usable ball centre
        miss = Hm & (dist > r)
        tol = {t: int((Hm & (dist > r + t)).sum()) for t in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)}
        print(f"LAB milldiag d {d_mm:.2f} iter {it} miss_cells_by_tolerance_cells {tol}", flush=True)
        if not miss.any():
            break
        _bins(f"milldiag iter {it} miss", miss, geom, d_mm)
        _bins(f"milldiag iter {it} miss_gt1cell", Hm & (dist > r + 1.0), geom, d_mm)
        add = machining._dilate(miss, r) & ~phi.hard_mask_solid
        _bins(f"milldiag iter {it} grown", add & ~A, geom, d_mm)
        A |= add


_stamp = None


def stamp_diag(g, X, Y, Z):
    """exact_zones.stamp, with the volume it removes split by the zone that removed it."""
    from bounding_volumes import default_rule_envelope
    ez = exact_zones
    d = up.GRID_SPACING_M
    d_mm = d * 1e3
    before = np.clip(0.5 - g.phi.grid.astype(np.float64) / d, 0.0, 1.0)
    out = _stamp(g, X, Y, Z)
    rem = (before - np.clip(0.5 - g.phi.grid.astype(np.float64) / d, 0.0, 1.0)) * d_mm ** 3
    aY = np.abs(Y)
    ref_A = g.landmarks["ref_plane_A_m"] * 1e3
    M = ez.MARGIN_MM
    names = ("envelope", "wheel_columns", "t79", "t851", "pocket", "block_slot", "halo_above", "halo_shadows")
    F = [ez.envelope_air(X, aY, Z, g.bv, default_rule_envelope(), d_mm) + M,
         ez.wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm) + M,
         ez.t79_zones(X, aY, Z, g.W_mm, g.x_front_mm) + M,
         ez.t851_cap(X, aY, Z, ref_A) + M,
         ez.halo_pocket_and_ballast(X, aY, Z, ref_A, g.d_halo_mm, d_mm, ballast=False) - 1e-6,
         ez.block_slot(X, aY, Z) - 1e-6,
         ez.halo_zones(X, aY, Z, ref_A, g.d_halo_mm, part="above") - 1e-6,
         ez.halo_zones(X, aY, Z, ref_A, g.d_halo_mm, ez._canister(g), part="shadows") + M]
    k = np.argmax(np.stack(F), axis=0)
    rear = (X >= 130.0) & (X <= 250.0)
    for i, n in enumerate(names):
        m = k == i
        w = rem * (m & rear)
        tot = w.sum()
        ym = (w * aY).sum() / tot if tot > 1e-9 else 0.0
        zm = (w * Z).sum() / tot if tot > 1e-9 else 0.0
        xm = (w * X).sum() / tot if tot > 1e-9 else 0.0
        print(f"LAB stampdiag d {d_mm:.2f} zone {n} removed_mm3 {rem[m].sum():.1f} rear_mm3 {tot:.1f} "
              f"rear_mean_x {xm:.1f} absy {ym:.1f} z {zm:.1f}", flush=True)
    hs = g.phi.hard_mask_solid
    print(f"LAB stampdiag d {d_mm:.2f} added_mm3 {-rem[rem < 0].sum():.1f} "
          f"forced_solid_in_zone_mm3 {(hs & (np.max(np.stack(F), axis=0) > 0)).sum() * d_mm ** 3:.1f}", flush=True)
    del F
    return out


_stamp = exact_zones.stamp
exact_zones.stamp = stamp_diag
_prof_wrap(pb, "_stamp_bore")
_prof_wrap(exact_zones, "stamp")

pb._mill_on = traced
machining.make_machinable = traced_mm
runpy.run_path(str(ROOT / ".github" / "lab" / "p1_grid_lab.py"), run_name="__main__")
