"""Physics sign and mapping checks of the drag adjoint on a real car (BUILD_SPEC 8, 12.3, 12.6).

One adjoint solve, exactly as Part 5's solver runs it (no wall layers unless asked), then:
  * front-face sign: on upstream-facing surface at the front, growing the solid must ADD
    drag, so the map read the way the car code reads it must be > 0 there;
  * inflate sign: growing the whole body out a little must add drag (more frontal area);
  * mapping onto the STL: unmatched share at 5 mm, median and p95 match distance;
  * primal convergence: drag spread over the last 200 primal iterations.
Saves the map on the CFD surface points (car_<seed>.npz) for the compass test.

    python car_sign.py <seed> <layers|nolayers> <out_dir>      (run from part5-simulation)
Runs on GitHub only (p3_car_sign.yml).
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

sys.path[:0] = [".", "checks", str(Path(__file__).resolve().parent)]
import pattern, solver                 # noqa: E402,F401  (these put the other parts on the path)
import run_car as rc                   # noqa: E402
import assembly as p4                  # noqa: E402
import openfoam_adjoint as oa          # noqa: E402
from known_answer import read_mesh     # noqa: E402
from scipy.spatial import cKDTree      # noqa: E402

seed, mesh_kind, out = int(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
car = solver.random_start(seed)
work = out / f"car{seed}"
work.mkdir(parents=True, exist_ok=True)
argv = ["--out", str(work), "--body-json", json.dumps(car["params"])]
a = rc.parse_args(argv)
geom, info, asm = rc.build_car(a, work, **rc.part4_kwargs(a))
b = rc.make_bindings(a, work, asm, seed_geom=copy.deepcopy(geom))
gate = b.run_quality_gates(copy.deepcopy(geom), "initial", str(work / "gates"))
if not gate.stl_half_path:
    raise SystemExit(f"the car failed the CFD gate: {gate.failure_reason}")
ref_a, ref_b = a.x_front - 16.0, a.x_front + a.W + 16.0
frame = (((ref_a - 41.0) / 1e3, 0.0, 0.0), ((ref_b + 41.0) / 1e3, 0.0435, 0.066))
layers = None if mesh_kind == "layers" else solver.SEARCH_CFD["layer_overrides"]
cfg = oa.AdjointRunConfig(resolution="medium", n_subdomains=4, domain_reference_bounds=frame,
                          extra_surfaces=p4.extra_surfaces_from(str(Path(asm["_dir"]) / "assembly.json")),
                          sensitivity_on_all_parts=True, layer_overrides=layers, keep_run_dir=True,
                          primal_iters=int(os.environ.get("P3_PRIMAL_ITERS", "1000")),
                          adjoint_iters=int(os.environ.get("P3_ADJOINT_ITERS", "1000")))
case_dir = Path(oa.__file__).resolve().parent / "cfd_case_template"
raw = oa.invoke_adjoint(str(gate.stl_half_path), str(case_dir), cfg, by_patch=True)
run = max((case_dir / "adjoint_runs").iterdir(), key=lambda p: p.stat().st_mtime)
m = read_mesh(run, walls=("car",), flat=False)
Pc, s = raw["car"]
assert np.allclose(Pc, m["P"][m["wall"]]), "patch point order differs"
A, n = m["area"], m["n_out"]
tag = f"LAB car {seed} {mesh_kind}:"

x = Pc[:, 0]
L = np.ptp(x)
front = (x < x.min() + 0.25 * L) & (n[:, 0] < -0.7)
rear = (x > x.max() - 0.25 * L) & (n[:, 0] > 0.7)
for name, sel in (("front-facing", front), ("rear-facing", rear)):
    if sel.any():
        print(f"{tag} {name} points {int(sel.sum())}: area-mean map {np.sum(s[sel] * A[sel]) / A[sel].sum():+.4e}"
              f", share > 0: {np.mean(s[sel] > 0):.2f}", flush=True)
print(f"{tag} inflate (sum map x area) {np.sum(s * A):+.4e}; (sum map) {np.sum(s):+.4e}  [physics: > 0]", flush=True)
front_ok = bool(front.any() and np.sum(s[front] * A[front]) > 0)
print(f"{tag} FRONT-FACE SIGN as coded: {'RIGHT' if front_ok else 'WRONG'}", flush=True)

stl = np.array(oa.oc.read_ascii_stl_vertices(str(gate.stl_half_path)))
dist = cKDTree(Pc).query(stl)[0]
print(f"{tag} STL vertices {len(stl)}, CFD surface points {len(Pc)}; unmatched at 5 mm {np.mean(dist > 5e-3):.4f};"
      f" median {np.median(dist) * 1e3:.3f} mm, p95 {np.percentile(dist, 95) * 1e3:.3f} mm,"
      f" max {dist.max() * 1e3:.2f} mm", flush=True)

inst = sorted((run / "optimisation/objective").rglob("*Instant*"))
if inst:
    J = np.array([float(l.split()[1]) for l in inst[0].read_text().splitlines()
                  if l.strip() and not l.startswith("#")])[:cfg.primal_iters]
    print(f"{tag} primal iterations {len(J)}, drag last value {J[-1]:.6e}, spread last 200 / value {np.ptp(J[-200:]) / abs(J[-1]):.2e}", flush=True)
logs = sorted(run.rglob("*adjoint*.log")) or sorted(run.rglob("log*"))
log = "".join(p.read_text(errors="replace") for p in logs if "adjoint" in p.name.lower()) if logs else ""
print(f"{tag} logs {[p.name for p in logs][:8]}", flush=True)
for f in ("Ux", "p", "Uax", "pa"):
    r = re.findall(rf"Solving for {f}, Initial residual = ([0-9.eE+-]+)", log)
    if r:
        print(f"{tag} residual {f}: first {float(r[0]):.1e} last {float(r[-1]):.1e}", flush=True)
miss = dist > 5e-3
for name, lo, hi in (("x", 0, 0), ("y", 1, 1), ("z", 2, 2)):
    print(f"{tag} unmatched STL vertices by {name} (mm, p5 p50 p95): "
          f"{np.round(np.percentile(stl[miss, lo] * 1e3, [5, 50, 95]), 1).tolist() if miss.any() else []}", flush=True)
np.savez(out / f"car_{seed}_{mesh_kind}.npz", P=Pc, s=s, n_out=n, area=A, stl_dist=dist, stl_miss=stl[miss],
         **{f"P_{k}": v[0] for k, v in raw.items()}, **{f"s_{k}": v[1] for k, v in raw.items()})
(out / f"car_{seed}_{mesh_kind}.json").write_text(json.dumps(dict(seed=seed, mesh=mesh_kind, front_ok=front_ok)))
