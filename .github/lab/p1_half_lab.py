"""p1_half_lab: what each half-body step does to volume, the block slot and the zones.

    python ../.github/lab/p1_half_lab.py <skin_mm>    (from part5-simulation, on GitHub)

The test body of test_body_mass_is_the_mass_of_the_mesh_that_gets_milled (lofted defaults,
1 mm, fixed skin). Half body three ways: raw (no projection, no box cut), projected, and
projected + box cut. For each: mesh volume (both halves) against the field's foam volume,
is_volume, body inside the block slot, and vertices inside each zone.
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402

skin = float(sys.argv[1])
from coarse import use_spacing  # noqa: E402
use_spacing(1.0)
import exact_zones as ez  # noqa: E402
import param_body as pb  # noqa: E402
import trimesh  # noqa: E402
import unified_phi as up  # noqa: E402
from geometry_contract import MODEL_BLOCK_SLOT_TOP_Z_MM, MODEL_BLOCK_SLOT_WIDTH_MM  # noqa: E402

g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=skin)
foam = [c for c in up.compute_mass_com(g) if c.name != "nose"]
nose = g.component_mask("nose") & (g.phi.grid < 0)
field_cm3 = sum(c.mass_kg for c in foam) / 163.0 * 1e6 + nose.sum() * 1e-3
slot = trimesh.creation.box(extents=[400.0, MODEL_BLOCK_SLOT_WIDTH_MM, 40.0])
slot.apply_translation([200.0, 0.0, MODEL_BLOCK_SLOT_TOP_Z_MM - 20.0])
proj, cut = ez.project_out, ez.cut_boxes
zones = {
    "envelope": lambda X, aY, Z: ez.envelope_air(X, aY, Z, g.bv, __import__("bounding_volumes").default_rule_envelope(), None) + ez.MARGIN_MM,
    "wheels": lambda X, aY, Z: ez.wheel_columns(X, aY, Z, g.W_mm, g.x_front_mm) + ez.MARGIN_MM,
    "t79": lambda X, aY, Z: ez.t79_zones(X, aY, Z, g.W_mm, g.x_front_mm) + ez.MARGIN_MM,
    "cap": lambda X, aY, Z: ez.t851_cap(X, aY, Z, g.landmarks["ref_plane_A_m"] * 1e3) + ez.MARGIN_MM,
    "pocket": lambda X, aY, Z: ez.halo_pocket_and_ballast(X, aY, Z, g.landmarks["ref_plane_A_m"] * 1e3, g.d_halo_mm, None),
    "slot": lambda X, aY, Z: ez.block_slot(X, aY, Z),
    "halo_above": lambda X, aY, Z: ez.halo_zones(X, aY, Z, g.landmarks["ref_plane_A_m"] * 1e3, g.d_halo_mm, part="above"),
    "halo_shadows": lambda X, aY, Z: ez.halo_zones(X, aY, Z, g.landmarks["ref_plane_A_m"] * 1e3, g.d_halo_mm, ez._canister(g), part="shadows") + ez.MARGIN_MM,
}
for tag in ("raw", "projected", "projected+cut"):
    ez.project_out = proj if tag != "raw" else (lambda gg, v, iters=4: (np.asarray(v), 0))
    ez.cut_boxes = cut if tag == "projected+cut" else (lambda gg, m: m)
    half = up.extract_half_surface(g)
    h = half.copy()
    h.apply_scale(1e3)
    inside = h.intersection(slot, engine="manifold").volume if h.is_volume else float("nan")
    V = np.asarray(half.vertices) * 1e3
    X, aY, Z = V[:, 0], np.abs(V[:, 1]), V[:, 2]
    worst = {k: float(f(X, aY, Z).max()) for k, f in zones.items()}
    bad = {k: round(v, 3) for k, v in worst.items() if v > 1e-3}
    print(f"LAB half skin {skin} {tag}: mesh {2 * abs(half.volume) * 1e6:.3f} cm3 field {field_cm3:.3f} cm3 "
          f"is_volume {half.is_volume} slot {inside:.2f} mm3 zones-with-vertices-inside {bad}", flush=True)
ez.project_out, ez.cut_boxes = proj, cut
h2 = cut(g, up.extract_half_surface(g))
print(f"LAB half skin {skin} cut changed faces: {len(h2.faces)}", flush=True)
