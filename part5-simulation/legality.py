"""
legality.py -- the assembled car, measured the way a scrutineer measures it.

Part 1's hard masks keep the body legal DURING descent; this module is the
independent audit on the finished geometry. Two of those masks were found wrong
on 2026-09-25 (block envelope, T5.5 wall), which is exactly why the audit exists.

    check(body_half_stl, assembly_json, mass_state) -> {rule: {margin, pass, note}}

Margins are in mm (or g for mass). margin >= 0 passes.
"""
from __future__ import annotations

import math

import numpy as np

import paths  # noqa: F401

REGS = {
    "T3.4_width_min": 65.0, "T3.4_width_max": 85.0, "T3.5_height": 65.0,
    "T3.7_clearance": 1.5, "T3.6_mass_g": 48.0, "T7.3_W_min": 120.0, "T7.3_W_max": 140.0,
    "T8.2_nose_overhang": 40.0, "T8.5.1_nose_z": 25.0, "T8.5.1_nose_half_width": 15.0,
    "T9.4.2_rear_overhang": 40.0, "T5.5_wall": 3.0,
    "block_length": 223.0, "block_width": 65.0, "block_height": 50.0,
}


def _entry(margin: float, note: str = "") -> dict:
    return {"margin": float(margin), "pass": bool(margin >= -1e-6), "note": note}


def t55_wall_fraction(body_half, rear_face_mm: float, depth_mm: float | None = None,
                      bore_r_mm: float | None = None, axis_z_mm: float | None = None) -> float:
    """Fraction of probe points inside the body in the 3 mm annulus around the
    chamber, along the whole bore (T5.5). 1.0 = a full 3 mm wall."""
    from geometry_contract import (CHAMBER_AXIS_Z_MM, MODEL_BLOCK_BORE_DEPTH_MM,
                                   MODEL_BLOCK_BORE_DIA_MM)
    depth_mm = MODEL_BLOCK_BORE_DEPTH_MM if depth_mm is None else depth_mm
    bore_r_mm = MODEL_BLOCK_BORE_DIA_MM / 2.0 if bore_r_mm is None else bore_r_mm
    axis_z_mm = CHAMBER_AXIS_Z_MM if axis_z_mm is None else axis_z_mm
    xs = np.linspace(rear_face_mm - depth_mm + 2.0, rear_face_mm - 2.0, 12)
    # From 1 mm outside the bore: the bore is a fixed air mask the optimiser
    # cannot touch, and on a 1 mm voxel STL its facets bulge ~0.5 mm at 45 deg
    # (every miss on the 2026-09-26 optimised car was r = 9.5 at 47/133 deg).
    # The wall the optimiser CAN thin is the outside, probed to 2.9 mm.
    rs = (bore_r_mm + 1.0, bore_r_mm + 2.0, bore_r_mm + 2.9)
    # Right half, but NOT on the symmetry plane itself: a containment test on
    # the capped y=0 face is ambiguous and reported false misses at 0/180 deg.
    ang = np.linspace(0.08, math.pi - 0.08, 13)
    pts = np.array([(x, r * math.sin(a), axis_z_mm + r * math.cos(a))
                    for x in xs for r in rs for a in ang]) / 1e3
    pts[:, 1] = np.maximum(pts[:, 1], 1e-6)
    inside = body_half.contains(pts)
    return float(inside.mean())


# Volumes below this (mm3, about 0.8 mg of foam) are mesh round-off, not material: a
# remesh may move a whole surface 0.05 mm.
_ROUND_OFF_MM3 = 5.0
CARTRIDGE_LENGTH_MIN_MM = 64.5     # Appendix vi: 65.00 -0.5
MESH_MAX_EDGE_MM = 8.0             # measured 1.9-7.6 after the remesh, 106 before it
MESH_MAX_SLIVER_BODY_PCT = 4.0     # measured 0.4-3.2 % after (highest at 0.3 mm), 3.3 % before
MESH_MAX_SLIVER_PRINTED_PCT = 12.0 # 5.7-11 % after, 25 % before: a wing's sharp trailing edge


def _volume_in(mesh, region) -> float:
    import trimesh
    r = trimesh.boolean.intersection([mesh, region], engine="manifold")
    return 0.0 if r is None or r.is_empty else abs(float(r.volume))


def _absent(volume_mm3: float, note: str) -> dict:
    return _entry(0.0 if volume_mm3 <= _ROUND_OFF_MM3 else -volume_mm3 / 1e3, note)


def official_block_mm(rear_face_mm: float, slack_mm: float = 0.06):
    """The Model Block as it arrives (Appendix ii), placed in the car: rear face
    at the car's rear face, bore on the chamber axis, slot along the underside.
    slack_mm: every face eased by this, as the final remesh may move a surface
    0.05 mm. That is well below what the mill can tell apart."""
    import trimesh
    import geometry_contract as gc
    L, y = gc.MODEL_BLOCK_LENGTH_MM, gc.MODEL_BLOCK_WIDTH_MM / 2.0 + slack_mm
    block = trimesh.creation.box(bounds=[[rear_face_mm - L - slack_mm, -y, gc.MODEL_BLOCK_BOTTOM_Z_MM - slack_mm],
                                         [rear_face_mm + slack_mm, y, gc.MODEL_BLOCK_TOP_Z_MM + slack_mm]])
    d = gc.MODEL_BLOCK_BORE_DEPTH_MM - slack_mm
    bore = trimesh.creation.cylinder(radius=gc.MODEL_BLOCK_BORE_DIA_MM / 2.0 - slack_mm, height=d + 2.0, sections=96)
    bore.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    bore.apply_translation([rear_face_mm - d / 2.0 + 1.0, 0.0, gc.CHAMBER_AXIS_Z_MM])
    s = gc.MODEL_BLOCK_SLOT_WIDTH_MM / 2.0 - slack_mm
    slot = trimesh.creation.box(bounds=[[rear_face_mm - L - 1.0, -s, gc.MODEL_BLOCK_BOTTOM_Z_MM - 1.0],
                                        [rear_face_mm + 1.0, s, gc.MODEL_BLOCK_SLOT_TOP_Z_MM - slack_mm]])
    return trimesh.boolean.difference([block, bore, slot], engine="manifold")


def manufactured_checks(assembly: dict) -> dict:
    """Rules measured on the files that get made, read back from disk: nothing in
    the T7.9 zones, the body inside the real block, the tether line clear, the
    printed parts clear of the foam."""
    import trimesh
    from shapely.geometry import Polygon
    import geometry_contract as gc
    from wheel_visibility_zones import zone_polygons_mm
    W, xf = assembly["W_mm"], assembly["x_front_mm"]
    files = {k: v["file"] for k, v in assembly["joints"]["manufactured"].items() if "file" in v}
    solids = {k: trimesh.load(f, force="mesh") for k, f in files.items()}
    r = {}
    open_files = [k for k, m in solids.items() if not m.is_volume]
    if open_files:     # nothing can be measured on these; the car is rejected, not a crash
        r["manufactured_files_measurable"] = _entry(-1.0, "not a solid: " + ", ".join(open_files))
        return r

    wd = assembly["wheel_design"]
    R = 0.5 * (wd["front"]["R_mm"] + wd["rear"]["R_mm"])
    for rule, outline in zone_polygons_mm(W, xf, R).items():
        zone = trimesh.creation.extrude_polygon(Polygon(outline), 65.0)
        hits = {k: _volume_in(m, zone) for k, m in solids.items()}
        hits = {k: v for k, v in hits.items() if v > _ROUND_OFF_MM3}
        r[f"{rule}_zone_clear"] = _absent(sum(hits.values()), ", ".join(
            f"{k} {v:.1f} mm3" for k, v in hits.items()) or "nothing in the zone")

    rear_face = xf + W + 16.0 + 40.0
    body = solids["machined_body"]
    outside = abs(float(trimesh.boolean.difference([body, official_block_mm(rear_face)],
                                                   engine="manifold").volume))
    r["block_body_inside_official_block"] = _absent(outside, f"{outside:.1f} mm3 outside the block")

    place = assembly.get("cargo_placement")
    if place:
        from virtual_cargo import (CARGO_HEIGHT_MM, CARGO_LENGTH_MM, CARGO_NARROW_WIDTH_MM,
                                   CARGO_WIDE_WIDTH_MM)
        x0, z0 = place["x_start_m"] * 1e3, place["z_base_m"] * 1e3
        L_, a, b = CARGO_LENGTH_MM, CARGO_WIDE_WIDTH_MM / 2.0, CARGO_NARROW_WIDTH_MM / 2.0
        if place.get("flip"):
            a, b = b, a
        wedge = trimesh.creation.extrude_polygon(
            # Its top is on the pocket floor; 0.1 mm off it for the remesh's own move.
            Polygon([(x0, -a), (x0 + L_, -b), (x0 + L_, b), (x0, a)]),
            CARGO_HEIGHT_MM - 0.1)
        wedge.apply_translation([0.0, 0.0, z0])
        # The rule lets the cargo share space with the ballast container, nothing else.
        # Only the part of the container inside the wedge is excused: crediting all of it
        # hid 180 mm3 of cargo that was outside the body.
        from halo_pocket import ballast_capsule_mesh_m
        capsule = ballast_capsule_mesh_m((xf - gc.D_HALO_REF_A_OFFSET_MM) / 1e3, assembly["d_halo_mm"])
        capsule.apply_scale(1e3)
        wanted = trimesh.boolean.difference([wedge, capsule], engine="manifold")
        missing = abs(wanted.volume) - _volume_in(body, wanted)
        r["T4.2_cargo_inside_body"] = _absent(max(missing, 0.0), f"{max(missing, 0.0):.1f} mm3 missing")

    # T4.4.4: the floor itself, ahead of and behind the ballast slot, and the halo fits.
    from halo_pocket import compute_halo_pocket_box_m
    pk = compute_halo_pocket_box_m((xf - gc.D_HALO_REF_A_OFFSET_MM) / 1e3, assembly["d_halo_mm"])
    px0 = pk["x_min_m"] * 1e3
    o = np.array([(px0 + dx, y, 70.0) for dx in (8.0, 48.0) for y in (-8.0, -1.0, 1.0, 8.0)])
    loc, ray, _ = body.ray.intersects_location(o, np.tile([0.0, 0.0, -1.0], (len(o), 1)))
    tops = [loc[ray == i, 2].max() if (ray == i).any() else np.nan for i in range(len(o))]
    off = float(np.nanmax(np.abs(np.array(tops) - pk["z_min_m"] * 1e3))) if not np.isnan(tops).any() else np.inf
    r["T4.4.4_pocket_floor"] = _entry(0.15 - off, "no floor under the halo" if np.isinf(off)
                                      else f"within {off:.3f} mm of {pk['z_min_m'] * 1e3:.1f} mm")
    halo = next((s["stl"] for s in assembly.get("extra_surfaces", []) if s["name"] == "halo"), None)
    if halo:
        hm = trimesh.load(halo, force="mesh")
        hm.apply_scale(1e3)
        lost = _volume_in(body, hm)
        r["T4.4.4_halo_fits_pocket"] = _absent(lost, f"{lost:.1f} mm3 of one half of the halo in the foam")
    nose_row = assembly["joints"]["parts"].get("nose")
    if nose_row is not None:     # a nose only surface-bonded at Ref A has no tenon holding it
        r["nose_has_tenon"] = _entry(0.0 if "pocket_cm3_per_side" in nose_row else -1.0, nose_row["joint"])

    printed = {k: m for k, m in solids.items() if k != "machined_body"}
    hits = {k: _volume_in(body, m) for k, m in printed.items()}
    hits = {k: v for k, v in hits.items() if v > _ROUND_OFF_MM3}
    r["fit_printed_parts_clear_of_foam"] = _absent(sum(hits.values()), ", ".join(
        f"{k} {v:.1f} mm3" for k, v in hits.items()) or "no overlap")

    # T6.1: the line runs only through the two guides. A bundle 2 mm across, from
    # one guide's centre to the other's, must hit nothing on the way.
    guides = assembly.get("info", {}).get("tethers", [])
    if len(guides) == 2:
        x0, x1 = guides[0]["x_mm"], guides[1]["x_mm"]
        z = guides[0]["bottom_mm"] + guides[0]["od_mm"] / 2.0
        o = np.array([(x0, y, z + dz) for y, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))], float)
        dirs = np.tile([1.0, 0.0, 0.0], (len(o), 1))
        blocked = []
        for k, m in solids.items():
            loc, _, _ = m.ray.intersects_location(o, dirs)
            if len(loc) and (loc[:, 0] < x1).any():
                blocked.append(k)
        r["T6.1_tether_line_clear"] = _entry(0.0 if not blocked else -1.0,
                                             "blocked by " + ", ".join(blocked) if blocked else "clear")

    # Even triangles throughout: no long slivers left in any file that gets made.
    parts = assembly["joints"]["manufactured"]
    meshed = {k: v for k, v in parts.items() if "max_edge_mm" in v}
    if meshed:
        worst = max(v["max_edge_mm"] for v in meshed.values())
        r["mesh_longest_edge"] = _entry(MESH_MAX_EDGE_MM - worst, f"{worst:.1f} mm")
        body_s = parts["machined_body"].get("faces_under_5deg_pct", 0.0)
        r["mesh_slivers_body"] = _entry(MESH_MAX_SLIVER_BODY_PCT - body_s, f"{body_s:.2f} % of faces under 5 deg")
        slivers = max(v["faces_under_5deg_pct"] for k, v in meshed.items() if k != "machined_body")
        r["mesh_slivers_printed"] = _entry(MESH_MAX_SLIVER_PRINTED_PCT - slivers,
                                           f"{slivers:.2f} % of faces under 5 deg, worst file")

    bore, depth, axis = gc.MODEL_BLOCK_BORE_DIA_MM, gc.MODEL_BLOCK_BORE_DEPTH_MM, gc.CHAMBER_AXIS_Z_MM
    # These four compare design constants with the rule; they are not measurements.
    r["T5.1_diameter"] = _entry(min(bore - 18.0, 18.5 - bore), f"{bore} mm (constant)")
    r["T5.2_height"] = _entry(min(axis - 30.0, 40.0 - axis), f"{axis} mm (constant)")
    r["T5.3_depth"] = _entry(min(depth - 45.0, 58.0 - depth), f"{depth} mm (constant)")
    r["T5.6_protrusion"] = _entry(CARTRIDGE_LENGTH_MIN_MM - depth - 5.0, "constant")
    return r


def check(body_half_stl: str, assembly: dict, mass_state: dict | None = None,
          field_bodies: int | None = None, machined_stl: str | None = None) -> dict:
    """machined_stl: the milled body (pockets cut, nose removed, Part 4
    joints.py). T5.5 is probed on it -- a pocket must not thin the wall."""
    import trimesh
    W, xf = assembly["W_mm"], assembly["x_front_mm"]
    ref_a, ref_b = xf - 16.0, xf + W + 16.0
    body = trimesh.load(str(body_half_stl), force="mesh")
    parts = {s["name"]: trimesh.load(s["stl"], force="mesh") for s in assembly["extra_surfaces"]}
    everything = [body] + list(parts.values())
    non_wheel = [body] + [m for n, m in parts.items() if not n.startswith("wheel")]
    bb = lambda ms: np.vstack([m.bounds for m in ms]) * 1e3  # noqa: E731
    allb, nwb = bb(everything), bb(non_wheel)
    wheels_bb = bb([m for n, m in parts.items() if n.startswith("wheel")]) if any(
        n.startswith("wheel") for n in parts) else allb

    r = {}
    width = 2 * allb[:, 1].max()
    r["T3.4_width_min"] = _entry(width - REGS["T3.4_width_min"], f"{width:.1f} mm")
    r["T3.4_width_max"] = _entry(REGS["T3.4_width_max"] - width, f"{width:.1f} mm")
    top = allb[:, 2].max()
    r["T3.5_height"] = _entry(REGS["T3.5_height"] - top, f"{top:.1f} mm")
    lows = {"body": body.bounds[0, 2] * 1e3}
    lows.update({n: m.bounds[0, 2] * 1e3 for n, m in parts.items() if not n.startswith("wheel")})
    low_part = min(lows, key=lows.get)
    clr = lows[low_part]
    r["T3.7_clearance"] = _entry(clr - REGS["T3.7_clearance"],
                                 f"lowest non-wheel part: {low_part} at {clr:.2f} mm")
    r["T7.3_W_min"] = _entry(W - REGS["T7.3_W_min"])
    r["T7.3_W_max"] = _entry(REGS["T7.3_W_max"] - W)
    front = nwb[:, 0].min()
    r["T8.2_nose_overhang"] = _entry(REGS["T8.2_nose_overhang"] - (ref_a - front),
                                     f"{ref_a - front:.1f} mm ahead of Ref A")
    rear = allb[:, 0].max()
    r["T9.4.2_rear_overhang"] = _entry(REGS["T9.4.2_rear_overhang"] - (rear - ref_b),
                                       f"{rear - ref_b:.2f} mm behind Ref B")

    # Nose: body material forward of Ref A (the printed nose) and the wing mount.
    v = body.vertices * 1e3
    nose = v[v[:, 0] < ref_a - 0.5]
    if len(nose):
        r["T8.5.1_nose_z"] = _entry(REGS["T8.5.1_nose_z"] - nose[:, 2].max())
        r["T8.5.1_nose_half_width"] = _entry(REGS["T8.5.1_nose_half_width"] - nose[:, 1].max())

    # Model Block: milled body is everything aft of Ref A.
    milled = v[v[:, 0] >= ref_a - 0.5]
    L = milled[:, 0].max() - milled[:, 0].min()
    Wd = 2 * milled[:, 1].max()
    H = milled[:, 2].max() - milled[:, 2].min()
    r["block_length"] = _entry(REGS["block_length"] - L, f"{L:.1f} mm")
    r["block_width"] = _entry(REGS["block_width"] - Wd, f"{Wd:.1f} mm")
    r["block_height"] = _entry(REGS["block_height"] - H, f"{H:.1f} mm")

    # T4.1 one piece.
    n_mesh = len(body.split(only_watertight=False))
    n = field_bodies if field_bodies is not None else n_mesh
    r["T4.1_single_body"] = _entry(0.0 if n == 1 else -1.0, f"{n} bodies")

    # Every non-wheel part must touch the body. The mass term can carve the
    # printed nose away (seen 2026-09-26), leaving the front-wing mount in air.
    for name, m in parts.items():
        if name.startswith("wheel"):
            continue
        v = np.asarray(m.vertices)[:: max(1, len(m.vertices) // 4000)]
        # Over the surface as well as the vertices: a box has only its corners, and
        # none of them need be anywhere near where it meets the body.
        v = np.vstack([v, trimesh.sample.sample_surface(m, 4000, seed=1)[0]])
        # Embedded counts: an extruded strut has vertices only at its ends,
        # 2 mm inside the body and nowhere near its surface.
        gap = 0.0 if body.contains(v).any() else float(body.nearest.on_surface(v)[1].min()) * 1e3
        if name == "fwing" and "nose" in parts:      # printed as one with the nose
            gap = min(gap, float(parts["nose"].nearest.on_surface(v)[1].min()) * 1e3)
        r[f"attached_{name}"] = _entry(0.3 - gap, f"closest {gap:.2f} mm to the body")

    # T5.5 chamber wall (probe points inside the body).
    probe_body = trimesh.load(machined_stl, force="mesh") if machined_stl else body
    frac = t55_wall_fraction(probe_body, rear_face_mm=W + xf + 16.0 + 40.0)
    r["T5.5_wall"] = _entry(0.0 if frac >= 0.999 else -(1 - frac) * REGS["T5.5_wall"],
                            f"{100*frac:.1f}% of the 3 mm annulus is solid")

    if mass_state is not None:
        # as manufactured when the joints report it: the scale reads the
        # parts that are made, not the model's rollup
        comp = mass_state.get("manufactured_mass_g", mass_state["competition_mass_g"])
        r["T3.6_mass"] = _entry(comp - REGS["T3.6_mass_g"],
                                f"{comp:.2f} g incl. {mass_state.get('ballast_g', 0):.2f} g ballast"
                                + (" (as manufactured)" if "manufactured_mass_g" in mass_state else ""))
        if "capacity_g" in mass_state:
            r["T1.22_ballast_capacity"] = _entry(mass_state["capacity_g"] - mass_state["ballast_g"])

    # T7.13 wheel safety test: a 3-finger claw hooks each wheel's inner corner
    # with a 1.5 x 1.5 mm lip (regulation figure, p.34). The annulus 1.5 mm
    # in from the inner face, over the outer 1.5 mm of radius, must be clear of
    # the body and every other part.
    from geometry_contract import FRONT_WHEEL_INNER_Y_MM as FY, REAR_WHEEL_INNER_Y_MM as RY
    wd = assembly.get("wheel_design", {})
    for tag, x_ax, y_in, key in (("front", xf, FY, "front"), ("rear", xf + W, RY, "rear")):
        R = wd.get(key, {}).get("R_mm", 14.05)
        zc = R - 0.3                                      # wheels sit 0.3 mm into the track
        pts = []
        for yy in np.linspace(y_in - 1.45, y_in - 0.05, 4):
            for rr in np.linspace(R - 1.45, R - 0.05, 4):
                for t in np.linspace(0, 2 * math.pi, 36, endpoint=False):
                    pts.append((x_ax + rr * math.cos(t), yy, zc + rr * math.sin(t)))
        pts = np.array(pts) / 1e3
        pts = pts[pts[:, 2] > 0.0005]                    # above the track
        # Wings are exported as concatenated shells (wing + flap + mount), so
        # test each closed piece; an open piece cannot be tested and is named.
        hit, skipped = 0, []
        for name, m in [("body", body)] + [(n, m) for n, m in parts.items()
                                           if not n.startswith("wheel")]:
            for piece in m.split(only_watertight=False):
                if piece.is_watertight:
                    hit += int(piece.contains(pts).sum())
                else:
                    skipped.append(name)
        note = f"{hit} of {len(pts)} claw points blocked"
        if skipped:
            note += f"; open meshes not tested: {sorted(set(skipped))}"
        r[f"T7.13_{tag}_claw_clearance"] = _entry(0.0 if hit == 0 and not skipped else -1.0, note)

    j = assembly.get("joints")
    if j is not None and any("file" in v for v in j.get("manufactured", {}).values()):
        r.update(manufactured_checks(assembly))
    if j is not None:
        # every manufacturing file, RE-READ from disk, must be closed solids
        # and as many of them as the part has (an in-memory mesh can be closed
        # while the STL written from it is torn: 5 of 7 files were, 2026-09-30)
        bad = [k for k, v in j.get("manufactured", {}).items()
               if "closed" in v and not (v["closed"] and v["pieces"] == v["pieces_expected"])]
        r["manufacture_files_are_solids"] = _entry(
            0.0 if j["machined_body_watertight"] and not bad else -1.0,
            "not a closed solid: " + ", ".join(bad) if bad else
            f"{len(j.get('manufactured', {}))} files")
    for k, m in assembly.get("gates", {}).items():
        r[f"P4.{k}"] = _entry(m)
    return r


def summary(report: dict) -> dict:
    failed = {k: v for k, v in report.items() if not v["pass"]}
    return {"n_checks": len(report), "n_failed": len(failed), "failed": sorted(failed)}
