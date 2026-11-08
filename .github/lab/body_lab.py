"""Why is a body's surface not closed, and what closes it? Prints only."""
import json, random, sys, tempfile
sys.path[:0] = ['.', 'checks']
import numpy as np, trimesh
import pattern, stress_cars as sc, param_body as pb, run_car as rc, unified_phi as up

seed, only = int(sys.argv[1]), int(sys.argv[2])
sc.SETTINGS = pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR) + list(pattern.PARTS)
rng = random.Random(seed)
for i in range(only + 1):
    c = sc.random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
args = ['--out', tempfile.mkdtemp(), '--skin-mm', sc.FIXED_SKIN_MM, '--support', 'beam', '--body-json', json.dumps(c['car']['params'])]
for key, flag in (('W', '--W'), ('x_front', '--x-front'), ('d_halo', '--d-halo')):
    if key in c.get('layout', {}):
        args += [flag, str(c['layout'][key])]
for part, flag in pattern.PART_FLAGS.items():
    if c['car']['parts'].get(part):
        args += [flag, json.dumps(c['car']['parts'][part])]


def show(name, m):
    e, n = np.unique(m.edges_sorted, axis=0, return_counts=True)
    bad = e[n != 2]
    print(f'LAB {name}: verts {len(m.vertices)} faces {len(m.faces)} watertight {m.is_watertight} winding {m.is_winding_consistent} counts {dict(zip(*[x.tolist() for x in np.unique(n[n != 2], return_counts=True)]))}', flush=True)
    if len(bad):
        print('LAB   bad edge midpoints mm', np.round(m.vertices[bad].mean(axis=1)[:12] * 1e3, 2).tolist(), flush=True)


orig = up.extract_half_surface
def spy(geom):
    half = orig(geom)
    if not half.is_watertight:
        show('as extracted', half)
        h = half.copy()
        h.vertices[h.vertices[:, 1] < 0, 1] = 0.0
        show('y clamped', h)
        print('LAB grid spacing', geom.phi.spacing if hasattr(geom.phi, 'spacing') else '?', 'y min', float(half.vertices[:, 1].min()), flush=True)
        h2 = h.copy(); h2.merge_vertices(); show('merged', h2)
        h3 = h2.copy(); trimesh.repair.fill_holes(h3); show('filled', h3)
        h4 = h.copy(); h4.update_faces(h4.nondegenerate_faces()); h4.remove_unreferenced_vertices(); h4.merge_vertices(); show('no degenerate faces', h4)
    return half
up.extract_half_surface = spy
try:
    S = rc.main(args)
    print('LAB built', S['legality']['summary']['failed'], S['body'].get('build', {}).get('pinch_cells_filled'), flush=True)
except SystemExit as e:
    print('LAB exit', e, flush=True)
