"""
stress_cars.py -- can the car builder make whatever the solver asks for?

Builds random cars across the whole range of every search setting, with no CFD,
and records for each one whether it built and which rules it broke. Any setting
the solver can choose must give a legal, closed car, or fail with a clear reason.

    python checks/stress_cars.py --seed 0 --n 10 --out results/
    python checks/stress_cars.py --summary results/

Cars are built at one fixed skin, not sized, so T3.6 (mass) is ignored here.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pattern  # noqa: E402

SETTINGS = None     # set in main: needs Part 1 on the path
FIXED_SKIN_MM = "2.5"
IGNORED = {"T3.6_mass"}


def random_car(rng: random.Random, share: float) -> dict:
    """A car with `share` of its settings drawn uniformly across their full range."""
    import param_body as pb
    d = {"params": pb.BodyParams().as_dict(), "parts": {}}
    moved = {}
    for name in SETTINGS:
        if rng.random() < share:
            lo, hi = pattern.bounds(name)
            value = rng.uniform(lo, hi)
            d = pattern.put(d, name, value)
            moved[name] = value
    # The car's layout as well: the solver has to be free to choose these too.
    layout = {}
    if rng.random() < share:
        layout["W"] = rng.uniform(120.3, 140.0)
    if rng.random() < share:
        layout["x_front"] = rng.uniform(46.0, 56.0)
    if rng.random() < share:
        layout["d_halo"] = rng.uniform(25.0, 75.0)
    moved.update(layout)
    return {"car": d, "moved": moved, "layout": layout}


def build_one(c: dict) -> dict:
    import run_car as rc
    out = Path(tempfile.mkdtemp())
    args = ["--out", str(out), "--skin-mm", FIXED_SKIN_MM, "--support", "beam",
            "--body-json", json.dumps(c["car"]["params"])]
    for key, flag in (("W", "--W"), ("x_front", "--x-front"), ("d_halo", "--d-halo")):
        if key in c.get("layout", {}):
            args += [flag, str(c["layout"][key])]
    for part, flag in pattern.PART_FLAGS.items():
        if c["car"]["parts"].get(part):
            args += [flag, json.dumps(c["car"]["parts"][part])]
    t0 = time.time()
    row = {"moved": c["moved"], "car": c["car"], "layout": c.get("layout", {})}
    try:
        S = rc.main(args)
        row["failed"] = [k for k in S["legality"]["summary"]["failed"] if k not in IGNORED]
        row["notes"] = {k: S["legality"]["checks"][k]["note"][:80] for k in row["failed"]}
        row["mass_g"] = S["mass"].get("manufactured_mass_g")
        row["status"] = "legal" if not row["failed"] else "illegal"
    except (Exception, SystemExit) as exc:  # noqa: BLE001 -- a car that will not build is the result
        row["status"] = "illegal" if str(exc).startswith("illegal car") else "crash"
        row["failed"], row["notes"] = (["no_nose_root"], {"no_nose_root": str(exc)[:80]}) if row["status"] == "illegal" else ([], {})
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
        row["where"] = traceback.format_exc().strip().splitlines()[-3][:160]
    row["seconds"] = round(time.time() - t0, 1)
    shutil.rmtree(out, ignore_errors=True)
    return row


def summary(root: Path) -> dict:
    rows = [json.loads(p.read_text()) for p in root.rglob("car_*.json")]
    status = Counter(r["status"] for r in rows)
    rules, crashes, blamed = Counter(), Counter(), Counter()
    for r in rows:
        rules.update(r.get("failed", []))
        if r["status"] == "crash":
            crashes[r["error"][:110]] += 1
        if r["status"] != "legal":
            blamed.update(r["moved"].keys())
    print(f"{len(rows)} cars: {dict(status)}")
    print("\nRules broken:")
    for k, n in rules.most_common(25):
        print(f"  {n:4d}  {k}")
    print("\nCrashes:")
    for k, n in crashes.most_common(15):
        print(f"  {n:4d}  {k}")
    # A setting moved in bad cars far more often than in good ones points at the cause.
    good = Counter()
    for r in rows:
        if r["status"] == "legal":
            good.update(r["moved"].keys())
    n_bad = max(sum(1 for r in rows if r["status"] != "legal"), 1)
    n_good = max(status["legal"], 1)
    lift = sorted(((blamed[k] / n_bad - good[k] / n_good, k) for k in blamed), reverse=True)
    print("\nSettings most linked to bad cars:")
    for d, k in lift[:12]:
        print(f"  {d:+.2f}  {k}")
    return dict(status)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", default="stress")
    ap.add_argument("--summary", default=None)
    a = ap.parse_args()
    if a.summary:
        summary(Path(a.summary))
        return
    global SETTINGS
    import param_body as pb
    SETTINGS = (pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR)
                + list(pattern.PARTS))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    for i in range(a.n):
        # From a few settings moved to all of them: failures from one setting alone
        # are easy to trace, and only all of them together reach the far corners.
        c = random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
        row = build_one(c)
        (out / f"car_{a.seed}_{i}.json").write_text(json.dumps(row, indent=1, default=str))
        print(f"car {a.seed}/{i}: {row['status']} {row.get('failed', row.get('error', ''))} "
              f"({len(c['moved'])} moved, {row['seconds']} s)", flush=True)


if __name__ == "__main__":
    main()
