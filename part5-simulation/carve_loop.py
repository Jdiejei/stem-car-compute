"""The carving loop's decisions (BUILD_SPEC 7 steps 1-2, 12.2, 12.4), one round at a time.

A chain is one car being improved. Each round, per chain:
  1. search:  the current car's time (two runs the first time, so noise is known) and one
              candidate per step size along the compass (k candidates);
  2. confirm: the best candidate re-timed twice on fresh runs; it is KEPT only if the fresh mean
              beats the current car's mean by z * sigma * sqrt(1/2 + 1/2), with
              z = Phi^-1(1 - 0.05 / k) (Bonferroni over the k candidates) and sigma pooled over
              every repeat pair the chain has (sigma^2 = mean (a - b)^2 / 2). Selection and the
              keep test use different runs, so picking the luckiest of k is not rewarded.
  3. scale:   kept at the largest size -> double the sizes; kept elsewhere -> keep; nothing
              kept -> halve. The chain stops when the scale falls below MIN_SCALE of its start.
A chain also stops, flagged "compass_suspect", once >= 12 candidates are timed and >= 90 % of
them were slower than the car they came from: a compass that points uphill.

Everything is a pure function of the state and the results so far, and every timing has a case
id (round, chain, tag), so a round is idempotent: `needed(state)` lists what is missing, a
rerun redoes only that, and `advance(state, results)` moves on once all of it is in.

The problem plugs in through four calls (fake bench: checks/bench.py; real cars: Parts 1-3):
  start(seed) -> x          step(x, direction, size) -> x'
  direction(x) -> unit downhill direction (-compass)  measure(x, case_id) -> race time, s
"""
from __future__ import annotations

from statistics import NormalDist

SIZES = (0.25, 0.5, 1.0, 2.0)        # candidates per round, as fractions of the chain's scale
CONFIRM = 2
MIN_SCALE = 1 / 16
MAX_ROUNDS = 25
ALPHA = 0.05
SEED0 = 46000


def new_chain(i: int, x, scale: float) -> dict:
    return {"id": i, "seed": SEED0 + i, "x": x, "scale": scale, "scale0": scale, "round": 0,
            "status": "running", "phase": "search", "times": [], "pairs": [], "history": [],
            "cands": {}, "slower": 0, "timed": 0}


def z_bonferroni(k: int) -> float:
    return NormalDist().inv_cdf(1 - ALPHA / k)


def pooled_sigma(c: dict, prior: float) -> float:
    """sqrt(mean (a - b)^2 / 2) over every repeat pair; the prior counts as one pair until there
    are two of the chain's own."""
    d = [(a - b) ** 2 / 2 for a, b in c["pairs"]]
    if len(d) < 2:
        d = d + [prior ** 2] * (2 - len(d))
    return (sum(d) / len(d)) ** 0.5


def case(c: dict, tag: str) -> str:
    return f"r{c['round']}_c{c['id']}_{tag}"


def needed(state: dict) -> dict:
    """{case id: (x, what)} still to time this round, for every running chain."""
    out = {}
    for c in state["chains"]:
        if c["status"] != "running":
            continue
        if c["phase"] == "search":
            for r in range(len(c["times"]), 2):
                out[case(c, f"cur{r}")] = (c["x"], "current")
            for s, x in c["cands"].items():
                out[case(c, f"s{s}")] = (x, "candidate")
        else:
            for r in range(CONFIRM):
                out[case(c, f"conf{r}")] = (c["cands"][c["best"]], "confirm")
    return out


def plan(state: dict, direction, step) -> None:
    """Make this round's candidates for chains in search that have none yet."""
    for c in state["chains"]:
        if c["status"] == "running" and c["phase"] == "search" and not c["cands"]:
            d = direction(c["x"])
            c["cands"] = {str(f): step(c["x"], d, f * c["scale"]) for f in SIZES}


def advance(state: dict, results: dict, prior_sigma: float) -> None:
    """Use whatever results exist; move each chain on once its round's cases are all in."""
    need = needed(state)
    for c in state["chains"]:
        if c["status"] != "running":
            continue
        mine = {k for k in need if k.startswith(f"r{c['round']}_c{c['id']}_")}
        if not mine <= set(results):
            continue
        if c["phase"] == "search":
            for r in range(len(c["times"]), 2):
                c["times"].append(results[case(c, f"cur{r}")])
            if len(c["times"]) == 2 and not c["pairs"]:
                c["pairs"].append(tuple(c["times"][:2]))
            T0 = sum(c["times"]) / len(c["times"])
            dT = {s: results[case(c, f"s{s}")] - T0 for s in c["cands"]}
            c["timed"] += len(dT)
            c["slower"] += sum(v > 0 for v in dT.values())
            c["dT"] = dT
            c["best"] = min(dT, key=dT.get)
            c["phase"] = "confirm"
            continue
        conf = [results[case(c, f"conf{r}")] for r in range(CONFIRM)]
        c["pairs"].append(tuple(conf))
        T0 = sum(c["times"]) / len(c["times"])
        sig = pooled_sigma(c, prior_sigma)
        z = z_bonferroni(len(c["cands"]))
        gain = T0 - sum(conf) / CONFIRM
        keep = gain > z * sig * (1 / len(c["times"]) + 1 / CONFIRM) ** 0.5
        c["history"].append({"round": c["round"], "scale": c["scale"], "best": float(c["best"]),
                             "dT_search": c["dT"][c["best"]], "gain_confirm": gain, "sigma": sig,
                             "z": z, "kept": keep})
        if keep:
            c["x"], c["times"] = c["cands"][c["best"]], list(conf)
            if float(c["best"]) == max(SIZES):
                c["scale"] *= 2
        else:
            c["scale"] /= 2
        c["round"] += 1
        c["phase"], c["cands"] = "search", {}
        if c["timed"] >= 12 and c["slower"] >= 0.9 * c["timed"]:
            c["status"] = "compass_suspect"
        elif c["scale"] < MIN_SCALE * c["scale0"]:
            c["status"] = "converged"
        elif c["round"] >= MAX_ROUNDS:
            c["status"] = "out_of_rounds"


def run_local(state: dict, direction, step, measure, prior_sigma: float) -> dict:
    """The whole loop with an immediate stopwatch (the fake bench); the farm does the same with
    needed/advance across GitHub jobs."""
    results = {}
    while any(c["status"] == "running" for c in state["chains"]):
        plan(state, direction, step)
        for k, (x, _) in needed(state).items():
            results[k] = measure(x, k)
        advance(state, results, prior_sigma)
    return state
