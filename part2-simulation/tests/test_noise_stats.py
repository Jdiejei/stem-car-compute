import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from noise_stats import car_row, residual_sd, split_noise


def test_exact_line_has_zero_noise_and_right_slope():
    s, lo, hi, k = residual_sd([0, 1, 2, 3, 4], [1.0, 1.5, 2.0, 2.5, 3.0])
    assert s == pytest.approx(0, abs=1e-12) and k == pytest.approx(0.5)


def test_recovers_known_sigma_and_interval_covers_it():
    rng = np.random.default_rng(47000)
    x = np.arange(16) * 0.01
    hits = 0
    for _ in range(400):
        t = 1.54 + 0.002 * x + rng.normal(0, 3e-4, 16)
        s, lo, hi, _ = residual_sd(x, t)
        hits += lo <= 3e-4 <= hi
    assert 0.92 <= hits / 400 <= 0.98          # a true 95 % interval


def test_interval_width_matches_the_spec_for_16_cars():
    _, lo, hi, _ = residual_sd(np.arange(16), np.r_[np.zeros(8), np.ones(8)] * 1e-3)
    s, *_ = residual_sd(np.arange(16), np.r_[np.zeros(8), np.ones(8)] * 1e-3)
    assert lo / s == pytest.approx(0.73, abs=0.02) and hi / s == pytest.approx(1.58, abs=0.04)


def test_noise_is_split_into_averaging_error_and_the_rest():
    rms, rest = split_noise(0.002, [0.0012, 0.0016])      # rms of the error bars is ~1.41 ms
    assert rms == pytest.approx(np.sqrt((0.0012**2 + 0.0016**2) / 2))
    assert rms**2 + rest**2 == pytest.approx(0.002**2)
    assert split_noise(0.001, [0.002])[1] == 0.0           # averaging alone explains it


def test_car_row_turns_the_drag_error_bar_into_race_time():
    c = {"D20_N": 0.42, "stderr": 0.005, "T_at_target_s": 1.55, "converged": True,
         "gradients": {"dT_dD20": 0.37}}
    skin, T, D, conv, s_avg = car_row(3.9, c)
    assert s_avg == pytest.approx(0.005 * 0.42 * 0.37)    # 0.78 ms
