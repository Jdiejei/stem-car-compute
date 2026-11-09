"""Step 3, ranking agreement: do the search mesh and the fine mesh order cars alike?

The 20 cars are Part 5's stress cars (checks/stress_cars.py, read only): a car
id "L<i>" is lofted car i of seed 47000, "C<i>" carved car i of seed 47001, so
every machine rebuilds exactly the same car.

    python rank_study.py car L3 --res medium --iters 1000 --cfd-json '{...}' --out out/L3
    python rank_study.py stats '{"L0": [T_search, T_fine], ...}'
"""
import argparse
import itertools
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS = {"L": 47000, "C": 47001}
# run_car, pattern and stress_cars live in Part 5 (read only); on the path
# before anything imports them (the first ranking runs died on `import run_car`).
sys.path[:0] = [str(ROOT / "part5-simulation"), str(ROOT / "part5-simulation" / "checks")]


def car_args(car_id: str, out: Path) -> list:
    """run_car arguments for stress car `car_id`, exactly as stress_cars.build_one."""
    import pattern
    import stress_cars as sc
    import param_body as pb
    sc.SETTINGS = (pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR)
                   + list(pattern.PARTS))
    kind, idx = car_id[0], int(car_id[1:])
    rng = random.Random(SEEDS[kind])
    for _ in range(idx + 1):
        c = sc.random_carve(rng) if kind == "C" else sc.random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
    out.mkdir(parents=True, exist_ok=True)
    args = ["--out", str(out), "--skin-mm", sc.FIXED_SKIN_MM, "--support", "beam",
            "--body-json", json.dumps(c["car"]["params"])]
    if kind == "C":
        sc.carve_field(c, out / "carved.npy")
        args = ["--out", str(out), "--skin-mm", "0", "--support", "beam", "--phi-npy", str(out / "carved.npy")]
    for key, flag in (("W", "--W"), ("x_front", "--x-front"), ("d_halo", "--d-halo")):
        if key in c.get("layout", {}):
            args += [flag, str(c["layout"][key])]
    for part, flag in pattern.PART_FLAGS.items():
        if c["car"]["parts"].get(part):
            args += [flag, json.dumps(c["car"]["parts"][part])]
    return args


def spearman(a, b) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).statistic)


def pair_agreement(search, fine, gap_s=3e-3):
    """(agreeing, total) over pairs more than gap_s apart on the fine mesh."""
    agree = total = 0
    for i, j in itertools.combinations(range(len(fine)), 2):
        d = fine[j] - fine[i]
        if abs(d) > gap_s:
            total += 1
            agree += (search[j] - search[i]) * d > 0
    return agree, total


def stats(pairs: dict) -> str:
    ids = sorted(k for k, v in pairs.items() if v[0] is not None and v[1] is not None)
    s, f = [pairs[k][0] for k in ids], [pairs[k][1] for k in ids]
    rho = spearman(s, f)
    ag, tot = pair_agreement(s, f)
    frac = ag / tot if tot else float("nan")
    ok = rho >= 0.9 and tot > 0 and frac >= 0.9
    return (f"RANK n = {len(ids)} cars, Spearman {rho:.3f} (pass >= 0.9), pairs > 3 ms apart on "
            f"fine: {ag}/{tot} = {frac:.1%} agree (pass >= 90 %) -> {'PASS' if ok else 'FAIL'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("car")
    c.add_argument("car_id")
    c.add_argument("--res", default="medium")
    c.add_argument("--iters", default="1000")
    c.add_argument("--cfd-json", default="{}")
    c.add_argument("--out", required=True)
    s = sub.add_parser("stats")
    s.add_argument("pairs_json")
    a = ap.parse_args()
    if a.cmd == "stats":
        print(stats(json.loads(a.pairs_json)))
        return
    import run_car
    args = car_args(a.car_id, Path(a.out)) + ["--cfd", "--res", a.res, "--np", "4",
                                              "--cfd-iters", a.iters, "--cfd-json", a.cfd_json]
    run_car.main(args)


if __name__ == "__main__":
    main()
