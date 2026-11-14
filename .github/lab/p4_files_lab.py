"""Part 4 lab: measure the kept files of rejected cars (p4_assembly keep_files).
Rear support: every piece's bounds and reach from the rear axle; front assembly: where
its thin (< 5 deg) triangles are, per piece and per source file (nose.stl, fwing.stl)."""
import glob
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import trimesh

RUNS = {"44130": 43604931818, "50002": 43605062909, "50135": 43605280301,
        "50250": 43605313729, "50323": 43605345488}
REPO = os.environ.get("GITHUB_REPOSITORY")
OUT = Path("../out/files")


def sliver_frac(m):
    a = m.face_angles.min(axis=1)
    return float((a < np.radians(5)).mean()), a < np.radians(5)


for car, run in RUNS.items():
    d = OUT / car
    subprocess.run(["gh", "run", "download", str(run), "-R", REPO, "-D", str(d)], check=False)
    asm = glob.glob(str(d / "**" / "assembly.json"), recursive=True)
    if not asm:
        print(f"CAR {car}: no kept files", flush=True)
        continue
    folder = Path(asm[0]).parent
    a = json.loads(Path(asm[0]).read_text())
    xr = a["x_front_mm"] + a["W_mm"]
    R = a.get("wheel_design", {}).get("rear", {}).get("R_mm", 14.12)
    za = R - 0.3
    print(f"CAR {car}: x_front {a['x_front_mm']:.2f} W {a['W_mm']:.2f} rear axle x {xr:.2f} z {za:.2f} R {R}", flush=True)
    s = trimesh.load(folder / "supports.stl", force="mesh")
    for i, p in enumerate(s.split(only_watertight=False)):
        v = p.vertices * 1e3
        rear = abs(v[:, 0].mean() - xr) < 30
        reach = np.hypot(v[:, 0] - xr, v[:, 2] - za).max() if rear else float("nan")
        print(f"  support piece {i}: bounds mm {np.round(p.bounds * 1e3, 2).tolist()} closed {p.is_watertight} "
              f"faces {len(p.faces)} rear {rear} reach_from_rear_axle {reach:.2f}", flush=True)
    for name in ("printed_front_assembly.stl", "nose.stl", "fwing.stl"):
        f = folder / name
        if not f.exists():
            continue
        m = trimesh.load(f, force="mesh")
        frac, bad = sliver_frac(m)
        c = m.triangles_center[bad] if bad.any() else np.zeros((0, 3))
        print(f"  {name}: faces {len(m.faces)} slivers {100 * frac:.2f} % bounds {np.round(m.bounds, 2).tolist()}"
              + (f" sliver box {np.round([c.min(0), c.max(0)], 2).tolist()}" if len(c) else ""), flush=True)
        for j, p in enumerate(m.split(only_watertight=False)):
            fr, _ = sliver_frac(p)
            print(f"    piece {j}: faces {len(p.faces)} slivers {100 * fr:.2f} % bounds {np.round(p.bounds, 2).tolist()}", flush=True)
