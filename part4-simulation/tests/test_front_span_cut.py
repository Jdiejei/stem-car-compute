"""T8.6.1: a nose crossing the front wing splits its span at the crossing (Part 1, car 41518/1)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trimesh  # noqa: E402

import wings as wg  # noqa: E402


def _box(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(bounds=[[x0 / 1e3, y0 / 1e3, z0 / 1e3], [x1 / 1e3, y1 / 1e3, z1 / 1e3]])


def test_cut_at_the_nose_edge():
    wing = _box(20, 35, 0, 34.46, 8, 11)
    nose = _box(16, 39, 0, 10.23, 3, 22)
    assert abs(wg.front_span_cut_mm(wing, [nose]) - 10.23) < 1e-6


def test_no_cut_when_clear():
    wing = _box(20, 35, 0, 34.46, 8, 11)
    nose = _box(40, 60, 0, 10.0, 3, 22)                 # behind the wing
    assert wg.front_span_cut_mm(wing, [nose]) == 0.0


def test_gate_fails_short_segment_and_passes_wide_one():
    fw = wg.FrontWing(half_span_mm=34.46)
    m = {"wing": _box(20, 35, 0, 34.46, 8, 11), "mount": _box(25, 45, 0, 1.5, 5, 15)}
    assert wg.front_wing_gates(fw, m, 60.0, 14.0, nose_half_width_mm=10.23)["T8.6.1_span"] < 0
    fw = wg.FrontWing(half_span_mm=10.23 + 25.05)
    m = {"wing": _box(20, 35, 0, 10.23 + 25.05, 8, 11), "mount": _box(25, 45, 0, 1.5, 5, 15)}
    assert wg.front_wing_gates(fw, m, 60.0, 14.0, nose_half_width_mm=10.23)["T8.6.1_span"] > 0
