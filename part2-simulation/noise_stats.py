"""Timing noise of the stopwatch (BUILD_SPEC 12.3).

Cars on a fine ladder of skin offsets; fit a straight line of race time
against offset (the true trend) and take the residual SD as the noise sigma,
with its 95 % chi-square interval on n - 2 degrees of freedom.

Each car's drag is already the MEAN over the last part of its run (the wake
moves, so the force swings; FORCE_AVERAGE_FRACTION in openfoam_case), and that
mean has its own error bar: the autocorrelation-corrected standard error. In
race time that is  s_avg = stderr x D20 x dT/dD20.  Every point on the ladder
carries that error, so the residual SD includes it:
    sigma^2  ~=  rms(s_avg)^2  +  sigma_other^2
and what is left over (sigma_other) is the remeshing and everything else. The
report prints both, so the noise figure visibly contains the swing.

    python noise_stats.py 3.90=out/s3.90/summary.json 3.91=...   # skin=path; prints markdown
"""
import json
import math
import sys

import numpy as np
from scipy.stats import chi2


def residual_sd(x, t):
    """(sigma, lo95, hi95, slope) of t about its least-squares line in x."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    n = len(x)
    if n < 4:
        raise ValueError("need at least 4 cars")
    slope, icpt = np.polyfit(x, t, 1)
    dof = n - 2
    s = math.sqrt(float(np.sum((t - (slope * x + icpt)) ** 2)) / dof)
    lo = s * math.sqrt(dof / chi2.ppf(0.975, dof))
    hi = s * math.sqrt(dof / chi2.ppf(0.025, dof))
    return s, lo, hi, float(slope)


def split_noise(sigma: float, s_avg) -> tuple:
    """(rms averaging error, the rest) with sigma^2 = rms^2 + rest^2 (rest 0 if
    averaging alone explains it)."""
    rms = math.sqrt(float(np.mean(np.square(s_avg))))
    return rms, math.sqrt(max(sigma * sigma - rms * rms, 0.0))


def car_row(skin: float, c: dict) -> tuple:
    """(skin, T, D20, converged, s_avg in s) from a run_car summary's cfd_initial."""
    D, se = float(c["D20_N"]), c.get("stderr")
    slope = float((c.get("gradients") or {}).get("dT_dD20", float("nan")))
    s_avg = float("nan") if se is None else float(se) * D * slope
    return skin, float(c["T_at_target_s"]), D, bool(c["converged"]), s_avg


def main(paths):
    rows = []
    for arg in paths:
        skin, _, p = arg.partition("=")
        try:
            rows.append(car_row(float(skin), json.load(open(p))["cfd_initial"]))
        except (OSError, KeyError, ValueError, TypeError) as e:
            print(f"skipped {p}: {e!r}")
    rows.sort()
    print("| skin mm | T s | D20 N | averaging error ms | converged |\n|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]:.3f} | {r[1]:.5f} | {r[2]:.5f} | {r[4]*1e3:.3f} | {r[3]} |")
    ok = [r for r in rows if r[3]]
    print(f"\n{len(ok)} of {len(rows)} cars converged; unconverged cars are left out.\n")
    if len(ok) >= 4:
        s, lo, hi, k = residual_sd([r[0] for r in ok], [r[1] for r in ok])
        sd, dlo, dhi, _ = residual_sd([r[0] for r in ok], [r[2] for r in ok])
        print(f"NOISE race time sigma = {s*1e3:.3f} ms (95 % {lo*1e3:.3f} to {hi*1e3:.3f} ms), "
              f"n = {len(ok)}, trend {k*1e3:.2f} ms per mm")
        print(f"NOISE drag sigma = {sd*1e3:.3f} mN (95 % {dlo*1e3:.3f} to {dhi*1e3:.3f} mN)")
        s_avg = [r[4] for r in ok if not math.isnan(r[4])]
        if s_avg:
            rms, rest = split_noise(s, s_avg)
            print(f"NOISE of that: averaging error (wake swing, each car's own error bar) "
                  f"rms {rms*1e3:.3f} ms over {len(s_avg)} cars; the rest (remeshing and other) "
                  f"{rest*1e3:.3f} ms")


if __name__ == "__main__":
    main(sys.argv[1:])
