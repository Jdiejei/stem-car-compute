"""Part 4 lab: why the rear support still blocks T7.13 on car 44130/0.
Logs every beam_support.build call (inputs, the claw-band numbers, each output
piece's bounds), then rebuilds the car the way the stress run does."""
import sys
from pathlib import Path

sys.path[:0] = [str(Path.cwd()), str(Path.cwd().parent / "part4-simulation"), str(Path.cwd() / "checks")]
import numpy as np
import beam_support as bsm

_orig = bsm.build


def build(bs, x_axle_mm, z_axle_mm, y_inner_mm, wheel_width_mm, disc, hub_mm=(5.25, 8.25), R_mm=14.12, channel=None, **kw):
    out = _orig(bs, x_axle_mm, z_axle_mm, y_inner_mm, wheel_width_mm, disc, hub_mm=hub_mm, R_mm=R_mm, channel=channel, **kw)
    st = out["_struct"]
    print("BUILD x_axle", x_axle_mm, "z_axle", z_axle_mm, "y_inner", y_inner_mm, "R", R_mm, "disc", disc,
          "pod", out["_pod"], "section_centre", out["_section_centre_mm"], "plate_h", st.get("plate_h_mm"),
          "disc_r", bs.disc_r_mm, "disc_recess", bs.disc_recess_mm, "pod_wall", bs.pod_wall_mm,
          "claw_band_r", st.get("claw_band_r_mm"), "claw_limit", st.get("claw_band_limit_mm"),
          "neck_stress", st.get("claw_neck_stress_mpa"), "channel", {k: channel[k] for k in ("z_arch_mm", "y_body_at_plate_mm", "length_mm")} if channel else None, flush=True)
    for p in out["support"].split(only_watertight=False):
        print("  piece mm", np.round(p.bounds * 1e3, 2).tolist(), "closed", p.is_watertight, flush=True)
    return out


bsm.build = build
import stress_cars
sys.argv = ["stress_cars.py", "--seed", "44130", "--n", "1", "--carve", "--only", "0", "--out", "../out/stress"]
stress_cars.main()
