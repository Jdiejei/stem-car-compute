"""Why does the adjoint not predict drag? Slopes for the start car, weighted several ways,
against what CFD measured. Prints only."""
import copy, json, sys, tempfile
from pathlib import Path
sys.path[:0] = ['.', 'checks']
import numpy as np
from scipy.spatial import cKDTree
import pattern, solver, run_car as rc, assembly as p4, openfoam_adjoint as oa

layers = sys.argv[1] == 'layers'
if not layers:
    orig = oa.oc.build_snappy_dict
    def no_layers(*a, **k):
        k['layer_overrides'] = {'nSurfaceLayers': 0}
        return orig(*a, **k)
    oa.oc.build_snappy_dict = no_layers

state = json.loads(solver.STATE.read_text())
c = state['chains'][0]
out = Path(tempfile.mkdtemp())
a = rc.parse_args(['--out', str(out), '--body-json', json.dumps(c['car']['params']), '--skin-mm', str(c['skin_mm'])])
geom, info, asm = rc.build_car(a, out, **rc.part4_kwargs(a))
b = rc.make_bindings(a, out, asm, seed_geom=copy.deepcopy(geom))
gate = b.run_quality_gates(copy.deepcopy(geom), 'initial', str(out / 'gates'))
ref_a, ref_b = a.x_front - 16.0, a.x_front + a.W + 16.0
frame = (((ref_a - 41.0) / 1e3, 0.0, 0.0), ((ref_b + 41.0) / 1e3, 0.0435, 0.066))
cfg = oa.AdjointRunConfig(resolution='medium', n_subdomains=4, domain_reference_bounds=frame,
                          extra_surfaces=p4.extra_surfaces_from(str(Path(asm['_dir']) / 'assembly.json')),
                          sensitivity_on_all_parts=True)
raw = oa.invoke_adjoint(str(gate.stl_half_path), str(Path(oa.__file__).resolve().parent / 'cfd_case_template'), cfg, by_patch=True)
P = raw['car'][0] * 1e3
s = raw['car'][1] * cfg.air_density_kgm3 * 2.0 * 1e-3
print('LAB points', len(P), 's mean', float(s.mean()), 'abs p50 p99 max', np.round(np.percentile(np.abs(s), [50, 99, 100]), 8).tolist(), flush=True)
frac = np.sort(np.abs(s))[::-1]
print('LAB share of |s| in the top 1%, 10%:', round(float(frac[:len(s) // 100].sum() / frac.sum()), 3), round(float(frac[:len(s) // 10].sum() / frac.sum()), 3), flush=True)
d_nn = cKDTree(P).query(P, k=7)[0][:, 1:].mean(axis=1)
area = np.pi * (d_nn / 2.0) ** 2 * 4.0        # mm2 a point stands for, near enough
print('LAB area per point mm2 p5 p50 p95', np.round(np.percentile(area, [5, 50, 95]), 3).tolist(), flush=True)
print('LAB corr(|s|, area)', round(float(np.corrcoef(np.abs(s), area)[0, 1]), 3), flush=True)

# dD/dp from CFD on this car, layers on: the two gradient checks. N per unit of the setting.
direct = {'st_zt3': -0.011535, 'mode47': 0.00085, 'mode5': 0.001238, 'mode41': 0.000527, 'st_b4': 0.001738, 'mode25': 0.00143,
          's_b': 0.000271, 'mode6': -0.0075, 'st_zb1': 0.00469, 'mode3': -0.00201, 'st_b0': 0.00319, 'p': 0.0575,
          'st_zb5': -0.00299, 'mode2': -0.00029, 'mode1': -0.00039, 'st_zb0': 0.00172, 'st_b1': -0.00159}
top = np.percentile(np.abs(s), 99)
variants = {'as is': s, 'x area': s * area, '/ area': s / area, 'clipped 99%': np.clip(s, -top, top), 'x area clipped': np.clip(s, -top, top) * area}
d = solver._d(c)
for name, sv in variants.items():
    sl = solver.body_slopes(d, c['skin_mm'], P, sv, ref_a, a.x_front + a.W + 56.0)
    names = [k for k in direct if k in sl]
    A = np.array([sl[k]['dD'] for k in names])
    B = np.array([direct[k] for k in names])
    w = np.array([pattern.step0(k) for k in names])
    big = np.abs(B * w) * 2 > 0.009      # clear of the 4.4 mN noise on a pair, twice over
    print(f'LAB {name}: r {np.corrcoef(A * w, B * w)[0, 1]:+.3f} signs {(np.sign(A) == np.sign(B)).mean():.2f}, clear ones ({big.sum()}): signs {(np.sign(A[big]) == np.sign(B[big])).mean():.2f} ', flush=True)
    print('LAB   ', {k: (round(float(x * pattern.step0(k)), 5), round(direct[k] * pattern.step0(k), 5)) for k, x in zip(names, A)}, flush=True)
