"""Edge tests: for each numeric rule the referee measures, a car just inside the limit
(limit - 0.2 mm, or 0.2 g) must pass and a car just outside (limit + 0.2) must fail,
on the right rule id and nothing else. See RULES_MAP.md.

The cars are boxes (fast, exact): a known-good box car is edited one thing at a time.
Rules the referee does not yet measure itself (RULES_MAP.md "gate only" / "constant")
are not here; they get their own measurement and tests first.
"""
import math
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
    """A legal half car (mm, y >= 0): body with a nose stub ahead of Ref A, a front wing
    on a centre mount, a rear wing on a pylon, two wheels. Keyword overrides move one thing."""
    xf = 50.0
    ra, rb = xf - 16.0, xf + W + 16.0
    top = o.get("top", 50.0)
    rear = o.get("rear", rb + 40.0 - 0.2)
    body = trimesh.boolean.union(
        [_box((ra, 0, 5), (rear, 13.0, top)),
         _box((o.get("nose_x", ra - 20.0), 0, o.get("nose_lo", 9.0)),
              (ra + 0.5, o.get("nose_y", 10.0), o.get("nose_z", 20.0)))]
        + [_box(*b) for b in o.get("extra", [])], engine="manifold")
    if o.get("bore", True):                 # the chamber: diameter, centre height, depth, tilt
        d, z, depth, ang = (o.get("bore_d", 18.15), o.get("bore_z", AXIS_Z), o.get("bore_depth", 52.0),
                            o.get("bore_deg", 0.0))
        bore = trimesh.creation.cylinder(radius=d / 2.0, height=depth + 5.0, sections=96)
        bore.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        bore.apply_translation([rear - depth + (depth + 5.0) / 2.0, 0.0, z])
        if ang:
            bore.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 1, 0], [rear, 0, z]))
        body = trimesh.boolean.difference([body, bore], engine="manifold")
        if "bore_slit" in o:                # a groove along the bore's top, this wide (both halves)
            top_r = z + d / 2.0
            slit = _box((rear - depth + 1, 0, top_r - 0.5), (rear + 1, o["bore_slit"] / 2.0, top_r + 0.85))
            body = trimesh.boolean.difference([body, slit], engine="manifold")
    if "loose" in o:                        # a second, separate piece of foam
        body = trimesh.util.concatenate([body, _box(*o["loose"])])
    # Front wing: one element (chord 16, 2.5 thick, 30 out), a centre mount into the nose.
    x1, ft, fc = o.get("fw_x1", 26.0), o.get("fw_top", 8.5), o.get("fw_chord", 16.0)
    fwing = [_box((x1 - fc, 0, ft - o.get("fw_t", 2.5)), (x1, o.get("fw_half", 30.0), ft)),
             _box((15, 0, 7), (35, 1.5, 12))]
    if "fw_flap" in o:                      # (gap) main 10 long + flap 6 long, above it
        g = o["fw_flap"]
        fwing[0] = _box((10, 0, 6), (20, 30, 8.5))
        fwing.append(_box((20 + g, 0, 8.6), (26, 30, 11.1)))
    if "fw_plate" in o:                     # (y0, width, z0, z1)
        y0, w, z0, z1 = o["fw_plate"]
        fwing.append(_box((10, y0, z0), (26, y0 + w, z1)))
    # Rear wing: chord 16, 2.5 thick, 26 out, on a pylon from the body.
    x0, rz = o.get("rw_x0", rb + 4.0), o.get("rw_z", top + 6.0)
    rw = _box((x0, 0, rz), (x0 + o.get("rw_chord", 16.0), o.get("rw_half", 26.0), rz + o.get("rw_t", 2.5)))
    if "rw_shear" in o:                     # the wing's top rises (or falls) along the span
        rw.apply_transform([[1, 0, 0, 0], [0, 1, 0, 0], [0, o["rw_shear"], 1, 0], [0, 0, 0, 1.0]])
    pylon = _box((x0 + 5, 0, top + o.get("rw_gap", 0.0)), (x0 + 11, 1.0, rz + 0.5))
    parts = {
        "fwing": trimesh.util.concatenate(fwing),
        "rwing": trimesh.util.concatenate([rw, pylon]),
        "wheelF": _box((xf - 14.0, o.get("wf_y0", FY), 0), (xf + 14.0, o.get("wf_y", 36.5), 28.1)),
        "wheelR": _box((xf + W - 14.0, o.get("wr_y0", RY), 0), (xf + W + 14.0, o.get("wr_y", 33.5), 28.1)),
        # Tether guides, 5 mm out from each axle, hole 4.5 mm, each on a stalk into the body.
        "tethers": trimesh.util.concatenate(
            [guide(x, o.get("tg_id", 4.5)) for x in o.get("tg_x", (xf - 5.0, xf + W + 5.0))]),
    }
    parts.update({k: _box(*b) for k, b in o.get("extra_parts", {}).items()})
    # The wheels' own files (mm): (diameter, contact width), 0.5 mm chamfers each side.
    wf = {"front": (30.0, 13.5), "rear": (30.0, 17.5)} | o.get("wheels", {})
    files = {}
    for tag, (d, w) in wf.items():
        p = tmp / f"{tag}_wheel.stl"
        wheel(d, w).export(str(p))
        files[tag] = str(p)
    asm = {"W_mm": W, "x_front_mm": xf, "wheel_files": files,
           "extra_surfaces": [{"name": k, "stl": _save(tmp, k, m)} for k, m in parts.items()]}
    return _save(tmp, "body", body), asm


def guide(x, hole, od=8.0, bottom=2.0):
    """Right half of a ring along x (hole `hole` mm), its top set into the body's floor (mm)."""
    ring = trimesh.creation.annulus(r_min=hole / 2.0, r_max=od / 2.0, height=2.0, sections=96)
    ring.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    ring.apply_translation([x, 0.0, bottom + od / 2.0])
    return trimesh.intersections.slice_mesh_plane(ring, [0, 1.0, 0], [0, 0, 0], cap=True)


def wheel(d, contact, chamfer=0.5):
    """A wheel turned from a profile (mm): bore 3, tread `contact` wide at full diameter."""
    R, w = d / 2.0, contact + 2 * chamfer
    prof = [(1.5, 0), (R - chamfer, 0), (R, chamfer), (R, w - chamfer), (R - chamfer, w), (1.5, w), (1.5, 0)]
    return trimesh.creation.revolve(prof, sections=96)


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
              "T7.13_front_claw_clearance", "T7.13_rear_claw_clearance", "attached_fwing",
              "T8.6.1_front_span", "T8.6.2_front_chord_min", "T8.6.2_front_chord_max",
              "T8.6.3_front_thickness_min", "T8.6.3_front_thickness_max", "T8.6.2_front_vanes_overlap",
              "T8.5.2_front_wing_ahead_of_ref_A", "T8.5.2_front_wing_height_outboard",
              "T9.5.1_rear_span", "T9.5.2_rear_chord_min", "T9.5.2_rear_chord_max",
              "T9.5.3_rear_thickness_min", "T9.5.3_rear_thickness_max", "T9.5.2_rear_vanes_overlap",
              "T9.5.4_rear_height_deviation", "T9.4.1_rear_wing_behind_ref_B", "T7.2_front_gap",
              "T7.2_rear_gap", "T7.4_front_contact_width", "T7.4_rear_contact_width",
              "T7.5_front_diameter_min", "T7.5_rear_diameter_max"):
        assert k in r, k


RA = 34.0                               # Ref A of the base car
WALL = AXIS_Z + BORE_R                  # top of the bore

# rule id: (just inside, just outside, other rules the outside car also breaks)
EDGES = {
    "T3.4_width_min": ({"wf_y": 32.6, "wr_y": 32.6}, {"wf_y": 32.4, "wr_y": 32.4}, set()),
    "T3.4_width_max": ({"wf_y": 42.4}, {"wf_y": 42.6}, set()),
    "T3.5_height": ({"rw_z": 64.8 - 2.5}, {"rw_z": 65.2 - 2.5}, set()),
    "T3.7_clearance": ({"fw_plate": (31, 5, 1.7, 10)}, {"fw_plate": (31, 5, 1.3, 10)}, set()),
    "T7.3_W_min": ({"W": 120.2}, {"W": 119.8}, set()),
    "T7.3_W_max": ({"W": 139.8}, {"W": 140.2}, set()),
    "T8.2_nose_overhang": ({"nose_x": RA - 39.8}, {"nose_x": RA - 40.2}, set()),
    "T8.5.1_nose_z": ({"nose_z": 24.8}, {"nose_z": 25.2}, set()),
    "T8.5.1_nose_half_width": ({"nose_y": 14.8}, {"nose_y": 15.2}, set()),
    "T9.4.2_rear_overhang": ({"rw_x0": 196.0 + 39.8 - 16}, {"rw_x0": 196.0 + 40.2 - 16}, set()),
    "T9.4.1_rear_wing_behind_ref_B": ({"rw_x0": 196.2}, {"rw_x0": 195.8}, set()),
    # Front wing (Ref A at 34; the centre mount splits the span into two segments).
    "T8.6.1_front_span": ({"fw_half": 1.5 + 25.2}, {"fw_half": 1.5 + 24.8}, set()),
    "T8.6.2_front_chord_min": ({"fw_chord": 15.2}, {"fw_chord": 14.8}, set()),
    "T8.6.2_front_chord_max": ({"fw_chord": 24.8}, {"fw_chord": 25.2}, set()),
    "T8.6.3_front_thickness_min": ({"fw_t": 2.2}, {"fw_t": 1.8}, set()),
    "T8.6.3_front_thickness_max": ({"fw_t": 5.8}, {"fw_t": 6.2}, set()),
    "T8.6.2_front_vanes_overlap": ({"fw_flap": -0.2, "nose_lo": 11.5}, {"fw_flap": 0.2, "nose_lo": 11.5}, set()),
    # Past Ref A the wing runs into the body, which also splits its span.
    "T8.5.2_front_wing_ahead_of_ref_A": ({"fw_x1": 33.8}, {"fw_x1": 34.2}, {"T8.6.1_front_span"}),
    "T8.5.2_front_wing_height_outboard": ({"fw_top": 19.8, "nose_z": 15}, {"fw_top": 20.2, "nose_z": 15}, set()),
    "T8.5.3_endplate0_width": ({"fw_plate": (30, 9.8, 6, 12)}, {"fw_plate": (30, 10.2, 6, 12)}, set()),
    "T8.5.3_endplate0_outside_span": ({"fw_plate": (25.2, 5, 6, 12)}, {"fw_plate": (24.8, 5, 6, 12)}, set()),
    "T8.5.3_endplate0_height": ({"fw_plate": (30, 9.8, 6, 24.8)}, {"fw_plate": (30, 9.8, 6, 25.2)}, set()),
    # Tether guides (axles at 50 and 180): within 10 mm, on the outer side; hole 3.5-6.0.
    "T6.1_front_guide_position": ({"tg_x": (40.2, 185.0)}, {"tg_x": (39.8, 185.0)}, set()),
    "T6.1_rear_guide_position": ({"tg_x": (45.0, 189.8)}, {"tg_x": (45.0, 190.2)}, set()),
    "T6.2_front_hole_min": ({"tg_id": 3.6}, {"tg_id": 3.4}, {"T6.2_rear_hole_min"}),
    "T6.2_front_hole_max": ({"tg_id": 5.8}, {"tg_id": 6.2}, {"T6.2_rear_hole_max"}),
    # The cartridge chamber, found and measured on the body.
    "T5.1_diameter_min": ({"bore_d": 18.2}, {"bore_d": 17.8}, set()),
    "T5.1_diameter_max": ({"bore_d": 18.3}, {"bore_d": 18.7}, set()),
    "T5.2_height_min": ({"bore_z": 30.2}, {"bore_z": 29.8}, set()),
    "T5.2_height_max": ({"bore_z": 39.8, "top": 54.8}, {"bore_z": 40.2, "top": 54.8}, set()),
    "T5.3_depth_min": ({"bore_depth": 45.2}, {"bore_depth": 44.8}, set()),
    "T5.3_depth_max": ({"bore_depth": 57.8}, {"bore_depth": 58.2}, set()),
    "T5.4_angle": ({"bore_deg": 2.8}, {"bore_deg": 3.2}, set()),
    # Wheels: their own files, and where they stand.
    "T7.5_front_diameter_min": ({"wheels": {"front": (28.2, 13.5)}}, {"wheels": {"front": (27.8, 13.5)}}, set()),
    "T7.5_front_diameter_max": ({"wheels": {"front": (31.8, 13.5)}}, {"wheels": {"front": (32.2, 13.5)}}, set()),
    "T7.5_rear_diameter_min": ({"wheels": {"rear": (28.2, 17.5)}}, {"wheels": {"rear": (27.8, 17.5)}}, set()),
    "T7.5_rear_diameter_max": ({"wheels": {"rear": (31.8, 17.5)}}, {"wheels": {"rear": (32.2, 17.5)}}, set()),
    "T7.4_front_contact_width": ({"wheels": {"front": (30.0, 13.2)}}, {"wheels": {"front": (30.0, 12.8)}}, set()),
    "T7.4_rear_contact_width": ({"wheels": {"rear": (30.0, 17.2)}}, {"wheels": {"rear": (30.0, 16.8)}}, set()),
    "T7.2_front_gap": ({"wf_y0": 19.1}, {"wf_y0": 18.9}, set()),
    "T7.2_rear_gap": ({"wr_y0": 15.1}, {"wr_y0": 14.9}, set()),
    # Rear wing.
    "T9.5.1_rear_span": ({"rw_half": 25.2}, {"rw_half": 24.8}, set()),
    "T9.5.2_rear_chord_min": ({"rw_chord": 15.2}, {"rw_chord": 14.8}, set()),
    "T9.5.2_rear_chord_max": ({"rw_chord": 24.8}, {"rw_chord": 25.2}, set()),
    "T9.5.3_rear_thickness_min": ({"rw_t": 2.2}, {"rw_t": 1.8}, set()),
    "T9.5.3_rear_thickness_max": ({"rw_t": 5.8}, {"rw_t": 6.2}, set()),
    # Highest at the centre, falling outboard; measured over the 26 mm half span.
    "T9.5.4_rear_height_deviation": ({"rw_z": 62.0, "rw_shear": -14.8 / 26}, {"rw_z": 62.0, "rw_shear": -15.2 / 26}, set()),
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


def test_the_team_wheels_meet_the_wheel_rules():
    """The team's own wheel files, as the referee reads them by default."""
    from paths import PARTS
    for tag, need in (("front", 13.0), ("rear", 17.0)):
        m = legality.wheel_measures(trimesh.load(str(PARTS["part1-simulation"] / "hardware_cad" /
                                                     legality.TEAM_WHEELS[tag]), force="mesh"))
        print(tag, m)
        assert 28.0 <= m["diameter_mm"] <= 32.0 and m["contact_mm"] >= need, (tag, m)


@pytest.mark.parametrize("xs,rule", [((50.2, 185.0), "T6.1_front_guide_position"),
                                     ((45.0, 179.8), "T6.1_rear_guide_position"),
                                     ((45.0, 185.0, 100.0), "T6.1_two_guides")])
def test_guides_on_the_wrong_side_or_too_many(xs, rule, tmp_path):
    bad, r = fails(tmp_path, tg_x=xs)
    assert rule in bad, r.get(rule)
    if rule != "T6.1_two_guides":
        assert bad == {rule}, bad
    (tmp_path / "ok").mkdir()
    bad, _ = fails(tmp_path / "ok", tg_x=(49.8, 180.2))          # 0.2 mm out from each axle
    assert not bad, bad


def test_a_groove_in_the_bore_is_not_a_wider_bore_but_is_reported(tmp_path):
    # The real milled file has a notch at y = 0 along the bore (lab 2026-11-09). T5.1 is
    # judged with plug gauges, which a groove does not let through; calipers across it
    # read wider, and the note says so. An oversize bore fails (EDGES, T5.1_diameter_max).
    bad, r = fails(tmp_path, bore_slit=1.0)
    assert not bad, {k: r[k] for k in bad}
    across = float(r["T5.1_diameter_max"]["note"].split("widest across ")[1].split()[0])
    assert across > 19.5, r["T5.1_diameter_max"]


def test_a_body_without_a_chamber_fails(tmp_path):
    bad, _ = fails(tmp_path, bore=False)
    assert bad == {"T5_chamber_found"}, bad


def test_only_the_listed_parts(tmp_path):
    # A part that is not in T1.1's list (a fin on the body).
    bad, _ = fails(tmp_path, extra_parts={"fin": ((100, 0, 49), (120, 1, 55))})
    assert bad == {"T3.3_only_listed_parts"}, bad


def test_nothing_may_sit_in_the_chamber(tmp_path):
    """T5.5's last line, on the files that get made: a printed plug in the bore fails."""
    body, asm = build(tmp_path)
    made = tmp_path / "made"
    made.mkdir()
    m = trimesh.load(body, force="mesh")
    m.apply_scale(1e3)
    full = m.copy()
    full.vertices[:, 1] *= -1
    full.invert()
    full = trimesh.boolean.union([m, full], engine="manifold")
    full.export(str(made / "machined_body.stl"))
    rear = 50.0 + 130.0 + 16.0 + 40.0 - 0.2

    def judge(plug):
        files = {"machined_body": {"file": str(made / "machined_body.stl")}}
        if plug is not None:
            plug.export(str(made / "printed_plug.stl"))
            files["printed_plug"] = {"file": str(made / "printed_plug.stl")}
        a = dict(asm, d_halo_mm=40.0, joints={"manufactured": files, "parts": {}},
                 wheel_design={"front": {"R_mm": 14.05}, "rear": {"R_mm": 14.05}})
        return legality.manufactured_checks(a)["T5.5_chamber_clear"]

    assert judge(None)["pass"]
    plug = trimesh.creation.cylinder(radius=4.0, height=10.0, sections=48)
    plug.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    plug.apply_translation([rear - 20.0, 0.0, AXIS_Z])
    c = judge(plug)
    assert not c["pass"] and "printed_plug" in c["note"], c


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
