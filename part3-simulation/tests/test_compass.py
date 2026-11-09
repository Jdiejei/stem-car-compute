"""Step 5: the race-time chain rule against finite differences of Part 2's race model."""
import numpy as np
import pytest

import compass
from race_objective_adapter import COM_TARGET_HEIGHT_M
import stopwatch

RHO = 600.0          # kg/m^3, any plausible block density
D0, L0 = 0.80, 0.05  # whole-car N


def _car(seed=0, n=400):
    rng = np.random.default_rng(seed)
    P = np.column_stack([rng.uniform(0.0, 0.22, n), rng.uniform(0.0, 0.035, n),
                         rng.uniform(0.005, 0.06, n)])
    A = rng.uniform(0.5, 1.5, n) * 0.03 / n            # about the half car's skin, m^2
    # slopes of a car's size: ~1 % more drag per mm of uniform growth
    return P, A, rng.normal(100.0, 300.0, n), rng.normal(0, 100.0, n), rng.normal(1.0, 1.0, n)


def _mass():
    return {"car_weight_kg": 0.055, "com_mm": [100.0, 0.0, COM_TARGET_HEIGHT_M * 1e3]}


def _time(eps, P, A, dD, dL, move):
    """Race time after moving the vertices by eps*move, then the uniform skin re-sizing."""
    m = _mass()
    d = eps * move
    d_skin = -np.sum(d * A) / np.sum(A)           # puts the mass back exactly
    dm = 2 * RHO * (d + d_skin) * A              # sums to zero
    m["com_mm"] = [m["com_mm"][0], 0.0, m["com_mm"][2] + 1e3 * np.sum(dm * P[:, 2]) / m["car_weight_kg"]]
    # the skin moves the surface too, so it changes the forces as well
    return stopwatch.race(D0 + np.sum(dD * (d + d_skin) * A), L0 + np.sum(dL * (d + d_skin) * A), m)[0]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_chain_rule_matches_race_model_within_1_percent(seed):
    P, A, dD, dL, move = _car(seed)
    _, dT_d, _ = stopwatch.race(D0, L0, _mass())
    m = _mass()
    slope = compass.race_slope(dD, dL, dT_d, P, A, RHO, m["car_weight_kg"], m["com_mm"][2] / 1e3)
    eps = 5e-4                                    # 0.5 mm, about one cut
    fd = (_time(eps, P, A, dD, dL, move) - _time(-eps, P, A, dD, dL, move)) / 2
    pred = eps * np.sum(slope * move * A)
    assert abs(fd) > 1e-5                         # well above float noise
    assert pred == pytest.approx(fd, rel=0.01)


def test_raw_mass_drops_out():
    P, A, *_ = _car()
    dT_d = {"car_weight_kg": 5.0, "com_height_m": -0.3}
    ms = compass.mass_slope(P, A, RHO, 0.055, 0.03, dT_d)
    assert abs(np.sum(ms * A)) < 1e-9 * np.sum(np.abs(ms) * A)
    flat = compass.mass_slope(P * [1, 1, 0], A, RHO, 0.055, 0.03, dT_d)
    assert np.allclose(flat, 0.0)                # same height everywhere: no time change


def test_lower_mass_is_faster_when_com_height_costs_time():
    P, A, *_ = _car()
    ms = compass.mass_slope(P, A, RHO, 0.055, 0.03, {"car_weight_kg": 0.0, "com_height_m": 1.0})
    assert np.corrcoef(ms, P[:, 2])[0, 1] > 0.99   # growing up high costs time


def test_save_and_load_roundtrip(tmp_path):
    P, A, dD, dL, _ = _car(n=20)
    N = np.tile([0.0, 0.0, 1.0], (20, 1))
    q = {"primal_converged": True, "adjoint_converged": True, "unmatched_frac": 0.0,
         "median_match_m": 1e-4, "method": "adjoint"}
    compass.save(tmp_path / "compass.npz", P, N, A, dD, dL, dD * 1e-3, q)
    c = compass.load(tmp_path / "compass.npz")
    assert np.allclose(c["points"], P) and c["quality"]["method"] == "adjoint"
    with pytest.raises(AssertionError):
        compass.save(tmp_path / "x.npz", P, N * 2, A, dD, dL, dD, q)
