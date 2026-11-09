"""Does the race model lose time when the centre of mass sits above the thrust line?

Target (team test data, 2026-11-09; a different car, ~4.5 s runs): 14 settings
with the COM 2.5 to 10 mm ABOVE the thrust line, 10 runs each; the time rose
steadily from 4.24 s to 4.90 s, about 2 % per mm, even at small offsets.

That car's thrust, mass and layout are not known, so it is set up as OUR car
(default layout, today's best car's mass and drag) with the measured thrust
scaled down until the 2.5 mm setting takes 4.24 s. Then the time is read at the
14 offsets, for plain rolling resistance (bearing_p = 1) and for bearings whose
drag grows faster than their load (p > 1), each with the thrust re-scaled so the
2.5 mm time stays 4.24 s.

    python com_calibration.py
"""
import json

import numpy as np

from race_objective import DEFAULT_GEOMETRY, BuildSettings, build_smooth_sheet_model, race_time_seconds
from pitch_balance import lift_threshold_offset_m
import jax.numpy as jnp

OFFSETS_MM = np.linspace(2.5, 10.0, 14)
T_FIRST, T_LAST = 4.24, 4.90
TARGET_PCT_PER_MM = (T_LAST - T_FIRST) / (OFFSETS_MM[-1] - OFFSETS_MM[0]) / T_FIRST * 100
BEST = dict(D20=0.38037, mass=0.0482 + 0.02115, mu=0.010, moi=1.39e-7, x=0.110)


def race(model, offset_mm, k, p):
    m = model._replace(force_coeffs=model.force_coeffs * k, bearing_p=p)
    h = DEFAULT_GEOMETRY.z_thrust_m + offset_mm / 1e3
    v = jnp.asarray([BEST["D20"], BEST["mass"], BEST["mu"], BEST["moi"], 1.0, h, 0.0, BEST["x"]])
    return float(race_time_seconds(v, m))


def scale_for(model, p, t_target=T_FIRST, offset_mm=OFFSETS_MM[0]):
    """Thrust scale k with race time t_target at offset_mm (bisection; T falls as k grows)."""
    lo, hi = 0.05, 1.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if race(model, offset_mm, mid, p) > t_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    model = build_smooth_sheet_model(settings=BuildSettings(n_steps=600))
    out = {"target_pct_per_mm": TARGET_PCT_PER_MM, "rows": []}
    for p in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0):
        k = scale_for(model, p)
        ts = np.array([race(model, o, k, p) for o in OFFSETS_MM])
        slope = np.polyfit(OFFSETS_MM, ts, 1)[0]
        row = {"bearing_p": p, "thrust_scale": k, "peak_thrust_N": 8.99 * k,
               "T_s": [round(t, 4) for t in ts], "T_last_s": ts[-1],
               "pct_per_mm": slope / ts[0] * 100,
               "pct_per_mm_first_3mm": (ts[4] - ts[0]) / (OFFSETS_MM[4] - OFFSETS_MM[0]) / ts[0] * 100}
        out["rows"].append(row)
        print(f"CAL p={p:.2f}: thrust x{k:.3f} (peak {8.99*k:.2f} N), {row['pct_per_mm']:.2f} %/mm overall, "
              f"{row['pct_per_mm_first_3mm']:.2f} %/mm over the first 3 mm, last {ts[-1]:.3f} s "
              f"(target {TARGET_PCT_PER_MM:.2f} %/mm, {T_LAST} s)", flush=True)
    # where our own car's wheels lift, at peak thrust, launch mass (car + 8 g CO2)
    m0 = BEST["mass"] + 0.008
    gx, gz = 0.1963, DEFAULT_GEOMETRY.z_thrust_m
    for h in (0.030,):
        xc = (BEST["mass"] * BEST["x"] + 0.008 * gx) / m0
        zc = (BEST["mass"] * h + 0.008 * gz) / m0
        up, down = lift_threshold_offset_m(8.99, m0, xc, zc, DEFAULT_GEOMETRY)
        out["lift_points_mm"] = {"thrust_line_above_com_rear_lifts": float(up) * 1e3,
                                 "thrust_line_below_com_front_lifts": float(-down) * 1e3}
        print(f"LIFT our car at 8.99 N: rear wheels lift when the thrust line is {up*1e3:.2f} mm "
              f"ABOVE the COM; front wheels lift when it is {-down*1e3:.2f} mm BELOW the COM")
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
