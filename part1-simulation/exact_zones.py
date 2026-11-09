"""Exact signed distances to the forced-air rule zones (team lead, 2026-11-09).

The rule masks are yes/no per cell, so a zone's face snaps to a cell boundary and moves
by up to half a cell between grids: the same carved body weighed 0.5 to 2 % differently
at 1.0, 0.75 and 0.5 mm, against a 0.5 % bar. Here every zone that bounds the body is a
distance field in mm, positive inside the zone, written from the same numbers as its mask
builder (named on each function). The finished body takes phi = max(phi, zone + margin),
so its surface lands on the zone's true face, MARGIN_MM clear of it, at any grid.

Slanted faces (the T7.9 wedges) are scaled to true distance; box edges and corners use
the exact box distance. tests/test_exact_zones.py checks every field against its mask.
"""
from __future__ import annotations

import numpy as np

MARGIN_MM = 0.05     # clear of every zone by the same amount at any grid (referee's zone checks)


def _box(X, Y, Z, x=(None, None), y=(None, None), z=(None, None)):
    """Signed distance to an axis box, positive inside. None = unbounded on that side."""
    outs = []
    for c, (lo, hi) in ((X, x), (Y, y), (Z, z)):
        d = np.full(np.broadcast(X, Y, Z).shape, -np.inf)
        if lo is not None:
            d = np.maximum(d, lo - c)
        if hi is not None:
            d = np.maximum(d, c - hi)
        outs.append(d)
    m = np.maximum(np.maximum(outs[0], outs[1]), outs[2])
    out = np.sqrt(sum(np.maximum(o, 0.0) ** 2 for o in outs))
    return -(out + np.minimum(m, 0.0))


def envelope_air(X, aY, Z, bv, re, d_mm=1.0):  # d_mm None: points, max() (exact outside)
    """Outside the legal envelope (unified_phi._zone_masks): the union of the nose, sidepod,
    rearpod and main-body boxes; positive outside all of them."""
    mm = 1e3
    boxes = [
        _box(X, aY, Z, x=(None, bv.ref_plane_A_m * mm), y=(None, re.y_nose_half_m * mm),
             z=(re.z_floor_m * mm, re.z_nose_top_m * mm)),
        _box(X, aY, Z, x=(bv.sidepod_x_min_m * mm, bv.sidepod_x_max_m * mm),
             y=(re.y_sidepod_inner_m * mm, re.y_sidepod_outer_m * mm),
             z=(re.z_floor_m * mm, re.z_sidepod_top_m * mm)),
        _box(X, aY, Z, x=(bv.rearpod.origin_m[0] * mm, bv.rearpod.x_max_m() * mm),
             y=(None, re.y_body_half_m * mm), z=(re.z_floor_m * mm, re.z_rearpod_top_m * mm)),
        _box(X, aY, Z, x=(bv.ref_plane_A_m * mm, bv.rearpod.origin_m[0] * mm),
             y=(None, re.y_body_half_m * mm), z=(re.z_floor_m * mm, re.z_body_top_m * mm)),
    ]
    return -(union(boxes, d_mm) if d_mm else np.maximum.reduce(boxes))


def wheel_columns(X, aY, Z, W_mm, x_front_mm):
    """unified_phi.wheel_keepclear_mask: full-height columns over the four wheels."""
    from geometry_contract import (FRONT_WHEEL_INNER_Y_M, REAR_WHEEL_INNER_Y_M,
                                   R_WHEEL_M, WHEEL_CLEARANCE_M, WHEEL_WIDTH_M)
    from unified_phi import WHEEL_KEEPOUT_MARGIN_M as k
    r = (R_WHEEL_M + WHEEL_CLEARANCE_M + k) * 1e3
    out = []
    for ax, inner in ((x_front_mm, FRONT_WHEEL_INNER_Y_M), (x_front_mm + W_mm, REAR_WHEEL_INNER_Y_M)):
        y0 = (inner - WHEEL_CLEARANCE_M - k) * 1e3
        y1 = (inner + WHEEL_WIDTH_M + WHEEL_CLEARANCE_M) * 1e3
        out.append(_box(X, aY, Z, x=(ax - r, ax + r), y=(y0, y1)))
    return np.maximum(out[0], out[1])


def t79_zones(X, aY, Z, W_mm, x_front_mm):
    """wheel_visibility_zones.build_t79_forbidden_mask: the T7.9.1 and T7.9.4 rectangles and
    the T7.9.2 / T7.9.3 wedges, without the mask's one-cell growth (MARGIN_MM instead)."""
    import wheel_visibility_zones as wv
    from geometry_contract import R_WHEEL_M
    R = R_WHEEL_M * 1e3
    yf, yr = wv.FRONT_INNER_GAP_ACTUAL_MM / 2.0, wv.REAR_INNER_GAP_ACTUAL_MM / 2.0
    zt = wv.T79_ZONE_HEIGHT_MM
    ff, fa = x_front_mm - R, x_front_mm + R
    rf, ra = x_front_mm + W_mm - R, x_front_mm + W_mm + R
    rect_f = _box(X, aY, Z, x=(ff - wv.T79_RECT_DEPTH_MM, ff), y=(yf, None), z=(0.0, zt))
    rect_r = _box(X, aY, Z, x=(ra, ra + wv.T79_RECT_DEPTH_MM), y=(yr, None), z=(0.0, zt))

    def wedge(x_wheel, near, ang, aft, yi):
        a = np.radians(ang)
        depth = (X - x_wheel) if aft else (x_wheel - X)
        far = (near + (aY - yi) / np.tan(a) - depth) * np.sin(a)      # true distance to the slant
        slab = _box(depth, aY, Z, x=(0.0, None), y=(yi, yi + wv.T79_WIDTH_Y_MM), z=(0.0, zt))
        return np.minimum(slab, far)
    w_f = wedge(fa, wv.T79_FRONT_NEAR_X_MM, wv.T79_FRONT_ANGLE_DEG, True, yf)
    w_r = wedge(rf, wv.T79_REAR_NEAR_X_MM, wv.T79_REAR_ANGLE_DEG, False, yr)
    return np.maximum.reduce([rect_f, rect_r, w_f, w_r])


def halo_pocket_and_ballast(X, aY, Z, ref_A_mm, d_halo_mm, d_mm=1.0):
    """halo_pocket.build_halo_pocket_forbidden_mask and build_ballast_container_forbidden_mask
    (the capsule at its true size; the mask's one-cell inset is not needed here)."""
    import halo_pocket as hp
    box = hp.compute_halo_pocket_box_m(ref_A_mm / 1e3, d_halo_mm)
    b = {k: v * 1e3 for k, v in box.items()}
    pocket = _box(X, aY, Z, x=(b["x_min_m"], b["x_max_m"]), y=(None, b["y_max_m"]),
                  z=(b["z_min_m"], b["z_max_m"]))
    r = hp.BALLAST_SLOT_WIDTH_MM / 2.0
    hs = max(hp.BALLAST_SLOT_LENGTH_MM / 2.0 - r, 0.0)
    cx = b["x_min_m"] + hp.BALLAST_CENTRE_FROM_POCKET_FRONT_MM
    z_top, z_bot = b["z_min_m"], b["z_min_m"] - hp.BALLAST_DEPTH_MM
    plan = r - np.hypot(np.maximum(np.abs(X - cx) - hs, 0.0), aY)
    capsule = np.minimum(plan, np.minimum(Z - z_bot, z_top - Z))
    return union([pocket, capsule], d_mm) if d_mm else np.maximum(pocket, capsule)


def block_slot(X, aY, Z):
    """unified_phi.model_block_slot_mask: the block's 6 x 6 mm underside slot."""
    from geometry_contract import MODEL_BLOCK_SLOT_TOP_Z_MM, MODEL_BLOCK_SLOT_WIDTH_MM
    return _box(X, aY, Z, y=(None, MODEL_BLOCK_SLOT_WIDTH_MM / 2.0), z=(None, MODEL_BLOCK_SLOT_TOP_Z_MM))


def t851_cap(X, aY, Z, ref_A_mm):
    """unified_phi.build_rule_masks' T8.5.1 cap: within 1 mm of Ref A the body stays inside
    14.5 mm of the centreline and 24.5 mm of the track (the mask adds a cell; not needed)."""
    return np.minimum(ref_A_mm + 1.0 - X, np.maximum(aY - 14.5, Z - 24.5))
def _shift(a, s, axis, fill=0.0):
    """a moved by s cells along axis (value at p is a[p - s]); the cells it uncovers get fill."""
    out = np.full_like(a, fill)
    src = [slice(None)] * 3
    dst = [slice(None)] * 3
    if s > 0:
        src[axis], dst[axis] = slice(0, -s), slice(s, None)
    else:
        src[axis], dst[axis] = slice(-s, None), slice(0, s)
    out[tuple(dst)] = a[tuple(src)]
    return out


def union(fields, d_mm):
    """Signed distance to the union of shapes, positive inside, from each shape's own field.

    max() of the fields is exact outside the union but only a lower bound inside: where two
    shapes touch (the envelope's boxes at Ref A, the pocket on the ballast slot) it is 0 on
    the seam, deep inside, and a body stamped with it was grooved along every seam (a 1 g
    loss, 2026-11-09). Inside, the distance is taken from the nearest cells that are truly
    outside, up to two cells along each axis: |step| - their outside distance, exact for a
    flat face. Further in than two cells it is 2 cells (deep enough for the stamp)."""
    lb = np.maximum.reduce(fields)
    out = np.maximum(-lb, 0.0)
    est = np.full(lb.shape, 2.0 * d_mm)
    for ax in range(3):
        for s in (1, -1, 2, -2):
            o = _shift(out, s, ax)
            est = np.where(o > 0, np.minimum(est, abs(s) * d_mm - o), est)
    return np.where(lb > 0, np.maximum(lb, est), lb)


def air_field_mm(g, X, Y, Z) -> np.ndarray:
    """All the zones above for geometry g, cell centres X, Y, Z in mm: positive inside any.
    Limits the referee checks (envelope, wheels, T7.9, T8.5.1) carry MARGIN_MM; the pocket,
    ballast slot and block slot, which Part 4 cuts exactly, keep cells on their faces solid."""
    from bounding_volumes import default_rule_envelope
    d = float(X[1, 0, 0] - X[0, 0, 0]) if X.shape[0] > 1 else 1.0
    aY = np.abs(Y)
    ref_A = g.landmarks["ref_plane_A_m"] * 1e3
    exact = -1e-6
    return union([
        envelope_air(X, aY, Z, g.bv, default_rule_envelope(), d) + MARGIN_MM,
        wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm) + MARGIN_MM,
        t79_zones(X, aY, Z, g.W_mm, g.x_front_mm) + MARGIN_MM,
        t851_cap(X, aY, Z, ref_A) + MARGIN_MM,
        halo_pocket_and_ballast(X, aY, Z, ref_A, g.d_halo_mm, d) + exact,
        block_slot(X, aY, Z) + exact,
    ], d)


def stamp(g, X, Y, Z) -> int:
    """phi = max(phi, zone distance) within two cells of the zones' faces, so the body's
    surface sits on (or MARGIN_MM clear of) each zone's true face at any grid. Cells the
    rules force solid are left alone (air wins only where the masks themselves overlap).
    Returns the cells changed."""
    d_mm = float(X[1, 0, 0] - X[0, 0, 0]) if X.shape[0] > 1 else 1.0
    a = air_field_mm(g, X, Y, Z)
    near = (a > -2.0 * d_mm) & ~g.phi.hard_mask_solid
    new = np.maximum(g.phi.grid[near], (a[near] / 1e3).astype(np.float32))
    changed = int((new != g.phi.grid[near]).sum())
    g.phi.grid[near] = new
    return changed


def air_at_points(g, P):
    """The zones' air field (as air_field_mm, with its margins) at points P (n, 3) in mm.
    Exact where it is positive (inside a zone), which is all project_out needs."""
    from bounding_volumes import default_rule_envelope
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    aY = np.abs(Y)
    ref_A = g.landmarks["ref_plane_A_m"] * 1e3
    return np.maximum.reduce([
        envelope_air(X, aY, Z, g.bv, default_rule_envelope(), None) + MARGIN_MM,
        wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm) + MARGIN_MM,
        t79_zones(X, aY, Z, g.W_mm, g.x_front_mm) + MARGIN_MM,
        t851_cap(X, aY, Z, ref_A) + MARGIN_MM,
        halo_pocket_and_ballast(X, aY, Z, ref_A, g.d_halo_mm, None) - 1e-6,
        block_slot(X, aY, Z) - 1e-6,
    ])


def project_out(g, V_m, iters: int = 4):
    """Mesh vertices (metres) that smoothing pushed into a zone moved back onto its face.
    Taubin smoothing rounds every sharp edge a little; where the edge is a zone's (the block
    slot's top corners, the block's faces) the rounding put body inside the zone: 5.4 mm3 in
    the slot on Part 4's start car, 2026-11-09. Returns the vertices and how many moved."""
    P = np.asarray(V_m, dtype=np.float64) * 1e3
    moved = np.zeros(len(P), bool)
    h = 1e-3
    for _ in range(iters):
        a = air_at_points(g, P)
        m = a > 0.0
        if not m.any():
            break
        moved |= m
        Q = P[m]
        grad = np.stack([(air_at_points(g, Q + e) - air_at_points(g, Q - e)) / (2 * h)
                         for e in np.eye(3) * h], axis=1)
        P[m] = Q - (a[m] / np.maximum((grad ** 2).sum(1), 1e-12))[:, None] * grad
    return P / 1e3, int(moved.sum())
