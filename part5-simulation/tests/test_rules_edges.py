"""Edge tests: for each numeric rule the referee measures, a car just inside the limit
(limit - 0.2 mm, or 0.2 g) must pass and a car just outside (limit + 0.2) must fail,
on the right rule id and nothing else. See RULES_MAP.md.

The cars are boxes (fast, exact): a known-good box car is edited one thing at a time.
Rules the referee does not yet measure itself (RULES_MAP.md "gate only" / "constant")
are not here; they get their own measurement and tests first.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _p in ("part1-simulation", "part2-simulation", "part4-simulation"):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / _p))

import pytest
import trimesh

import legality

FY, RY = 23.25, 16.25            # wheel inner faces (geometry_contract, v2 CAD)
AXIS_Z, BORE_R = 31.0, 18.15 / 2.0
MASS = {"competition_mass_g": 48.2, "ballast_g": 0.0, "capacity_g": 5.0}


def _box(lo, hi):
    return trimesh.creation.box(bounds=[lo, hi])


def _save(tmp, name, mesh_mm):
    m = mesh_mm.copy()
    m.apply_scale(1e-3)                     # half meshes are stored in metres
    p = tmp / f"{name}.stl"
    m.export(str(p))
    return str(p)


def build(tmp, W=130.0, **o):
    """A legal half car (mm, y >= 0): body with a nose stub ahead of Ref A, rear wing on
    top, two wheels. Keyword overrides move one thing."""
    xf = 50.0
    ra, rb = xf - 16.0, xf + W + 16.0
    top = o.get("top", 50.0)
    body = trimesh.boolean.union(
        [_box((ra, 0, 5), (o.get("rear", rb + 40.0 - 0.2), 14.5, top)),
         _box((o.get("nose_x", ra - 20.0), 0, o.get("nose_lo", 8.0)),
              (ra + 0.5, o.get("nose_y", 10.0), o.get("nose_z", 20.0)))]
        + [_box(*b) for b in o.get("extra", [])], engine="manifold")
    if "loose" in o:                        # a second, separate piece of foam
        body = trimesh.util.concatenate([body, _box(*o["loose"])])
    gap = o.get("rw_gap", 0.0)
    parts = {
        "rwing": _box((rb + 4.0, 0, top + gap), (o.get("rw_x1", rb + 34.0), 25.0, o.get("rw_top", top + 3.0))),
        "wheelF": _box((xf - 14.0, FY, 0), (xf + 14.0, o.get("wf_y", 36.5), 28.1)),
        "wheelR": _box((xf + W - 14.0, RY, 0), (xf + W + 14.0, o.get("wr_y", 33.5), 28.1)),
    }
    asm = {"W_mm": W, "x_front_mm": xf,
           "extra_surfaces": [{"name": k, "stl": _save(tmp, k, m)} for k, m in parts.items()]}
    return _save(tmp, "body", body), asm


def fails(tmp, mass=MASS, **o):
    body, asm = build(tmp, **o)
    r = legality.check(body, asm, mass)
    return {k for k, v in r.items() if not v["pass"]}, r


def test_the_base_car_passes_every_check(tmp_path):
    bad, r = fails(tmp_path)
    assert not bad, {k: r[k] for k in bad}
    for k in ("T3.4_width_min", "T3.4_width_max", "T3.5_height", "T3.7_clearance", "T3.6_mass",
              "T1.22_ballast_capacity", "T7.3_W_min", "T7.3_W_max", "T8.2_nose_overhang",
              "T8.5.1_nose_z", "T8.5.1_nose_half_width", "T9.4.2_rear_overhang", "block_length",
              "block_width", "block_height", "T4.1_single_body", "attached_rwing", "T5.5_wall",
              "T7.13_front_claw_clearance", "T7.13_rear_claw_clearance"):
        assert k in r, k


RA = 34.0                               # Ref A of the base car
WALL = AXIS_Z + BORE_R                  # top of the bore

# rule id: (just inside, just outside, other rules the outside car also breaks)
EDGES = {
    "T3.4_width_min": ({"wf_y": 32.6, "wr_y": 32.6}, {"wf_y": 32.4, "wr_y": 32.4}, set()),
    "T3.4_width_max": ({"wf_y": 42.4}, {"wf_y": 42.6}, set()),
    "T3.5_height": ({"rw_top": 64.8}, {"rw_top": 65.2}, set()),
    "T3.7_clearance": ({"nose_lo": 1.7}, {"nose_lo": 1.3}, set()),
    "T7.3_W_min": ({"W": 120.2}, {"W": 119.8}, set()),
    "T7.3_W_max": ({"W": 139.8}, {"W": 140.2}, set()),
    "T8.2_nose_overhang": ({"nose_x": RA - 39.8}, {"nose_x": RA - 40.2}, set()),
    "T8.5.1_nose_z": ({"nose_z": 24.8}, {"nose_z": 25.2}, set()),
    "T8.5.1_nose_half_width": ({"nose_y": 14.8}, {"nose_y": 15.2}, set()),
    "T9.4.2_rear_overhang": ({"rw_x1": 196.0 + 39.8}, {"rw_x1": 196.0 + 40.2}, set()),
    "block_width": ({"extra": [((100, 0, 10), (150, 32.4, 40))]},
                    {"extra": [((100, 0, 10), (150, 32.6, 40))]}, set()),
    "block_height": ({"top": 5.0 + 49.8}, {"top": 5.0 + 50.2}, set()),
    "attached_rwing": ({"rw_gap": 0.1}, {"rw_gap": 0.5}, set()),
    "T5.5_wall": ({"top": WALL + 3.2}, {"top": WALL + 2.8}, set()),
    "T7.13_front_claw_clearance": ({"extra": [((40, 0, 20), (60, FY - 1.7, 27))]},
                                   {"extra": [((40, 0, 20), (60, FY - 1.3, 27))]}, set()),
    "T7.13_rear_claw_clearance": ({"extra": [((170, 0, 20), (190, RY - 1.7, 27))]},
                                  {"extra": [((170, 0, 20), (190, RY - 1.3, 27))]}, set()),
}


@pytest.mark.parametrize("rule", sorted(EDGES))
def test_edge(rule, tmp_path):
    inside, outside, also = EDGES[rule]
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    bad, r = fails(tmp_path / "in", **inside)
    assert not bad, (rule, "inside", {k: r[k] for k in bad})
    bad, r = fails(tmp_path / "out", **outside)
    assert bad == {rule} | also, (rule, "outside", bad, r.get(rule))


def test_one_piece_of_foam(tmp_path):
    bad, _ = fails(tmp_path, loose=((100, 20, 10), (110, 22, 20)))
    assert bad == {"T4.1_single_body"}, bad


def test_block_length(tmp_path):
    # The body behind Ref A can only pass 223 mm by running past Ref B + 40 as well.
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    bad, _ = fails(tmp_path / "in", W=140.0, rear=34.0 + 222.8)
    assert bad == {"T9.4.2_rear_overhang"}, bad
    bad, _ = fails(tmp_path / "out", W=140.0, rear=34.0 + 223.2)
    assert bad == {"T9.4.2_rear_overhang", "block_length"}, bad


@pytest.mark.parametrize("rule,key,inside,outside", [
    ("T3.6_mass", "competition_mass_g", 48.2, 47.8),
    ("T3.6_mass", "competition_mass_g", 48.0, 47.9),          # T2.7.1's own example
    ("T1.22_ballast_capacity", "ballast_g", 4.8, 5.2),
])
def test_mass_edges(rule, key, inside, outside, tmp_path):
    body, asm = build(tmp_path)
    ok = legality.check(body, asm, {**MASS, key: inside})
    bad = legality.check(body, asm, {**MASS, key: outside})
    assert ok[rule]["pass"] and not bad[rule]["pass"]
    assert {k for k, v in bad.items() if not v["pass"]} == {rule}


# Sight lines and clear air, on the box car of test_legality_visibility (mm).
def _vstl(tmp, name, lo, hi):
    return {"name": name, "stl": _save(tmp, name, _box(lo, hi))}


def _vis(tmp, things):
    asm = {"x_front_mm": 50.0, "extra_surfaces": [
        _vstl(tmp, "halo", (100, 0, 24), (150, 12.5, 39)),
        _vstl(tmp, "wheelF", (35, 20, 0), (65, 36, 30)),
        _vstl(tmp, "wheelR", (165, 20, 0), (195, 36, 30)),
        _vstl(tmp, "fwing", (20, 16, 6), (28, 38, 9)),
        _vstl(tmp, "nose", (0, 0, 8), (40, 10, 20)),
        _vstl(tmp, "rwing", (205, 0, 40), (225, 30, 43)),
    ]}
    solids = {"machined_body": _box((40, -18, 5), (200, 18, 23))}
    solids.update({k: _box(*b) for k, b in things.items()})
    r = legality._visibility_checks(asm, solids)
    return {k for k, v in r.items() if not v["pass"]}, r


VIS_EDGES = {
    # 5.0 mm of clear air behind the front wing's trailing edge (x = 28).
    "T8.7_front_wing_clear_air_all_parts": ((28 + 5.2, 15, 10), (28 + 4.8, 15, 10)),
    # 5.0 mm under the rear wing (z = 40).
    "T9.6_rear_wing_clear_air_all_parts": ((40 - 5.2, None, None), (40 - 4.8, None, None)),
    # Front wheel hidden from the front only up to 20.0 mm.
    "T7.11_front_wheel_seen_from_front": ((19.8, None, None), (20.2, None, None)),
}


def _thing(rule, v):
    if rule.startswith("T8.7"):
        return {"thing": ((v[0], 16, 6), (v[0] + 5, 19, 9))}
    if rule.startswith("T9.6"):
        return {"thing": ((205, 10, 30), (225, 20, v[0]))}
    return {"thing": ((-10, 25, 10), (0, 32, v[0]))}


@pytest.mark.parametrize("rule", sorted(VIS_EDGES))
def test_sight_and_air_edges(rule, tmp_path):
    inside, outside = VIS_EDGES[rule]
    (tmp_path / "in").mkdir()
    (tmp_path / "out").mkdir()
    bad, r = _vis(tmp_path / "in", _thing(rule, inside))
    assert not bad, (rule, "inside", {k: r[k] for k in bad})
    bad, r = _vis(tmp_path / "out", _thing(rule, outside))
    assert bad == {rule}, (rule, "outside", bad, r.get(rule))
