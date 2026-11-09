"""The measured thrust sheet (2026-11-09) and the calibrated race model."""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import thrust_convert as tcv
from physics_contract import TIME_COEFFICIENT
from race_objective import build_smooth_sheet_model, finite_difference_check

# today's best search car (solver chain 2, 2026-11-08): D20, mass at the 48.2 g
# target + the 21.15 g cartridge shell
BEST = np.array([0.38037, 0.0482 + 0.02115, 0.010, 1.39e-7, TIME_COEFFICIENT, 0.030, 0.0, 0.0])


def test_committed_sheet_is_what_the_converter_writes():
    with tempfile.TemporaryDirectory() as d:
        fresh = tcv.convert(out=Path(d) / "s.csv")
    sheet = pd.read_csv(tcv.SHEET, comment="#")
    assert list(sheet.columns) == ["time (s)", "force (N)", "mass (kg)"]
    assert np.allclose(sheet.to_numpy(), fresh.to_numpy(), rtol=1e-8, atol=1e-12)
    assert "DERIVED, not measured" in tcv.SHEET.read_text()


def test_mass_curve_is_8g_of_co2_leaving_with_the_impulse():
    s = pd.read_csv(tcv.SHEET, comment="#")
    m = s["mass (kg)"].to_numpy()
    assert m[0] == pytest.approx(0.056) and m[-1] == pytest.approx(0.048)
    assert np.all(np.diff(m) <= 1e-15)
    imp = tcv.cumulative_impulse(s["time (s)"].to_numpy(), s["force (N)"].to_numpy())
    assert imp[-1] == pytest.approx(2.15, abs=0.01)          # the team's figure


def test_fit_keeps_the_impulse():
    r = tcv.fit_report()
    print(r)
    assert r["impulse_fit_0_to_1s_Ns"] == pytest.approx(r["impulse_data_Ns"], rel=0.01)


def test_gradient_check_on_the_measured_thrust():
    """JAX gradient vs central finite differences within 0.1 % (BUILD_SPEC 8)."""
    rows = finite_difference_check(BEST, build_smooth_sheet_model())
    for r in rows:
        tol = 1e-3 * abs(r["finite_diff"]) + 1e-9
        assert r["abs_error"] <= tol, r
