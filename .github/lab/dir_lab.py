"""One setting of the start car moved one step, measured by CFD on the given mesh. Prints only."""
import json, sys, tempfile
sys.path[:0] = ['.', 'checks']
import numpy as np
import pattern, solver, run_car as rc

name, sign, opt = sys.argv[1], float(sys.argv[2]), sys.argv[3]
state = json.loads(solver.STATE.read_text())
c = state['chains'][0]
d = solver._d(c)
if name != 'base':
    lo, hi = pattern.bounds(name)
    v = float(np.clip(pattern.get(d, name) + sign * pattern.step0(name), lo, hi))
    d = pattern.put(d, name, v)
else:
    v = 0.0
args = ['--out', tempfile.mkdtemp(), '--cfd', '--res', 'medium', '--np', '4', '--cfd-iters', '1000', '--cfd-json', opt,
        '--body-json', json.dumps(d['params']), '--skin-mm', str(c['skin_mm'])] + solver._layout_args(d.get('layout', {}))
for part, flag in pattern.PART_FLAGS.items():
    if d.get('parts', {}).get(part):
        args += [flag, json.dumps(d['parts'][part])]
S = rc.main(args)
ci = S['cfd_initial']
print('DIR', name, sign, v, 'D', ci['D20_N'], 'T', ci['T_at_target_s'], 'failed', [f for f in S['legality']['summary']['failed'] if f != 'T3.6_mass'], flush=True)
