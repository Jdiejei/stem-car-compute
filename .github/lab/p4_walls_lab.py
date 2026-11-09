"""Part 4 lab (Step 6): how thin is each file the team makes? Builds the reference cars, then
for every printed part measures wall thickness at 4000 surface points: a ray from each point
straight into the part, to where it comes out. Prints the thinnest, the 1st and 5th
percentiles, and where the thinnest wall is. Run from part5-simulation."""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, ".")
import paths  # noqa: F401,E402
import run_car  # noqa: E402

CARS = {"start": ["--body-json", "{}"],
        "round2": ["--body-json", Path("checks/round2_car.json").read_text()]}


def walls(m, n=4000):
    pts, fi = trimesh.sample.sample_surface(m, n, seed=4)
    d = -m.face_normals[fi]
    o = pts + d * 1e-3
    loc, ray, _ = m.ray.intersects_location(o, d, multiple_hits=False)
    t = np.full(len(pts), np.nan)
    t[ray] = np.linalg.norm(loc - o[ray], axis=1) + 1e-3
    return pts, t


out = {}
for car, args in CARS.items():
    run_car.main(["--out", f"../out/{car}"] + args)
    for f in sorted(Path(f"../out/{car}/manufacture").glob("*.stl")):
        m = trimesh.load(str(f), force="mesh")
        pts, t = walls(m)
        ok = ~np.isnan(t)
        i = np.nanargmin(t)
        row = {"thinnest_mm": float(t[i]), "p1_mm": float(np.nanpercentile(t, 1)),
               "p5_mm": float(np.nanpercentile(t, 5)), "median_mm": float(np.nanmedian(t)),
               "thinnest_at": np.round(pts[i], 1).tolist(), "rays_missed": int((~ok).sum()),
               "under_1mm_pct": float(100 * np.nanmean(t < 1.0)), "under_0_8mm_pct": float(100 * np.nanmean(t < 0.8))}
        out[f"{car}/{f.name}"] = row
        print(f"{car:7s} {f.name:30s} thinnest {row['thinnest_mm']:6.2f}  p1 {row['p1_mm']:6.2f}  "
              f"p5 {row['p5_mm']:6.2f}  median {row['median_mm']:6.2f}  <1mm {row['under_1mm_pct']:5.1f}%  "
              f"<0.8mm {row['under_0_8mm_pct']:5.1f}%  at {row['thinnest_at']}")
Path("../out/walls.json").write_text(json.dumps(out, indent=1))
