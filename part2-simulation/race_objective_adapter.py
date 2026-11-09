"""Adapter from race_objective.py to the Stage 7 keys, with input guards.

    Returns:
        T_raw       = predicted 20 m race time
        T_penalized = the same number. The placeholder COM penalties were
                      removed on 2026-11-09: the centre of mass now acts through
                      physics inside the race time (pitch_balance), so there is
                      nothing to add or subtract. The pair is kept because
                      callers' contracts carry both (manufacturing penalties,
                      if any, are added by the optimiser, not here).
        gradients   = dict of dT/d(param) for each input, gradients of T_raw
"""

from __future__ import annotations

import numpy as np

from mass_com_ingest import COM_SANITY_BOUNDS_M
from race_objective import (
    PARAM_NAMES,
    _clean_csv_arrays,
    BuildSettings,
    COM_TARGET_HEIGHT_M,
    build_smooth_sheet_model,
    race_value_and_grad,
)

# The time coefficient is a fixed calibration factor (team lead, 2026-11-09):
# physics_contract.TIME_COEFFICIENT = 0.802. The guard admits exactly that value
# or 1.0 (the uncalibrated model) -- never a free optimiser input.
def _assert_time_coefficient_unity(param_vector) -> None:
    from physics_contract import TIME_COEFFICIENT
    tc = param_vector[PARAM_NAMES.index("time_coefficient")]
    assert tc in (1.0, TIME_COEFFICIENT), (
        f"time_coefficient must be 1.0 (uncalibrated) or the approved "
        f"calibration factor {TIME_COEFFICIENT}, got {tc}"
    )


# T3.5 caps the car at 65 mm tall, so a real COM height is strictly inside
# (0, 0.065) m. Outside that is a units or origin bug.
COM_HEIGHT_PHYSICAL_MAX_M: float = 0.065


def _assert_physical_inputs(param_vector):
    """Guard against physically meaningless inputs that would produce silently
    wrong results (negative mass or mu, a COM height outside the car). The race
    model uses smooth floors to avoid crashes, which would mask garbage."""
    p = {name: float(param_vector[i]) for i, name in enumerate(PARAM_NAMES)}
    if p["car_weight_kg"] <= 0:
        raise ValueError(f"car_weight_kg must be positive, got {p['car_weight_kg']}")
    if p["mu"] < 0:
        raise ValueError(f"mu (friction) must be non-negative, got {p['mu']}")
    if p["drag_20_n"] < 0:
        raise ValueError(f"drag_20_n must be non-negative, got {p['drag_20_n']}")
    if p["wheel_moi_kg_m2"] < 0:
        raise ValueError(f"wheel_moi_kg_m2 must be non-negative, got {p['wheel_moi_kg_m2']}")
    # lift_20_n: any value (lift and downforce are both physical)
    if not (0.0 < p["com_height_m"] < COM_HEIGHT_PHYSICAL_MAX_M):
        raise ValueError(
            f"com_height_m={p['com_height_m']} is outside the physically possible "
            f"range (0, {COM_HEIGHT_PHYSICAL_MAX_M}) m above the track -- a units or "
            f"origin bug upstream in mass/COM ingestion.")
    if not (COM_SANITY_BOUNDS_M[0] <= p["com_x_m"] <= COM_SANITY_BOUNDS_M[1]):
        raise ValueError(
            f"com_x_m={p['com_x_m']} outside sanity bounds {COM_SANITY_BOUNDS_M}, "
            f"likely a units or origin bug")
    return param_vector


def adapt_gradients(raw_grads: dict) -> dict:
    """race_value_and_grad's PARAM_NAMES-keyed gradients -> 'dT_dD20',
    'dT_dmass', 'dT_dh_com', 'dT_dx_com', 'dT_dL' (s/N, s/kg, s/m, s/m, s/N).
    dT_dh_com is per metre of COM height above the track; dT_dx_com per metre of
    COM x from the nose tip, + towards the tail."""
    return {
        "dT_dD20": raw_grads["drag_20_n"],
        "dT_dmass": raw_grads["car_weight_kg"],
        "dT_dh_com": raw_grads["com_height_m"],
        "dT_dx_com": raw_grads["com_x_m"],
        "dT_dL": raw_grads["lift_20_n"],
    }


def race_value_and_grad_guarded(param_vector, model):
    """(T_raw, T_penalized, adapted gradients) after the input guards; see the
    module docstring. Raises AssertionError for an unapproved time coefficient
    and ValueError for physically impossible inputs."""
    _assert_time_coefficient_unity(param_vector)
    param_vector = _assert_physical_inputs(param_vector)
    T, raw_grads = race_value_and_grad(param_vector, model)
    return T, T, adapt_gradients(raw_grads)
