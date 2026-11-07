"""Why does a body not reach Ref A, so the nose has no root? Prints only."""
import json, random, sys, tempfile
sys.path[:0] = ['.', 'checks']
import numpy as np
import pattern, stress_cars as sc, param_body as pb, run_car as rc, unified_phi as up
from coarse import use_spacing

seed, only = int(sys.argv[1]), int(sys.argv[2])
sc.SETTINGS = pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR) + list(pattern.PARTS)
rng = random.Random(seed)
for i in range(only + 1):
    c = sc.random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
args = ['--out', tempfile.mkdtemp(), '--skin-mm', sc.FIXED_SKIN_MM, '--body-json', json.dumps(c['car']['params'])]
for key, flag in (('W', '--W'), ('x_front', '--x-front'), ('d_halo', '--d-halo')):
    if key in c.get('layout', {}):
        args += [flag, str(c['layout'][key])]
a = rc.parse_args(args)
use_spacing(a.cfd_mm)
bp = pb.BodyParams.from_dict(json.loads(a.body_json))
g = pb.build(a.W, a.x_front, a.d_halo, bp, skin_offset_mm=float(sc.FIXED_SKIN_MM))
r, d = g.region, up.GRID_SPACING_M
xs = (r.origin_m[0] + np.arange(r.shape[0]) * d) * 1e3
ys = (r.origin_m[1] + np.arange(r.shape[1]) * d) * 1e3
zs = (r.origin_m[2] + np.arange(r.shape[2]) * d) * 1e3
X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
ref_a = g.landmarks['ref_plane_A_m'] * 1e3
print('LAB x_front', a.x_front, 'W', a.W, 'ref_a', round(ref_a, 2), 'spacing', d * 1e3, 'grid x', round(xs[0], 2), round(xs[-1], 2),
      'y', round(ys[0], 2), round(ys[-1], 2), 'z', round(zs[0], 2), round(zs[-1], 2), flush=True)
stub = (np.abs(Y) <= 4.0) & (Z >= 9.0) & (Z <= 18.0) & (X >= ref_a) & (X <= ref_a + 2.0)
print('LAB stub cells', int(stub.sum()), 'hard solid', int((stub & g.phi.hard_mask_solid).sum()),
      'hard air', int((stub & g.phi.hard_mask_air).sum()), 'solid now', int((stub & (g.phi.grid < 0)).sum()), flush=True)
sol = g.phi.grid < 0
print('LAB solid x min', round(float(X[sol].min()), 2), 'build', {k: v for k, v in g.build_report.items() if not isinstance(v, (list, dict))}, flush=True)
air = g.phi.hard_mask_air & (X >= ref_a) & (X <= ref_a + 14.0) & (np.abs(Y) <= 4.0) & (Z >= 9.0) & (Z <= 18.0)
if air.any():
    print('LAB air in the band: x', round(float(X[air].min()), 2), round(float(X[air].max()), 2), 'z', round(float(Z[air].min()), 2), round(float(Z[air].max()), 2), 'cells', int(air.sum()), flush=True)
