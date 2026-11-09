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
    python benchmarks/ahmed.py --shape cube --res medium ...   (second benchmark, see half_cube)
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


def half_cube():
    """Second benchmark, at the cars' Reynolds number: a cube face-on to the flow,
    side CUBE (Re = 3.1e5 at 20 m/s, like the car on its length), its base two
    sides above a rolling road so the ground has no boundary layer. Published
    drag: Cd = 1.05 on its face area (S.F. Hoerner, Fluid-Dynamic Drag, 1965,
    ch. 3). Its sharp edges fix the separation lines, so Cd does not depend on
    Re here (no drag crisis), and it is the same kind of flow as the car's
    blunt base and sharp wing edges."""
    import trimesh
    z0 = 2.0 * CUBE
    c = [(x, y, z) for x in (0.0, CUBE) for y in (0.0, CUBE / 2) for z in (z0, z0 + CUBE)]
    return trimesh.convex.convex_hull(np.array(c))


CUBE = 0.23
CUBE_CD = 1.05


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", choices=("ahmed", "cube"), default="ahmed")
    ap.add_argument("--slant", type=float, default=35.0, help="Ahmed slant, degrees")
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
    nu = 1.813e-5 / RHO                      # what run_half_car_cfd uses
    if a.shape == "ahmed":
        tag, body, a_ref = f"ahmed{a.slant:g}_{a.res}", half_body(a.slant), A_REF
        u, re, still = RE * nu / L, RE, True  # the experiment's Re, still floor
    else:
        tag, body, a_ref = f"cube_{a.res}", half_cube(), CUBE * CUBE
        u, still = 20.0, False                # the cars' speed and rolling road
        re = u * CUBE / nu
    stl = out / f"{tag}.stl"
    write_ascii_stl(body, stl)

    # The underbody box exists for the cars' 1.5 mm ride-height gap; these gaps
    # are 50 mm and 460 mm and the surface cells already fill them, so it is off.
    kw = {"moving_ground": not still, "keep_run_dir": True, "underbody_refinement_level": 0,
          **json.loads(a.cfd_json)}
    t0 = time.time()
    half, health = run_half_car_cfd(str(stl), reference_speed_mps=u, air_density_kgm3=RHO,
                                    max_iterations=a.iters, resolution=a.res,
                                    n_subdomains=a.np, **kw)
    q = 0.5 * RHO * u * u * a_ref
    rec = {"shape": a.shape, "slant_deg": a.slant if a.shape == "ahmed" else None,
           "res": a.res, "iters": a.iters, "cfd": kw,
           "speed_mps": u, "re": re, "a_ref_m2": a_ref,
           "cd": 2.0 * half.D20 / q, "cl": 2.0 * half.L / q,
           "drag_full_n": 2.0 * half.D20, "lift_full_n": 2.0 * half.L,
           "health": dataclasses.asdict(health), "seconds": round(time.time() - t0)}
    (out / f"{tag}.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
