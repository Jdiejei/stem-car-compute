"""p1_carve_stress: Part 1's carve stress test (BUILD_SPEC Step 3), carving through the cutter.

    python ../.github/lab/p1_carve_stress.py <seed> <n_cars>    (from part5-simulation, on GitHub)

Uses Part 5's random-car tester (checks/stress_cars.py) as a library, unchanged: its random
layouts and parts, its guarded full-car build (run_car) and every rule check. Only the carving
is replaced: instead of raw Hamilton-Jacobi moves, each car is carved by cutter.cut, 1 to 6
cuts, with a smooth sensitivity concentrated on the surface (Gaussian bumps of both signs plus
a thinning bias, the random_carve recipe); one car in four is thinned hard, toward the 48 g
floor. Prints one "LAB {json}" line per car (status, rules broken, cut verdicts, error).
"""
import json
import sys
import warnings
import zlib
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(Path.cwd() / "checks"))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402

import stress_cars as sc  # noqa: E402


def carve_field(c: dict, path: Path) -> None:
    import cutter
    from unified_phi import extract_half_surface
    lay = {"W": 120.3, "x_front": 46.0, "d_halo": 43.72, **{k: v for k, v in c.get("layout", {}).items()
                                                          if k in ("W", "x_front", "d_halo")}}
    cv = c["carve"]
    rng = np.random.default_rng(zlib.crc32(json.dumps(cv, sort_keys=True).encode()))   # same on every machine
    hard = rng.random() < 0.25
    g = cutter.start_block(lay, spacing_mm=1.0)
    verdicts = []
    for _ in range(max(cv["steps"], 4) if hard else cv["steps"]):
        v = np.asarray(extract_half_surface(g).vertices)
        lo, hi = v.min(0), v.max(0)
        grow = np.full(len(v), (-2.5 if hard else cv["bias_mm"]))          # +: grow, as random_carve
        for b in cv["blobs"]:
            cen = lo + np.array(b["u"]) * (hi - lo)
            s = b["sigma_mm"] * 1e-3
            grow += b["amp_mm"] * np.exp(-((v - cen) ** 2).sum(1) / (2 * s * s))
        dT_dn = -grow / max(np.abs(grow).max(), 1e-12)                    # growing where it is fastest
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g2, rep = cutter.cut(g, dT_dn, type("M", (), {"vertices": v})(), step_m=1.0,
                                 max_substeps=6, trust_radius_m=1e-3)
        verdicts.append(rep["status"] if rep["status"] == "ok" else rep["reason"][:40])
        g = g2
    c.setdefault("layout", {})["cuts"] = verdicts       # rides into the row (only W/x_front/d_halo become flags)
    c["layout"]["hard"] = bool(hard)
    cutter.save_field(g, path)


sc.carve_field = carve_field
seed, n = int(sys.argv[1]), int(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else ""     # nocorner | nobars: switch off one 11-Nov cutter change
if "nocorner" in MODE:                                # corner relief for every body (6b95197) off
    import machining
    _ra = machining.reachable_air
    machining.reachable_air = lambda A, r, any_side=False: np.ones(A.shape, bool) if any_side else _ra(A, r)
if "nobars" in MODE:                                  # loose pieces joined (e63d51e) off: dropped again
    import param_body
    param_body.BRIDGE_MIN_MM3 = 1e18
out = Path("../stress_p1")
sys.argv = ["stress_cars.py", "--seed", str(seed), "--n", str(n), "--out", str(out), "--carve"]
sc.main()
for p in sorted(out.glob(f"car_{seed}_*.json"), key=lambda p: int(p.stem.split("_")[-1])):
    r = json.loads(p.read_text())
    print("LAB " + json.dumps({"car": p.stem, "status": r["status"], "failed": r.get("failed"),
                               "notes": r.get("notes"), "error": r.get("error"), "where": r.get("where"),
                               "cuts": r.get("layout", {}).get("cuts"), "hard": r.get("layout", {}).get("hard"),
                               "seconds": r.get("seconds"), "peak_gb": r.get("peak_gb")}), flush=True)
