"""Does the best car stay best when the uncertain constants move? (reviewer Q11)

The drag correction (1 / 1.09, range 1.05-1.13) and the rolling friction
(0.010, range 0.005-0.020) are the same for every car but only roughly known.
Re-time the top cars with the race model only (no new flow runs) at the low,
central and high values and report each ranking and whether the winner changes.

    python rerank.py cars.json
cars.json: [{"name", "D20_N", "L20_N", "car_weight_kg", "com_x_m", "com_height_m"}, ...]
(full-car forces from the CFD; mass incl. the cartridge shell; COM from the nose
tip and above the track, without CO2).
"""
import json
import sys

import numpy as np

from physics_contract import DRAG_BIAS, DRAG_BIAS_RANGE, TIME_COEFFICIENT
from race_objective import build_smooth_sheet_model, race_value_and_grad

MU_CENTRAL, MU_RANGE = 0.010, (0.005, 0.020)
WHEEL_MOI = 1.39e-7


def times(cars: list, drag_bias: float, mu: float) -> dict:
    m = build_smooth_sheet_model()._replace(drag_bias=drag_bias)
    out = {}
    for c in cars:
        p = np.array([c["D20_N"], c["car_weight_kg"], mu, WHEEL_MOI, TIME_COEFFICIENT,
                      c["com_height_m"], c.get("L20_N", 0.0), c["com_x_m"]])
        out[c["name"]] = race_value_and_grad(p, m)[0]
    return out


def rerank(cars: list) -> dict:
    cases = {"central": (DRAG_BIAS, MU_CENTRAL)}
    for b in DRAG_BIAS_RANGE:
        cases[f"drag_bias {b}"] = (b, MU_CENTRAL)
    for mu in MU_RANGE:
        cases[f"mu {mu}"] = (DRAG_BIAS, mu)
    res = {}
    for k, (b, mu) in cases.items():
        t = times(cars, b, mu)
        res[k] = sorted(t, key=t.get)
    best = res["central"][0]
    return {"orders": res, "best": best,
            "winner_changes": [k for k, o in res.items() if o[0] != best]}


if __name__ == "__main__":
    r = rerank(json.load(open(sys.argv[1])))
    for k, o in r["orders"].items():
        print(f"RERANK {k:>16}: {' < '.join(o)}")
    print("RERANK best", r["best"], "| winner changes under:", r["winner_changes"] or "none")
