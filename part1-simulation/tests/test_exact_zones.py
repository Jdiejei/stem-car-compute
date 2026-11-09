"""exact_zones: every distance field agrees with the mask it replaces, cell by cell.

Inside a zone by more than a hair -> the mask has the cell. A mask cell is inside the zone,
or (for masks grown by a cell on purpose: the T7.9 wedges, the T8.5.1 cap) within one cell
of it. Checked on the right half (y >= 0; the masks are mirrored) at 1.0 and 0.75 mm, the
second because its cells do not line up with the zones' millimetre faces.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

LAY = (127.0, 49.0, 41.0)
EPS = 1e-6


def _setup(spacing):
    import coarse
    coarse.use_spacing(spacing)
    import unified_phi as up
    g = up.build_unified_geometry(*LAY, init_mode="full")
    r, d = g.region, up.GRID_SPACING_M
    X, Y, Z = np.meshgrid(*[(r.origin_m[a] + np.arange(r.shape[a]) * d) * 1e3 for a in range(3)], indexing="ij")
    right = Y >= -1e-9
    _XYZ[:] = [(X, Y, Z)]
    return g, X, Y, Z, right, d * 1e3


_XYZ = []


def _where(sel, field):
    """Where the disagreeing cells are, for the message: x, |y|, z ranges (mm) and field values."""
    X, Y, Z = _XYZ[0]
    return (f"x {X[sel].min():.2f}..{X[sel].max():.2f} |y| {np.abs(Y[sel]).min():.2f}..{np.abs(Y[sel]).max():.2f} "
            f"z {Z[sel].min():.2f}..{Z[sel].max():.2f} field {field[sel].min():.3f}..{field[sel].max():.3f}")


def _agree(field, mask, right, d_mm, grown=0.0, name="", shrunk=0.0):
    # shrunk: a mask drawn up to a cell inside its zone (the loft ceiling rounds up a cell)
    bad = (field > shrunk + EPS) & right & ~mask
    assert not bad.any(), f"{name}: {int(bad.sum())} cells inside the zone, not in the mask: {_where(bad, field)}"
    stray = mask & right & (field < -(grown + EPS))
    assert not stray.any(), f"{name}: {int(stray.sum())} mask cells outside the zone by > {grown} mm: {_where(stray, field)}"


@pytest.mark.parametrize("spacing", [1.0, 0.75])
def test_each_zone_field_matches_its_mask(spacing):
    import exact_zones as ez
    import halo_pocket as hp
    import unified_phi as up
    from bounding_volumes import default_rule_envelope
    from wheel_visibility_zones import build_t79_forbidden_mask
    g, X, Y, Z, right, d = _setup(spacing)
    aY = np.abs(Y)
    r = g.region
    border = np.zeros(r.shape, bool)
    border[[0, -1], :, :] = border[:, [0, -1], :] = border[:, :, [0, -1]] = True
    ref_A = g.landmarks["ref_plane_A_m"] * 1e3

    _agree(ez.envelope_air(X, aY, Z, g.bv, default_rule_envelope(), d),
           g.labels == up.LABEL_NONE, right & ~border, d, name="envelope")   # the grid seal is not a zone
    _agree(ez.wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm),
           up.wheel_keepclear_mask(r, g.W_mm, g.x_front_mm), right, d, name="wheel columns")
    t79 = np.zeros(r.shape, bool)
    for comp in ("main_body", "sidepod", "rearpod"):
        m = build_t79_forbidden_mask(comp, r.origin_m, r.shape, g.W_mm, g.x_front_mm)
        if m is not None:
            t79 |= m
    _agree(ez.t79_zones(X, aY, Z, g.W_mm, g.x_front_mm), t79, right, d, grown=d, name="T7.9")
    pb = (hp.build_halo_pocket_forbidden_mask(r.origin_m, r.shape, ref_A / 1e3, g.d_halo_mm)
          | hp.build_ballast_container_forbidden_mask(r.origin_m, r.shape, ref_A / 1e3, g.d_halo_mm))
    _agree(ez.halo_pocket_and_ballast(X, aY, Z, ref_A, g.d_halo_mm, d), pb, right, d, name="pocket and ballast")
    _agree(ez.block_slot(X, aY, Z), up.model_block_slot_mask(r), right, d, name="block slot")
    cap = up.build_rule_masks(g)[0]
    _agree(ez.t851_cap(X, aY, Z, ref_A), cap, right, d, grown=d, name="T8.5.1 cap")


def test_box_distance_is_exact():
    import exact_zones as ez
    p = np.array([0.0, 2.0, 5.0, 13.0])
    X, Y, Z = p, np.full(4, 0.0), np.full(4, 0.0)
    sd = ez._box(X, Y, Z, x=(1.0, 10.0), y=(-1.0, 1.0), z=(-1.0, 1.0))
    assert np.allclose(sd, [-1.0, 1.0, 1.0, -3.0])
    corner = ez._box(np.array([13.0]), np.array([5.0]), np.array([0.0]), x=(1.0, 10.0), y=(-1.0, 1.0))
    assert np.isclose(corner[0], -5.0)


def test_stamp_puts_a_flat_face_on_the_zone_at_any_grid():
    """A solid block stamped: the block slot's top face (exact, no margin: Part 4 cuts it)
    lands on its drawn height within a few hundredths of a mm, at 1.0 and 0.75 mm."""
    import exact_zones as ez
    from geometry_contract import MODEL_BLOCK_SLOT_TOP_Z_MM as top
    for spacing in (1.0, 0.75):
        g, X, Y, Z, right, d = _setup(spacing)
        g.phi.grid[:] = -1e-3                      # all solid, then stamp
        ez.stamp(g, X, Y, Z)
        j = int(np.argmin(np.abs(Y[0, :, 0])))
        col = g.phi.grid[X.shape[0] // 2, j, :] * 1e3
        k = np.where((col[:-1] > 0) & (col[1:] <= 0))[0][0]
        z0 = Z[0, 0, k] + col[k] / (col[k] - col[k + 1]) * (Z[0, 0, k + 1] - Z[0, 0, k])
        assert abs(z0 - top) < 0.02, (spacing, z0)


def test_half_body_mesh_stays_out_of_every_zone():
    """After smoothing, no vertex of the half body is inside a rule zone (Part 4 found the
    slot's top corners rounded 0.2 mm into the block slot, 2026-11-09)."""
    import exact_zones as ez
    import unified_phi as up
    g, *_ = _setup(1.0)
    up.enforce_symmetry(g)
    mesh = up.extract_half_surface(g)
    a = ez.air_at_points(g, np.asarray(mesh.vertices) * 1e3)
    assert a.max() <= 1e-3, f"{int((a > 1e-3).sum())} vertices inside a zone, worst {a.max():.3f} mm"
    assert mesh.is_watertight and mesh.is_volume


@pytest.mark.parametrize("spacing", [1.0, 0.75])
def test_halo_zone_fields_match_their_masks(spacing):
    """The halo void, its visibility shadows (T4.4.2/T4.4.3) and the loft ceiling."""
    import exact_zones as ez
    import fixed_hardware as fh
    g, X, Y, Z, right, d = _setup(spacing)
    r, hw = g.region, g.fixed_hardware
    mask = (hw.halo_void_mask
            | fh.halo_visibility_air_mask(hw.halo_void_mask, z_origin_m=r.origin_m[2], dz_m=d / 1e3)
            | fh.halo_canister_loft_air_mask(hw.halo_void_mask, hw.canister_cylinder, x_origin_m=r.origin_m[0],
                                             y_origin_m=r.origin_m[1], z_origin_m=r.origin_m[2], d_m=d / 1e3))
    f = ez.halo_zones(X, np.abs(Y), Z, g.landmarks["ref_plane_A_m"] * 1e3, g.d_halo_mm, hw.canister_cylinder)
    _agree(f, mask, right, d, grown=d, name="halo", shrunk=d)


def test_slot_corners_are_sharp_in_the_half_body():
    """No body inside the block slot: its top edges are inside corners of the body, which
    marching cubes chamfered 0.2 mm into the slot (5.5 mm3 on Part 4's start car)."""
    import trimesh
    import unified_phi as up
    from geometry_contract import MODEL_BLOCK_SLOT_TOP_Z_MM, MODEL_BLOCK_SLOT_WIDTH_MM
    g, *_ = _setup(1.0)
    up.enforce_symmetry(g)
    half = up.extract_half_surface(g)
    slot = trimesh.creation.box(extents=[400.0, MODEL_BLOCK_SLOT_WIDTH_MM, 40.0])
    slot.apply_translation([200.0, 0.0, MODEL_BLOCK_SLOT_TOP_Z_MM - 20.0])
    h = half.copy()
    h.apply_scale(1e3)
    assert h.is_volume, "the half body is not a closed volume"
    inside = h.intersection(slot, engine="manifold").volume
    assert inside < 0.5, f"{inside:.2f} mm3 of body inside the block slot"
