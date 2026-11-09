"""p1_maxmass_lab: the heaviest body a layout allows (the whole legal block, grown to the
envelope), at a given grid. Checks whether a 48.2 g body is reachable at all.

    python ../.github/lab/p1_maxmass_lab.py <W> <x_front> <d_halo> <spacing_mm>
"""
import sys
from pathlib import Path

ROOT = Path.cwd().parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation", "part4-simulation"):
    sys.path.insert(0, str(ROOT / p))

W, xf, dh, s = (float(a) for a in sys.argv[1:5])
import coarse  # noqa: E402
coarse.use_spacing(s)
import param_body as pb  # noqa: E402
import unified_phi as up  # noqa: E402
block = up.build_unified_geometry(W, xf, dh, init_mode="full").phi.grid * 1e3
for skin in (0.0, 4.0, 15.0):
    b = pb.build(W, xf, dh, pb.BodyParams(), skin_offset_mm=skin, field_mm=block)
    m = sum(c.mass_kg for c in up.compute_mass_com(b)) * 1e3
    print(f"LAB layout W {W:.2f} x_front {xf:.2f} d_halo {dh:.2f} grid {s} mm skin {skin} mm: block body {m:.3f} g", flush=True)
