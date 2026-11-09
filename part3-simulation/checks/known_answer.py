"""Step 1 of Part 3: prove the adjoint on a case with a known answer (BUILD_SPEC 7, 12.5).

A 2-D NACA 0012 at Re ~ 3e5 (OpenFOAM's shipped mesh), drag objective. The adjoint map
is compared with central finite differences of drag for smooth Gaussian bumps.

The adjoint dictionaries are Part 2's car dictionaries (openfoam_adjoint), with only the
patch names, the drag direction, the speed and the iteration counts changed, so this tests
OUR settings, not the tutorial's.

Sign convention under test: the car code reads `pointSensNormal` as "drag change per
OUTWARD (solid grows) move". That is used as is here; nothing is fitted.

    python known_answer.py base <variant> <out_dir>     primal + adjoint, saves the map
    python known_answer.py bump <k> <amp> <out_dir>     primal on the bumped mesh, saves J
    python known_answer.py judge <in_dir>               compares and prints PASS / FAIL
Runs on GitHub only (p3_known_answer.yml).
"""
from __future__ import annotations

import gzip
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "part2-simulation"))
import openfoam_adjoint as oa  # noqa: E402

BASHRC = "/usr/lib/openfoam/openfoam2412/etc/bashrc"
TUT = "incompressible/adjointOptimisationFoam"
WALLS = ("suction", "pressure")
RE = 3.0e5
U = np.array([59.96344962, 2.0939698, 0.0])     # the tutorial's freestream (2 deg)
PRIMAL_ITERS = 4000      # fixed counts (residual targets unreachable) so every run ends
ADJOINT_ITERS = 4000     # at a known iteration and writes its fields there
BUMP_R = 0.04            # Gaussian radius, chords
BUMP_A = 1.0e-3          # amplitude, chords (amp=1); amp=0.5 checks linearity
MORPH_L = 0.10           # how far the move fades into the mesh, chords
# 20 bump centres: (wall, x/c). The first 10 are the pre-chosen official set (pass mark
# 9/10 signs, r >= 0.9); all 20 are reported too for a firmer r.
CENTRES = [("suction", .1), ("suction", .3), ("suction", .5), ("suction", .7), ("suction", .9),
           ("pressure", .03), ("pressure", .2), ("pressure", .4), ("pressure", .6), ("pressure", .8),
           ("suction", .03), ("suction", .2), ("suction", .4), ("suction", .6), ("suction", .8),
           ("pressure", .1), ("pressure", .3), ("pressure", .5), ("pressure", .7), ("pressure", .9)]
OFFICIAL = 10
# Adjoint variants run side by side. "car" is exactly the car's setting.
VARIANTS = {
    "car":        dict(ras="adjointLaminar", atc="standard", mesh_move=False),
    "car_cancel": dict(ras="adjointLaminar", atc="cancel", mesh_move=False),
    "car_mm":     dict(ras="adjointLaminar", atc="standard", mesh_move=True),
    "sst":        dict(ras="adjointkOmegaSST", atc="standard", mesh_move=False),
    "sst_mm":     dict(ras="adjointkOmegaSST", atc="standard", mesh_move=True),
}


def foam(case: Path, cmd: str, log: str) -> None:
    r = subprocess.run(["bash", "-c", f"source {BASHRC} >/dev/null 2>&1 || true; cd {case} && {cmd} > {log} 2>&1"])
    if r.returncode:
        print((case / log).read_text()[-3000:])
        raise SystemExit(f"{cmd} failed")


def read(path: Path) -> str:
    gz = Path(str(path) + ".gz")
    return gzip.open(gz, "rt").read() if gz.exists() and not path.exists() else path.read_text()


def case_setup(case: Path, adjoint_iters: int, variant: dict) -> dict:
    """Copy the tutorial, convert the mesh to plain text, write our settings. Returns the mesh."""
    src = Path(subprocess.run(["bash", "-c", f"source {BASHRC} >/dev/null 2>&1; echo $FOAM_TUTORIALS"],
                              capture_output=True, text=True).stdout.strip()) / TUT
    shutil.copytree(src / "shapeOptimisation/naca0012/kOmegaSST/lift", case)
    shutil.copytree(src / "resources/meshes/naca0012/polyMesh", case / "constant/polyMesh")
    (case / "constant/dynamicMeshDict").unlink()
    end = PRIMAL_ITERS + adjoint_iters
    cd = (case / "system/controlDict").read_text()
    for k, v in {"endTime": end, "writeInterval": end, "writeCompression": "off",
                 "writePrecision": 16, "startFrom": "startTime"}.items():
        cd = re.sub(rf"^{k}\s+[^;]*;", f"{k} {v};", cd, flags=re.M)
    (case / "system/controlDict").write_text(cd)
    foam(case, "foamFormatConvert -constant", "log.convert")
    for gz in (case / "constant/polyMesh").glob("*.gz"):
        if gz.with_suffix("").exists():
            gz.unlink()
    mesh = read_mesh(case)
    chord = np.ptp(mesh["P"][mesh["wall"], 0])
    nu = np.linalg.norm(U) * chord / RE
    tp = (case / "constant/transportProperties").read_text()
    (case / "constant/transportProperties").write_text(re.sub(r"\]\s*[0-9.eE+-]+;", f"] {nu:.8e};", tp))
    # Part 2's car dictionaries, retargeted.
    (case / "system/fvSchemes").write_text(oa._FV_SCHEMES_ADJOINT)
    (case / "system/fvSolution").write_text(oa._FV_SOLUTION_ADJOINT)
    ras = oa.build_adjoint_ras_properties().replace("adjointLaminar", variant["ras"])
    (case / "constant/adjointRASProperties").write_text(ras)
    speed = float(np.linalg.norm(U))
    cfg = oa.AdjointRunConfig(primal_iters=PRIMAL_ITERS, adjoint_iters=adjoint_iters,
                              reference_speed_mps=speed, atc_model=variant["atc"])
    od = oa.build_optimisation_dict(cfg, 0.0)
    d = U / speed
    od = od.replace("patches    (car);", f"patches    ({' '.join(WALLS)});")
    od = od.replace("patches            (car);", f"patches            ({' '.join(WALLS)});")
    od = od.replace("direction  (1 0 0);", f"direction  ({d[0]:.12f} {d[1]:.12f} 0);")
    od = re.sub(r"(\"[A-Za-z]+\.\*\"\s+)1\.e-5;", r"\g<1>1.e-14;", od)
    if variant["mesh_move"]:
        od = od.replace("includeMeshMovement false;", "includeMeshMovement true;")
    assert od.count(" ".join(WALLS)) == 2 and "(1 0 0)" not in od and od.count("1.e-14") == 8, od
    (case / "system/optimisationDict").write_text(od)
    mesh["chord"], mesh["nu"] = chord, nu
    return mesh


def read_mesh(case: Path, walls=WALLS, flat: bool = True) -> dict:
    """Wall points (sorted ids), outward-from-solid unit normals and point areas.
    flat: a 2-D case, so the normals lie in the x-y plane."""
    poly = case / "constant/polyMesh"
    P = oa._parse_foam_vector_list(read(poly / "points"))
    bnd = oa._read_boundary(read(poly / "boundary"))
    ftxt = read(poly / "faces")
    area_vec = np.zeros_like(P)
    area = np.zeros(len(P))
    side = {}
    for w in walls:
        for f in oa._read_faces(ftxt, *bnd[w]):
            q = P[f]
            av = 0.5 * np.cross(q, np.roll(q, -1, axis=0)).sum(axis=0)   # OpenFOAM: out of the fluid
            area_vec[f] += av / len(f)
            area[f] += np.linalg.norm(av) / len(f)
            for i in f:
                side[int(i)] = w
    wall = np.array(sorted(side))
    n_mesh = area_vec[wall] / np.linalg.norm(area_vec[wall], axis=1)[:, None]
    n_out = -n_mesh                                # out of the SOLID (grow), our + direction
    if flat:
        n_out[:, 2] = 0.0
        n_out /= np.linalg.norm(n_out, axis=1)[:, None]
    c = P[wall].mean(axis=0)
    assert np.sum(((P[wall] - c) * n_out).sum(axis=1) * area[wall]) > 0, "normals do not point out of the body"
    return dict(P=P, wall=wall, n_out=n_out, area=area[wall], side=np.array([side[i] for i in wall]))


def bump(mesh: dict, k: int) -> np.ndarray:
    """Outward move of every wall point (chords) for bump k at amplitude 1: a*b_i."""
    w, xc = CENTRES[k]
    Pw = mesh["P"][mesh["wall"]]
    chord, x0 = mesh["chord"], Pw[:, 0].min()
    on = np.flatnonzero(mesh["side"] == w)
    centre = Pw[on[np.argmin(np.abs((Pw[on, 0] - x0) / chord - xc))]]
    d2 = ((Pw[:, :2] - centre[:2]) ** 2).sum(axis=1)
    return BUMP_A * chord * np.exp(-d2 / (2 * (BUMP_R * chord) ** 2))


def objective(case: Path) -> tuple[float, float]:
    """Final J and its spread over the last 500 primal iterations (the convergence noise)."""
    def rows(name):
        return np.array([[float(x) for x in l.split()[:2]] for l in (case / "optimisation/objective/0" / name)
                         .read_text().splitlines() if l.strip() and not l.startswith("#")])
    inst = rows("dragInstantadjS1")
    primal = inst[inst[:, 0] <= PRIMAL_ITERS]
    print(f"LAB {case}: instant J rows {len(inst)} (primal {len(primal)}), first {inst[:3, 1].round(3).tolist()},"
          f" last {inst[-3:, 1].tolist()}", flush=True)
    return float(rows("dragadjS1")[-1, 1]), float(np.ptp(primal[-500:, 1]))


def run_base(name: str, out: Path) -> None:
    case = Path("ka_base_" + name)
    mesh = case_setup(case, ADJOINT_ITERS, VARIANTS[name])
    foam(case, "adjointOptimisationFoam", "log.run")
    J, spread = objective(case)
    times = sorted((p for p in case.iterdir() if re.fullmatch(r"[0-9.e+-]+", p.name)), key=lambda p: float(p.name))
    print(f"LAB base {name}: time dirs {[p.name for p in times]}; last holds {sorted(q.name for q in times[-1].iterdir())}",
          flush=True)
    sens = [f for f in case.rglob("*Sens*") if f.is_file() and "processor" not in str(f)]
    print(f"LAB base {name}: sensitivity files {[str(f.relative_to(case)) for f in sens]}", flush=True)
    fields = {}
    last = max((f.parent for f in sens if re.fullmatch(r"[0-9.e+-]+", f.parent.name)), key=lambda p: float(p.name), default=None)
    for f in sorted(f for f in sens if f.parent == last):
        txt = f.read_text()
        try:
            v = oa._parse_foam_vector_list(txt) if "Vector" in txt[:600] else oa._parse_foam_scalar_list(txt)
        except ValueError as e:
            print(f"LAB skip {f.name}: {e}")
            continue
        if len(v) == len(mesh["P"]):
            fields[f.name] = v[mesh["wall"]]
    print(f"LAB base {name}: J {J:.8e} spread {spread:.2e} chord {mesh['chord']:.4f} nu {mesh['nu']:.3e}"
          f" wall points {len(mesh['wall'])} fields {list(fields)}", flush=True)
    log = (case / "log.run").read_text()
    ua = re.findall(r"Solving for Uax, Initial residual = ([0-9.eE+-]+)", log)
    print(f"LAB base {name}: last Uax residual {ua[-1] if ua else 'none'}", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"base_{name}.npz", P=mesh["P"][mesh["wall"]], n_out=mesh["n_out"], area=mesh["area"],
             side=mesh["side"], chord=mesh["chord"], J=J, spread=spread,
             bumps=np.array([bump(mesh, k) for k in range(len(CENTRES))]),
             **{"f_" + k: v for k, v in fields.items()})


def morph(mesh: dict, move_wall: np.ndarray) -> np.ndarray:
    from scipy.spatial import cKDTree
    Pw = mesh["P"][mesh["wall"]]
    dist, nn = cKDTree(Pw).query(mesh["P"])
    disp = (move_wall[:, None] * mesh["n_out"])[nn] * np.exp(-(dist / (MORPH_L * mesh["chord"])) ** 2)[:, None]
    return mesh["P"] + disp


def run_bump(k: int, amp: float, out: Path) -> None:
    case = Path(f"ka_bump_{k}_{amp:+g}")
    mesh = case_setup(case, 1, VARIANTS["car"])
    P = morph(mesh, amp * bump(mesh, k))
    body = "\n".join(f"({x:.16e} {y:.16e} {z:.16e})" for x, y, z in P)
    head = read(case / "constant/polyMesh/points").split(f"\n{len(P)}\n(")[0]
    (case / "constant/polyMesh/points").write_text(f"{head}\n{len(P)}\n(\n{body}\n)\n")
    foam(case, "checkMesh", "log.checkMesh")
    ok = "Mesh OK" in (case / "log.checkMesh").read_text()
    foam(case, "adjointOptimisationFoam", "log.run")
    J, spread = objective(case)
    print(f"LAB bump {k} amp {amp:+g}: J {J:.10e} spread {spread:.2e} mesh ok {ok}", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"bump_{k}_{amp:+g}.json").write_text(json.dumps(dict(k=k, amp=amp, J=J, spread=spread, mesh_ok=ok)))


def stats(pred: np.ndarray, meas: np.ndarray) -> dict:
    return dict(r=float(np.corrcoef(pred, meas)[0, 1]), sign=float(np.mean(np.sign(pred) == np.sign(meas))),
                slope=float(np.dot(pred, meas) / np.dot(pred, pred)))


def judge(src: Path) -> int:
    runs = {}
    for f in src.rglob("bump_*.json"):
        d = json.loads(f.read_text())
        runs[(d["k"], d["amp"])] = d
    K = len(CENTRES)
    cd = {a: np.array([(runs[(k, a)]["J"] - runs[(k, -a)]["J"]) / 2 for k in range(K)]) for a in (1.0, 0.5)}
    noise = np.array([max(runs[(k, s * a)]["spread"] for a in (1.0, 0.5) for s in (1, -1)) for k in range(K)])
    bad_mesh = [k for (k, a), d in runs.items() if not d["mesh_ok"]]
    meas = cd[1.0]
    lin = cd[1.0] / (2 * cd[0.5])
    clear = np.abs(meas) >= 3 * noise
    print(f"LAB measured (central difference, amp 1): {np.array2string(meas, precision=3)}")
    print(f"LAB noise (spread of J at the end): max {noise.max():.2e}; bumps clear of 3x noise: {int(clear.sum())}/{K}")
    print(f"LAB linearity (cd(a)/(2 cd(a/2)), 1 = linear): {np.array2string(lin, precision=3)}")
    print(f"LAB meshes not OK: {bad_mesh}")
    result = {"measured": meas.tolist(), "noise": noise.tolist(), "linearity": lin.tolist(), "variants": {}}
    verdict = None
    for f in sorted(src.rglob("base_*.npz")):
        name = f.stem[5:]
        z = np.load(f)
        for key in [k for k in z.files if k.startswith("f_")]:
            v = z[key]
            if v.ndim == 2:     # a vector map: dJ = sum(v . move), no sign convention needed
                vn = (v * z["n_out"]).sum(axis=1)
                preds = {"vector, per area": z["bumps"] @ (vn * z["area"]), "vector, per point": z["bumps"] @ vn}
            else:
                preds = {"as coded, per area": z["bumps"] @ (v * z["area"]),
                         "as coded, per point": z["bumps"] @ v}
            for how, pred in preds.items():
                off, all_ = stats(pred[:OFFICIAL], meas[:OFFICIAL]), stats(pred, meas)
                result["variants"][f"{name} {key[2:]} {how}"] = dict(official=off, all=all_, pred=pred.tolist())
                print(f"LAB {name:10s} {key[2:]:28s} {how:20s} official: signs {off['sign']:.2f} r {off['r']:+.3f}"
                      f" slope {off['slope']:+.3g} | all 20: signs {all_['sign']:.2f} r {all_['r']:+.3f}", flush=True)
                if name == "car" and key.startswith("f_pointSensNormal") and how == "as coded, per area":
                    verdict = off["sign"] >= 0.9 and off["r"] >= 0.9
    ok = verdict is True and not bad_mesh and bool(clear[:OFFICIAL].all())
    print(f"LAB VERDICT car settings (sign >= 9/10, r >= 0.9, all official bumps clear of noise): "
          f"{'PASS' if ok else 'FAIL'}")
    (src / "known_answer_result.json").write_text(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "base":
        run_base(sys.argv[2], Path(sys.argv[3]))
    elif cmd == "bump":
        run_bump(int(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4]))
    else:
        sys.exit(judge(Path(sys.argv[2])))
