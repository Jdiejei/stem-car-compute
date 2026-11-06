"""The sight-line rules, on boxes standing in for the car's parts (mm)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _p in ("part1-simulation", "part2-simulation", "part4-simulation"):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / _p))

import trimesh

import legality


def _stl(tmp, name, lo, hi):
    """Parts' half meshes are stored in metres, right half."""
    m = trimesh.creation.box(bounds=[[v / 1e3 for v in lo], [v / 1e3 for v in hi]])
    p = tmp / f"{name}.stl"
    m.export(str(p))
    return {"name": name, "stl": str(p), "rotating": None}


def _assembly(tmp):
    return {"extra_surfaces": [
        _stl(tmp, "halo", (100, 0, 24), (150, 12.5, 39)),
        _stl(tmp, "wheelF", (35, 20, 0), (65, 36, 30)),
        _stl(tmp, "wheelR", (165, 20, 0), (195, 36, 30)),
        _stl(tmp, "fwing", (20, 16, 6), (28, 38, 9)),
        _stl(tmp, "nose", (0, 0, 8), (40, 10, 20)),
    ]}


def _box(lo, hi):
    return trimesh.creation.box(bounds=[lo, hi])


def test_a_clear_car_passes_every_sight_line(tmp_path):
    r = legality._visibility_checks(_assembly(tmp_path), {"machined_body": _box((40, -18, 5), (200, 18, 23))})
    assert all(v["pass"] for v in r.values()), r
    assert len(r) == 7


def test_each_sight_line_catches_what_blocks_it(tmp_path):
    a = _assembly(tmp_path)
    cases = {
        "T4.4.2_halo_seen_from_front": _box((80, -5, 30), (95, 5, 36)),
        "T4.4.2_halo_seen_from_side": _box((110, 40, 30), (120, 50, 36)),
        "T4.4.3_halo_seen_from_top": _box((110, -5, 45), (120, 5, 50)),
        "T7.10_wheelF_seen_from_side": _box((45, 40, 5), (55, 50, 25)),
        "T7.11_front_wheel_seen_from_front": _box((10, 25, 22), (20, 32, 28)),
        "T8.8_front_wing_seen_from_front": _box((5, 16, 5), (15, 38, 10)),
    }
    for rule, blocker in cases.items():
        assert not legality._visibility_checks(a, {"thing": blocker})[rule]["pass"], rule


def test_a_hub_behind_the_tread_does_not_hide_the_wheel(tmp_path):
    # Above 20 mm but behind the curve of the wheel; and a support may cover it from the side.
    hub = _box((45, 22, 21), (55, 34, 25))
    r = legality._visibility_checks(_assembly(tmp_path), {"printed_hubcaps_front": hub})
    assert r["T7.11_front_wheel_seen_from_front"]["pass"]
    side = _box((45, 40, 5), (55, 50, 25))
    assert legality._visibility_checks(_assembly(tmp_path), {"printed_hubcaps_front": side})["T7.10_wheelF_seen_from_side"]["pass"]
