"""remap_lab: why does a field remapped from 3 mm to 1.5 mm mesh with 0-degree slivers?

    python ../.github/lab/remap_lab.py <variant>     (run from part5-simulation, on GitHub)

variants: asis | norules (no build rules anywhere) | norules_dst (none on the new grid)
          | pinch (close pinches after the remap)
Prints LAB lines: did the remapped body pass the mesh check, and where the slivers are.
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402

variant = sys.argv[1]
import coarse  # noqa: E402
coarse.use_spacing(3.0)
import unified_phi as up  # noqa: E402
import surface_extraction as SE  # noqa: E402
from phi_updater import hj_update, cfl_limited_dt, reinitialise_sdf  # noqa: E402


def carve(g, n):
    for _ in range(n):
        vel = np.full(g.phi.grid.shape, -1.0)
        hj_update(g.phi, vel, cfl_limited_dt(vel, 0.5))
        reinitialise_sdf(g.phi, n_steps=3)
        up.enforce_symmetry(g)


if variant == "norules":
    up.apply_build_rules = lambda g: None
src = up.build_unified_geometry(130.0, 46.0, 20.0, init_mode="full", seed=0)
up.enforce_symmetry(src)
carve(src, 4)
print(f"LAB {variant} src volume {up.extract_unified_surface(src, allow_inaccessible=True)[0].volume*1e9:.0f} mm3")

coarse.use_spacing(1.5)
if variant == "norules_dst":
    up.apply_build_rules = lambda g: None
dst = up.remap_geometry(src)
if variant == "pinch":
    print(f"LAB {variant} pinch cells {up.close_pinches(dst, 0.0015)}")

mesh = SE._repair_mesh(SE._marching_cubes(dst.phi))
ang = np.degrees(mesh.face_angles.min(axis=1))
bad = ang < 1.0
print(f"LAB {variant} faces {len(ang)} below 1 deg {int(bad.sum())} min {ang.min():.3f}")
if bad.any():
    c = np.round(mesh.triangles_center[bad] * 1e3 / 3.0) * 3.0          # mm, 3 mm bins
    spots, n = np.unique(c, axis=0, return_counts=True)
    for k in np.argsort(-n)[:12]:
        print(f"LAB {variant} sliver spot x,y,z mm {spots[k].tolist()} count {n[k]}")
lm = dst.landmarks
print(f"LAB {variant} ref_A x {lm['ref_plane_A_m']*1e3:.1f} mm; d_halo {dst.d_halo_mm}")
try:
    up.extract_unified_surface(dst, allow_inaccessible=True)
    print(f"LAB {variant} RESULT pass")
except Exception as exc:  # noqa: BLE001
    print(f"LAB {variant} RESULT fail: {str(exc)[:160]}")
