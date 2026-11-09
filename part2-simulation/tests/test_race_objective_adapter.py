import csv
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from race_objective import (BuildSettings, PARAM_NAMES, build_smooth_sheet_model,
                            race_value_and_grad)
from race_objective_adapter import adapt_gradients, race_value_and_grad_guarded


# The former SHA-256 pin, kept only as a provenance marker. The lock was
# removed on the owner's instruction (2026-07-28); see
# test_objective_physics_is_unchanged_by_edits for what replaced it.
_ORIGINAL_LOCKED_HASH = "9d8c49c488b5c2f960daca9ab575f03ccb1eba99534a24303233f7ccc61d2c84"


def _synthetic_csv():
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
    with f:
        writer = csv.DictWriter(f, fieldnames=["time (s)", "force (N)", "mass (kg)"])
        writer.writeheader()
        writer.writerows(
            [
                {"time (s)": 0.0, "force (N)": 3.0, "mass (kg)": 0.048},
                {"time (s)": 0.1, "force (N)": 3.0, "mass (kg)": 0.045},
                {"time (s)": 0.2, "force (N)": 2.0, "mass (kg)": 0.040},
                {"time (s)": 0.3, "force (N)": 1.0, "mass (kg)": 0.035},
                {"time (s)": 0.4, "force (N)": 0.2, "mass (kg)": 0.030},
            ]
        )
    return f.name


def _model_and_params(com_height_m=0.040, time_coefficient=1.0, lift_20_n=0.5, com_x_m=0.110):
    path = _synthetic_csv()
    try:
        model = build_smooth_sheet_model(
            path,
            BuildSettings(n_basis=5, ridge=1e-8, tail_tau=0.025, x_start=1e-4, x_grid_power=2.0, n_steps=60),
        )
    finally:
        Path(path).unlink(missing_ok=True)
    params = np.array([1.0, 0.050, 0.02, 1e-7, time_coefficient, com_height_m, lift_20_n, com_x_m], dtype=np.float64)
    return model, params


def test_objective_physics_is_unchanged_by_edits():
    """The hash lock is gone (owner's instruction, 2026-07-28). What replaces it
    is a check on BEHAVIOUR, which is what the lock was actually protecting.

    The lock blocked two necessary changes in a row -- the cartridge
    double-count, then `jax.value_and_grad` being rebuilt per call until Stage 1
    exhausted vm.max_map_count and segfaulted -- while never once catching a
    physics regression. A hash cannot tell a fix from a corruption; these
    invariants can.
    """
    import numpy as np
    from race_objective import build_smooth_sheet_model, race_value_and_grad

    csv = str(Path(__file__).resolve().parents[1] / "co2_thrust_data.csv")
    model = build_smooth_sheet_model(csv)
    p = np.array([0.7076, 0.158598, 0.06, 1.5e-7, 1.0, 0.025, 0.02, 0.10],
                 dtype=np.float64)
    T, grads = race_value_and_grad(p, model)

    assert 1.0 < T < 20.0, f"race time {T} s is not physical for a 20 m run"
    # Signs are the physics: heavier and draggier are slower. (The COM height's
    # sign depends on where it sits against the thrust line: tests/test_race_com.)
    assert grads["car_weight_kg"] > 0, "a heavier car must be slower"
    assert grads["drag_20_n"] > 0, "more drag must be slower"
    assert np.isfinite(grads["com_height_m"]) and np.isfinite(grads["com_x_m"])
    # Determinism: repeated calls must agree exactly. This is also what caught
    # the retrace leak -- a fresh trace per call still returns the same number,
    # so only the mapping count exposed it. Kept as a cheap sanity anchor.
    T2, _ = race_value_and_grad(p, model)
    assert T == T2, f"objective is not deterministic: {T} != {T2}"


def test_mapping_leak_is_documented_where_it_bites():
    """The leak is MITIGATED (vm.max_map_count), not fixed in code.

    An earlier version of this test asserted that hoisting
    jax.value_and_grad out of the call fixed it. That was wrong:
    value_and_grad is not a caching transform, only jax.jit is, and hoisting
    changed nothing (999 vs 1017 ms/call measured). Asserting a false invariant
    is worse than asserting none -- it would have let someone "restore" the real
    fix and think they had broken something.

    What this pins instead is that the next person meets the explanation.
    """
    import inspect
    import race_objective as ro

    src = inspect.getsource(ro)
    head = src[:src.index("def race_value_and_grad(")]
    for needed in ("max_map_count", "jax.jit", "not bit-identical"):
        assert needed in head, (
            f"the mapping-leak note lost its mention of {needed!r}; whoever "
            f"hits the segfault next needs the measurement, the real fix, and "
            f"why it was not applied")


def test_cartridge_mass_is_not_double_counted():
    """car_weight_kg owns the cartridge HARDWARE; the objective owns only the
    unspent propellant.

    Regression guard for the 2026-07-24 correction. The old formula was
    `car_weight_kg + 0.021 + sheet(t) - 0.048`, which added a SECOND cartridge
    shell on top of the CO2_CARTRIDGE_MASS_KG already summed into
    car_weight_kg by mass_com_ingest -- a 50 g car entered the integrator at
    78.9 g. Two properties pin it:

      1. at the finish the vehicle must weigh EXACTLY car_weight_kg (all
         propellant spent, nothing else added);
      2. at the line the excess must equal the CSV's own propellant mass,
         not a cartridge-shell-sized lump.
    """
    import jax.numpy as jnp
    from race_objective import build_smooth_sheet_model, car_mass_from_time, sheet_mass

    path = _synthetic_csv()
    try:
        model = build_smooth_sheet_model(path, BuildSettings(
            n_basis=5, ridge=1e-8, tail_tau=0.025, x_start=1e-4,
            x_grid_power=2.0, n_steps=60))
    finally:
        Path(path).unlink(missing_ok=True)

    cw = 0.050
    end = float(car_mass_from_time(jnp.asarray(1e3), jnp.asarray(cw), model))
    assert abs(end - cw) < 1e-6, (
        f"at the finish the car must weigh exactly car_weight_kg ({cw} kg), got "
        f"{end} kg -- something other than propellant is being added"
    )
    start = float(car_mass_from_time(jnp.asarray(0.0), jnp.asarray(cw), model))
    expected = cw + float(sheet_mass(jnp.asarray(0.0), model) - model.mass_sheet_final)
    assert abs(start - expected) < 1e-9, (
        f"start mass {start} != car_weight_kg + propellant {expected}"
    )
    # Same two properties against the REAL project thrust curve, where the
    # numbers are meaningful: its mass column runs 0.05589 -> 0.04802, so the
    # excess at the line must be ~7.9 g of CO2. The old formula gave 28.9 g.
    real_csv = Path(__file__).resolve().parents[1] / "co2_thrust_data.csv"
    if real_csv.exists():
        real = build_smooth_sheet_model(str(real_csv))
        r_start = float(car_mass_from_time(jnp.asarray(0.0), jnp.asarray(cw), real))
        r_end = float(car_mass_from_time(jnp.asarray(1e3), jnp.asarray(cw), real))
        assert abs(r_end - cw) < 1e-6, f"real CSV: finish mass {r_end} != {cw}"
        excess_g = (r_start - cw) * 1000.0
        assert 5.0 < excess_g < 12.0, (
            f"real CSV: excess at the line is {excess_g:.2f} g, expected ~7.9 g of "
            "CO2. Near 29 g means the cartridge shell is being double-counted again."
        )


def test_adapt_gradients_key_mapping():
    model, params = _model_and_params()
    _T_raw, _T_penalized, raw = race_value_and_grad_guarded(params, model)
    adapted = raw
    assert set(adapted) == {"dT_dD20", "dT_dmass", "dT_dh_com", "dT_dx_com", "dT_dL"}
    # Verify the adapter correctly maps locked-file gradient keys
    _value, locked_grads = race_value_and_grad(params, model)
    assert adapted["dT_dD20"] == locked_grads["drag_20_n"]
    assert adapted["dT_dmass"] == locked_grads["car_weight_kg"]
    assert adapted["dT_dh_com"] == locked_grads["com_height_m"]
    assert adapted["dT_dx_com"] == locked_grads["com_x_m"]


def test_dT_dL_is_nonzero():
    """Lift gradient must be non-zero now that lift-dependent friction is modeled."""
    model, params = _model_and_params(lift_20_n=0.5)
    _T_raw, _T_penalized, adapted = race_value_and_grad_guarded(params, model)
    assert "dT_dL" in adapted
    assert adapted["dT_dL"] != 0.0


def test_time_coefficient_guard_blocks_non_unity():
    model, params = _model_and_params(time_coefficient=1.05)
    try:
        race_value_and_grad_guarded(params, model)
    except AssertionError:
        return
    raise AssertionError("Expected AssertionError")


def test_time_coefficient_guard_allows_unity():
    model, params = _model_and_params(time_coefficient=1.0)
    race_value_and_grad_guarded(params, model)


def test_time_coefficient_guard_allows_the_calibration_and_scales_time():
    model, p1 = _model_and_params(time_coefficient=1.0)
    _, pc = _model_and_params(time_coefficient=0.802)
    T1, _, g1 = race_value_and_grad_guarded(p1, model)
    Tc, _, gc = race_value_and_grad_guarded(pc, model)
    assert Tc == pytest.approx(0.802 * T1, rel=1e-9)
    assert gc["dT_dD20"] == pytest.approx(0.802 * g1["dT_dD20"], rel=1e-6)


def test_returns_three_tuple_T_raw_T_penalized_gradients():
    """The adapter returns (T_raw, T_penalized, gradients). Since 2026-11-09 the
    COM acts inside the physics, so there is no penalty and the two are equal at
    every COM height."""
    for h in (0.020, 0.030, 0.045):
        model, params = _model_and_params(com_height_m=h)
        T_raw, T_penalized, gradients = race_value_and_grad_guarded(params, model)
        assert isinstance(T_raw, float) and isinstance(gradients, dict)
        assert T_penalized == T_raw
        assert set(gradients) == {"dT_dD20", "dT_dmass", "dT_dh_com", "dT_dx_com", "dT_dL"}


def test_negative_mass_rejected():
    """Negative car_weight_kg must raise ValueError, not produce garbage."""
    model, _ = _model_and_params()
    params = np.array([12.0, -0.050, 0.02, 1e-7, 1.0, 0.040, 0.5, 0.005], dtype=np.float64)
    try:
        race_value_and_grad_guarded(params, model)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for negative mass")


def test_negative_mu_rejected():
    """Negative mu must raise ValueError."""
    model, _ = _model_and_params()
    params = np.array([12.0, 0.050, -0.05, 1e-7, 1.0, 0.040, 0.5, 0.005], dtype=np.float64)
    try:
        race_value_and_grad_guarded(params, model)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for negative mu")


def test_negative_drag_rejected():
    """Negative D20 must raise ValueError."""
    model, _ = _model_and_params()
    params = np.array([-12.0, 0.050, 0.02, 1e-7, 1.0, 0.040, 0.5, 0.005], dtype=np.float64)
    try:
        race_value_and_grad_guarded(params, model)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for negative drag")


def test_any_legal_com_height_is_timed_not_clamped():
    """50 mm is a legal COM height on a 65 mm car: timed as it is (the old
    placeholder penalty clamped it; there is nothing to clamp now)."""
    model, _ = _model_and_params()
    params = np.array([12.0, 0.050, 0.02, 1e-7, 1.0, 0.050, 0.5, 0.110],
                      dtype=np.float64)
    T_raw, T_pen, _ = race_value_and_grad_guarded(params, model)
    assert T_raw > 0 and T_pen == T_raw


def test_com_height_outside_the_car_is_still_rejected():
    """A COM above the 65 mm car or below the track is a units/origin bug."""
    model, _ = _model_and_params()
    for bad in (0.50, -0.01):     # 500 mm up, and below the track
        params = np.array([12.0, 0.050, 0.02, 1e-7, 1.0, bad, 0.5, 0.005],
                          dtype=np.float64)
        try:
            race_value_and_grad_guarded(params, model)
        except ValueError as exc:
            assert "units or origin bug" in str(exc), f"wrong guard: {exc}"
            continue
        raise AssertionError(f"com_height_m={bad} was accepted")


def test_com_height_at_boundary_accepted():
    """A low but legal COM height is accepted."""
    model, _ = _model_and_params()
    params = np.array([12.0, 0.050, 0.02, 1e-7, 1.0, 0.018, 0.5, 0.110], dtype=np.float64)
    race_value_and_grad_guarded(params, model)


def test_negative_wheel_moi_rejected():
    """Negative wheel_moi_kg_m2 must raise ValueError."""
    model, _ = _model_and_params()
    params = np.array([12.0, 0.050, 0.02, -1e-7, 1.0, 0.040, 0.5, 0.005], dtype=np.float64)
    try:
        race_value_and_grad_guarded(params, model)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for negative wheel_moi")


def test_propellant_remaining_is_never_negative():
    """The car cannot un-burn its CO2.

    car_mass_from_time adds `sheet_mass(t) - mass_sheet_final` to the dry car.
    The RBF fit rings slightly below its own endpoint, so that term used to go
    negative for t in [0.177, 2.433] s -- half a 3.0 s race, starting INSIDE
    the data range rather than only in extrapolation -- reaching -42.3 ug, and
    rising again near t=1.61 s, i.e. spent propellant flowing back in.

    _smooth_positive was already applied, but to `car_weight + propellant`,
    which is ~0.149 kg and never near zero, so the clamp did nothing. Nothing
    ever caught it because nothing checks the sign of a mass; it just made the
    car up to 42 ug too light for half the race. Worth 0.74 ms worst case
    against +/-15 ms of drag noise -- negligible, and still not a thing that
    should happen.
    """
    import numpy as np
    import jax.numpy as jnp
    from race_objective import build_smooth_sheet_model, car_mass_from_time

    import os
    csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "co2_thrust_data.csv")
    model = build_smooth_sheet_model(csv)

    # Well past the csv (1.499 s) -- the race integrates to ~3 s regardless.
    ts = np.linspace(0.0, 3.2, 3201)
    prop = np.array([float(car_mass_from_time(jnp.float64(t), 0.0, model))
                     for t in ts])
    assert prop.min() >= -1e-12, (
        f"propellant remaining reaches {prop.min():.3e} kg at "
        f"t={ts[prop.argmin()]:.3f} s; the car is lighter than empty")
    # And it must still start at the csv's own charge and end at ~zero.
    assert abs(prop[0] - 0.007871) < 5e-6, (
        f"propellant at t=0 is {prop[0]:.6f} kg, not the csv's 7.871 g")
    assert prop[-1] < 1e-6, (
        f"propellant at t=3.2 s is {prop[-1]:.3e} kg; it should be spent")
