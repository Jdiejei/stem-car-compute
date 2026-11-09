"""p1_bore_lab: why do carved cars fail T5.1 (chamber 20.1 mm wide) and T5.5 (wall 99.x %)?

    python ../.github/lab/p1_bore_lab.py <variant>    (from part5-simulation, on GitHub)

variants: block (the uncut block through run_car) | cut1 (one cutter cut first) |
          body_block / body_cut1 (Part 1 only: the field across the bore after param_body.build)
"""
import json
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402

variant = sys.argv[1]
LAY = {"W": 120.3, "x_front": 46.0, "d_halo": 43.72}


def carved(n_cuts):
    import cutter
    from unified_phi import extract_half_surface
    g = cutter.start_block(LAY, 1.0)
    for _ in range(n_cuts):
        v = np.asarray(extract_half_surface(g).vertices)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g, rep = cutter.cut(g, np.full(len(v), 0.3), type("M", (), {"vertices": v})(), step_m=1.0)
        print(f"LAB {variant} cut {rep['status']} {rep['reason']}", flush=True)
    return g


def profile(tag, g):
    """phi/dx and the masks along +y and +z from the chamber axis, 20 mm ahead of the rear face."""
    import unified_phi as up
    r, d = g.region, up.GRID_SPACING_M
    lm = g.landmarks
    xr = lm["rear_face_m"] - 0.020
    i = int(round((xr - r.origin_m[0]) / d))
    j0 = int(round((0.0 - r.origin_m[1]) / d))
    k0 = int(round((0.031 - r.origin_m[2]) / d))
    for name, sl in (("+y", (i, slice(j0, j0 + 16), k0)), ("+z", (i, j0, slice(k0, k0 + 16)))):
        print(f"LAB {variant} {tag} {name} phi/dx {np.round(g.phi.grid[sl] / d, 2).tolist()}", flush=True)
        print(f"LAB {variant} {tag} {name} air {g.phi.hard_mask_air[sl].astype(int).tolist()} "
              f"solid {g.phi.hard_mask_solid[sl].astype(int).tolist()}", flush=True)


if variant in ("body_block", "body_cut1"):
    import param_body as pb
    g = carved(0 if variant == "body_block" else 1)
    profile("field", g)
    b = pb.build(LAY["W"], LAY["x_front"], LAY["d_halo"], pb.BodyParams(), skin_offset_mm=0.0,
                 field_mm=g.phi.grid * 1e3)
    profile("built", b)
else:
    import cutter
    import run_car as rc
    out = Path(tempfile.mkdtemp())
    if variant == "block":
        npy = "block"
    else:
        cutter.save_field(carved(1), out / "carved.npy")
        npy = str(out / "carved.npy")
    S = rc.main(["--out", str(out), "--skin-mm", "0", "--support", "beam", "--phi-npy", npy])
    ch = S["legality"]["checks"]
    for k in ("T5.1_diameter_max", "T5.1_diameter_min", "T5.5_wall"):
        print(f"LAB {variant} {k} {json.dumps(ch.get(k))[:300]}", flush=True)
    print(f"LAB {variant} failed {S['legality']['summary']['failed']}", flush=True)
