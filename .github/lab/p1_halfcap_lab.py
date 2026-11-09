"""p1_halfcap_lab: how to close the half body at y = 0 so that BOTH the mesh volume matches
the field's mass (bar 0.10 g) AND the mirrored chamber is round (T5.1 <= 18.5 mm).

    python ../.github/lab/p1_halfcap_lab.py <variant>    (from part5-simulation, on GitHub)

variants: pin_rim (current code) | nopin (cap free in smoothing) |
          nopin_snapT (free, then every vertex with y < T mm put on y = 0; T e.g. 0.1, 0.3) |
          nosmooth (marching cubes only, no Taubin)
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402

v = sys.argv[1]
from coarse import use_spacing  # noqa: E402
use_spacing(1.0)
import param_body as pb  # noqa: E402
import surface_extraction as SE  # noqa: E402
import unified_phi as up  # noqa: E402

_rep = SE._repair_mesh
if v.startswith("nopin"):
    SE._repair_mesh = lambda m, pin_plane_y0=False: _rep(m, False)
if v == "nosmooth":
    import trimesh.smoothing as sm
    sm.filter_taubin = lambda m, iterations=10, **k: m

g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=1.0)
half = up.extract_half_surface(g)
if "_snap" in v:
    t = float(v.split("_snap")[1]) * 1e-3
    vv = half.vertices.copy()
    vv[vv[:, 1] < t, 1] = 0.0
    half.vertices = vv
foam = [c for c in up.compute_mass_com(g) if c.name != "nose"]
nose_cells = g.component_mask("nose") & (g.phi.grid < 0)
field = sum(c.mass_kg for c in foam) / 163.0 * 1e6 + nose_cells.sum() * 1e-3
mesh = 2 * abs(half.volume) * 1e6
ang = np.degrees(half.face_angles.min(axis=1))
import legality as lg  # noqa: E402
hm = half.copy()
hm.apply_scale(1e3)
x_back = float(hm.bounds[1, 0])
widest = []
for x in np.linspace(x_back - 44.0, x_back - 4.0, 5):
    hs = lg._x_section_holes(hm, x)
    if hs:
        q = max(hs, key=lambda q: q.area)
        c = q.centroid
        pts = np.asarray(q.exterior.coords)
        widest.append(2 * float(np.hypot(pts[:, 0] - c.x, pts[:, 1] - c.y).max()))
print(f"LAB {v} gap {(field - mesh) * 0.163:+.3f} g (field {field:.3f} mesh {mesh:.3f} cm3) watertight {half.is_watertight} "
      f"min angle {ang.min():.2f} faces<5deg {(ang < 5).mean() * 100:.3f}% chamber widest {max(widest) if widest else 0:.3f} mm", flush=True)
