"""Part 4 lab: would the referee have caught Part 1's skin >= 4.00 mm slab ahead of Ref A
(fixed in 55696e3)? Builds the start car with a 4.00 mm skin on Part 1's code from just
before the fix (61035f0) and just after it (55696e3), and prints the checks that limit
material ahead of Ref A, and where that material is. Run from part5-simulation; the job
needs the full git history."""
import json
import subprocess
import sys

import numpy as np

for tag, commit in (("before", "61035f0"), ("after", "55696e3")):
    subprocess.run(["git", "checkout", commit, "--", "../part1-simulation"], check=True)
    out = f"../out/{tag}"
    p = subprocess.run([sys.executable, "-W", "ignore", "run_car.py", "--out", out, "--body-json", "{}",
                        "--skin-mm", "4.0"], capture_output=True, text=True)
    print(f"\n===== {tag} ({commit}): run_car exit {p.returncode}")
    print("\n".join(p.stdout.splitlines()[-5:] + p.stderr.splitlines()[-5:]))
    try:
        S = json.load(open(f"{out}/summary.json"))
    except FileNotFoundError:
        continue
    chk = S["legality"]["checks"]
    print("failed:", S["legality"]["summary"]["failed"])
    for k in sorted(chk):
        if k.startswith(("T8.2", "T8.5", "T3.7", "T3.4", "T3.5", "T7.9", "T4.1", "attached", "block_")):
            print(f"  {k:40s} {chk[k]['margin']:+8.3f} {chk[k]['pass']}  {chk[k]['note']}")
    import trimesh
    b = trimesh.load(f"{out}/body_half.stl", force="mesh")
    v = b.vertices * 1e3
    ref_a = S["args"]["x_front"] - 16.0 if "x_front" in S["args"] else None
    if ref_a is not None:
        ahead = v[v[:, 0] < ref_a]
        print(f"  body ahead of Ref A ({ref_a:.1f}): {len(ahead)} vertices, x {ahead[:, 0].min():.1f}-{ahead[:, 0].max():.1f}, "
              f"y up to {ahead[:, 1].max():.2f}, z {ahead[:, 2].min():.2f}-{ahead[:, 2].max():.2f}" if len(ahead) else
              "  no body ahead of Ref A")
subprocess.run(["git", "checkout", "HEAD", "--", "../part1-simulation"], check=True)
