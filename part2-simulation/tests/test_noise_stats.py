import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from noise_stats import residual_sd


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
