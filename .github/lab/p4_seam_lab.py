"""Part 4 lab: where the bore notch at y = 0 comes from. Builds the start car, then at a few
stations along the bore prints the outline of the half body, the milled half and the
fused milled file near the top and bottom of the bore (|y| < 2 mm). Run from part5-simulation."""
import sys

import numpy as np
import trimesh

sys.path.insert(0, ".")
import paths  # noqa: F401,E402
import legality  # noqa: E402
import run_car  # noqa: E402

run_car.main(["--out", "../out/start", "--body-json", "{}"])
files = {"body_half": "../out/start/body_half.stl", "milled_half": "../out/start/machined_body_half.stl",
         "milled_full": "../out/start/manufacture/machined_body.stl"}
meshes = {}
for k, f in files.items():
    m = trimesh.load(f, force="mesh")
    if m.extents.max() < 1.0:
        m.apply_scale(1e3)
    meshes[k] = m
ch = legality.chamber_measures(meshes["milled_full"])
print("chamber", ch)
zc, r = ch["axis_z_mm"], ch["diameter_area_mm"] / 2.0
for x in (ch["rim_x_mm"] - 40.0, ch["rim_x_mm"] - 20.0, ch["rim_x_mm"] - 5.0):
    print(f"\n== x {x:.1f}")
    for k, m in meshes.items():
        s = m.section(plane_origin=[x, 0, 0], plane_normal=[1.0, 0, 0])
        if s is None:
            print(f"  {k}: no section")
            continue
        v = s.vertices
        for side, sgn in (("top", 1), ("bottom", -1)):
            near = v[(np.abs(v[:, 1]) < 2.0) & (sgn * (v[:, 2] - zc) > 0) & (np.abs(np.abs(v[:, 2] - zc) - r) < 2.0)]
            near = near[np.argsort(near[:, 1])]
            pts = ", ".join(f"({p[1]:+.3f}, {p[2] - zc:+.3f})" for p in near[:12])
            print(f"  {k} {side}: {len(near)} outline points (y, z - axis): {pts}")
