"""The centre of mass inside the race time (pitch_balance wired into the race model)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from race_objective import (DEFAULT_GAS_XZ_M, DEFAULT_GEOMETRY, PARAM_NAMES, BuildSettings, build_smooth_sheet_model,
                            finite_difference_check, geometry_from_assembly, race_value_and_grad)

FAST = BuildSettings(n_steps=300)
ZT = DEFAULT_GEOMETRY.z_thrust_m


@pytest.fixture(scope="module")
def model():
    return build_smooth_sheet_model(settings=FAST)


def T(model, h, x=0.110, bearing_p=None, **kw):
    m = model if bearing_p is None else model._replace(bearing_p=bearing_p)
    p = np.array([0.38, 0.0694, 0.010, 1.39e-7, 1.0, h, kw.get("lift", 0.0), x])
    return race_value_and_grad(p, m)


def test_com_well_above_the_thrust_line_lifts_the_front_and_costs_time(model):
    t_on, _ = T(model, ZT)                 # thrust line through the COM
    t_hi, g = T(model, ZT + 0.012)         # 12 mm above: past the front-lift point
    assert t_hi > t_on + 1e-3
    assert g["com_height_m"] > 0           # the slope agrees with the time


def test_plain_rolling_resistance_ignores_small_offsets(model):
    """With mu*N on both axles and no wheel off the track, the total rolling
    resistance does not depend on how the load is split (pitch_balance)."""
    t0, _ = T(model, ZT)
    t1, _ = T(model, ZT + 0.0015)          # well inside the lift point
    assert abs(t1 - t0) < 2e-4


def test_a_load_sensitive_bearing_makes_small_offsets_cost_time(model):
    t0, _ = T(model, ZT, bearing_p=1.6)
    t1, _ = T(model, ZT + 0.0025, bearing_p=1.6)
    assert t1 > t0


def test_gradients_match_finite_differences_with_the_pitch_physics(model):
    for h in (ZT - 0.004, ZT + 0.002, ZT + 0.012):
        p = np.array([0.38, 0.0694, 0.010, 1.39e-7, 1.0, h, 0.02, 0.110])
        for r in finite_difference_check(p, model):
            assert r["abs_error"] <= 1e-3 * abs(r["finite_diff"]) + 1e-9, r


def test_geometry_from_assembly():
    asm = {"x_front_mm": 46.0, "W_mm": 120.3,
           "fixed_hardware_kwargs": {"co2_cartridge_com": [0.1963, 0.0, 0.031]},
           "info": {"tethers": [{"x_mm": 171.3, "bottom_mm": 2.0, "od_mm": 8.0, "id_mm": 4.5},
                                {"x_mm": 41.0, "bottom_mm": 2.0, "od_mm": 8.0, "id_mm": 4.5}]}}
    geo, gas = geometry_from_assembly(asm)
    assert geo.x_front_axle_m == pytest.approx(0.046) and geo.wheelbase_m == pytest.approx(0.1203)
    assert (geo.x_guide_front_m, geo.x_guide_rear_m) == pytest.approx((0.041, 0.1713))
    assert geo.z_guide_m == pytest.approx(0.006) and geo.z_thrust_m == pytest.approx(0.031)
    assert gas == pytest.approx((0.1963, 0.031))
    # Part 4's mass report (start car, 2026-11-09) gives the cartridge and the line as built
    mr = {"cartridge_rear_centre_x_mm": 235.3, "cartridge_axis_z_mm": 31.0, "tether_line_z_mm": 6.0}
    geo, gas = geometry_from_assembly(asm, mr)
    assert geo.x_thrust_m == pytest.approx(0.2353) and gas == pytest.approx((0.2028, 0.031))
    for f in ("x_front_axle_m", "wheelbase_m", "x_thrust_m", "z_thrust_m", "x_guide_front_m",
              "x_guide_rear_m", "z_guide_m"):
        assert getattr(geo, f) == pytest.approx(getattr(DEFAULT_GEOMETRY, f))
    assert DEFAULT_GAS_XZ_M == pytest.approx(gas)


def test_param_names_are_unchanged():
    assert PARAM_NAMES == ("drag_20_n", "car_weight_kg", "mu", "wheel_moi_kg_m2",
                           "time_coefficient", "com_height_m", "lift_20_n", "com_x_m")
