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
_prof_wrap(pb, "_stamp_bore")
_prof_wrap(exact_zones, "stamp")

pb._mill_on = traced
machining.make_machinable = traced_mm
runpy.run_path(str(ROOT / ".github" / "lab" / "p1_grid_lab.py"), run_name="__main__")
