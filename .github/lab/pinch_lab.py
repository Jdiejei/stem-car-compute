"""Which step makes a support's pinched edges, and which repair closes them? Prints only."""
import collections, json, os, random, sys, tempfile, time
sys.path[:0] = ['.', 'checks']
import numpy as np, trimesh, manifold3d as m3, pymeshlab as ml
import pattern, stress_cars as sc, param_body as pb, joints, run_car as rc

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
tmp = os.path.join(tempfile.mkdtemp(), 'x.stl')


def counted(t):
    t.export(tmp)
    b = trimesh.load(tmp, force='mesh')
    e, n = np.unique(b.edges_sorted, axis=0, return_counts=True)
    return b, e, n


def report(name, t, t0, ref):
    b, e, n = counted(t)
    print(f'LAB {name}: {time.time() - t0:.0f}s faces {len(b.faces)} bad {(n != 2).sum()} volume? {b.is_volume} watertight {b.is_watertight} winding {b.is_winding_consistent} '
          f'mm3 {b.volume:.1f} vs {ref:.1f} shells {sorted((round(float(p.volume), 1) for p in b.split(only_watertight=False)), key=abs, reverse=True)[:5]}', flush=True)
    return b


# Which boolean first leaves surfaces an STL welds together?
orig_bool = joints._bool
seen = []
def bool_spy(op, meshes, *a, **k):
    out = orig_bool(op, meshes, *a, **k)
    try:
        if out is not None and not out.is_empty and out.bounds[0, 0] < 0.09:
            t = out.copy()
            t.apply_scale(1e3)
            b, e, n = counted(t)
            bad = int((n != 2).sum())
            if bad and (not seen or seen[-1] != bad):
                seen.append(bad)
                mid = np.abs(b.vertices[e[n != 2]].mean(axis=1))
                print(f'LAB step {op} of {len(meshes)}: bad {bad} bounds {np.round(t.bounds, 1).tolist()} at x {np.round(np.percentile(mid[:, 0], [0, 100]), 1).tolist()} |y| {np.round(np.percentile(mid[:, 1], [0, 100]), 2).tolist()} z {np.round(np.percentile(mid[:, 2], [0, 100]), 1).tolist()}', flush=True)
    except Exception as exc:
        print('LAB spy', exc, flush=True)
    return out
joints._bool = bool_spy

orig_pod = joints.pod_joint
def pod_spy(part, body_half, channels, keep_out=None):
    j = orig_pod(part, body_half, channels, keep_out)
    print('LAB channels', {k: {a: round(float(b), 2) for a, b in v.items()} for k, v in channels.items()}, flush=True)
    if j is not None and j.printed_whole is not None:
        report('pod whole', j.printed_whole.copy().apply_scale(1e3), time.time(), abs(j.printed_whole.volume) * 1e9)
    return j
joints.pod_joint = pod_spy


def lab(mesh):
    m = mesh.copy()
    m.apply_scale(1e3)
    ref = float(m.volume)
    man = m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    o = man.simplify(1e-3).to_mesh()
    t = trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False)
    b = report('plain', t, time.time(), ref)
    e, n = np.unique(b.edges_sorted, axis=0, return_counts=True)
    ends = b.vertices[e[n != 2]]
    print('LAB some bad edges', np.round(ends[:: max(1, len(ends) // 8)][:8].reshape(-1, 3), 3).tolist(), flush=True)
    t0 = time.time()
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(b.vertices, b.faces))
    for _ in range(4):
        ms.apply_filter('meshing_merge_close_vertices', threshold=ml.PureValue(0.01))
        ms.apply_filter('meshing_remove_duplicate_faces')
        ms.apply_filter('meshing_repair_non_manifold_edges', method='Remove Faces')
        ms.apply_filter('meshing_repair_non_manifold_vertices')
        ms.apply_filter('meshing_close_holes', maxholesize=200)
    ms.apply_filter('meshing_re_orient_faces_coherently')
    q = ms.current_mesh()
    f = trimesh.Trimesh(q.vertex_matrix(), q.face_matrix(), process=False)
    f.remove_unreferenced_vertices()
    f.merge_vertices()
    report('weld and fill', f, t0, ref)
    t0 = time.time()
    cube = m3.Manifold.cube((0.04, 0.04, 0.04), True)
    grown = man.simplify(5e-3).minkowski_sum(cube)
    o = grown.to_mesh()
    report('grown 20 um', trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=False), t0, ref)


orig = joints._export_mm
def spy(mesh, path, fair=False, *a, **k):
    if 'printed_support_front' in str(path) and not a and not k:
        try:
            lab(mesh)
        except Exception as exc:
            print('LAB failed', type(exc).__name__, exc, flush=True)
    return orig(mesh, path, fair, *a, **k)
joints._export_mm = spy
rc.main(args)
