"""T7.13: a pod-high plate must step down clear of the claw at the wheel's inner corner
(cars 44130/0 and 44430/0: the plate at z 27.2-27.4 blocked 12 claw points)."""
import numpy as np
import trimesh

import beam_support as bsm
import wheel as wh


def test_tall_pod_plate_clears_claw_band():
    front_hub, _ = wh.hub_span_mm()
    bs = bsm.BeamSupport()
    y_in, w, x, z, R = 23.25, 13.25, 46.0, 13.82, 14.12
    body = trimesh.creation.box(bounds=[[0.030, 0.0, 0.005], [0.222, 0.015, 0.034]])   # tall: high arch
    ch = bsm.pod_channel(bs, body, x, z, R)
    out = bsm.build(bs, x, z, y_in, w, True, hub_mm=front_hub, R_mm=R, channel=ch)
    part = out["support"]
    assert out["_pod"] and part.is_watertight and len(part.split(only_watertight=False)) == 1
    # the same points the referee samples: 1.5 mm in from the inner face, outer 1.5 mm of radius
    pts = [(x + rr * np.cos(t), yy, z + rr * np.sin(t))
           for yy in np.linspace(y_in - 1.45, y_in - 0.05, 4)
           for rr in np.linspace(R - 1.45, R - 0.05, 4)
           for t in np.linspace(0, 2 * np.pi, 36, endpoint=False)]
    pts = np.array(pts) / 1e3
    assert not part.contains(pts).any()
    g = bsm.gates(bs, out, x, z, R, "rear")
    assert g["T7.13_rear_support_clear_of_claw"] >= 0, g
    assert all(m >= 0 for m in g.values()), {k: m for k, m in g.items() if m < 0}
    # the trimmed end is sized: a neck (plate + web) carries the stub's moment
    assert "claw_neck_stress_mpa" in out["_struct"]
    assert g["load_rear_claw_neck_stress"] >= 0, g


def test_neck_section_modulus_of_a_rectangle_is_bh2_over_6():
    from shapely.geometry import box
    assert abs(bsm.neck_section_modulus_mm3(box(0, 0, 6.0, 2.0)) - 6.0 * 2.0 ** 2 / 6) < 1e-9
