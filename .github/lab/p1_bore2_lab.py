"""p1_bore2_lab: where on a carved car is the chamber's widest point?

    python ../.github/lab/p1_bore2_lab.py <variant>    (from part5-simulation, on GitHub)

variants: block | cut1. Builds the car through run_car, then cuts the machined body (the
file the referee reads) and Part 1's own body_half at the referee's 7 depths, and prints
each hole's centroid, narrowest and widest size and where its farthest points are.
"""
import json
import math
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402

variant = sys.argv[1]
LAY = {"W": 120.3, "x_front": 46.0, "d_halo": 43.72}


def holes_report(tag, mesh_mm):
    import legality as lg
    x_back = float(mesh_mm.bounds[1, 0])
    for x in np.linspace(x_back - 47.0, x_back - 0.5, 32):
        hs = lg._x_section_holes(mesh_mm, x)
        for q in sorted(hs, key=lambda q: -q.area)[:2]:
            c = q.centroid
            pts = np.asarray(q.exterior.coords)
            r = np.hypot(pts[:, 0] - c.x, pts[:, 1] - c.y)
            far = np.argsort(-r)[:4]
            print(f"LAB {variant} {tag} x {x:.1f} hole area {q.area:.1f} centre ({c.x:.2f},{c.y:.2f}) "
                  f"thick {lg._thickness(q):.3f} widest {2 * r.max():.3f} n {len(pts)} far "
                  + " ".join(f"({pts[i, 0]:.2f},{pts[i, 1]:.2f} r{r[i]:.2f})" for i in far), flush=True)


import cutter  # noqa: E402
import run_car as rc  # noqa: E402
import trimesh  # noqa: E402

out = Path(tempfile.mkdtemp())
if variant == "block":
    npy = "block"
else:
    from unified_phi import extract_half_surface
    g = cutter.start_block(LAY, 1.0)
    v = np.asarray(extract_half_surface(g).vertices)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g, _ = cutter.cut(g, np.full(len(v), 0.3), type("M", (), {"vertices": v})(), step_m=1.0)
    cutter.save_field(g, out / "carved.npy")
    npy = str(out / "carved.npy")
S = rc.main(["--out", str(out), "--skin-mm", "0", "--support", "beam", "--phi-npy", npy])
print(f"LAB {variant} referee {json.dumps(S['legality']['checks'].get('T5.1_diameter_max'))}", flush=True)
f = S["manufactured"]["machined_body"]["file"]
holes_report("machined", trimesh.load(f, force="mesh"))
half = trimesh.load(out / "body_half.stl", force="mesh")
half.apply_scale(1e3)                                          # metres -> mm
holes_report("body_half", half)
