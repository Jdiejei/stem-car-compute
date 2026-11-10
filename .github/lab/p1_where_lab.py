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
        gr = [(float(ez.air_at_points(g, P[i:i + 1] + e)[0]) - float(ez.air_at_points(g, P[i:i + 1] - e)[0])) / 2e-3 for e in np.eye(3) * 1e-3]
        print(f"LAB where inside     gradient {np.round(gr, 3).tolist()}", flush=True)
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

if what == "est":
    import coarse
    coarse.use_spacing(1.0)
    # Which weight is right? Shapes of known volume (cells): the straight ramp, the
    # curvature-corrected fractions, the whole-cell count, raw marching cubes, and the
    # repaired (smoothed, volume-restored) mesh the car ships.
    import surface_extraction as SE
    from bounding_volumes import BoundingRegion
    from phi_grid import PhiGrid
    from unified_phi import fill_fraction
    d = 1e-3
    n = 40
    i = np.indices((n, n, n)).astype(np.float64)
    c = np.array([19.5, 20.0, 19.7])[:, None, None, None]
    shapes = {}
    for R in (5.3, 9.3, 12.1):
        shapes[f"sphere {R}"] = ((np.sqrt(((i - c) ** 2).sum(0)) - R), 4 / 3 * np.pi * R ** 3)
    a, b, cc = 14.0, 8.0, 6.0     # ellipsoid: a near-distance field (scaled), true volume known
    q = np.sqrt(((i[0] - c[0]) / a) ** 2 + ((i[1] - c[1]) / b) ** 2 + ((i[2] - c[2]) / cc) ** 2)
    shapes["ellipsoid 14x8x6"] = ((q - 1.0) * min(a, b, cc), 4 / 3 * np.pi * a * b * cc)
    bv = BoundingRegion("main_body", (0.0, -(n // 2) * d, 0.0), (n, n, n))
    import phi_updater as pu
    for name, (f, true) in shapes.items():
        z = np.zeros((n, n, n), bool)
        ph = PhiGrid("main_body", bv, (f * d).astype(np.float32), z, z.copy())
        if name.startswith("ellipsoid"):
            pu.reinitialise_sdf(ph)
        g = ph.grid.astype(np.float64)
        ramp = float(np.clip(0.5 - g / d, 0, 1).sum())
        corr = float(fill_fraction(g, d).sum())
        cells = float((g < 0).sum())
        mc = SE._marching_cubes(ph, 0.0)
        mcv = abs(mc.volume) / d ** 3
        rep = SE._repair_mesh(mc.copy())
        rv = abs(rep.volume) / d ** 3
        pct = lambda v: f"{v:.2f} ({(v - true) / true * 100:+.3f} %)"
        print(f"LAB where est {name}: true {true:.2f}; ramp {pct(ramp)}; corrected {pct(corr)}; cells {pct(cells)}; "
              f"marching cubes {pct(mcv)}; shipped mesh {pct(rv)}", flush=True)


if what == "mass":   # test_body_mass_is_the_mass_of_the_mesh_that_gets_milled: where the 0.15 cm3 is
    import unified_phi as up
    from mass_com_calculator import get_density
    g = lofted()
    dx = up.GRID_SPACING_M
    fill = up.fill_fraction(g.phi.grid, dx)
    cm3 = dx ** 3 * 1e6
    print(f"LAB mass: whole-grid fill {fill.sum() * cm3:.4f}, cells phi<0 {(g.phi.grid < 0).sum() * cm3:.4f}", flush=True)
    union = np.zeros(fill.shape, bool)
    count = np.zeros(fill.shape, int)
    for name in ("nose", "sidepod", "rearpod", "main_body"):
        m = g.component_mask(name)
        union |= m
        count += m
        print(f"LAB mass:   {name}: fill {fill[m].sum() * cm3:.4f}, cells {(m & (g.phi.grid < 0)).sum() * cm3:.4f}, density {get_density(name)}", flush=True)
    print(f"LAB mass: fill outside every mask {fill[~union].sum() * cm3:.4f}, in 2+ masks {fill[count > 1].sum() * cm3:.4f}", flush=True)
    for c in up.compute_mass_com(g):
        print(f"LAB mass:   compute_mass_com {c.name}: {c.mass_kg * 1e3:.4f} g = {c.mass_kg / get_density(c.name) * 1e6:.4f} cm3", flush=True)
    up.enforce_symmetry(g)
    fill = up.fill_fraction(g.phi.grid, dx)
    print(f"LAB mass: after symmetry: whole-grid fill {fill.sum() * cm3:.4f}", flush=True)
    import exact_zones as ez
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (print(f"LAB mass:   before cut {2 * abs(mesh.volume) * 1e6:.4f}", flush=True), real_cut(geom, mesh))[1]
    mesh = up.extract_half_surface(g)
    print(f"LAB mass: mesh {2 * abs(mesh.volume) * 1e6:.4f}, volume {mesh.is_volume}", flush=True)


if what.startswith("sliver"):   # sliver_<mm>: where the box cut leaves faces under 5 deg (fine03 4.4 %)
    import exact_zones as ez
    import unified_phi as up
    import coarse; coarse.use_spacing(float(what.split("_")[1]))
    g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
    up.enforce_symmetry(g)
    seen = {}
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (seen.setdefault("pre", mesh.copy()), real_cut(geom, mesh))[1]
    mesh = up.extract_half_surface(g)
    pre = seen["pre"]

    def bad(m):
        return np.degrees(m.face_angles.min(1)) < 5.0
    print(f"LAB sliver {what}: before cut {100 * bad(pre).mean():.2f} % of {len(pre.faces)}, after {100 * bad(mesh).mean():.2f} % of {len(mesh.faces)}, volume {mesh.is_volume}", flush=True)
    V = np.asarray(mesh.vertices) * 1e3
    planes = []
    for box in ez._air_boxes(g):
        for a, (lo, hi) in enumerate(box):
            for p in (lo, hi):
                if p is not None:
                    planes.append((a, p))
    def dplane(P):   # distance to the nearest box plane (any extent)
        return np.min([np.abs(np.abs(P[:, a]) - p) if a == 1 else np.abs(P[:, a] - p) for a, p in planes], axis=0)
    old = {tuple(np.round(v, 6)) for v in np.asarray(pre.vertices) * 1e3}
    new = np.array([tuple(np.round(v, 6)) not in old for v in V])
    b = bad(mesh)
    F = mesh.faces[b]
    edges = np.asarray(mesh.edges_unique_length)[...] if False else None
    L = np.linalg.norm(V[F] - V[np.roll(F, 1, axis=1)], axis=2)
    dmin = dplane(V[F].reshape(-1, 3)).reshape(-1, 3).min(1)
    print(f"LAB sliver {what}: {int(b.sum())} slivers; with a new (cut) vertex {int(new[F].any(1).sum())}; "
          f"a vertex within 0.01 mm of a box plane {int((dmin < 0.01).sum())}, within 0.1 mm {int((dmin < 0.1).sum())}", flush=True)
    print(f"LAB sliver {what}: shortest edge pct 10/50/90 {np.round(np.percentile(L.min(1), [10, 50, 90]), 5).tolist()} mm, "
          f"longest {np.round(np.percentile(L.max(1), [10, 50, 90]), 4).tolist()} mm", flush=True)
    ang = np.degrees(mesh.face_angles.min(1))
    print(f"LAB sliver {what}: slivers by min angle <0.5/<2/<5 deg: {int((ang < 0.5).sum())}/{int((ang < 2).sum())}/{int((ang < 5).sum())}", flush=True)
    pb_ = bad(pre)
    Vp = np.asarray(pre.vertices) * 1e3
    dpre = dplane(Vp[pre.faces[pb_]].reshape(-1, 3)).reshape(-1, 3).min(1) if pb_.any() else np.array([])
    print(f"LAB sliver {what}: before cut, slivers within 0.1 mm of a box plane {int((dpre < 0.1).sum())}", flush=True)


if what.startswith("zonevol"):   # zonevol_<mm>: body inside each cut box, field vs mesh (the cut took 0.1465 cm3)
    import manifold3d as m3
    import exact_zones as ez
    import unified_phi as up
    from coarse import use_spacing
    use_spacing(float(what.split("_")[1]))
    import param_body as pb
    g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
    dmm = up.GRID_SPACING_M * 1e3
    fill = up.fill_fraction(g.phi.grid, up.GRID_SPACING_M)
    nx, ny, nz = fill.shape
    o = np.asarray(g.region.origin_m) * 1e3
    cx, cy, cz = (o[a] + np.arange(n) * dmm for a, n in enumerate(fill.shape))   # cell centres
    print(f"LAB zonevol {what}: origin {o.tolist()}, shape {fill.shape}, field {fill.sum() * dmm ** 3 / 1e3:.4f} cm3", flush=True)
    seen = {}
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (seen.setdefault("pre", mesh.copy()), real_cut(geom, mesh))[1]
    mesh = up.extract_half_surface(g)
    pre = seen["pre"]
    def man(m):
        return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices * 1e3, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    Mpre, Mpost = man(pre), man(mesh)
    print(f"LAB zonevol {what}: mesh before cut {2 * Mpre.volume() / 1e3:.4f}, after {2 * Mpost.volume() / 1e3:.4f} cm3", flush=True)
    def ov(c, lo, hi):   # overlap of each cell [c - d/2, c + d/2] with [lo, hi], as a fraction
        lo = -1e9 if lo is None else lo
        hi = 1e9 if hi is None else hi
        return np.clip(np.minimum(c + dmm / 2, hi) - np.maximum(c - dmm / 2, lo), 0, dmm) / dmm
    tot = 0.0
    for i, box in enumerate(ez._air_boxes(g)):
        (x0, x1), (y0, y1), (z0, z1) = box
        yh = 1e9 if y1 is None else y1
        fy = ov(cy, -yh, yh) if y0 is None else ov(cy, y0, yh) + ov(cy, -yh, -y0)
        vf = float(np.einsum("ijk,i,j,k->", fill, ov(cx, x0, x1), fy, ov(cz, z0, z1))) * dmm ** 3
        tot += vf
        lo = [b[0] if b[0] is not None else (-1.0 if a == 1 else -500.0) for a, b in enumerate(box)]
        hi = [b[1] if b[1] is not None else 500.0 for b in box]
        B = m3.Manifold.cube(np.subtract(hi, lo).tolist()).translate(lo)
        print(f"LAB zonevol {what}:   box {i} {box}: field {vf:.2f}, mesh before cut {2 * (Mpre ^ B).volume():.2f}, after {2 * (Mpost ^ B).volume():.2f} mm3", flush=True)
    print(f"LAB zonevol {what}: field in all boxes {tot:.2f} mm3", flush=True)


if what.startswith("fix_"):   # fix_<mm>_<lofted|layout>: candidate fixes for the slivers and the field's in-zone volume
    import time
    import manifold3d as m3
    import pymeshlab as ml
    import trimesh
    import exact_zones as ez
    import unified_phi as up
    sys.path.insert(0, str(ROOT / "part4-simulation"))
    import mesh_fairing
    _, mm, body = what.split("_")
    from coarse import use_spacing
    use_spacing(float(mm))
    if body == "lofted":
        import param_body as pb
        g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
    else:
        g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
        up.enforce_symmetry(g)
    dx = up.GRID_SPACING_M
    dmm = dx * 1e3
    fill = up.fill_fraction(g.phi.grid, dx)
    # field trimmed by the zones: min(fill, ramp of the zone distance) on cells near the surface
    t0 = time.time()
    nx, ny, nz = fill.shape
    o = np.asarray(g.region.origin_m) * 1e3
    idx = np.nonzero(fill > 0.0)
    P = np.stack([o[a] + idx[a] * dmm for a in range(3)], axis=1)
    a = ez.air_at_points(g, P)
    legal = np.clip(0.5 - a / dmm, 0.0, 1.0)
    eff = fill.copy()
    eff[idx] = np.minimum(fill[idx], legal)
    print(f"LAB fix {what}: field {fill.sum() * dmm ** 3 / 1e3:.4f}, trimmed {eff.sum() * dmm ** 3 / 1e3:.4f} cm3 "
          f"({len(P)} cells, {time.time() - t0:.1f} s); cells with centre in a zone and fill>0: {int((a > 0).sum())}", flush=True)
    seen = {}
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (seen.setdefault("pre", mesh.copy()), real_cut(geom, mesh))[1]
    mesh = up.extract_half_surface(g)
    print(f"LAB fix {what}: mesh before cut {2 * abs(seen['pre'].volume) * 1e6:.4f}, after {2 * abs(mesh.volume) * 1e6:.4f} cm3", flush=True)
    boxes = []
    for box in ez._air_boxes(g):
        lo = [b[0] if b[0] is not None else (-1.0 if k == 1 else -500.0) for k, b in enumerate(box)]
        hi = [b[1] if b[1] is not None else 500.0 for b in box]
        boxes.append(m3.Manifold.cube(np.subtract(hi, lo).tolist()).translate(lo))
    def report(name, m):     # m in mm
        M = m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
        inz = sum(2 * (M ^ B).volume() for B in boxes)
        ang = np.degrees(m.face_angles.min(1))
        aw = ez.air_at_points(g, np.asarray(m.vertices))
        print(f"LAB fix {what}:   {name}: {100 * (ang < 5).mean():.2f} % under 5 deg of {len(m.faces)}, volume {m.is_volume}, "
              f"{2 * abs(m.volume) / 1e3:.4f} cm3, in boxes {inz:.2f} mm3, worst vertex {aw.max():+.4f} mm", flush=True)
    base = trimesh.Trimesh(np.asarray(mesh.vertices) * 1e3, mesh.faces, process=False)
    for eps in (0.0, 0.005, 0.01, 0.02, 0.05):
        m = base.copy()
        if eps:
            ms = ml.MeshSet()
            ms.add_mesh(ml.Mesh(m.vertices, m.faces))
            ms.apply_filter("meshing_merge_close_vertices", threshold=ml.PureValue(eps * dmm))
            ms.apply_filter("meshing_remove_null_faces")
            ms.apply_filter("meshing_remove_duplicate_faces")
            ms.apply_filter("meshing_remove_unreferenced_vertices")
            q = ms.current_mesh()
            m = trimesh.Trimesh(q.vertex_matrix(), q.face_matrix(), process=False)
        report(f"merge {eps} dx", m)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "b.stl"
            m.export(str(f))
            r = mesh_fairing.remesh_file(f, 0.6 if float(mm) >= 0.5 else 0.6)
            r2 = trimesh.load(str(f), force="mesh")
        report(f"merge {eps} dx, then Part 4 remesh (remeshed {r['remeshed']})", r2)


if what.startswith("fix2"):   # fix2_<mm>_<lofted|layout>: box-only field trim; manifold simplify; why a cut falls back
    import warnings
    import manifold3d as m3
    import trimesh
    import exact_zones as ez
    import unified_phi as up
    sys.path.insert(0, str(ROOT / "part4-simulation"))
    import mesh_fairing
    _, mm, body = what.split("_")
    from coarse import use_spacing
    use_spacing(float(mm))
    if body == "lofted":
        import param_body as pb
        g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
    else:
        g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
        up.enforce_symmetry(g)
    dx = up.GRID_SPACING_M
    dmm = dx * 1e3
    fill = up.fill_fraction(g.phi.grid, dx)
    o = np.asarray(g.region.origin_m) * 1e3
    idx = np.nonzero(fill > 0.0)
    X, Y, Z = (o[a] + idx[a] * dmm for a in range(3))
    db = np.maximum.reduce([ez._box(X, np.abs(Y), Z, x=b[0], y=b[1], z=b[2]) for b in ez._air_boxes(g)])
    for name, legal in (("box ramp", np.clip(0.5 - db / dmm, 0.0, 1.0)),):
        eff = fill.copy()
        eff[idx] = np.minimum(fill[idx], legal)
        print(f"LAB fix2 {what}: field {fill.sum() * dmm ** 3 / 1e3:.4f}, {name} trimmed {eff.sum() * dmm ** 3 / 1e3:.4f} cm3", flush=True)
    seen = {}
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (seen.setdefault("pre", mesh.copy()), real_cut(geom, mesh))[1]
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        mesh = up.extract_half_surface(g)
    pre = seen["pre"]
    print(f"LAB fix2 {what}: mesh before cut {2 * abs(pre.volume) * 1e6:.4f}, after {2 * abs(mesh.volume) * 1e6:.4f} cm3; "
          f"warnings {[str(w.message)[:70] for w in ws if 'cut_boxes' in str(w.message)]}", flush=True)
    M = m3.Manifold(m3.Mesh(vert_properties=np.asarray(pre.vertices, np.float32), tri_verts=np.asarray(pre.faces, np.uint32)))
    print(f"LAB fix2 {what}: pre-cut mesh: watertight {pre.is_watertight}, volume {pre.is_volume}, manifold status {M.status()}, empty {M.is_empty()}", flush=True)
    boxes = []
    for box in ez._air_boxes(g):
        lo = [b[0] if b[0] is not None else (-1.0 if k == 1 else -500.0) for k, b in enumerate(box)]
        hi = [b[1] if b[1] is not None else 500.0 for b in box]
        boxes.append(m3.Manifold.cube(np.subtract(hi, lo).tolist()).translate(lo))
    def report(name, m):     # m in mm
        Mm = m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
        inz = sum(2 * (Mm ^ B).volume() for B in boxes)
        ang = np.degrees(m.face_angles.min(1))
        print(f"LAB fix2 {what}:   {name}: {100 * (ang < 5).mean():.2f} % under 5 deg of {len(m.faces)}, volume {m.is_volume}, "
              f"{2 * abs(m.volume) / 1e3:.4f} cm3, in boxes {inz:.2f} mm3", flush=True)
    base = trimesh.Trimesh(np.asarray(mesh.vertices) * 1e3, mesh.faces, process=False)
    for tol in (0.0, 0.002, 0.005, 0.01, 0.02):
        m = base
        if tol:
            q = m3.Manifold(m3.Mesh(vert_properties=np.asarray(base.vertices, np.float32),
                                    tri_verts=np.asarray(base.faces, np.uint32))).simplify(tol).to_mesh()
            m = trimesh.Trimesh(np.asarray(q.vert_properties)[:, :3], np.asarray(q.tri_verts), process=False)
            m.merge_vertices()
        report(f"simplify {tol} mm", m)
        try:
            with tempfile.TemporaryDirectory() as d:
                f = Path(d) / "b.stl"
                m.export(str(f))
                r = mesh_fairing.remesh_file(f, 0.6)
                report(f"simplify {tol} mm, then Part 4 remesh (remeshed {r['remeshed']})", trimesh.load(str(f), force="mesh"))
        except Exception as e:  # noqa: BLE001
            print(f"LAB fix2 {what}:   remesh raised {type(e).__name__}: {str(e)[:100]}", flush=True)


def field_in_boxes(g, boxes, k=8):
    """Solid volume (mm3) of the field inside each box, as marching cubes sees it: each cube
    between grid nodes sampled k^3 times by trilinear phi, the samples inside the box and
    phi < 0 counted. boxes: ((x lo, hi), (|y| lo, hi), (z lo, hi)) in mm, None = open."""
    phi = np.asarray(g.phi.grid, np.float64)
    d = g.phi.bv.voxel_size_m * 1e3 if hasattr(g.phi.bv, "voxel_size_m") else None
    import unified_phi as up
    d = up.GRID_SPACING_M * 1e3
    o = np.asarray(g.region.origin_m) * 1e3
    n = np.array(phi.shape)
    s = (np.arange(k) + 0.5) / k
    out = []
    for box in boxes:
        (x0, x1), (y0, y1), (z0, z1) = box
        yh = 1e9 if y1 is None else y1
        signed = [(-yh, yh)] if y0 is None else [(y0, yh), (-yh, -y0)]
        tot = 0.0
        for ys in signed:
            lim = [(-1e9 if x0 is None else x0, 1e9 if x1 is None else x1), ys,
                   (-1e9 if z0 is None else z0, 1e9 if z1 is None else z1)]
            lo = [max(int(np.floor((lim[a][0] - o[a]) / d)) - 1, 0) for a in range(3)]
            hi = [min(int(np.ceil((lim[a][1] - o[a]) / d)) + 1, n[a] - 1) for a in range(3)]
            if any(h <= l for l, h in zip(lo, hi)):
                continue
            blk = phi[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
            cmin = np.minimum.reduce([blk[i:blk.shape[0] - 1 + i, j:blk.shape[1] - 1 + j, kk:blk.shape[2] - 1 + kk]
                                      for i in (0, 1) for j in (0, 1) for kk in (0, 1)])
            ci = np.argwhere(cmin < 0)
            if not len(ci):
                continue
            for ch in np.array_split(ci, max(1, len(ci) // 20000)):
                # sample points of each cube (local coords u in [0,1]^3)
                U = np.stack(np.meshgrid(s, s, s, indexing="ij"), -1).reshape(-1, 3)
                c = ch[:, None, :] + U[None]                        # block index coords
                P = o + (np.array(lo) + c) * d                      # mm
                inside = np.all([(P[..., a] >= lim[a][0]) & (P[..., a] <= lim[a][1]) for a in range(3)], axis=0)
                i0 = np.floor(c).astype(int)
                f = c - i0
                val = np.zeros(c.shape[:2])
                for di in (0, 1):
                    for dj in (0, 1):
                        for dk in (0, 1):
                            w = (f[..., 0] if di else 1 - f[..., 0]) * (f[..., 1] if dj else 1 - f[..., 1]) * (f[..., 2] if dk else 1 - f[..., 2])
                            val += w * blk[np.minimum(i0[..., 0] + di, blk.shape[0] - 1), np.minimum(i0[..., 1] + dj, blk.shape[1] - 1), np.minimum(i0[..., 2] + dk, blk.shape[2] - 1)]
                tot += float((inside & (val < 0)).sum()) * (d / k) ** 3
        out.append(tot)
    return out


if what.startswith("wedge"):   # wedge_<mm>_<lofted|layout>: field-in-box quadrature vs the mesh; the 0.5 mm cut fallback
    import io
    import manifold3d as m3
    import trimesh
    import exact_zones as ez
    import unified_phi as up
    _, mm, body = what.split("_")
    from coarse import use_spacing
    use_spacing(float(mm))
    if body == "lofted":
        import param_body as pb
        g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
    else:
        g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
        up.enforce_symmetry(g)
    boxes = ez._air_boxes(g)
    for k in (4, 8):
        vb = field_in_boxes(g, boxes, k)
        print(f"LAB wedge {what}: field in boxes (k={k}): {[round(v, 2) for v in vb]} total {sum(vb):.2f} mm3", flush=True)
    seen = {}
    real_cut = ez.cut_boxes
    ez.cut_boxes = lambda geom, mesh: (seen.setdefault("pre", mesh.copy()), real_cut(geom, mesh))[1]
    mesh = up.extract_half_surface(g)
    pre = seen["pre"]
    Mpre = m3.Manifold(m3.Mesh(vert_properties=np.asarray(pre.vertices * 1e3, np.float32), tri_verts=np.asarray(pre.faces, np.uint32)))
    mb = []
    for box in boxes:
        lo = [b[0] if b[0] is not None else (-1.0 if a == 1 else -500.0) for a, b in enumerate(box)]
        hi = [b[1] if b[1] is not None else 500.0 for b in box]
        mb.append(2 * (Mpre ^ m3.Manifold.cube(np.subtract(hi, lo).tolist()).translate(lo)).volume())
    print(f"LAB wedge {what}: mesh in boxes before cut: {[round(v, 2) for v in mb]} total {sum(mb):.2f}; cut took {2 * (abs(pre.volume) - abs(mesh.volume)) * 1e9:.2f} mm3", flush=True)
    # the fallback, step by step
    body_m = m3.Manifold(m3.Mesh(vert_properties=np.asarray(pre.vertices, np.float32), tri_verts=np.asarray(pre.faces, np.uint32)))
    cut = None
    e = 1e-3
    for box in boxes:
        lo = [(b[0] - e) if b[0] is not None else (-1.0 if a == 1 else -500.0) for a, b in enumerate(box)]
        hi = [(b[1] + e) if b[1] is not None else 500.0 for b in box]
        c = m3.Manifold.cube([(h - l) / 1e3 for l, h in zip(lo, hi)]).translate([l / 1e3 for l in lo])
        cut = c if cut is None else cut + c
    r = body_m - cut
    o_ = r.to_mesh()
    raw = trimesh.Trimesh(np.asarray(o_.vert_properties)[:, :3].astype(np.float64), np.asarray(o_.tri_verts), process=False)
    out = trimesh.load(io.BytesIO(raw.export(file_type="stl")), file_type="stl", force="mesh")
    def stats(m):
        from collections import Counter
        ec = Counter(map(tuple, np.sort(m.edges, axis=1).tolist()))
        return (f"volume {m.is_volume}, watertight {m.is_watertight}, winding {m.is_winding_consistent}, "
                f"faces {len(m.faces)}, degenerate {int((m.area_faces < 1e-18).sum())}, edges used !=2 times {sum(1 for v in ec.values() if v != 2)}")
    print(f"LAB wedge {what}: boolean status {r.status()}, raw: {stats(raw)}", flush=True)
    print(f"LAB wedge {what}: after STL reload: {stats(out)}", flush=True)
    if not out.is_volume:
        from collections import Counter
        ec = Counter(map(tuple, np.sort(out.edges, axis=1).tolist()))
        bad = [k_ for k_, v in ec.items() if v != 2][:6]
        for a_, b_ in bad:
            print(f"LAB wedge {what}:   bad edge {np.round(out.vertices[a_] * 1e3, 4).tolist()} - {np.round(out.vertices[b_] * 1e3, 4).tolist()} used {ec[(a_, b_)]}", flush=True)


if what.startswith("diag"):   # diag_<mm>: ed9e488 regressions, step by step on the zone test body
    import manifold3d as m3
    import trimesh
    import exact_zones as ez
    import unified_phi as up
    import halo_pocket as hp
    import coarse
    coarse.use_spacing(float(what.split("_")[1]))
    g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
    up.enforce_symmetry(g)
    d = up.GRID_SPACING_M * 1e3
    o = np.asarray(g.region.origin_m) * 1e3
    b = {k: v * 1e3 for k, v in hp.compute_halo_pocket_box_m(g.landmarks["ref_plane_A_m"], g.d_halo_mm).items()}
    i = int(round((b["x_min_m"] + 8.0 - o[0]) / d)); j = int(round(-o[1] / d))
    ks = [k for k in range(g.phi.grid.shape[2]) if 20.0 <= o[2] + k * d <= 27.0]
    print(f"LAB diag {what}: pocket box {b}; column x={o[0] + i * d:.2f}, y={o[1] + j * d:.2f}: "
          + ", ".join(f"z{o[2] + k * d:.1f}:{g.phi.grid[i, j, k] * 1e3:+.2f}{'S' if g.phi.hard_mask_solid[i, j, k] else ''}{'A' if g.phi.hard_mask_air[i, j, k] else ''}" for k in ks), flush=True)
    slot = [bx for bx in ez._air_boxes(g)][0]
    def inside(V, tag):
        a = ez.air_at_points(g, V * 1e3)
        w = int(np.argmax(a))
        print(f"LAB diag {what}: {tag}: volume {2 * abs(trimesh.Trimesh(V, F, process=False).volume) * 1e6:.4f} cm3, "
              f"{int((a > 1e-3).sum())} vertices in a zone, worst {a.max():.3f} mm at {np.round(V[w] * 1e3, 2).tolist()}", flush=True)
    import surface_extraction as SE
    real_po, real_cut = ez.project_out, ez.cut_boxes
    step = {"n": 0}
    def po(geom, V, iters=8):
        global F
        step["n"] += 1
        r = real_po(geom, V, iters)
        print(f"LAB diag {what}: project_out call {step['n']}: moved {r[1]}", flush=True)
        return r
    def cb(geom, mesh):
        global F
        F = mesh.faces
        inside(np.asarray(mesh.vertices), "before cut")
        out = real_cut(geom, mesh)
        F = out.faces
        inside(np.asarray(out.vertices), "after cut")
        return out
    ez.project_out, ez.cut_boxes = po, cb
    mesh = up.extract_half_surface(g)
    F = mesh.faces
    inside(np.asarray(mesh.vertices), "returned")


if what.startswith("rim"):   # rim_<mm>: the pocket floor next to the ballast slot, stage by stage
    import trimesh
    import exact_zones as ez
    import unified_phi as up
    import halo_pocket as hp
    import coarse
    coarse.use_spacing(float(what.split("_")[1]))
    g = up.build_unified_geometry(127.0, 49.0, 41.0, init_mode="full")
    up.enforce_symmetry(g)
    b = {k: v * 1e3 for k, v in hp.compute_halo_pocket_box_m(g.landmarks["ref_plane_A_m"], g.d_halo_mm).items()}
    cx = b["x_min_m"] + hp.BALLAST_CENTRE_FROM_POCKET_FRONT_MM
    r = hp.BALLAST_SLOT_WIDTH_MM / 2.0
    o = np.array([(cx + dxx, r + dy, b["z_min_m"] + 1.0) for dxx in (-2.0, 0.0, 2.0) for dy in (0.1, 0.45, 0.85)])
    print(f"LAB rim {what}: pocket box {b}, slot cx {cx:.3f} r {r}", flush=True)
    def show(V, F, tag):
        m = trimesh.Trimesh(np.asarray(V) * 1e3, F, process=False)
        loc, ray, tri = m.ray.intersects_location(o, np.tile([0.0, 0.0, -1.0], (len(o), 1)), multiple_hits=False)
        print(f"LAB rim {what}: {tag}: hits " + ", ".join(f"({o[k,0]-cx:+.0f},{o[k,1]:.2f})->{z:.4f}" for k, z in zip(ray, loc[:, 2])), flush=True)
        for k, t in zip(ray, tri):
            if loc[list(ray).index(k), 2] < 23.999:
                print(f"LAB rim {what}:   tri at ray {k}: " + "; ".join(str(np.round(m.vertices[v], 4).tolist()) for v in m.faces[t]), flush=True)
        P = m.vertices
        sel = (np.abs(P[:, 0] - cx) < 6) & (P[:, 1] > 5.5) & (P[:, 1] < 8.5) & (P[:, 2] > 22.5) & (P[:, 2] < 24.0)
        lo = np.argsort(P[sel, 2])[:8]
        print(f"LAB rim {what}:   lowest near-floor vertices: " + "; ".join(str(np.round(P[sel][i], 4).tolist()) for i in lo), flush=True)
    real_po, real_cut = ez.project_out, ez.cut_boxes
    step = {"n": 0}
    def po(geom, V, iters=16):
        r_ = real_po(geom, V, iters)
        step["n"] += 1
        return r_
    def cb(geom, mesh):
        show(mesh.vertices, mesh.faces, "before cut")
        out = real_cut(geom, mesh)
        show(out.vertices, out.faces, "after cut")
        return out
    ez.project_out, ez.cut_boxes = po, cb
    mesh = up.extract_half_surface(g)
    show(mesh.vertices, mesh.faces, "returned")
