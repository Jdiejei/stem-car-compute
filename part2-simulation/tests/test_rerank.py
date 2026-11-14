import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rerank


def car(name, D, kg):
    return {"name": name, "D20_N": D, "L20_N": 0.0, "car_weight_kg": kg,
            "com_x_m": 0.110, "com_height_m": 0.030}


def test_clear_winner_holds_and_a_drag_vs_mass_trade_can_flip():
    cars = [car("a", 0.38, 0.0700), car("b", 0.42, 0.0700)]
    r = rerank.rerank(cars)
    assert r["best"] == "a" and r["winner_changes"] == []
    assert set(r["orders"]) == {"central", "drag_bias 1.05", "drag_bias 1.13", "mu 0.005", "mu 0.02"}
    # lower drag but heavier: the drag factor moves the trade, so the order may change
    t = rerank.times([car("light", 0.42, 0.0690), car("sleek", 0.40, 0.0702)], 1.09, 0.010)
    assert set(t) == {"light", "sleek"} and all(0.4 < v < 2.0 for v in t.values())
