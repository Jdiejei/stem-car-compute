"""Pictures of stress cars, built exactly as the stress run builds them. Writes render/*.png."""
import json, random, sys, tempfile, os
sys.path[:0] = ['.', 'checks']
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import pattern, stress_cars as sc, param_body as pb, run_car as rc

seed, only = int(sys.argv[1]), int(sys.argv[2])
sc.SETTINGS = pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR) + list(pattern.PARTS)
rng = random.Random(seed)
for i in range(only + 1):
    c = sc.random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
if seed == 0:
    c = {"car": {"params": {}, "parts": {}}, "layout": {}, "moved": {}}       # the start car
args = ['--out', tempfile.mkdtemp(), '--skin-mm', sc.FIXED_SKIN_MM, '--support', 'beam', '--body-json', json.dumps(c['car']['params'])]
for key, flag in (('W', '--W'), ('x_front', '--x-front'), ('d_halo', '--d-halo')):
    if key in c.get('layout', {}):
        args += [flag, str(c['layout'][key])]
for part, flag in pattern.PART_FLAGS.items():
    if c['car']['parts'].get(part):
        args += [flag, json.dumps(c['car']['parts'][part])]
a = rc.parse_args(args)
from pathlib import Path
out = Path(a.out)
geom, info, asm = rc.build_car(a, out, **rc.part4_kwargs(a))
meshes = []
colours = {'machined_body': '#d9dde3', 'printed_front_assembly': '#e4572e', 'printed_rwing': '#e4572e',
           'printed_support_front': '#29335c', 'printed_support_rear': '#29335c'}
for name, part in asm['joints']['manufactured'].items():
    if 'file' in part:
        m = trimesh.load(part['file'], force='mesh')
        meshes.append((m, colours.get(name, '#f3a712')))
for s in asm.get('extra_surfaces', []):
    if s['name'] in ('wheelF', 'wheelR', 'halo'):
        h = trimesh.load(s['stl'], force='mesh'); h.apply_scale(1e3)
        mir = h.copy(); mir.apply_transform(np.diag([1, -1, 1, 1])); mir.invert()
        for p in (h, mir):
            meshes.append((p, '#111111' if s['name'] != 'halo' else '#7a7a7a'))
lo = np.min([m.bounds[0] for m, _ in meshes], axis=0); hi = np.max([m.bounds[1] for m, _ in meshes], axis=0)
os.makedirs('render', exist_ok=True)
fig = plt.figure(figsize=(14, 9))
for k, (elev, azim, title) in enumerate(((22, -58, 'three-quarter'), (0, -90, 'side'), (90, -90, 'top'), (8, 180, 'front'))):
    ax = fig.add_subplot(2, 2, k + 1, projection='3d')
    for m, col in meshes:
        f = m.faces
        if len(f) > 30000:
            f = f[np.random.default_rng(0).choice(len(f), 30000, replace=False)]
        tri = m.vertices[f]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.45 + 0.55 * np.clip(n @ np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8]), 0, 1)
        base = np.array(matplotlib.colors.to_rgb(col))
        ax.add_collection3d(Poly3DCollection(tri, facecolors=np.clip(base[None] * shade[:, None], 0, 1), linewidths=0))
    ctr, span = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(ctr[0] - span, ctr[0] + span); ax.set_ylim(ctr[1] - span, ctr[1] + span); ax.set_zlim(ctr[2] - span, ctr[2] + span)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title(title)
fig.suptitle(f"car {seed}/{only}: {len(c['moved'])} settings moved" if seed else "start car", fontsize=14)
fig.tight_layout()
fig.savefig(f'render/car_{seed}_{only}.png', dpi=110)
print('LAB rendered', seed, only, flush=True)
