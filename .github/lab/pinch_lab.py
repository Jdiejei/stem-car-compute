"""Where do a support's pinched edges sit, and which repair closes them? Prints only."""
import collections, json, os, random, sys, tempfile, time
sys.path[:0] = ['.', 'checks']
import numpy as np, trimesh, manifold3d as m3, pymeshlab as ml
import pattern, stress_cars as sc, param_body as pb, joints, run_car as rc

seed, only = int(sys.argv[1]), int(sys.argv[2])
sc.SETTINGS = pattern.LOFT + [f"mode{i}" for i in range(pb.N_MODES)] + list(pattern.FLOOR) + list(pattern.PARTS)
rng = random.Random(seed)
for i in range(only + 1):
    c = sc.random_car(rng, rng.choice((0.05, 0.2, 0.5, 1.0)))
print('LAB sup', c['car']['parts'].get('sup'), 'layout', c.get('layout'), flush=True)
args = ['--out', tempfile.mkdtemp(), '--skin-mm', sc.FIXED_SKIN_MM, '--support', 'beam', '--body-json', json.dumps(c['car']['params'])]
for key, flag in (('W', '--W'), ('x_front', '--x-front'), ('d_halo', '--d-halo')):
    if key in c.get('layout', {}):
        args += [flag, str(c['layout'][key])]
for part, flag in pattern.PART_FLAGS.items():
    if c['car']['parts'].get(part):
        args += [flag, json.dumps(c['car']['parts'][part])]
tmp = os.path.join(tempfile.mkdtemp(), 'x.stl')


def report(name, t, t0, ref):
    t.export(tmp)
    b = trimesh.load(tmp, force='mesh')
    e, n = np.unique(b.edges_sorted, axis=0, return_counts=True)
    ps = b.split(only_watertight=False)
    print(f'LAB {name}: {time.time() - t0:.0f}s faces {len(b.faces)} bad {(n != 2).sum()} volume? {b.is_volume} watertight {b.is_watertight} winding {b.is_winding_consistent} '
          f'mm3 {b.volume:.1f} vs {ref:.1f} shells {sorted((round(float(p.volume), 1) for p in ps), key=abs, reverse=True)[:5]}', flush=True)
    return b


def lab(mesh):
    m = mesh.copy()
    m.apply_scale(1e3)
    ref = float(m.volume)
    print('LAB in: bounds', np.round(m.bounds, 2).tolist(), 'mm3', round(ref, 1), flush=True)
    man = m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    o = man.simplify(1e-3).to_mesh()
    t = trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False)
    b = report('plain', t, time.time(), ref)
    e, n = np.unique(b.edges_sorted, axis=0, return_counts=True)
    mid = b.vertices[e[n != 2]].mean(axis=1)
    cells = collections.Counter(tuple(int(v) for v in np.floor(p / 2.0) * 2) for p in np.c_[mid[:, 0], np.abs(mid[:, 1]), mid[:, 2]])
    print('LAB bad edges by 2 mm cell (x, |y|, z):', cells.most_common(14), flush=True)
    print('LAB |y| of bad edges, percentiles', np.round(np.percentile(np.abs(mid[:, 1]), [0, 10, 50, 90, 100]), 3).tolist(), flush=True)
    # A: rebuild on a grid.
    for cell in (0.1, 0.2):
        t0 = time.time()
        ms = ml.MeshSet()
        ms.add_mesh(ml.Mesh(m.vertices, m.faces))
        ms.apply_filter('generate_resampled_uniform_mesh', cellsize=ml.PureValue(cell), offset=ml.PureValue(0.0), mergeclosevert=False, multisample=True)
        q = ms.current_mesh()
        f = trimesh.Trimesh(q.vertex_matrix(), q.face_matrix(), process=False)
        f.remove_unreferenced_vertices()
        f.merge_vertices()
        report(f'grid {cell}', f, t0, ref)
    # G: weld, delete the bad faces, close the holes, a few times over.
    t0 = time.time()
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(b.vertices, b.faces))
    for _ in range(4):
        ms.apply_filter('meshing_merge_close_vertices', threshold=ml.PureValue(0.01))
        ms.apply_filter('meshing_remove_duplicate_faces')
        ms.apply_filter('meshing_repair_non_manifold_edges', method='Remove Faces')
        ms.apply_filter('meshing_repair_non_manifold_vertices')
        ms.apply_filter('meshing_close_holes', maxholesize=200, newfaceselected=False)
    ms.apply_filter('meshing_re_orient_faces_coherently')
    q = ms.current_mesh()
    f = trimesh.Trimesh(q.vertex_matrix(), q.face_matrix(), process=False)
    f.remove_unreferenced_vertices()
    f.merge_vertices()
    report('weld and fill', f, t0, ref)
    # B: close the gaps: grow by 20 um, then shrink back.
    t0 = time.time()
    cube = m3.Manifold.cube((0.04, 0.04, 0.04), True)
    grown = man.simplify(5e-3).minkowski_sum(cube)
    o = grown.to_mesh()
    report('grown 20 um', trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False), t0, ref)
    t0 = time.time()
    back = grown.minkowski_difference(cube)
    o = back.to_mesh()
    report('grown and shrunk', trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False), t0, ref)


orig = joints._export_mm
def spy(mesh, path, fair=False):
    if 'printed_support_front' in str(path):
        try:
            lab(mesh)
        except Exception as exc:
            print('LAB failed', type(exc).__name__, exc, flush=True)
    return orig(mesh, path, fair)
joints._export_mm = spy
cap = {}
build = rc.build_car
def spy2(*a, **k):
    out = build(*a, **k)
    cap['asm'] = out[2]
    return out
rc.build_car = spy2
rc.main(args)
print('LAB guides', cap['asm'].get('info', {}).get('tethers'), flush=True)
