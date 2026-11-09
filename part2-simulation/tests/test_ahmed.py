"""The Ahmed benchmark body and the still-floor switch it needs."""
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))

import ahmed
import openfoam_case as oc
from cfd_wrapper import _assert_watertight_stl


@pytest.mark.parametrize("slant", [25.0, 35.0])
def test_half_body_matches_the_published_drawing(slant):
    m = ahmed.half_body(slant)
    assert m.is_watertight and m.is_volume
    lo, hi = m.bounds
    assert np.allclose(lo, (0.0, 0.0, ahmed.GAP), atol=1e-4)
    assert np.allclose(hi, (ahmed.L, ahmed.W / 2, ahmed.GAP + ahmed.H), atol=1e-4)
    # the rear base ends where a 222 mm slant at `slant` degrees says it does
    rear = m.vertices[m.vertices[:, 0] > ahmed.L - 1e-9]
    z_base = ahmed.GAP + ahmed.H - ahmed.LS * math.sin(math.radians(slant))
    assert rear[:, 2].max() == pytest.approx(z_base, abs=1e-9)

    with tempfile.TemporaryDirectory() as d:
        stl = Path(d) / "a.stl"
        ahmed.write_ascii_stl(m, stl)
        _assert_watertight_stl(str(stl))            # what the CFD wrapper demands
        # frontal area: the 0.389 x 0.288 box less four R = 100 mm rounded corners
        want = (ahmed.W * ahmed.H - (4 - math.pi) * ahmed.R ** 2) / 2
        assert oc.compute_frontal_area_half(str(stl)) == pytest.approx(want, rel=5e-3)


@pytest.mark.parametrize("moving, want", [(True, "fixedValue; value uniform (60.0 0 0)"),
                                          (False, "noSlip")])
def test_ground_is_rolling_road_or_still_floor(moving, want):
    cfg = oc.OpenFOAMRunConfig(reference_speed_mps=60.0, moving_ground=moving)
    with tempfile.TemporaryDirectory() as d:
        oc._write_initial_fields(Path(d), cfg, 1.0)
        u = (Path(d) / "U").read_text()
    assert f"lowerWall   {{ type {want}; }}" in u


def test_cars_keep_the_rolling_road_by_default():
    assert oc.OpenFOAMRunConfig().moving_ground is True
