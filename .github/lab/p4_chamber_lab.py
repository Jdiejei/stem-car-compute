"""Part 4 lab: the chamber of a real built car, section by section along its axis.
Builds the start car, then prints each section's hole: narrowest and widest diameter,
centre, and where the widest point is. Run from part5-simulation."""
import math
import sys

import numpy as np
import trimesh

sys.path.insert(0, ".")
import paths  # noqa: F401,E402
import legality  # noqa: E402
import run_car  # noqa: E402

run_car.main(["--out", "../out/start", "--body-json", "{}"])
body = trimesh.load("../out/start/manufacture/machined_body.stl", force="mesh")
print("bounds", np.round(body.bounds, 2).tolist(), "volume", body.is_volume)
ch = legality.chamber_measures(body)
print("measures", ch)
x_back = body.bounds[1, 0]
for x in np.arange(x_back - 56.0, x_back + 0.01, 0.5):
    hs = legality._x_section_holes(body, x)
    if not hs:
        print(f"x {x:7.2f} (back {x - x_back:+6.2f}): no hole")
        continue
    for q in sorted(hs, key=lambda q: -q.area)[:3]:
        c = q.centroid
        far = max(q.exterior.coords, key=lambda p: math.hypot(p[0] - c.x, p[1] - c.y))
        print(f"x {x:7.2f} (back {x - x_back:+6.2f}): area {q.area:7.2f} in {legality._thickness(q):6.3f} "
              f"out {2 * math.hypot(far[0] - c.x, far[1] - c.y):6.3f} centre ({c.x:+.2f}, {c.y:.2f}) "
              f"widest at ({far[0]:+.2f}, {far[1]:.2f}) n {len(q.exterior.coords)}")
