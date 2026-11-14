"""The pod's strip lies under the plate and on the disc, or is not built (cars 44130/0 and
50002/0: a high body floor at the rear axle put it above the roof as a loose slab)."""
import numpy as np
import pytest
import trimesh

import beam_support as bsm
import wheel as wh

X, R, Y_IN, W = 166.3, 14.123, 16.25, 17.25
Z = R - 0.3


def _build(floor_mm, top_mm=40.0):
    body = trimesh.creation.box(bounds=[[0.030, 0.0, floor_mm / 1e3], [0.222, 0.016, top_mm / 1e3]])
    bs = bsm.BeamSupport()
    ch = bsm.pod_channel(bs, body, X, Z, R)
    _, hub = wh.hub_span_mm()
    out = bsm.build(bs, X, Z, Y_IN, W, True, hub_mm=hub, R_mm=R, channel=ch)
    return bs, out, bsm.gates(bs, out, X, Z, R, "rear")


@pytest.mark.parametrize("floor_mm", [24.5, 26.6])          # the floors of 44130/0 and 50002/0
def test_high_floor_builds_no_loose_strip_and_says_why(floor_mm):
    bs, out, g = _build(floor_mm)
    part = out["support"]
    assert part.is_watertight and len(part.split(only_watertight=False)) == 1
    v = part.vertices * 1e3
    assert np.hypot(v[:, 0] - X, v[:, 2] - Z).max() <= R - 0.05          # T7.12.1 with margin
    assert g["T7.13_rear_support_clear_of_claw"] >= 0.05
    assert g["fit_rear_strip_under_plate_on_disc"] < 0                   # the car is illegal, and why
    assert "body floor at the axle" in out["_struct"]["strip_fit_note"]


def _fit_floor():
    """The floor height at which the strip just fits (fit margin 0), found on the builder."""
    lo, hi = 2.0, 24.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _build(mid)[1]["_struct"]["strip_fit_mm"] >= 0:
            lo = mid
        else:
            hi = mid
    return lo


def test_strip_fit_just_inside_and_just_outside():
    f0 = _fit_floor()
    for floor, ok in ((f0 - 0.05, True), (f0 + 0.05, False)):
        bs, out, g = _build(floor)
        assert (g["fit_rear_strip_under_plate_on_disc"] >= 0) is ok, floor
        assert len(out["support"].split(only_watertight=False)) == 1
        load = {k: m for k, m in g.items() if k.startswith("load_")}
        assert all(m >= 0 for m in load.values()), load                  # strength gates still pass


def test_a_loose_piece_stops_the_build():
    # the guard: a support in more than one piece is a builder bug and raises
    import dataclasses
    bs = bsm.BeamSupport(pod=False, disc_r_mm=0.5)
    _, hub = wh.hub_span_mm()
    with pytest.raises(ValueError, match="pieces"):
        bsm.build(dataclasses.replace(bs, z_offset_mm=13.0), X, Z, Y_IN, W, False, hub_mm=hub, R_mm=R, channel={})
