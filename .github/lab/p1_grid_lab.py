"""p1_grid_lab: does the grid change the car? (BUILD_SPEC Step 4)

    python ../.github/lab/p1_grid_lab.py <seed> <k>    (from part5-simulation, on GitHub)

Carve one body at 1 mm with the cutter, carry the field to 0.75 mm and 0.5 mm (remap), and
finish each at the SAME fixed skin (no mass sizing, so the grid is the only change). Prints
mass, the body's extents, and the Richardson-extrapolated mass with its gap from 0.5 mm.
"""
import json
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(ROOT / ".github" / "lab"))
import numpy as np  # noqa: E402

from p1_carve_common import carve  # noqa: E402

seed, k = int(sys.argv[1]), int(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else ""             # nomill | block | block_nomill
MILL = "nomill" not in MODE
lay, src, verdicts = carve(seed, k, 1.0)
if MODE.startswith("block"):                 # the uncut block: no carved shape to carry across grids
    import cutter
    src, verdicts = cutter.start_block(lay, 1.0), []
rows = {}
for s in (1.0, 0.75, 0.5):
    import coarse
    import param_body as pb
    import unified_phi as up
    coarse.use_spacing(s)
    dst = up.remap_geometry(src) if (s != 1.0 or "selfremap" in MODE) else src   # selfremap: 1.0 carried too
    b = pb.build(lay["W"], lay["x_front"], lay["d_halo"], pb.BodyParams(), skin_offset_mm=0.0,
                 field_mm=dst.phi.grid * 1e3, machinable=MILL)
    comps = up.compute_mass_com(b)
    m = sum(c.mass_kg for c in comps) * 1e3
    com = [sum(c.mass_kg * getattr(c, a) for c in comps) / (m / 1e3) * 1e3 for a in ("com_x_m", "com_z_m")]
    S = b.phi.grid < 0
    r, d = b.region, up.GRID_SPACING_M
    idx = [np.where(S.any(axis=tuple(a for a in range(3) if a != ax)))[0] for ax in range(3)]
    ext = [float((ix.max() - ix.min() + 1) * d * 1e3) for ix in idx]
    # where the mass sits: per 10 mm along x and per 5 mm up z (sub-cell fill x density), to
    # find which part of the body the grids disagree on
    fill = np.clip(0.5 - b.phi.grid.astype(np.float64) / d, 0.0, 1.0)
    rho = up.density_field(b)
    w = fill * rho * d ** 3 * 1e3
    xc = (r.origin_m[0] + np.arange(r.shape[0]) * d) * 1e3
    zc = (r.origin_m[2] + np.arange(r.shape[2]) * d) * 1e3
    sx = np.bincount(np.floor(xc / 10).astype(int), weights=w.sum(axis=(1, 2)), minlength=26)[:26]
    sz = np.bincount(np.floor(zc / 5).astype(int), weights=w.sum(axis=(0, 1)), minlength=12)[:12]
    print(f"LAB slabs k {k} s {s} x10 {np.round(sx, 3).tolist()} z5 {np.round(sz, 3).tolist()}", flush=True)
    from geometry_contract import DENSITY_BODY_KGM3 as _rho_f
    mesh_g = 2 * abs(up.extract_half_surface(b).volume) * _rho_f * 1e3       # the milled mesh, foam only
    print(f"LAB meshmass k {k} s {s} field_g {m:.4f} mesh_g {mesh_g:.4f}", flush=True)
    rows[s] = {"mass_g": m, "extent_mm": ext, "com_mm": com, "mesh_g": mesh_g}
    print(f"LAB {json.dumps({'seed': seed, 'k': k, 'spacing_mm': s, 'mass_g': round(m, 4), 'com_x_z_mm': [round(v, 3) for v in com], 'extent_mm': ext})}", flush=True)
# Richardson: m(h) = m0 + C h^p through the three points, p by bisection
h = np.array([1.0, 0.75, 0.5])
mm = np.array([rows[x]["mass_g"] for x in h])
def resid(p):
    C = (mm[0] - mm[2]) / (h[0] ** p - h[2] ** p)
    return mm[1] - (mm[2] + C * (h[1] ** p - h[2] ** p))
p_lo, p_hi, p = 0.2, 6.0, None
if resid(p_lo) * resid(p_hi) < 0:
    for _ in range(60):
        p = 0.5 * (p_lo + p_hi)
        p_lo, p_hi = (p, p_hi) if resid(p_lo) * resid(p) > 0 else (p_lo, p)
m0 = None
if p is not None:
    C = (mm[0] - mm[2]) / (h[0] ** p - h[2] ** p)
    m0 = float(mm[2] - C * h[2] ** p)
spread = float((mm.max() - mm.min()) / mm[2] * 100)
print("LAB " + json.dumps({"seed": seed, "k": k, "summary": True, "mill": MILL, "spread_pct": round(spread, 3),
                           "order_p": None if p is None else round(p, 2),
                           "richardson_mass_g": None if m0 is None else round(m0, 4),
                           "grid_error_g": None if m0 is None else round(float(mm[2] - m0), 4),
                           "com_shift_mm": round(max(float(np.hypot(*(np.array(rows[a]["com_mm"]) - np.array(rows[0.5]["com_mm"])))) for a in rows), 3),
                           "cuts": verdicts}), flush=True)
