"""Part 4 lab: where a built car's body breaks into pieces, and what sits in its chamber.
Builds the start car, then describes every piece of the half body and of the milled
body, and the material inside the measured bore. Run from part5-simulation."""
import json
import sys

import numpy as np
import trimesh

sys.path.insert(0, ".")
import paths  # noqa: F401,E402
import legality  # noqa: E402
import run_car  # noqa: E402

run_car.main(["--out", "../out/start", "--body-json", "{}"])
for name in ("body_half.stl", "machined_body_half.stl", "manufacture/machined_body.stl"):
    m = trimesh.load(f"../out/start/{name}", force="mesh")
    s = 1e3 if m.extents.max() < 1.0 else 1.0
    pieces = sorted(m.split(only_watertight=False), key=lambda p: -abs(p.volume))
    print(f"\n{name}: {len(pieces)} piece(s), watertight {m.is_watertight}")
    for p in pieces:
        print(f"  volume {abs(p.volume) * s ** 3:10.2f} mm3  bounds {np.round(p.bounds * s, 2).tolist()}  "
              f"watertight {p.is_watertight}")
body = trimesh.load("../out/start/manufacture/machined_body.stl", force="mesh")
ch = legality.chamber_measures(body)
print("\nchamber", json.dumps(ch))
bore = legality._x_cylinder(ch["diameter_area_mm"] / 2.0 - 0.05, ch["rim_x_mm"] - ch["depth_mm"] + 0.5,
                            ch["rim_x_mm"], ch["axis_z_mm"])
inside = trimesh.boolean.intersection([body, bore], engine="manifold")
print("in the bore:", abs(inside.volume), "mm3")
for p in inside.split(only_watertight=False):
    print(f"  volume {abs(p.volume):8.2f} mm3  bounds {np.round(p.bounds, 2).tolist()}")
x_back = body.bounds[1, 0]
for x in np.arange(x_back - 54.0, x_back + 0.01, 1.0):
    hs = legality._x_section_holes(body, x)
    big = max(hs, key=lambda q: q.area) if hs else None
    print(f"x back{x - x_back:+6.1f}: " + (f"hole area {big.area:7.2f} plug {legality._thickness(big):6.3f}"
                                         if big else "no hole"))

# Where the milled body leaves the official block.
blk = legality.official_block_mm(float(body.bounds[1, 0]), axis_z_mm=ch["axis_z_mm"])
out = trimesh.boolean.difference([body, blk], engine="manifold")
print("\noutside the block:", abs(out.volume), "mm3; block bounds", np.round(blk.bounds, 2).tolist())
for p in sorted(out.split(only_watertight=False), key=lambda p: -abs(p.volume))[:10]:
    print(f"  volume {abs(p.volume):8.2f} mm3  bounds {np.round(p.bounds, 2).tolist()}")
