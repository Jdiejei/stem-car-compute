"""A bare beam's slot corner (car 44027/0: 17.2 x 3.96 mm, corner 0.46 mm under a 3.125 mm ball)."""
import dataclasses

import pytest

import beam_support as bsm


def test_ellipse_corner_is_b2_over_a():
    bs = bsm.BeamSupport(beam_w_mm=16.0, beam_h_mm=4.0, p=2.0)
    assert bsm.min_curvature_radius_mm(bs) == pytest.approx(2.0 ** 2 / 8.0, rel=1e-3)


def test_car_44027_beam_fails_then_grown_beam_passes():
    bs = bsm.BeamSupport(beam_w_mm=17.214, beam_h_mm=3.960, pod=False)
    assert bsm.min_curvature_radius_mm(bs) < bsm.TOOL_R_MM
    r = bsm.TOOL_R_MM + 0.01
    grown = dataclasses.replace(bs, beam_h_mm=2 * r, round_r_mm=r)
    assert bsm.min_curvature_radius_mm(grown) == pytest.approx(r, rel=1e-6)
    assert bsm.min_curvature_radius_mm(grown) >= bsm.TOOL_R_MM
    sec = bsm.section(grown)
    assert sec[:, 1].max() - sec[:, 1].min() == pytest.approx(2 * r, abs=1e-6)
    assert sec[:, 0].max() - sec[:, 0].min() == pytest.approx(17.214, abs=1e-6)
