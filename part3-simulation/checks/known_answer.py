"""Step 1 of Part 3: prove the adjoint on a case with a known answer (BUILD_SPEC 7, 12.5).

A 2-D NACA 0012 at Re ~ 3e5 (OpenFOAM's shipped mesh), drag objective. The adjoint map
is compared with central finite differences of drag for smooth Gaussian bumps.

The adjoint dictionaries are Part 2's car dictionaries (openfoam_adjoint), with only the
patch names, the drag direction, the speed and the iteration counts changed, so this tests
OUR settings, not the tutorial's.

Sign convention under test: Part 2's reader, openfoam_adjoint.OUTWARD_SIGN, which turns
OpenFOAM's into-the-solid wall normal into "+ = grow the solid". Nothing is fitted.

    python known_answer.py base <variant> <out_dir>     primal + adjoint, saves the map
    python known_answer.py bump <k> <amp> <out_dir>     primal on the bumped mesh, saves J
    python known_answer.py judge <in_dir>               compares and prints PASS / FAIL
Runs on GitHub only (p3_known_answer.yml).
"""
from __future__ import annotations

import gzip
import json
import os
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
RE = float(os.environ.get("P3_RE", "3e5"))      # 3e5 is our car's; the shipped wing cases are built for 6e6
USCALE = float(os.environ.get("P3_USCALE", "1"))   # freestream speed factor (units check)
U = np.array([59.96344962, 2.0939698, 0.0]) * USCALE   # the tutorial's freestream (2 deg)
PRIMAL_ITERS = 4000      # fixed counts (residual targets unreachable) so every run ends
ADJOINT_ITERS = 4000     # at a known iteration and writes its fields there
BUMP_R = 0.04            # Gaussian radius, chords
BUMP_A = 1.0e-3          # amplitude, chords (amp=1); amp=0.5 checks linearity
MORPH_L = float(os.environ.get("P3_MORPH", "0.10"))   # how far the move fades into the mesh, chords
REFINE = int(os.environ.get("P3_REFINE", "0"))         # mesh refinements (each 4x the cells)
# 20 bump centres: (wall, x/c). The first 10 are the pre-chosen official set (pass mark
# 9/10 signs, r >= 0.9); all 20 are reported too for a firmer r.
CENTRES = [("suction", .1), ("suction", .3), ("suction", .5), ("suction", .7), ("suction", .9),
           ("pressure", .03), ("pressure", .2), ("pressure", .4), ("pressure", .6), ("pressure", .8),
           ("suction", .03), ("suction", .2), ("suction", .4), ("suction", .6), ("suction", .8),
           ("pressure", .1), ("pressure", .3), ("pressure", .5), ("pressure", .7), ("pressure", .9)]
OFFICIAL = 10
# 10 "move material" shapes: grow at bump i, shrink at bump j. Every single outward bump on
# this wing adds drag, so a map that is simply positive everywhere would pass a sign check
# on single bumps; these can make drag go either way, so the sign check can fail (user,
# 2026-11-09). They are official for the sign mark.
PAIRS = [(0, 1), (2, 1), (2, 3), (4, 3), (5, 6), (7, 6), (7, 8), (9, 8), (0, 5), (9, 4)]
# Backup measured map dry run (BUILD_SPEC 7 Step 4, 12.7): 40 Gaussian modes on a grid over
# the wing (20 a side), each measured by central difference; the map they give is judged on
# the 30 test shapes above, which it never saw.
NMODES = int(os.environ.get("P3_NMODES", "40"))      # modes in all (half a side each)
MODE_R = float(os.environ.get("P3_MODE_R", str(0.04)))  # mode radius, chords
MODE_X = np.round(np.linspace(0.02, 0.95, NMODES // 2), 4)
MODES = [("suction", x) for x in MODE_X] + [("pressure", x) for x in MODE_X]
N_TEST = 20 + 10                                     # singles + pairs; modes follow
# HARD test shapes for the measured map (lead chat, 2026-11-09): the 30 shapes above are the
# modes' own family (same radius), so a good score there is partly a fit. These are outside
# it: narrower than a mode (r 0.015, 0.025), wider (0.08), and mixes of three narrow bumps
# with mixed signs at positions between the mode centres. (wall, x/c, r, sign) per bump.
HARD0 = N_TEST + len(MODES)                          # 70
HARD = ([[("suction", x, 0.015, 1)] for x in (0.25, 0.55, 0.85)]
        + [[("pressure", x, 0.015, 1)] for x in (0.15, 0.45, 0.75)]
        + [[("suction", x, 0.025, 1)] for x in (0.35, 0.65)] + [[("pressure", x, 0.025, 1)] for x in (0.25, 0.55)]
        + [[("suction", x, 0.08, 1)] for x in (0.3, 0.6)] + [[("pressure", x, 0.08, 1)] for x in (0.3, 0.6)]
        + [[("suction", .13, .015, 1), ("suction", .41, .015, -1), ("pressure", .27, .015, 1)],
           [("suction", .22, .02, -1), ("suction", .47, .015, 1), ("pressure", .62, .02, 1)],
           [("pressure", .08, .015, 1), ("pressure", .33, .02, -1), ("suction", .73, .015, -1)],
           [("suction", .57, .015, 1), ("suction", .69, .015, -1), ("suction", .81, .015, 1)],
           [("pressure", .44, .02, -1), ("pressure", .58, .015, 1), ("suction", .36, .02, 1)],
           [("suction", .06, .015, 1), ("pressure", .06, .015, -1), ("suction", .9, .02, 1)]])
# Adjoint variants run side by side. "car" is exactly the car's setting.
VARIANTS = {
    "car":        dict(ras="adjointLaminar", atc="standard", mesh_move=False),
    "car_cancel": dict(ras="adjointLaminar", atc="cancel", mesh_move=False),
    "car_mm":     dict(ras="adjointLaminar", atc="standard", mesh_move=True),
    "car_raw":    dict(ras="adjointLaminar", atc="standard", mesh_move=False, raw=True),   # dJ/dx, no area division
    "sst":        dict(ras="adjointkOmegaSST", atc="standard", mesh_move=False),
    "sst_mm":     dict(ras="adjointkOmegaSST", atc="standard", mesh_move=True),
    # OpenFOAM's shipped turbulent sensitivity-map case (sensitivityMaps/naca0012/turbulent/
    # liftFullSetup): Spalart-Allmaras primal with its matching adjoint, distance and
    # mesh-movement terms, with its own schemes. Its primal differs, so it needs its own bumps.
    "sa_full":    dict(setup="sa", ras="adjointSpalartAllmaras", mesh_move=True, distance=True),
    "sa_min":     dict(setup="sa", ras="adjointSpalartAllmaras", mesh_move=False, distance=False),
    "sa_frozen":  dict(setup="sa", ras="adjointLaminar", mesh_move=False, distance=False),
}
SA_CASE = "sensitivityMaps/naca0012/turbulent/liftFullSetup"
SETUP = os.environ.get("P3_SETUP", "car")      # whose primal the bump runs use: car or sa


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
    sa = variant.get("setup") == "sa"
    shutil.copytree(src / (SA_CASE if sa else "shapeOptimisation/naca0012/kOmegaSST/lift"), case)
    shutil.copytree(src / "resources/meshes/naca0012/polyMesh", case / "constant/polyMesh")
    if sa:
        shutil.copytree(case / "0.orig", case / "0")
    else:
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
    for _ in range(REFINE):      # split every cell in x and y (2-D), 4x the cells each time
        (case / "system/refineMeshDict").write_text(
            "FoamFile { version 2.0; format ascii; class dictionary; object refineMeshDict; }\n"
            "set c0; coordinateSystem global; globalCoeffs { tan1 (1 0 0); tan2 (0 1 0); }\n"
            "directions (tan1 tan2); useHexTopology yes; geometricCut no; writeMesh no;\n")
        foam(case, "refineMesh -overwrite -all -dict system/refineMeshDict", "log.refine")
    if USCALE != 1.0:
        # Same flow at another speed (Re held by nu below): velocities x s, k x s^2,
        # omega, nut and nuTilda x s. A units fault in the map would change its size with s.
        power = {"U": 1, "k": 2, "omega": 1, "nut": 1, "nuTilda": 1}
        for name, pw in power.items():
            f = case / "0" / name
            if f.exists():
                t = re.sub(r"(uniform\s*\(?)([^;)]*)", lambda m: m.group(1) + " ".join(
                    f"{float(x) * USCALE ** pw:.10g}" if re.fullmatch(r"[0-9.eE+-]+", x) else x
                    for x in m.group(2).split()), f.read_text())
                f.write_text(t)
    mesh = read_mesh(case)
    chord = np.ptp(mesh["P"][mesh["wall"], 0])
    nu = np.linalg.norm(U) * chord / RE
    tp = (case / "constant/transportProperties").read_text()
    tp, n = re.subn(r"^(nu\s.*?)[0-9.eE+-]+;", rf"\g<1>{nu:.8e};", tp, flags=re.M)
    assert n == 1, tp
    (case / "constant/transportProperties").write_text(tp)
    mesh["chord"], mesh["nu"] = chord, nu
    d = U / np.linalg.norm(U)
    if sa:
        # the shipped case as it is, retargeted to drag with fixed iteration counts
        ras = (case / "constant/adjointRASProperties").read_text()
        (case / "constant/adjointRASProperties").write_text(ras.replace("adjointSpalartAllmaras", variant["ras"]))
        od = (case / "system/optimisationDict").read_text()
        od = re.sub(r"^(\s*)lift(\s*)$", r"\1drag\2", od, flags=re.M)
        od = re.sub(r"direction\s+\([^)]*\);", f"direction ({d[0]:.12f} {d[1]:.12f} 0);", od)
        it = iter([PRIMAL_ITERS, adjoint_iters])
        od = re.sub(r"nIters\s+\d+;", lambda m: f"nIters {next(it)};", od)
        od = re.sub(r"(\"[A-Za-z.*]+\"\s+)1\.e-6;", r"\g<1>1.e-14;", od)   # residual targets only
        od = re.sub(r"includeMeshMovement\s+\w+;", f"includeMeshMovement {str(variant['mesh_move']).lower()};", od)
        od = re.sub(r"includeDistance\s+\w+;", f"includeDistance {str(variant['distance']).lower()};", od)
        geo = f"includeSurfaceArea {str(variant.get('raw', False)).lower()};"
        od, n = re.subn(r"includeSurfaceArea\s+\w+;", geo, od)
        assert n == 1, od
        assert "lift" not in re.sub(r"//.*", "", od) and od.count("1.e-14") == 6, od
        (case / "system/optimisationDict").write_text(od)
        return mesh
    # Part 2's car dictionaries, retargeted.
    (case / "system/fvSchemes").write_text(oa._FV_SCHEMES_ADJOINT)
    (case / "system/fvSolution").write_text(oa._FV_SOLUTION_ADJOINT)   # no early primal stop (fixed there)
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
    # raw: dJ/dx with no division by the point area (includeSurfaceArea true), for the units.
    # (writeGeometricInfo would give OpenFOAM's point areas, but v2412 crashes on it:
    # "cannot find file nfOnPatch"; read_mesh computes the same pointMagSf instead.)
    geo = f"includeSurfaceArea {str(variant.get('raw', False)).lower()};\n"
    od, n = re.subn(r"^(\s*)(includeMeshMovement (true|false);)", lambda m: m.group(1) + geo + m.group(1) + m.group(2),
                    od, flags=re.M)
    assert n == 1, od
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
    magsf = np.zeros(len(P))     # OpenFOAM's pointMagSf: the FULL area of every wall face at the point
    side = {}
    for w in walls:
        for f in oa._read_faces(ftxt, *bnd[w]):
            q = P[f]
            av = 0.5 * np.cross(q, np.roll(q, -1, axis=0)).sum(axis=0)   # OpenFOAM: out of the fluid
            area_vec[f] += av / len(f)
            area[f] += np.linalg.norm(av) / len(f)
            magsf[f] += np.linalg.norm(av)
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
    return dict(P=P, wall=wall, n_out=n_out, area=area[wall], magsf=magsf[wall],
                side=np.array([side[i] for i in wall]))


def gauss(mesh: dict, w: str, xc: float, r: float = BUMP_R) -> np.ndarray:
    """Gaussian outward move of amplitude BUMP_A, radius r (chords), centred on wall `w` at x/c."""
    Pw = mesh["P"][mesh["wall"]]
    chord, x0 = mesh["chord"], Pw[:, 0].min()
    on = np.flatnonzero(mesh["side"] == w)
    centre = Pw[on[np.argmin(np.abs((Pw[on, 0] - x0) / chord - xc))]]
    d2 = ((Pw[:, :2] - centre[:2]) ** 2).sum(axis=1)
    return BUMP_A * chord * np.exp(-d2 / (2 * (r * chord) ** 2))


def bump(mesh: dict, k: int) -> np.ndarray:
    """Outward move of every wall point (chords) for shape k at amplitude 1: a*b_i.
    k < 20: one test bump; 20..29 the PAIRS (grow at i minus grow at j); 30..69 the MODES;
    70.. the HARD shapes (sizes and mixes the modes were not built from)."""
    if len(CENTRES) <= k < N_TEST:
        i, j = PAIRS[k - len(CENTRES)]
        return bump(mesh, i) - bump(mesh, j)
    if k >= HARD0:
        return sum(s * gauss(mesh, w, x, r) for w, x, r, s in HARD[k - HARD0])
    if N_TEST <= k < HARD0:
        return gauss(mesh, *MODES[k - N_TEST], MODE_R)
    w, xc = CENTRES[k]
    return gauss(mesh, w, xc)


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
            v = oa._parse_foam_vector_list(txt) if "VectorField" in txt[:3000] else oa._parse_foam_scalar_list(txt)
        except ValueError as e:
            print(f"LAB skip {f.name}: {e}")
            continue
        if len(v) == len(mesh["P"]):
            fields[f.name] = v[mesh["wall"]] * (oa.OUTWARD_SIGN if v.ndim == 1 else 1.0)
    geom = {"m_pointMagSf": mesh["magsf"]}               # as sensitivitySurfacePoints.C computes it
    print(f"LAB base {name}: pointMagSf / my point area: p5 p50 p95 "
          f"{np.round(np.percentile(mesh['magsf'] / mesh['area'], [5, 50, 95]), 3).tolist()}", flush=True)
    print(f"LAB base {name}: J {J:.8e} spread {spread:.2e} chord {mesh['chord']:.4f} nu {mesh['nu']:.3e}"
          f" wall points {len(mesh['wall'])} fields {list(fields)}", flush=True)
    log = (case / "log.run").read_text()
    ua = re.findall(r"Solving for Uax, Initial residual = ([0-9.eE+-]+)", log)
    print(f"LAB base {name}: last Uax residual {ua[-1] if ua else 'none'}", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"base_{name}.npz", P=mesh["P"][mesh["wall"]], n_out=mesh["n_out"], area=mesh["area"],
             side=mesh["side"], chord=mesh["chord"], J=J, spread=spread,
             bumps=np.array([bump(mesh, k) for k in range(HARD0 + len(HARD))]),
             **{"f_" + k: v for k, v in fields.items()}, **geom)


def morph(mesh: dict, move_wall: np.ndarray) -> np.ndarray:
    from scipy.spatial import cKDTree
    Pw = mesh["P"][mesh["wall"]]
    dist, nn = cKDTree(Pw).query(mesh["P"])
    disp = (move_wall[:, None] * mesh["n_out"])[nn] * np.exp(-(dist / (MORPH_L * mesh["chord"])) ** 2)[:, None]
    return mesh["P"] + disp


def run_moved(case: Path, move) -> tuple:
    """Primal drag of the wing with its wall moved outward by move(mesh) (chords).
    Returns (J, spread, mesh ok, mesh)."""
    mesh = case_setup(case, 1, VARIANTS["sa_min" if SETUP == "sa" else "car"])
    P = morph(mesh, move(mesh))
    body = "\n".join(f"({x:.16e} {y:.16e} {z:.16e})" for x, y, z in P)
    head = read(case / "constant/polyMesh/points").split(f"\n{len(P)}\n(")[0]
    (case / "constant/polyMesh/points").write_text(f"{head}\n{len(P)}\n(\n{body}\n)\n")
    foam(case, "checkMesh", "log.checkMesh")
    ok = "Mesh OK" in (case / "log.checkMesh").read_text()
    foam(case, "adjointOptimisationFoam", "log.run")
    J, spread = objective(case)
    return J, spread, ok, mesh


def run_bump(k: int, amp: float, out: Path) -> None:
    J, spread, ok, _ = run_moved(Path(f"ka_bump_{k}_{amp:+g}"), lambda mesh: amp * bump(mesh, k))
    print(f"LAB bump {k} amp {amp:+g}: J {J:.10e} spread {spread:.2e} mesh ok {ok}", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"bump_{k}_{amp:+g}.json").write_text(json.dumps(dict(k=k, amp=amp, J=J, spread=spread, mesh_ok=ok)))


def map_density(mesh: dict, c) -> np.ndarray:
    """The measured map (per unit area, + = growing adds drag) from mode slopes c (12.7)."""
    Phi = np.array([bump(mesh, k) for k in range(N_TEST, HARD0)])
    A = mesh["area"]
    return Phi.T @ np.linalg.solve((Phi * A) @ Phi.T, np.asarray(c))


def run_step(result_json: Path, size: float, out: Path) -> None:
    """Step 6 dry run on the wing: one step DOWN the measured map, with the area-mean taken off
    (the wing keeps its size, as the car keeps its mass), largest move = size x BUMP_A x chord.
    Predicted change sum(m d A) against the measured change from the unmoved wing."""
    c = json.loads(result_json.read_text())["measured_map"]["modes"]
    assert len(c) == HARD0 - N_TEST, f"result has {len(c)} modes, this run is set for {HARD0 - N_TEST}"
    saved = {}

    def move(mesh):
        m = map_density(mesh, c)
        A = mesh["area"]
        d = -(m - np.sum(m * A) / np.sum(A))
        d *= size * BUMP_A * mesh["chord"] / np.max(np.abs(d)) if size else 0.0
        saved.update(pred=float(np.sum(m * d * A)), d_max=float(np.max(np.abs(d))))
        return d

    J, spread, ok, _ = run_moved(Path(f"ka_step_{size:g}"), move)
    print(f"LAB step size {size:g}: J {J:.10e} predicted change {saved['pred']:+.5f} spread {spread:.1e} mesh ok {ok}",
          flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"step_{size:g}.json").write_text(json.dumps(dict(size=size, J=J, spread=spread, mesh_ok=ok, **saved)))


def step_report(src: Path) -> None:
    rows = sorted((json.loads(f.read_text()) for f in src.rglob("step_*.json")), key=lambda r: r["size"])
    base = next(r for r in rows if r["size"] == 0)
    for r in rows:
        if r["size"]:
            dJ = r["J"] - base["J"]
            print(f"LAB step {r['size']:g} x bump height: drag change measured {dJ:+.5f} predicted {r['pred']:+.5f}"
                  f" ({dJ / base['J'] * 100:+.3f} %), noise {max(r['spread'], base['spread']):.1e},"
                  f" {'FASTER (lower drag)' if dJ < -3 * max(r['spread'], base['spread']) else 'NOT clearly lower'}",
                  flush=True)


def stats(pred: np.ndarray, meas: np.ndarray) -> dict:
    return dict(r=float(np.corrcoef(pred, meas)[0, 1]), sign=float(np.mean(np.sign(pred) == np.sign(meas))),
                slope=float(np.dot(pred, meas) / np.dot(pred, pred)))


def measured_map(src: Path, runs: dict, meas, singles, sign_set, result: dict, ks) -> None:
    """The backup measured map (12.7) built from the 40 modes alone, judged on the test shapes.
    Map density m (per unit area) is the least-squares one in the modes' span that reproduces
    every mode's measured slope: sum_i m_i phi_k(i) A_i = c_k. A shape b then predicts
    sum_i m_i b_i A_i."""
    idx = [N_TEST + m for m in range(len(MODES))]
    idx = [k for k in idx if (k, 1.0) in runs and (k, -1.0) in runs]
    print(f"LAB measured map: {len(idx)}/{len(MODES)} modes measured", flush=True)
    if len(idx) < len(MODES) * 0.9:
        print("LAB measured map: under 90% of the modes measured, skipped")
        return
    c = np.array([(runs[(k, 1.0)]["J"] - runs[(k, -1.0)]["J"]) / 2 for k in idx])
    z = np.load(next(src.rglob("base_*.npz")))
    Phi, A, B = z["bumps"][idx], z["area"], z["bumps"][ks]
    G = (Phi * A) @ Phi.T
    m = Phi.T @ np.linalg.solve(G, c)
    pred = B @ (m * A)
    resid = np.linalg.norm(B - (B @ (Phi.T * A[:, None])) @ np.linalg.solve(G, Phi) , axis=1) / np.linalg.norm(B, axis=1)
    off = stats(pred[singles], meas[singles])
    sg = float(np.mean(np.sign(pred[sign_set]) == np.sign(meas[sign_set])))
    result["measured_map"] = dict(official=off, sign_set=sg, pred=pred.tolist(), modes=c.tolist())
    print(f"LAB measured map ({len(idx)} modes, {2 * len(idx)} runs): official r {off['r']:+.3f} slope {off['slope']:+.3g} | "
          f"signs incl. pairs {sg:.2f} ({len(sign_set)}); share of each test shape outside the modes' span "
          f"p50 {np.median(resid):.2f} max {resid.max():.2f}", flush=True)
    print(f"LAB measured map VERDICT (sign >= 90% of singles and pairs, r >= 0.9 on the 10 official singles): "
          f"{'PASS' if sg >= 0.9 and off['r'] >= 0.9 else 'FAIL'}", flush=True)
    # HARD shapes, outside the modes' family: the real test of the measured map
    hk = [k for k in range(HARD0, HARD0 + len(HARD)) if all((k, a) in runs for a in (1.0, -1.0, 0.5, -0.5))]
    if len(hk) < 2:
        print(f"LAB measured map on HARD shapes: {len(hk)}/{len(HARD)} measured, skipped", flush=True)
        return
    Bh = z["bumps"][hk]
    mh = np.array([(runs[(k, 1.0)]["J"] - runs[(k, -1.0)]["J"]) / 2 for k in hk])
    lin = np.array([mh[i] / (runs[(k, 0.5)]["J"] - runs[(k, -0.5)]["J"]) for i, k in enumerate(hk)])
    noise = np.array([max(runs[(k, s)]["spread"] for s in (1.0, -1.0, 0.5, -0.5)) for k in hk])
    ph = Bh @ (m * A)
    # share of each shape (A-weighted) the modes can represent
    proj = (Bh @ (Phi.T * A[:, None])) @ np.linalg.solve(G, Phi)
    capt = 1 - np.sqrt(((Bh - proj) ** 2 * A).sum(axis=1) / ((Bh ** 2) * A).sum(axis=1))
    st = stats(ph, mh)
    sgn = np.sign(ph) == np.sign(mh)
    result["measured_map_hard"] = dict(r=st["r"], sign=st["sign"], slope=st["slope"], measured=mh.tolist(),
                                       pred=ph.tolist(), captured=capt.tolist(), linearity=(lin / 2).tolist())
    print(f"LAB measured map on HARD shapes ({len(hk)}/{len(HARD)}): r {st['r']:+.3f} slope {st['slope']:+.3g}"
          f" signs {st['sign']:.2f}; clear of 3x noise {int(np.sum(np.abs(mh) >= 3 * noise))}", flush=True)
    for i, k in enumerate(hk):
        print(f"LAB   hard {k - HARD0:2d} {HARD[k - HARD0][0][0][:4]} x {HARD[k - HARD0][0][1]:.2f} r {HARD[k - HARD0][0][2]:.3f}"
              f"{' mix' if len(HARD[k - HARD0]) > 1 else '    '}: measured {mh[i]:+.4f} predicted {ph[i]:+.4f}"
              f" captured {capt[i]:.2f} sign {'ok' if sgn[i] else 'WRONG'}", flush=True)


def judge(src: Path) -> int:
    runs = {}
    for f in src.rglob("bump_*.json"):
        d = json.loads(f.read_text())
        runs[(d["k"], d["amp"])] = d
    ks = np.array([k for k in range(N_TEST) if all((k, a) in runs for a in (1.0, -1.0, 0.5, -0.5))])
    missing = sorted(set(range(N_TEST)) - set(ks.tolist()))
    K = len(ks)
    print(f"LAB test shapes measured: {K}/{N_TEST}; missing {missing}")
    singles = np.flatnonzero(ks < OFFICIAL)                          # r mark (positions in ks)
    sign_set = np.flatnonzero((ks < OFFICIAL) | (ks >= len(CENTRES)))  # sign mark: singles and pairs
    all_singles = np.flatnonzero(ks < len(CENTRES))
    cd = {a: np.array([(runs[(k, a)]["J"] - runs[(k, -a)]["J"]) / 2 for k in ks]) for a in (1.0, 0.5)}
    noise = np.array([max(runs[(k, s * a)]["spread"] for a in (1.0, 0.5) for s in (1, -1)) for k in ks])
    bad_mesh = [k for (k, a), d in runs.items() if not d["mesh_ok"]]
    meas = cd[1.0]
    lin = cd[1.0] / (2 * cd[0.5])
    clear = np.abs(meas) >= 3 * noise
    print(f"LAB measured (central difference, amp 1): {np.array2string(meas, precision=3)}")
    print(f"LAB noise (spread of J at the end): max {noise.max():.2e}; bumps clear of 3x noise: {int(clear.sum())}/{K}")
    print(f"LAB linearity (cd(a)/(2 cd(a/2)), 1 = linear): {np.array2string(lin, precision=3)}")
    print(f"LAB meshes not OK: {bad_mesh}")
    result = {"measured": meas.tolist(), "noise": noise.tolist(), "linearity": lin.tolist(), "variants": {}}
    verdict = {}
    for f in sorted(src.rglob("base_*.npz")):
        name = f.stem[5:]
        z = np.load(f)
        B = z["bumps"][ks]
        raw = VARIANTS.get(name, {}).get("raw", False)
        for key in [k for k in z.files if k.startswith("f_")]:
            v = z[key]
            if v.ndim == 2:     # a vector map: dJ = sum(v . move), no sign convention needed
                vn = (v * z["n_out"]).sum(axis=1)
                preds = {"vector, per area": B @ (vn * z["area"]), "vector, per point": B @ vn}
            elif raw:           # dJ/dx . n per point (includeSurfaceArea true): sum over points
                preds = {"raw dJ/dx, per point": B @ v}
            else:
                # read through Part 2's OUTWARD_SIGN (base saves it that way): + = grow.
                # OpenFOAM divides dJ/dx by pointMagSf (the FULL area of every face at the
                # point), so dJ = sum(value * pointMagSf * move) is its exact definition.
                preds = {"x my point area": B @ (v * z["area"]), "per point": B @ v}
                if "m_pointMagSf" in z.files:
                    preds["x OpenFOAM pointMagSf"] = B @ (v * z["m_pointMagSf"])
            for how, pred in preds.items():
                off, all_ = stats(pred[singles], meas[singles]), stats(pred[all_singles], meas[all_singles])
                sg = float(np.mean(np.sign(pred[sign_set]) == np.sign(meas[sign_set])))
                result["variants"][f"{name} {key[2:]} {how}"] = dict(official=off, all=all_, sign_set=sg,
                                                                     pred=pred.tolist())
                print(f"LAB {name:10s} {key[2:]:24s} {how:22s} official r {off['r']:+.3f} slope {off['slope']:+.3g}"
                      f" | signs incl. pairs {sg:.2f} ({len(sign_set)}) | all 20 singles r {all_['r']:+.3f}", flush=True)
                if name == "car" and how == "x OpenFOAM pointMagSf":
                    verdict[how] = sg >= 0.9 and off["r"] >= 0.9
                    print(f"LAB car per shape: measured / predicted: "
                          f"{np.array2string(meas / pred, precision=3, max_line_width=250)}", flush=True)
    for how, v in verdict.items():
        ok = v and not bad_mesh and bool(clear[sign_set].all()) and not [k for k in missing if k < OFFICIAL or k >= len(CENTRES)]
        print(f"LAB VERDICT car settings, {how} (sign >= 90% of singles and pairs, r >= 0.9 on the 10 official "
              f"singles, all clear of 3x noise): {'PASS' if ok else 'FAIL'}")
    measured_map(src, runs, meas, singles, sign_set, result, ks)
    (src / "known_answer_result.json").write_text(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "base":
        run_base(sys.argv[2], Path(sys.argv[3]))
    elif cmd == "bump":
        run_bump(int(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4]))
    elif cmd == "step":
        run_step(Path(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4]))
    elif cmd == "step_report":
        step_report(Path(sys.argv[2]))
    else:
        sys.exit(judge(Path(sys.argv[2])))
