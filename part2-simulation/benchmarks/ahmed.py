"""Ahmed body benchmark: the cars' CFD on a shape with published wind-tunnel drag.

Experiment: S.R. Ahmed, G. Ramm, G. Faltin, "Some salient features of the
time-averaged ground vehicle wake", SAE 840300 (1984). 60 m/s, Re = 4.29e6 on
length, still ground plate. Geometry as given by ERCOFTAC AC1-05:
length 1.044 m, width 0.389 m, height 0.288 m; the rounded fore-body (first
100 mm) from Ahmed's own surface table (ahmed_front.dat, ERCOFTAC); sharp
edges behind it; slant 0.222 m long measured ALONG the slant, at phi; body
50 mm above the ground.

The body is convex, so it is the convex hull of the fore-body table and the
rear corners.
ponytail: stilts (4 x 30 mm) left out; add them if the residual error points there.

    python benchmarks/ahmed.py --slant 35 --res medium --iters 2000 --np 4 --out out
"""
import argparse
import dataclasses
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

L, W, H, LS, GAP = 1.044, 0.389, 0.288, 0.222, 0.050
A_REF = W * H            # 0.112 m^2, full-body reference area used by Ahmed
RE = 4.29e6              # on length, as in the experiment
RHO = 1.225


FRONT = Path(__file__).with_name("ahmed_front.dat")


def half_body(slant_deg: float):
    """Closed trimesh of the right half (y >= 0), metres, ground at z = 0."""
    import trimesh

    q = np.loadtxt(FRONT, comments="#") / 1000.0          # quarter fore-body, m
    # the table overshoots the 389 x 288 box by up to 0.2 mm: clamp onto it
    q[:, 1] = np.minimum(q[:, 1], W / 2)
    q[:, 2] = np.minimum(q[:, 2], H / 2)
    zmid = GAP + H / 2
    pts = []
    for sz in (1.0, -1.0):                                 # upper and lower quarter
        p = np.c_[q[:, 0], q[:, 1], zmid + sz * q[:, 2]]
        pts += [p, p * (1.0, 0.0, 1.0)]                   # and its shadow on the symmetry plane
    a = math.radians(slant_deg)
    x_slant, z_base = L - LS * math.cos(a), GAP + H - LS * math.sin(a)
    for y in (0.0, W / 2):
        pts.append(np.array([[x_slant, y, GAP + H], [L, y, z_base], [L, y, GAP]]))
    return trimesh.convex.convex_hull(np.vstack(pts))


def write_ascii_stl(mesh, path) -> None:
    with open(path, "w", encoding="ascii") as f:
        f.write("solid car\n")
        for nrm, tri in zip(mesh.face_normals, mesh.triangles):
            f.write(f" facet normal {nrm[0]:.6e} {nrm[1]:.6e} {nrm[2]:.6e}\n  outer loop\n")
            for v in tri:
                f.write(f"   vertex {v[0]:.9e} {v[1]:.9e} {v[2]:.9e}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid car\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slant", type=float, required=True)
    ap.add_argument("--res", default="medium")
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out", default="out")
    ap.add_argument("--cfd-json", default="{}", help="extra run_half_car_cfd keywords")
    a = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from cfd_wrapper import run_half_car_cfd

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"ahmed{a.slant:g}_{a.res}"
    stl = out / f"{tag}.stl"
    write_ascii_stl(half_body(a.slant), stl)

    nu = 1.813e-5 / RHO                      # what run_half_car_cfd uses
    u = RE * nu / L                          # match the experiment's Reynolds number
    kw = {"moving_ground": False, "keep_run_dir": True, **json.loads(a.cfd_json)}
    t0 = time.time()
    half, health = run_half_car_cfd(str(stl), reference_speed_mps=u, air_density_kgm3=RHO,
                                    max_iterations=a.iters, resolution=a.res,
                                    n_subdomains=a.np, **kw)
    q = 0.5 * RHO * u * u * A_REF
    rec = {"slant_deg": a.slant, "res": a.res, "iters": a.iters, "cfd": kw,
           "speed_mps": u, "re": RE, "a_ref_m2": A_REF,
           "cd": 2.0 * half.D20 / q, "cl": 2.0 * half.L / q,
           "drag_full_n": 2.0 * half.D20, "lift_full_n": 2.0 * half.L,
           "health": dataclasses.asdict(health), "seconds": round(time.time() - t0)}
    (out / f"{tag}.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
