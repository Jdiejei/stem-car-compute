"""p1_where_lab: where are the leftovers? (2026-11-10)

    python ../.github/lab/p1_where_lab.py <what>    (from part5-simulation, on GitHub)

what = halo:    the lofted test body's half mesh: vertices inside the halo zones (raw), where,
                and the field cells there (phi, forced solid?, forced air?)
       mask:    the halo masks against exact_zones.halo_zones at 1.0 and 0.75 mm: stray mask
                cells (x, y, z, field, exact ceiling) for the first few
       sphere:  the redistancing test's surface cells: worst errors and where
       cut:     cut_boxes on the half mesh via trimesh's manifold boolean in mm, and whether it
                survives an STL save and reload
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402

what = sys.argv[1]


def lofted():
    from coarse import use_spacing
    use_spacing(1.0)
    import param_body as pb
    return pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)


if what == "halo":
    import exact_zones as ez
    import unified_phi as up
    g = lofted()
    ez.project_out = lambda gg, v, iters=4: (np.asarray(v), 0)
    ez.cut_boxes = lambda gg, m: m
    V = np.asarray(up.extract_half_surface(g).vertices) * 1e3
    ra = g.landmarks["ref_plane_A_m"] * 1e3
    for part in ("above", "shadows"):
        f = ez.halo_zones(V[:, 0], np.abs(V[:, 1]), V[:, 2], ra, g.d_halo_mm, ez._canister(g), part=part)
        for i in np.argsort(-f)[:6]:
            if f[i] <= 0.05:
                break
            r, d = g.region, 1.0
            idx = tuple(int(round(V[i, a] - r.origin_m[a] * 1e3)) for a in range(3))
            cc = [r.origin_m[a] * 1e3 + idx[a] for a in range(3)]
            bb = float(ez.halo_zones(np.array(cc[0]), np.array(abs(cc[1])), np.array(cc[2]), ra, g.d_halo_mm, ez._canister(g), part=part))
            print(f"LAB where halo {part}: cell centre {np.round(cc, 2).tolist()} zone there {bb:+.3f}", flush=True)
            print(f"LAB where halo {part}: vertex ({V[i, 0]:.2f},{V[i, 1]:.2f},{V[i, 2]:.2f}) inside {f[i]:.3f} mm; "
                  f"cell {idx} phi {g.phi.grid[idx] * 1e3:+.3f} mm forced solid {bool(g.phi.hard_mask_solid[idx])} "
                  f"forced air {bool(g.phi.hard_mask_air[idx])} label {int(g.labels[idx])}", flush=True)

if what == "mask":
    import coarse
    import exact_zones as ez
    import fixed_hardware as fh
    import unified_phi as up
    for s in (1.0, 0.75):
        coarse.use_spacing(s)
        g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
        r, d = g.region, s
        X, Y, Z = np.meshgrid(*[(r.origin_m[a] * 1e3 + np.arange(r.shape[a]) * d) for a in range(3)], indexing="ij")
        hw = g.fixed_hardware
        vis = fh.halo_visibility_air_mask(hw.halo_void_mask, z_origin_m=r.origin_m[2], dz_m=d / 1e3)
        loft = fh.halo_canister_loft_air_mask(hw.halo_void_mask, hw.canister_cylinder, x_origin_m=r.origin_m[0],
                                              y_origin_m=r.origin_m[1], z_origin_m=r.origin_m[2], d_m=d / 1e3)
        f = ez.halo_zones(X, np.abs(Y), Z, g.landmarks["ref_plane_A_m"] * 1e3, g.d_halo_mm, hw.canister_cylinder)
        for name, m in (("void", hw.halo_void_mask), ("visibility", vis), ("loft", loft)):
            stray = m & (Y >= 0) & (f < -d)
            print(f"LAB where mask s {s} {name}: {int(stray.sum())} cells outside the exact zone by > a cell", flush=True)
            for c in np.argwhere(stray)[:: max(1, int(stray.sum()) // 5)][:5]:
                c = tuple(c)
                col = np.flatnonzero(m[c[0], c[1]])
                print(f"LAB where mask s {s} {name}   ({X[c]:.2f},{Y[c]:.2f},{Z[c]:.2f}) field {f[c]:.3f}; "
                      f"mask air in this column from z {Z[c[0], c[1], col[0]]:.2f}", flush=True)
            back = (f > d) & (Y >= 0) & ~m & ~hw.halo_void_mask & ~vis & ~loft
            print(f"LAB where mask s {s} {name}: zone cells deeper than a cell with no mask: {int(back.sum())}", flush=True)
        import halo_pocket as hp
        bx = hp.compute_halo_pocket_box_m(g.landmarks["ref_plane_A_m"], g.d_halo_mm)
        print(f"LAB where mask s {s} halo box x1 {bx['x_max_m'] * 1e3:.3f} rear-face top {fh.HALO_REAR_FACE_TOP_MM} "
              f"top {fh.HALO_CROSS_SECTION_TOP_MM} half width {fh.HALO_CROSS_SECTION_HALF_WIDTH_MM} z origin {r.origin_m[2] * 1e3:.3f}", flush=True)
        print(f"LAB where mask s {s} halo x {hw.halo_void_mask.any(axis=(1, 2)).nonzero()[0][[0, -1]] * d + r.origin_m[0] * 1e3} "
              f"canister front {(hw.canister_cylinder.x_center_m - hw.canister_cylinder.x_half_width_m) * 1e3:.2f}", flush=True)

if what == "sphere":
    import phi_updater as pu
    from bounding_volumes import BoundingRegion
    from geometry_contract import GRID_SPACING_M as d
    from phi_grid import PhiGrid
    n = 32
    bv = BoundingRegion("main_body", (0.0, -(n // 2) * d, 0.0), (n, n, n))
    i = np.indices((n, n, n)).astype(np.float64)
    c = np.array([15.5, n // 2, 15.7])[:, None, None, None]
    sdf = (np.sqrt(((i - c) ** 2).sum(0)) - 9.3) * d
    z = np.zeros((n, n, n), bool)
    phi = PhiGrid("main_body", bv, (3.0 * sdf).astype(np.float32), z, z.copy())
    pu.reinitialise_sdf(phi)
    s0 = sdf < 0
    pad = np.pad(s0, 1, mode="edge")
    ring = np.zeros_like(s0)
    for ax in range(3):
        for sh in (slice(0, -2), slice(2, None)):
            idx = [slice(1, -1)] * 3
            idx[ax] = sh
            ring |= pad[tuple(idx)] != s0
    err = np.where(ring, np.abs(phi.grid - sdf) / d, 0.0)
    print(f"LAB where sphere surface cells {int(ring.sum())} max err {err.max():.3f} cells, mean {err[ring].mean():.3f}; "
          f"cells over 0.1: {int((err > 0.1).sum())}", flush=True)
    for w in np.argwhere(err > 0.1)[:5]:
        w = tuple(w)
        print(f"LAB where sphere   cell {w} sdf {sdf[w] / d:+.3f} phi {phi.grid[w] / d:+.3f} cells", flush=True)

if what == "cut":
    import exact_zones as ez
    import trimesh
    import unified_phi as up
    g = lofted()
    real = ez.cut_boxes
    for name, fn in (("no cut", lambda gg, m: m), ("cut", real)):
        ez.cut_boxes = fn
        half = up.extract_half_surface(g)
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as t:
            half.export(t.name)
            back = trimesh.load(t.name, force="mesh")
        a = ez.air_at_points(g, np.asarray(back.vertices) * 1e3)
        print(f"LAB where cut [{name}]: volume {back.is_volume} after an STL reload, faces {len(back.faces)}, "
              f"{2 * abs(back.volume) * 1e6:.3f} cm3; vertices in zones {int((a > 1e-4).sum())} worst {a.max():.4f} mm",
              flush=True)

if what == "inside":
    sys.path.insert(0, str(ROOT / "part1-simulation" / "tests"))
    import exact_zones as ez
    import unified_phi as up
    from bounding_volumes import default_rule_envelope
    import coarse; coarse.use_spacing(1.0)
    g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
    up.enforce_symmetry(g)
    import warnings
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        mesh = up.extract_half_surface(g)
    print(f"LAB where inside: warnings {[str(w.message)[:80] for w in ws]}", flush=True)
    P = np.asarray(mesh.vertices) * 1e3
    X, aY, Z = P[:, 0], np.abs(P[:, 1]), P[:, 2]
    ra = g.landmarks["ref_plane_A_m"] * 1e3
    parts = {"envelope": ez.envelope_air(X, aY, Z, g.bv, default_rule_envelope(), None) + ez.MARGIN_MM,
             "wheels": ez.wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm) + ez.MARGIN_MM,
             "t79": ez.t79_zones(X, aY, Z, g.W_mm, g.x_front_mm) + ez.MARGIN_MM,
             "t851": ez.t851_cap(X, aY, Z, ra) + ez.MARGIN_MM,
             "slot": ez.block_slot(X, aY, Z) - 1e-6,
             "above": ez.halo_zones(X, aY, Z, ra, g.d_halo_mm, part="above") - 1e-6,
             "shadows": ez.halo_zones(X, aY, Z, ra, g.d_halo_mm, ez._canister(g), part="shadows") + ez.MARGIN_MM}
    a = np.maximum.reduce(list(parts.values()))
    print(f"LAB where inside: {int((a > 1e-3).sum())} vertices, volume {mesh.is_volume}", flush=True)
    for i in np.argsort(-a)[:8]:
        if a[i] <= 1e-3:
            break
        who = {k: round(float(v[i]), 3) for k, v in parts.items() if v[i] > -0.5}
        print(f"LAB where inside   ({P[i, 0]:.3f},{P[i, 1]:.3f},{P[i, 2]:.3f}) {a[i]:.3f} mm: {who}", flush=True)

        q, _k = ez.project_out(g, P[i:i + 1] / 1e3)
        print(f"LAB where inside     projected to {np.round(q[0] * 1e3, 4).tolist()}, then {float(ez.air_at_points(g, q * 1e3)[0]):+.4f} mm", flush=True)
if what == "sphere3":
    import phi_updater as pu
    from bounding_volumes import BoundingRegion
    from geometry_contract import GRID_SPACING_M as d
    from phi_grid import PhiGrid
    n = 32
    bv = BoundingRegion("main_body", (0.0, -(n // 2) * d, 0.0), (n, n, n))
    i = np.indices((n, n, n)).astype(np.float64)
    c = np.array([15.5, n // 2, 15.7])[:, None, None, None]
    sdf = (np.sqrt(((i - c) ** 2).sum(0)) - 9.3) * d
    z = np.zeros((n, n, n), bool)
    phi = PhiGrid("main_body", bv, (3.0 * sdf).astype(np.float32), z, z.copy())
    vol = lambda gr: float(np.clip(0.5 - gr.astype(np.float64) / d, 0.0, 1.0).sum())
    v0 = vol(sdf)
    band = np.abs(sdf) < 2 * d
    for k in range(4):
        pu.reinitialise_sdf(phi)
        e = (phi.grid - sdf)[band] / d
        print(f"LAB where sphere3 pass {k + 1}: volume {vol(phi.grid):.2f} vs {v0:.2f} ({(vol(phi.grid) - v0) / v0 * 100:+.3f} %), "
              f"band error mean {e.mean():+.4f} max {np.abs(e).max():.3f} cells", flush=True)
