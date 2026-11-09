"""Part 4 lab: is the body in the block's slot from Part 1's half body, Part 4's fuse and
pockets, or Part 4's final remesh? Builds the start car, then measures the official block's
overrun on: the half body (mirrored), the milled half before the remesh, and the made file."""
import sys
import numpy as np
import trimesh
sys.path.insert(0, ".")
import paths  # noqa: F401,E402
import legality  # noqa: E402
import joints  # noqa: E402
import run_car  # noqa: E402

run_car.main(["--out", "../out/start", "--body-json", "{}"])
made = trimesh.load("../out/start/manufacture/machined_body.stl", force="mesh")
ch = legality.chamber_measures(made)
rear = ch["rim_x_mm"] - ch["depth_mm"] + 52.0
blk = legality.official_block_mm(rear, axis_z_mm=ch["axis_z_mm"])
for name, f in (("body_half (Part 1), fused", "../out/start/body_half.stl"),
                ("milled half before remesh (Part 4), fused", "../out/start/machined_body_half.stl"),
                ("made file after remesh", "../out/start/manufacture/machined_body.stl")):
    m = trimesh.load(f, force="mesh")
    if m.extents.max() < 1.0:
        m.apply_scale(1e3)
    if m.bounds[0, 1] > -0.01:
        a = m.copy(); a.vertices[np.abs(a.vertices[:, 1]) < 1e-6, 1] = -0.01
        b = a.copy(); b.vertices[:, 1] *= -1; b.invert()
        m = trimesh.boolean.union([a, b], engine="manifold")
    over = trimesh.boolean.difference([m, blk], engine="manifold")
    v = 0.0 if over is None or over.is_empty else abs(over.volume)
    print(f"{name:45s} {v:8.2f} mm3 outside the block{legality._where(over) if v > 0.5 else ''}")
