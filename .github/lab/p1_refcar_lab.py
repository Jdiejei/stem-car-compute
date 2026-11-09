"""p1_refcar_lab: Part 4's reference cars (p4_cars.yml) plus a block car and a carved car,
built and sized through run_car, with the checks Part 4 flagged.

    python ../.github/lab/p1_refcar_lab.py <id>    (from part5-simulation, on GitHub)

ids: start | round2 | parts (as p4_cars.yml) | block | cut1
Prints the car's mass, field bodies, every failed rule with its note, and the T5.1, T4.2
cargo and model-block checks whether they pass or not.
"""
import json
import sys
import tempfile
import time
import warnings
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402

cid = sys.argv[1]
out = Path(tempfile.mkdtemp())
r2 = Path("checks/round2_car.json").read_text()
args = {
    "start": ["--body-json", "{}"],
    "round2": ["--body-json", r2],
    "parts": ["--body-json", r2, "--fwing-json", '{"aoa_deg": 8.0}', "--support-json", '{"disc_front": true}',
              "--nose-json", '{"length_mm": 25.0, "wall_mm": 99.0}'],
}.get(cid)
if cid == "block":
    args = ["--phi-npy", "block"]
if cid == "cut1":
    import cutter
    from unified_phi import extract_half_surface
    g = cutter.start_block({"W": 120.3, "x_front": 46.0, "d_halo": 43.72}, 1.0)
    v = np.asarray(extract_half_surface(g).vertices)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g, _ = cutter.cut(g, np.full(len(v), 0.3), type("M", (), {"vertices": v})(), step_m=1.0)
    cutter.save_field(g, out / "carved.npy")
    args = ["--phi-npy", str(out / "carved.npy")]
import run_car as rc  # noqa: E402
t0 = time.time()
S = rc.main(["--out", str(out)] + args)
L = S["legality"]
body = S.get("body", {}) or {}
print(f"LAB {cid} seconds {time.time() - t0:.0f} mass {json.dumps(S.get('mass'))[:300]}", flush=True)
print(f"LAB {cid} body {json.dumps({k: body.get(k) for k in ('faces', 'watertight', 'field_bodies')})} "
      f"build {json.dumps({k: v for k, v in (body.get('build') or {}).items() if k != 'sizing_tried'}, default=str)[:600]}", flush=True)
import re  # noqa: E402
sj = json.dumps(S, default=str)
fb = re.findall(r'"field_bodies": (\d+)', sj)
me = re.findall(r'"mass_error_g": ([-0-9.e]+)', sj)[:4]
sb = re.findall(r'"sizing_builds": (\d+)', sj)[:4]
print(f"LAB {cid} keys {list(S)} field_bodies {fb} mass_error_g {me} sizing_builds {sb}", flush=True)
print(f"LAB {cid} failed {L['summary']['failed']}", flush=True)
for k, v in sorted(L["checks"].items()):
    if not v["pass"] or any(s in k for s in ("T5.1", "T4.2", "block", "T5.5", "T3.6", "T4.1")):
        print(f"LAB {cid} check {k} pass {v['pass']} margin {v['margin']:+.3f} note {v['note'][:120]}", flush=True)
