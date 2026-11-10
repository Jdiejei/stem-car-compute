"""Measured map on a real car, pilot (the backup map of BUILD_SPEC 7, step 4, on cars).

One base car is built and run once with its case kept. Each mode is a Gaussian bump of
radius R on the car's own half-body STL, moved along the outward vertex normal by a few
amplitudes (+ = grow the solid). Every bumped car reuses the base car's mesh, reshaped onto
it (Part 2's morph_from), and starts from the base car's flow (warm_from), so remeshing noise
is zero and every car starts on the same flow branch. Points on the symmetry plane keep
y = 0 (their y move is dropped), so the closing face never moves.

The pilot asks: is drag (and lift) linear in the amplitude, and is the +a / -a difference
well clear of the noise, at amplitudes small enough to stay local? The report gives, per mode,
the central-difference slope at each amplitude and how far the slopes at a and 2a disagree.

    python car_modes.py base   <seed> <out>                (run from part5-simulation)
    python car_modes.py mode   <out> <k> "<amps mm>"
    python car_modes.py report <dir with mode_*.json>
Runs on GitHub only (p3_car_modes.yml). Env: P3_NMODES (10), P3_MODE_R_MM (10),
P3_CFD_RES (medium), P3_CFD_ITERS (2000).
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np

NMODES = int(os.environ.get("P3_NMODES", "10"))
R_M = float(os.environ.get("P3_MODE_R_MM", "10")) / 1e3
RES = os.environ.get("P3_CFD_RES", "medium")
ITERS = int(os.environ.get("P3_CFD_ITERS", "2000"))
VERTEX = re.compile(r"^(\s*vertex\s+)(\S+)\s+(\S+)\s+(\S+)\s*$")


def stl_vertex_lines(text: str):
    """(line index, xyz) of every 'vertex' line of an ASCII STL, in file order."""
    out = []
    for i, line in enumerate(text.splitlines()):
        m = VERTEX.match(line)
        if m:
            out.append((i, [float(m.group(2)), float(m.group(3)), float(m.group(4))]))
    return out


def surface(stl: Path):
    """Merged vertices, outward unit vertex normals and vertex areas of a watertight half body."""
    import trimesh
    m = trimesh.load(str(stl), force="mesh")
    V = np.asarray(m.vertices, float)
    A = np.zeros(len(V))
    np.add.at(A, m.faces.ravel(), np.repeat(m.area_faces / 3.0, 3))
    N = np.asarray(m.vertex_normals, float)
    if m.volume < 0:
        N = -N
    return V, N, A


def bump_disp(V, N, c, amp_m):
    """Gaussian bump of radius R at c, along the outward normal; symmetry-plane points keep y = 0."""
    d = amp_m * np.exp(-np.sum((V - c) ** 2, axis=1) / (2 * R_M ** 2))[:, None] * N
    d[V[:, 1] < 1e-7, 1] = 0.0
    return d


def write_moved_stl(src: Path, dst: Path, V, D):
    """The source STL text with every vertex line moved by D of its merged vertex."""
    from scipy.spatial import cKDTree
    lines = src.read_text().splitlines()
    vl = stl_vertex_lines("\n".join(lines))
    dist, idx = cKDTree(V).query(np.array([p for _, p in vl]))
    assert dist.max() < 1e-9, f"STL vertex not found among the merged vertices ({dist.max():.2e} m)"
    for (i, p), j in zip(vl, idx):
        q = np.asarray(p) + D[j]
        lines[i] = VERTEX.match(lines[i]).group(1) + " ".join(f"{t:.12e}" for t in q)
    dst.write_text("\n".join(lines) + "\n")


def centres(V, N, n):
    """n mode centres spread over the body (farthest-point), off the closing face."""
    ok = np.where(N[:, 1] > -0.9)[0]
    P = V[ok]
    pick = [int(np.argmin(P[:, 0]))]                       # start at the nose tip
    d = np.linalg.norm(P - P[pick[0]], axis=1)
    while len(pick) < n:
        pick.append(int(np.argmax(d)))
        d = np.minimum(d, np.linalg.norm(P - P[pick[-1]], axis=1))
    return P[pick]


def cfd(stl: Path, frame, extra, **kw):
    import cfd_wrapper as cw
    import solver
    q, h = cw.run_half_car_cfd(str(stl), max_iterations=ITERS, resolution=RES, n_subdomains=4,
                               extra_surfaces=extra, domain_reference_bounds=frame,
                               layer_overrides=solver.SEARCH_CFD["layer_overrides"], **kw)
    return {"D20_N": 2 * q.D20, "L_N": 2 * q.L, "converged": bool(h.converged),
            "residual": h.residual_final, "stderr": h.force_mean_stderr}


def base(seed: int, out: Path):
    import pattern, solver                             # noqa: F401  (these put the other parts on the path)
    import run_car as rc
    import assembly as p4
    import cfd_wrapper as cw
    out.mkdir(parents=True, exist_ok=True)
    car = solver.random_start(seed)
    work = out / "build"
    work.mkdir(exist_ok=True)
    a = rc.parse_args(["--out", str(work), "--body-json", json.dumps(car["params"])])
    geom, info, asm = rc.build_car(a, work, **rc.part4_kwargs(a))
    b = rc.make_bindings(a, work, asm, seed_geom=copy.deepcopy(geom))
    gate = b.run_quality_gates(copy.deepcopy(geom), "initial", str(work / "gates"))
    if not gate.stl_half_path:
        raise SystemExit(f"the car failed the CFD gate: {gate.failure_reason}")
    stl = out / "base.stl"
    shutil.copy(gate.stl_half_path, stl)
    extra = []                                          # Part 4's parts, copied next to base.stl
    for i, s in enumerate(p4.extra_surfaces_from(str(Path(asm["_dir"]) / "assembly.json"))):
        dst = out / f"part{i}_{Path(s['stl']).name}"
        shutil.copy(s["stl"], dst)
        extra.append({**s, "stl": str(dst.resolve())})
    ref_a, ref_b = a.x_front - 16.0, a.x_front + a.W + 16.0
    frame = (((ref_a - 41.0) / 1e3, 0.0, 0.0), ((ref_b + 41.0) / 1e3, 0.0435, 0.066))
    r, case = cfd_kept(stl, frame, extra)
    shutil.copytree(case, out / "base_case", ignore=shutil.ignore_patterns("processor*"))
    shutil.rmtree(case)
    V, N, A = surface(stl)
    C = centres(V, N, NMODES)
    np.savez(out / "base.npz", V=V, N=N, A=A, C=C, frame=np.array(frame, dtype=object), seed=seed)
    (out / "base.json").write_text(json.dumps({"seed": seed, "frame": frame, "extra": extra, **r}, default=str))
    print(f"LAB base car {seed}: drag {r['D20_N']:.5f} N, lift {r['L_N']:.5f} N, converged {r['converged']},"
          f" force-mean error {r['stderr']}; {NMODES} mode centres of radius {R_M * 1e3:.1f} mm", flush=True)


def cfd_kept(stl: Path, frame, extra, **kw):
    """cfd() with the case kept; returns (result, case dir). The caller removes the case."""
    import cfd_wrapper as cw
    runs = Path(cw.__file__).resolve().parent / "cfd_case_template" / "runs"
    before = set(runs.iterdir()) if runs.exists() else set()
    r = cfd(stl, frame, extra, keep_run_dir=True, **kw)
    return r, (set(runs.iterdir()) - before).pop()


def mode(out: Path, k: int, amps_mm):
    import pattern, solver                             # noqa: F401
    z = np.load(out / "base.npz", allow_pickle=True)
    meta = json.loads((out / "base.json").read_text())
    frame = tuple(tuple(t) for t in meta["frame"])
    V, N, c = z["V"], z["N"], z["C"][k]
    for amp in amps_mm:
        D = bump_disp(V, N, c, amp / 1e3)
        stl = out / f"mode_{k}_{amp:+g}.stl"
        write_moved_stl(out / "base.stl", stl, V, D)
        r, case = cfd_kept(stl, frame, meta["extra"], morph_from=str((out / "base_case").resolve()),
                           warm_from=str((out / "base_case").resolve()))
        fallback = (case / "MORPH_FALLBACK").exists()
        shutil.rmtree(case)
        dV = float(np.sum(np.einsum("ij,ij->i", D, N) * z["A"]))
        rec = {"k": k, "amp_mm": amp, "centre_mm": (c * 1e3).tolist(), "half_volume_change_m3": dV,
               "morph_fallback": fallback, **r}
        (out / f"mode_{k}_{amp:+g}.json").write_text(json.dumps(rec, default=float))
        print(f"LAB mode {k} at {amp:+g} mm: drag {r['D20_N']:.6f} N ({r['D20_N'] - meta['D20_N']:+.2e}),"
              f" lift {r['L_N']:.6f} N, converged {r['converged']}", flush=True)
        stl.unlink()


def report(d: Path):
    recs = [json.loads(p.read_text()) for p in Path(d).rglob("mode_*.json")]
    bases = [json.loads(p.read_text()) for p in Path(d).rglob("base.json")]
    if not bases:
        raise SystemExit("no base.json")
    b = bases[0]
    print(f"LAB base drag {b['D20_N']:.5f} N, lift {b['L_N']:.5f} N; {len(recs)} bumped cars")
    by = {}
    for r in recs:
        by.setdefault(r["k"], {})[r["amp_mm"]] = r
    bad = [r for r in recs if not r["converged"] or r.get("morph_fallback")]
    if bad:
        print(f"LAB WARNING: {len(bad)} bumped cars did not converge or fell back to a fresh mesh")
    disagree = []
    for k in sorted(by):
        m = by[k]
        line = []
        slopes = {}
        for a in sorted({abs(x) for x in m}):
            if a in m and -a in m:
                s = (m[a]["D20_N"] - m[-a]["D20_N"]) / (2 * a)
                curv = (m[a]["D20_N"] + m[-a]["D20_N"] - 2 * b["D20_N"]) / a ** 2
                slopes[a] = s
                line.append(f"{a:g} mm: slope {s:+.3e} N/mm, bend {curv:+.2e} N/mm2")
        if len(slopes) >= 2:
            lo, hi = min(slopes), max(slopes)
            rel = abs(slopes[hi] - slopes[lo]) / max(abs(slopes[hi]), 1e-30)
            disagree.append(rel)
            line.append(f"slopes at {lo:g} and {hi:g} mm differ by {rel:.0%}")
        print(f"LAB mode {k}: " + "; ".join(line))
    if disagree:
        print(f"LAB linear check: slopes at small and large amplitude differ by median {np.median(disagree):.0%},"
              f" worst {max(disagree):.0%} over {len(disagree)} modes")


if __name__ == "__main__":
    sys.path[:0] = [".", str(Path(__file__).resolve().parent)]
    cmd = sys.argv[1]
    if cmd == "base":
        base(int(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "mode":
        mode(Path(sys.argv[2]), int(sys.argv[3]), [float(t) for t in sys.argv[4].split()])
    elif cmd == "report":
        report(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
