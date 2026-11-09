"""Do Part 2's race-time slopes (stopwatch.race's dT_d) match its own race time?
Central differences of the time stopwatch.race returns, against the dT_d it returns. Prints only.
    python race_slopes_check.py          (part2-simulation on the path; GitHub only)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "part2-simulation"))
import stopwatch                                          # noqa: E402
from race_objective_adapter import COM_TARGET_HEIGHT_M   # noqa: E402

D, L, M, H = 0.80, 0.05, 0.055, COM_TARGET_HEIGHT_M
T0, g, _ = stopwatch.race(D, L, {"car_weight_kg": M, "com_mm": [100.0, 0.0, H * 1e3]})
print(f"LAB race time {T0:.6f} s; dT_d {g}")
for name, h in (("drag_20_n", 1e-3), ("lift_20_n", 1e-3), ("car_weight_kg", 1e-4), ("com_height_m", 1e-4)):
    def t(s):
        d, l, m, z = D, L, M, H
        if name == "drag_20_n":
            d += s
        elif name == "lift_20_n":
            l += s
        elif name == "car_weight_kg":
            m += s
        else:
            z += s
        return stopwatch.race(d, l, {"car_weight_kg": m, "com_mm": [100.0, 0.0, z * 1e3]})[0]
    fd = (t(h) - t(-h)) / (2 * h)
    print(f"LAB {name:14s} dT_d {g[name]:+.6e}   central difference of the returned time {fd:+.6e}"
          f"   ratio {fd / g[name] if g[name] else float('nan'):.4f}")
