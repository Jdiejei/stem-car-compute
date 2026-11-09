"""p1_massmesh_lab: which change parted the field's mass from the exported mesh's volume?

    python ../.github/lab/p1_massmesh_lab.py <variant>    (from part5-simulation, on GitHub)

variants: now | nokeep (milling rebuilds the whole field, as before) | nostamp (no exact
chamber) | nopin (half body's cap free in smoothing) | old (all three off).
Same body as test_body_mass_is_the_mass_of_the_mesh_that_gets_milled; also prints the field
around the bottom of the chamber on the centreline.
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402

v = sys.argv[1]
from coarse import use_spacing  # noqa: E402
use_spacing(1.0)
import param_body as pb  # noqa: E402
import scipy.ndimage as ndi  # noqa: E402
import surface_extraction as SE  # noqa: E402
import unified_phi as up  # noqa: E402

if v in ("nokeep", "old"):
    ndi.binary_erosion = lambda a, **k: np.zeros_like(a, dtype=bool)
if v in ("nostamp", "old"):
    pb._stamp_bore = lambda *a: 0
if v in ("nopin", "old"):
    _rep = SE._repair_mesh
    SE._repair_mesh = lambda m, pin_plane_y0=False: _rep(m, False)

g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
foam = [c for c in up.compute_mass_com(g) if c.name != "nose"]
nose_cells = g.component_mask("nose") & (g.phi.grid < 0)
half = up.extract_half_surface(g)
mesh_cm3 = 2 * abs(half.volume) * 1e6
field_cm3 = sum(c.mass_kg for c in foam) / 163.0 * 1e6 + nose_cells.sum() * 1e-3
print(f"LAB {v} field {field_cm3:.3f} cm3 mesh {mesh_cm3:.3f} cm3 gap {(field_cm3 - mesh_cm3) * 0.163:+.3f} g", flush=True)
r, d = g.region, up.GRID_SPACING_M
i = int(round((g.landmarks["rear_face_m"] - 0.020 - r.origin_m[0]) / d))
j0 = int(round((0.0 - r.origin_m[1]) / d))
k0 = int(round((0.031 - r.origin_m[2]) / d))
for dj in (0, 1):
    col = g.phi.grid[i, j0 + dj, k0 - 12:k0 - 6] / d
    print(f"LAB {v} chamber bottom, y {dj} mm, z {31 - 12}..{31 - 7} mm: phi/dx {np.round(col, 3).tolist()} "
          f"air {g.phi.hard_mask_air[i, j0 + dj, k0 - 12:k0 - 6].astype(int).tolist()} "
          f"solid {g.phi.hard_mask_solid[i, j0 + dj, k0 - 12:k0 - 6].astype(int).tolist()}", flush=True)
x0 = (r.origin_m[0] + i * d)
near = half.vertices[(np.abs(half.vertices[:, 0] - x0) < 0.003) & (half.vertices[:, 1] < 0.0015)
                     & (np.abs(half.vertices[:, 2] - 0.0215) < 0.0015)]
print(f"LAB {v} half-body vertices near the chamber bottom (y, z mm): "
      f"{np.round(near[:, 1:] * 1e3, 3)[:20].tolist()}", flush=True)
