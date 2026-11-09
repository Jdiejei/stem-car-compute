"""p1_jump_lab: what switches on between two skins? (Part 2: the start car jumps between
skin 3.99 and 4.00 mm: +0.17 g, +196 faces, halo drag -35 %.)

    python ../.github/lab/p1_jump_lab.py <s1> <s2> [s3 ...]    (from part5-simulation, on GitHub)

Builds the default start car (BodyParams()) at each skin with param_body.build at 1 mm, as
run_car --skin-mm does, and prints mass and the build report per skin. For each neighbouring
pair, the cells whose solid/air state changed, grouped into connected clusters with their
size and bounding box (mm) and the zone label they sit in: a uniform 0.01 mm offset flips
almost no cells, so the clusters are the jump.
"""
import json
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
import numpy as np  # noqa: E402
from scipy.ndimage import label  # noqa: E402

skins = [float(s) for s in sys.argv[1:]]
from coarse import use_spacing  # noqa: E402
use_spacing(1.0)
import param_body as pb  # noqa: E402
import unified_phi as up  # noqa: E402

bodies = {}
for s in skins:
    g = pb.build(120.3, 46.0, 43.72, pb.BodyParams(), skin_offset_mm=s)
    m = sum(c.mass_kg for c in up.compute_mass_com(g)) * 1e3
    rep = {k: v for k, v in g.build_report.items() if k != "sizing_tried"}
    print(f"LAB skin {s} mass {m:.4f} report {json.dumps(rep, default=str)[:700]}", flush=True)
    bodies[s] = g
inv = {v: k for k, v in up.LABEL_IDS.items()}
for a, b in zip(skins, skins[1:]):
    ga, gb = bodies[a], bodies[b]
    Sa, Sb = ga.phi.grid < 0, gb.phi.grid < 0
    d = Sa != Sb
    r, dx = ga.region, up.GRID_SPACING_M * 1e3
    lab, n = label(d)
    print(f"LAB pair {a}->{b}: {int(d.sum())} cells changed ({int((Sb & ~Sa).sum())} to solid, "
          f"{int((Sa & ~Sb).sum())} to air), {n} clusters", flush=True)
    sizes = np.bincount(lab.ravel())[1:]
    for i in np.argsort(-sizes)[:12]:
        c = np.argwhere(lab == i + 1)
        lo = (np.asarray(r.origin_m) * 1e3 + c.min(0) * dx).round(1).tolist()
        hi = (np.asarray(r.origin_m) * 1e3 + c.max(0) * dx).round(1).tolist()
        to_solid = int((Sb & ~Sa)[tuple(c.T)].sum())
        labs = np.bincount(ga.labels[tuple(c.T)], minlength=len(inv) + 1)
        zone = inv.get(int(labs.argmax()), "none")
        forced = int(ga.phi.hard_mask_air[tuple(c.T)].sum()), int(ga.phi.hard_mask_solid[tuple(c.T)].sum())
        print(f"LAB   cluster {sizes[i]} cells, {to_solid} to solid, x,y,z {lo}..{hi} zone {zone} "
              f"forced air/solid cells {forced}", flush=True)
