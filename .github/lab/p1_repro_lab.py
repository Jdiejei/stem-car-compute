"""p1_repro_lab: the same carving and finish on different machines must give identical files.

    python ../.github/lab/p1_repro_lab.py <seed> <n> [tag]    (from part5-simulation, on GitHub)

Run the same <seed> <n> in two jobs (tags a and b: two machines). Prints one LAB line per
body with the SHA-256 of carved_phi.npy, body_half.stl, body.stl and cut.json.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(ROOT / ".github" / "lab"))
import platform  # noqa: E402

from p1_carve_common import carve  # noqa: E402

seed, n = int(sys.argv[1]), int(sys.argv[2])
tag = sys.argv[3] if len(sys.argv) > 3 else ""
for k in range(n):
    import cutter
    lay, g, verdicts = carve(seed, k)
    out = Path(tempfile.mkdtemp())
    res = cutter.finish(g, lay, 48.2, out)
    sha = {f: hashlib.sha256((out / f).read_bytes()).hexdigest()[:16] if (out / f).exists() else None
           for f in ("carved_phi.npy", "body_half.stl", "body.stl", "cut.json")}
    print("LAB " + json.dumps({"seed": seed, "k": k, "tag": tag, "host": platform.node(),
                               "cpu": platform.processor(), "status": res["status"],
                               "mass_g": res.get("mass_g"), "sha": sha}), flush=True)
