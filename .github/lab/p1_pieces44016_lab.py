"""Rebuild stress car <seed>/0 (carved) exactly as stress_cars.build_one, keep its files and
print where the machined body's extra pieces are."""
import json, random, sys, tempfile
from pathlib import Path
sys.path.insert(0, "checks")
import numpy as np, trimesh
import stress_cars as sc
import param_body as pb
import pattern
sc.SETTINGS = (pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR) + list(pattern.PARTS))
seed = int(sys.argv[1])
c = sc.random_carve(random.Random(seed))
import run_car as rc
out = Path(tempfile.mkdtemp())
sc.carve_field(c, out / "carved.npy")
args = ["--out", str(out), "--skin-mm", "0", "--support", "beam", "--phi-npy", str(out / "carved.npy")]
for key, flag in (("W", "--W"), ("x_front", "--x-front"), ("d_halo", "--d-halo")):
    if key in c.get("layout", {}):
        args += [flag, str(c["layout"][key])]
for part, flag in pattern.PART_FLAGS.items():
    if c["car"]["parts"].get(part):
        args += [flag, json.dumps(c["car"]["parts"][part])]
S = rc.main(args)
print("LAB failed", S["legality"]["summary"]["failed"], "layout", c.get("layout"), flush=True)
v = S["manufactured"]["machined_body"]
m = trimesh.load(v["file"], force="mesh")
ps = sorted(m.split(only_watertight=False), key=lambda p: -abs(p.volume))
for p in ps[:6]:
    print(f"LAB piece {abs(p.volume):.2f} mm3 bounds {np.round(p.bounds, 2).tolist()}", flush=True)
