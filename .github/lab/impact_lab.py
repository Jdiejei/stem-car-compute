"""What would more freedom be worth in race time? `sweep NAME SKIN`: one variation of the start
car by CFD. `map`: how much of what the adjoint asks for today's settings can reach. Prints only."""
import copy, json, sys, tempfile
from pathlib import Path
sys.path[:0] = ['.', 'checks']
import numpy as np
from scipy.spatial import cKDTree
import pattern, solver, run_car as rc, assembly as p4, openfoam_adjoint as oa

OPT = '{"layer_overrides":{"nSurfaceLayers":0}}'
V = {'base': {},
     'fw_endplate8': {'fw': {'endplate_h_mm': 8.0}}, 'fw_endplate15': {'fw': {'endplate_h_mm': 15.0}},
     'fw_chord18': {'fw': {'chord_mm': 18.0}}, 'fw_chord22': {'fw': {'chord_mm': 22.0}},
     'fw_flapgap1': {'fw': {'flap_gap_mm': 1.0}}, 'fw_noflap': {'fw': {'flap_chord_mm': 0.0}},
     'rw_aoa-4': {'rw': {'aoa_deg': -4.0}}, 'rw_aoa4': {'rw': {'aoa_deg': 4.0}}, 'rw_camber4': {'rw': {'camber': 0.04}},
     'rw_chord20': {'rw': {'chord_mm': 20.0}}, 'rw_span30': {'rw': {'half_span_mm': 30.0}}, 'rw_span35': {'rw': {'half_span_mm': 35.0}},
     'rw_x10': {'rw': {'x_le_after_ref_b_mm': 10.0}}, 'rw_x20': {'rw': {'x_le_after_ref_b_mm': 20.0}},
     'rw_pylon6': {'rw': {'pylon_chord_mm': 6.0}}, 'rw_pylon15': {'rw': {'pylon_chord_mm': 15.0}}, 'rw_high3': {'rw': {'clear_air_margin_mm': 3.5}},
     'sup_nodiscF': {'sup': {'disc_front': False}}, 'sup_nodiscR': {'sup': {'disc_rear': False}}, 'sup_disc9': {'sup': {'disc_r_mm': 9.0}},
     'sup_pod10': {'sup': {'pod_len_mm': 10.0}}, 'sup_arch16': {'sup': {'pod_arch_mm': 16.0}}, 'sup_arch22': {'sup': {'pod_arch_mm': 22.0}},
     'nose_blend5': {'nose': {'blend_after_ref_a_mm': 5.0}},
     'wheel_round1': {'round': 1.0}, 'wheel_round2': {'round': 2.0}, 'wheel_round3': {'round': 3.0},
     # T7.4 measures contact width without chamfers or fillets, so the rounded wheels above are
     # illegal (1 mm off each side of 13.25). These keep the flat and grow the wheel outward.
     'wheel_legal1': {'round': 1.0, 'wider': True}, 'wheel_legal2': {'round': 2.0, 'wider': True}}
FLAGS = {'fw': '--fwing-json', 'rw': '--rwing-json', 'sup': '--support-json', 'nose': '--nose-json'}
state = json.loads(solver.STATE.read_text())
c = state['chains'][0]

if sys.argv[1] == 'sweep':
    name, skin = sys.argv[2], sys.argv[3]
    v = V[name]
    if 'round' in v:             # the CFD wheel with its shoulders rounded: tread width kept in the middle
        import trimesh, wheel as wh
        rad = v['round']
        def rounded(R_mm, width_mm, x_axle_mm, y_inner_mm, sink_mm=0.3, sections=128):
            t = np.linspace(0.0, np.pi / 2, 9)
            hw = (width_mm + (2 * rad if v.get('wider') else 0.0)) / 2.0
            top = [(R_mm - rad + rad * np.cos(a), hw - rad + rad * np.sin(a)) for a in t]
            prof = [(R_mm - rad + rad * np.cos(a), -hw + rad - rad * np.sin(a)) for a in t[::-1]] + top
            line = np.array([(0.0, -hw)] + prof + [(0.0, hw)]) / 1e3
            m = trimesh.creation.revolve(line, sections=sections)
            m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
            m.apply_translation([x_axle_mm / 1e3, (y_inner_mm + hw) / 1e3, (R_mm - sink_mm) / 1e3])
            return m
        wh.cfd_surface = rounded
    args = ['--out', tempfile.mkdtemp(), '--cfd', '--res', 'medium', '--np', '4', '--cfd-iters', '1000', '--cfd-json', OPT,
            '--body-json', json.dumps(c['car']['params']), '--skin-mm', skin]
    for k, flag in FLAGS.items():
        if k in v:
            args += [flag, json.dumps(v[k])]
    S = rc.main(args)
    ci = S['cfd_initial']
    print('IMP', name, skin, 'D', round(ci['D20_N'], 5), 'T', round(ci['T_at_target_s'], 5), 'L', round(ci['L_N'], 4), 'mass', round(S['mass']['manufactured_mass_g'], 2),
          'failed', [f for f in S['legality']['summary']['failed'] if f != 'T3.6_mass'], flush=True)
else:
    orig = oa.oc.build_snappy_dict
    d = solver._d(c)
    out = Path(tempfile.mkdtemp())
    a = rc.parse_args(['--out', str(out), '--body-json', json.dumps(c['car']['params']), '--skin-mm', str(c['skin_mm'])])
    geom, info, asm = rc.build_car(a, out, **rc.part4_kwargs(a))
    b = rc.make_bindings(a, out, asm, seed_geom=copy.deepcopy(geom))
    gate = b.run_quality_gates(copy.deepcopy(geom), 'initial', str(out / 'gates'))
    ref_a, ref_b = a.x_front - 16.0, a.x_front + a.W + 16.0
    frame = (((ref_a - 41.0) / 1e3, 0.0, 0.0), ((ref_b + 41.0) / 1e3, 0.0435, 0.066))
    cfg = oa.AdjointRunConfig(resolution='medium', n_subdomains=4, domain_reference_bounds=frame,
                              extra_surfaces=p4.extra_surfaces_from(str(Path(asm['_dir']) / 'assembly.json')),
                              sensitivity_on_all_parts=True, layer_overrides=solver.SEARCH_CFD['layer_overrides'])
    raw = oa.invoke_adjoint(str(gate.stl_half_path), str(Path(oa.__file__).resolve().parent / 'cfd_case_template'), cfg, by_patch=True)
    total = sum(float(np.abs(v[1]).sum()) for v in raw.values())
    print('IMP map share of |sensitivity| by part', {k: round(float(np.abs(v[1]).sum()) / total, 3) for k, v in raw.items()}, flush=True)
    P, s = raw['car'][0] * 1e3, raw['car'][1]
    x1 = a.x_front + a.W + 56.0
    skin = c['skin_mm']
    eps = 0.1
    grad = np.stack([(solver._phi(d['params'], P + e, ref_a, x1, skin) - solver._phi(d['params'], P - e, ref_a, x1, skin)) / (2 * eps) for e in np.eye(3) * eps], axis=1)
    gn = np.maximum(np.linalg.norm(grad, axis=1), 0.2)
    active = np.abs(solver._phi(d['params'], P, ref_a, x1, skin)) < 1.0
    print('IMP map points', len(P), 'free to move', int(active.sum()), flush=True)
    names = solver.body_settings()
    Vm = np.stack([solver.surface_speed(d, n, P, gn, ref_a, x1, skin) * active for n in names], axis=1)[active]
    Pa, sa = P[active], s[active]
    tree = cKDTree(Pa)
    for ell in (0.0, 2.0, 3.0, 5.0, 7.0, 10.0):
        if ell:
            nb = tree.query_ball_point(Pa, ell)
            sm = np.array([sa[i].mean() for i in nb])
        else:
            sm = sa
        coef, *_ = np.linalg.lstsq(Vm, sm, rcond=None)
        fit = Vm @ coef
        print(f'IMP map features over {ell:g} mm: settings reach {np.linalg.norm(fit) / np.linalg.norm(sm):.3f} of what the adjoint asks for', flush=True)
        if ell == 5.0:
            res = sm - fit
            bins = np.arange(np.floor(Pa[:, 0].min() / 20) * 20, Pa[:, 0].max() + 20, 20)
            idx = np.digitize(Pa[:, 0], bins)
            print('IMP map out of reach by x (mm): share', {int(bins[i - 1]): round(float((res[idx == i] ** 2).sum() / (res ** 2).sum()), 3) for i in np.unique(idx)}, flush=True)
            zmid = (Pa[:, 2] > np.median(Pa[:, 2]))
            print('IMP map out of reach, upper half vs lower half of the points', round(float((res[zmid] ** 2).sum() / (res ** 2).sum()), 3), flush=True)
            print('IMP map out of reach, inner |y|<10 vs outer', round(float((res[np.abs(Pa[:, 1]) < 10] ** 2).sum() / (res ** 2).sum()), 3), flush=True)
