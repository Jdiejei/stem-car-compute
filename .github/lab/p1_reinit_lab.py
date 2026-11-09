"""p1_reinit_lab: does redistancing (phi_updater.reinitialise_sdf) move the surface?

    python ../.github/lab/p1_reinit_lab.py <seed> <k> <spacing_mm>    (from part5-simulation)

Carves body (seed, k) at 1 mm, carries it to <spacing_mm>, builds it (fixed skin 0, no
milling), then weighs it (sub-cell field mass and mesh volume) before and after 1, 2 and 5
more redistancing passes, and counts cells whose sign flipped. A pass that only redistances
should move nothing.
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))
sys.path.insert(0, str(ROOT / ".github" / "lab"))
import numpy as np  # noqa: E402

from p1_carve_common import carve  # noqa: E402

seed, k, s = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
lay, src, _ = carve(seed, k, 1.0)
import coarse  # noqa: E402
coarse.use_spacing(s)
import param_body as pb  # noqa: E402
import unified_phi as up  # noqa: E402
from geometry_contract import DENSITY_BODY_KGM3  # noqa: E402
from phi_updater import reinitialise_sdf  # noqa: E402
dst = up.remap_geometry(src) if s != 1.0 else src
b = pb.build(lay["W"], lay["x_front"], lay["d_halo"], pb.BodyParams(), skin_offset_mm=0.0,
             field_mm=dst.phi.grid * 1e3, machinable=False)


def weigh(tag, S0):
    fm = sum(c.mass_kg for c in up.compute_mass_com(b)) * 1e3
    mm = 2 * abs(up.extract_half_surface(b).volume) * DENSITY_BODY_KGM3 * 1e3
    flips = int(((b.phi.grid < 0) != S0).sum())
    print(f"LAB reinit seed {seed} k {k} s {s} {tag}: field {fm:.4f} g mesh {mm:.4f} g cells flipped {flips}", flush=True)


S0 = b.phi.grid < 0
weigh("built", S0)
for n in (1, 1, 3):
    for _ in range(n):
        reinitialise_sdf(b.phi)
    weigh(f"+{n} pass(es)", S0)
