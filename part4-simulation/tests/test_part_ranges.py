"""Every part setting's legal range: just inside it all the part's gates pass, just
outside it the gate named for that bound fails (part_ranges.py)."""
import json
import os

import pytest
import trimesh

import joints
import part_ranges as pr

D = 0.03          # > 2 x the bisection tolerance (0.01)


def _car():
    # a body box with a low nose block ahead (T8.5.1: the nose under 25 mm, within 15 mm of the centre)
    b = trimesh.creation.box(bounds=[[0.045, -0.025, 0.0015], [0.205, 0.025, 0.0415]])
    n = trimesh.creation.box(bounds=[[0.025, -0.012, 0.004], [0.050, 0.012, 0.020]])
    return pr.Car(body=trimesh.boolean.union([b, n], engine="manifold"))


CASES = [(p, s) for p in pr.SETTINGS for s in pr.SETTINGS[p]]


@pytest.mark.parametrize("part,setting", CASES)
def test_bounds_just_inside_and_just_outside(part, setting):
    car = _car()
    base = pr.DEFAULTS[part]()
    r = pr.legal_range(part, setting, car)
    out = os.environ.get("P4_RANGES_OUT")
    if out:                                   # CI collects the table for Part 5
        with open(out, "a") as f:
            f.write(json.dumps({"part": part, "setting": setting, **r}) + "\n")
    assert r["lo"] <= r["default"] <= r["hi"]
    for side, sign in (("lo", -1), ("hi", +1)):
        if not r[f"{side}_limited"]:
            continue
        inside, outside = r[side] - sign * D, r[side] + sign * D
        assert pr._first_fail(part, base, setting, inside, car) is None, (side, inside)
        assert pr._first_fail(part, base, setting, outside, car) == r[f"{side}_gate"], (side, outside)


def test_rule_table_covers_every_setting():
    assert set(CASES) == set(pr.RULES)


def test_every_density_has_a_source_and_is_flagged_unweighed():
    for rho in set(joints.DENSITY_G_CM3.values()) | {joints.FOAM_G_CM3}:
        src, weighed = joints.density_source(rho)
        assert "no source" not in src and weighed is False
