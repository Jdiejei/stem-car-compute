"""A high body floor at the axle (cars 44130/0, 50002/0): the pod's strip went above the
roof as a loose slab. Now the support switches to a floor-high rod, set FLOOR_EMBED_MM
into the floor and inside the wheel's cylinder, or says why it cannot."""
import dataclasses

import numpy as np
import pytest
import trimesh

import beam_support as bsm
import wheel as wh

X, R, Y_IN, W = 166.3, 14.123, 16.25, 17.25
Z = R - 0.3
CEILING = Z + R - 0.3 - bsm.FLOOR_EMBED_MM          # the highest floor any support can hold


def _build(floor_mm, top_mm=40.0, bs=None):
    body = trimesh.creation.box(bounds=[[0.030, 0.0, floor_mm / 1e3], [0.222, 0.016, top_mm / 1e3]])
    bs = bs or bsm.BeamSupport()
    ch = bsm.pod_channel(bs, body, X, Z, R)
    _, hub = wh.hub_span_mm()
    out = bsm.build(bs, X, Z, Y_IN, W, True, hub_mm=hub, R_mm=R, channel=ch)
    return out, bsm.gates(bs, out, X, Z, R, "rear")


def _common(out, g):
    part = out["support"]
    assert part.is_watertight and len(part.split(only_watertight=False)) == 1
    v = part.vertices * 1e3
    assert np.hypot(v[:, 0] - X, v[:, 2] - Z).max() <= R - 0.05            # T7.12.1, margin 0.05
    assert g["T7.13_rear_support_clear_of_claw"] >= 0.05                  # T7.13, margin 0.05
    load = {k: m for k, m in g.items() if k.startswith("load_")}
    assert all(m >= 0 for m in load.values()), load                       # strong enough


def test_floor_of_44130_gets_a_legal_floor_high_rod():
    out, g = _build(24.5)
    assert out["_floor_high"] and not out["_pod"]
    _common(out, g)
    assert g["fit_rear_floor_rod_embed"] >= 0                             # 3 mm into the foam


def test_floor_of_50002_is_above_any_legal_support_and_says_why():
    out, g = _build(26.6)
    assert out["_floor_high"]
    _common(out, g)                                                       # still one legal solid
    assert g["fit_rear_floor_rod_embed"] < -1.5                           # only ~1 mm of foam in reach
    assert "body floor at the axle" in out["_struct"]["floor_embed_note"]


def test_rod_embed_just_inside_and_just_outside_the_ceiling():
    for floor, ok in ((CEILING - 0.05, True), (CEILING + 0.05, False)):
        out, g = _build(floor)
        _common(out, g)
        assert (g["fit_rear_floor_rod_embed"] >= 0) is ok, floor


def _switch_floor():
    lo, hi = 3.0, CEILING
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _build(mid)[0]["_pod"]:
            lo = mid
        else:
            hi = mid
    return lo


def test_pod_to_rod_switch_just_inside_and_just_outside():
    f0 = _switch_floor()
    assert 12.0 < f0 < 16.0                                               # ~15 mm with the defaults
    below, gb = _build(f0 - 0.05)
    above, ga = _build(f0 + 0.05)
    assert below["_pod"] and not below["_floor_high"]
    assert above["_floor_high"] and not above["_pod"]
    for out, g in ((below, gb), (above, ga)):
        _common(out, g)
        assert all(m >= 0 for k, m in g.items() if k.startswith("fit_")), g


def test_a_loose_piece_stops_the_build():
    # the guard: a support in more than one piece is a builder bug and raises
    bs = bsm.BeamSupport(pod=False, disc_r_mm=0.5)
    _, hub = wh.hub_span_mm()
    with pytest.raises(ValueError, match="pieces"):
        bsm.build(dataclasses.replace(bs, z_offset_mm=13.0), X, Z, Y_IN, W, False, hub_mm=hub, R_mm=R, channel={})
