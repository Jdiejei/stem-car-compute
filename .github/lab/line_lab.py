"""Does the adjoint point downhill? `slopes`: solve it on the start car, no layers. `step`: move
the body along it (minus = downhill; plus = uphill, the control) and measure drag. Prints only."""
import copy, json, sys, tempfile
from pathlib import Path
sys.path[:0] = ['.', 'checks']
import numpy as np
import pattern, solver, run_car as rc, assembly as p4, openfoam_adjoint as oa

OPT = '{"layer_overrides":{"nSurfaceLayers":0}}'
state = json.loads(solver.STATE.read_text())
c = state['chains'][0]
d = solver._d(c)
if sys.argv[1] == 'slopes':
    orig = oa.oc.build_snappy_dict
    def no_layers(*a, **k):
        k['layer_overrides'] = {'nSurfaceLayers': 0}
        return orig(*a, **k)
    oa.oc.build_snappy_dict = no_layers
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
    P, s = raw['car'][0] * 1e3, raw['car'][1]
    sl = solver.body_slopes(d, c['skin_mm'], P, s, ref_a, a.x_front + a.W + 56.0)
    Path(sys.argv[2]).write_text(json.dumps({k: v for k, v in sl.items() if not k.startswith('_')}))
    print('LINE slopes', len(sl), flush=True)
else:
    sl = json.loads(Path(sys.argv[2]).read_text())
    move = float(sys.argv[3])                 # mm of typical surface move; + is downhill
    g = {k: v['dD'] for k, v in sl.items()}
    speeds = {k: v['speed'] for k, v in sl.items()}
    n = solver.plan_step(d, g, speeds, move) if move else d
    changed = sum(pattern.get(n, k) != pattern.get(d, k) for k in g)
    args = ['--out', tempfile.mkdtemp(), '--cfd', '--res', 'medium', '--np', '4', '--cfd-iters', '1000', '--cfd-json', OPT,
            '--body-json', json.dumps(n['params']), '--skin-mm', str(c['skin_mm'])]
    S = rc.main(args)
    ci = S['cfd_initial']
    print('LINE move', move, 'settings moved', changed, 'D', ci['D20_N'], 'T', ci['T_at_target_s'], 'body volume cm3', S['manufactured']['machined_body'].get('cm3'),
          'failed', [f for f in S['legality']['summary']['failed'] if f != 'T3.6_mass'], flush=True)
