"""Measured thrust -> the race model's thrust sheet, and a check of the RBF fit.

Input (from the team, 2026-11-09): thrust_measured_beta_raw.csv, columns
time_s, beta_fit_N; 0 to 0.5 s in 1 ms steps; a beta-function fit to load-cell
data averaged over cartridges.

Output: thrust_measured_beta.csv with the columns race_objective reads,
"time (s)", "force (N)", "mass (kg)". THE MASS COLUMN IS DERIVED, NOT MEASURED:
final car mass + the CO2 still on board, assuming an 8 g charge that leaves in
proportion to the impulse delivered so far,
    CO2(t) = 8 g x (1 - I(t) / I_total),   I(t) = trapezoid integral of F.
The race model uses only mass(t) - mass(end), so the final-mass constant does
not change any race time.

    python thrust_convert.py            # writes the sheet, prints the fit check
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "thrust_measured_beta_raw.csv"
SHEET = HERE / "thrust_measured_beta.csv"
CO2_KG = 0.008
FINAL_MASS_KG = 0.048          # as the old sheet's end value; cancels out in the model


def cumulative_impulse(t: np.ndarray, f: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * np.diff(t))])


def convert(raw=RAW, out=SHEET) -> pd.DataFrame:
    d = pd.read_csv(raw)
    t, f = d["time_s"].to_numpy(float), d["beta_fit_N"].to_numpy(float)
    imp = cumulative_impulse(t, f)
    mass = FINAL_MASS_KG + CO2_KG * (1.0 - imp / imp[-1])
    df = pd.DataFrame({"time (s)": t, "force (N)": f, "mass (kg)": mass})
    with open(out, "w", newline="") as fh:
        fh.write("# Measured thrust (team load cell, beta fit, 2026-11-09), from thrust_measured_beta_raw.csv.\n"
                 "# mass (kg) is DERIVED, not measured: 48 g + an 8 g CO2 charge leaving in proportion\n"
                 "# to the impulse so far. Written by thrust_convert.py; do not edit by hand.\n")
        df.to_csv(fh, index=False, float_format="%.9g")
    return df


def fit_report(sheet=SHEET) -> dict:
    """How closely the race model's smooth thrust follows the sheet."""
    import jax
    import jax.numpy as jnp
    from race_objective import build_smooth_sheet_model, thrust_force

    jax.config.update("jax_enable_x64", True)
    d = pd.read_csv(sheet, comment="#")
    t, f = d["time (s)"].to_numpy(float), d["force (N)"].to_numpy(float)
    model = build_smooth_sheet_model(sheet)
    fit = np.asarray(jax.vmap(lambda x: thrust_force(x, model))(jnp.asarray(t)))
    err = fit - f
    i = int(np.argmax(np.abs(err)))
    tt = np.linspace(0.0, 1.0, 20001)          # the fit keeps a short tail past the data
    fit_long = np.asarray(jax.vmap(lambda x: thrust_force(x, model))(jnp.asarray(tt)))
    return {"max_abs_err_N": float(abs(err[i])), "at_s": float(t[i]),
            "rms_err_N": float(np.sqrt(np.mean(err ** 2))),
            "max_abs_err_after_10ms_N": float(np.max(np.abs(err[t >= 0.010]))),
            "impulse_data_Ns": float(cumulative_impulse(t, f)[-1]),
            "impulse_fit_0_to_end_Ns": float(cumulative_impulse(t, fit)[-1]),
            "impulse_fit_0_to_1s_Ns": float(cumulative_impulse(tt, fit_long)[-1]),
            "peak_data_N": float(f.max()), "peak_at_s": float(t[np.argmax(f)])}


if __name__ == "__main__":
    convert()
    import json
    print(json.dumps(fit_report(), indent=1))
    sys.exit(0)
