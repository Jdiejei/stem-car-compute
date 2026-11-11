"""p1_sizing_lab: carve random bodies with the cutter, then size each to the mass target.

    python ../.github/lab/p1_sizing_lab.py <seed> <n_bodies>    (from part5-simulation, on GitHub)

Each body: a random layout, 1 to 6 cuts with a smooth random sensitivity (Gaussian bumps of
both signs on the surface plus a thinning bias; one body in four strongly thinned), then
param_body.build sized to 48.2 g. One "LAB {json}" line per body: mass error, builds used,
skin offset, whether the target was bracketed, cut reports, timings. Errors are caught and
printed as a crash line, so one bad body never hides the rest.
"""
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import warnings  # noqa: E402

import numpy as np  # noqa: E402

TARGET_KG = 0.0482
seed, n = int(sys.argv[1]), int(sys.argv[2])
ONLY = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None   # rerun these bodies only


def one(k):
    import cutter
    import param_body as pb
    from unified_phi import extract_half_surface
    rng = np.random.default_rng(seed * 1000 + k)
    W = float(rng.uniform(120.3, 140.0))
    lay = {"W": W, "x_front": float(rng.uniform(46.0, 56.0)),
           "d_halo": float(rng.uniform(25.0, min(75.0, W - 34.5)))}
    aggressive = rng.random() < 0.25
    n_cuts = int(rng.integers(4, 7) if aggressive else rng.integers(1, 7))
    t0 = time.time()
    g = cutter.start_block(lay, spacing_mm=1.0)
    cuts = []
    for _ in range(n_cuts):
        v = np.asarray(extract_half_surface(g).vertices)
        dT = np.full(len(v), rng.uniform(0.6, 1.0) if aggressive else rng.uniform(-0.2, 0.5))
        for _b in range(int(rng.integers(3, 15))):
            c = v[rng.integers(len(v))]
            s = rng.uniform(0.005, 0.020)
            dT += rng.uniform(-1.0, 1.0) * np.exp(-((v - c) ** 2).sum(1) / (2 * s * s))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g2, rep = cutter.cut(g, dT, type("M", (), {"vertices": v})(), step_m=1.0,
                                 max_substeps=6, trust_radius_m=1e-3)
        cuts.append({k2: rep.get(k2) for k2 in ("status", "reason", "substeps", "disp_p90_m",
                                                  "thin_cells", "pinch_cells")})
        g = g2
    t_cut = time.time() - t0
    body = pb.build(lay["W"], lay["x_front"], lay["d_halo"], pb.BodyParams(),
                    target_body_kg=TARGET_KG, field_mm=g.phi.grid * 1e3)
    br = body.build_report
    mass_g = br["mass_error_g"] + TARGET_KG * 1e3
    return {"seed": seed, "k": k, "layout": lay, "aggressive": aggressive, "cuts": cuts,
            "mass_g": round(mass_g, 4), "mass_error_g": round(br["mass_error_g"], 4),
            "builds": br["sizing_builds"], "bracketed": br["mass_bracketed"], "unreachable": br.get("mass_unreachable", False), "ballast_needed_g": br.get("ballast_needed_g", 0.0),
            "skin_mm": round(br["skin_offset_mm"], 4), "tried": br.get("sizing_tried"), "t_cut_s": round(t_cut, 1),
            "t_build_s": round(time.time() - t0 - t_cut, 1)}


for k in range(n):
    if ONLY is not None and k not in ONLY:
        continue
    try:
        print("LAB " + json.dumps(one(k)), flush=True)
    except Exception as exc:  # noqa: BLE001
        print("LAB " + json.dumps({"seed": seed, "k": k, "crash": repr(exc)[:300],
                                   "trace": traceback.format_exc()[-1200:]}), flush=True)
