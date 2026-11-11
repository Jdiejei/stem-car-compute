"""Skin weight w per surface vertex: how far Part 1's mass sizing really moves each point.

Part 1 (2026-11-09): sizing is one uniform offset of the field, but rule zones, block faces,
milling and stamps hold parts of the surface still. Measured as Part 1 advised: build the same
car at two fixed skins s and s + ds (param_body.build(..., skin_offset_mm=...)), sample both
fields at the vertices of the first body_half.stl, w = -(phi_{s+ds} - phi_s) / ds (the field
falls by ds where the surface moves out by ds). Milling can jump between skins, so the mass
change must match density x sum(w A) x ds; if not, s is shifted and the pair redone.
compass.race_slope takes w as skin_weight.
    python skin_weight.py <seed> <out_dir>        (run from part5-simulation; GitHub only)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path[:0] = [".", "checks", str(Path(__file__).resolve().parents[1])]
import pattern, solver                 # noqa: E402,F401  (these put the other parts on the path)
import run_car as rc                   # noqa: E402
import param_body as pb                # noqa: E402
import unified_phi as up               # noqa: E402
import compass                         # noqa: E402
from scipy.interpolate import RegularGridInterpolator  # noqa: E402

DS_MM = 0.1
seed, out = int(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
car = solver.random_start(seed)
a = rc.parse_args(["--out", str(out / "base"), "--body-json", json.dumps(car["params"])])
(out / "base").mkdir(exist_ok=True)
geom, info, asm = rc.build_car(a, out / "base", **rc.part4_kwargs(a))
s0 = float(info["build"].get("skin_offset_mm") or geom.build_report["skin_offset_mm"])
field = geom.phi.grid * 1e3          # the sized body's own field, mm, as a carved field


def at_skin(s):
    g = pb.build(a.W, a.x_front, a.d_halo, pb.BodyParams.from_dict(json.loads(a.body_json)),
                 skin_offset_mm=s, field_mm=field)
    return g, sum(c.mass_kg for c in up.compute_mass_com(g))


def sampler(g):
    r = g.region
    import geometry_contract
    axes = [r.origin_m[i] + np.arange(r.shape[i]) * geometry_contract.GRID_SPACING_M for i in range(3)]
    return RegularGridInterpolator(axes, np.asarray(g.phi.grid, float), bounds_error=False, fill_value=None)


rho = compass.body_density_kgm3()
for shift in (0.0, 0.03, -0.03, 0.06):
    s = s0 + shift
    g1, m1 = at_skin(s)
    g2, m2 = at_skin(s + DS_MM)
    half = up.extract_half_surface(g1)
    V = np.asarray(half.vertices)
    A = np.zeros(len(V))
    np.add.at(A, half.faces.ravel(), np.repeat(half.area_faces / 3.0, 3))
    w = -(sampler(g2)(V) - sampler(g1)(V)) / (DS_MM * 1e-3)
    dm_pred = 2 * rho * np.sum(w * A) * DS_MM * 1e-3      # both halves
    ok = abs((m2 - m1) - dm_pred) <= 0.15 * abs(dm_pred)
    print(f"LAB car {seed} skin {s:.3f} mm: w p5 p50 p95 {np.round(np.percentile(w, [5, 50, 95]), 3).tolist()},"
          f" held (w < 0.2) {np.mean(w < 0.2):.2f} of vertices / {np.sum(A[w < 0.2]) / np.sum(A):.2f} of area;"
          f" mass change {1e3 * (m2 - m1):.4f} g vs density x moved area {1e3 * dm_pred:.4f} g"
          f" -> {'consistent' if ok else 'JUMP (milling), shifting the skin'}", flush=True)
    if ok:
        np.savez(out / f"skin_weight_{seed}.npz", vertices=V, area=A, w=w, skin_mm=s, ds_mm=DS_MM)
        break
else:
    raise SystemExit("no consistent skin pair found: milling jumps at every skin tried")
