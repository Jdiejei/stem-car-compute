"""Is a car's adjoint map the same from different points of its flow's cycle?

car_sign.py run on one car at several primal lengths (e.g. 3000, 3037, 3074) stops the
oscillating flow at different phases. If the maps disagree, a steady adjoint on that flow
is not a usable map without an averaged primal. Prints only.
    python compare_maps.py <dir with car_<seed>_<mesh>_<iters>.npz files>
"""
import itertools
import re
import sys
from pathlib import Path

import numpy as np

runs = {}
for f in sorted(Path(sys.argv[1]).rglob("car_*_*_*.npz")):
    seed, mesh, iters = re.fullmatch(r"car_(\d+)_(\w+?)_(\d+)", f.stem).groups()
    runs.setdefault((int(seed), mesh), {})[int(iters)] = np.load(f)
for (seed, mesh), by in sorted(runs.items()):
    for a, b in itertools.combinations(sorted(by), 2):
        za, zb = by[a], by[b]
        if za["P"].shape != zb["P"].shape or not np.allclose(za["P"], zb["P"]):
            print(f"LAB car {seed} {mesh} {a} vs {b}: different surface points, not comparable")
            continue
        sa, sb, A = za["s"], zb["s"], za["area"]
        r = np.corrcoef(sa * A, sb * A)[0, 1]
        sign = np.mean(np.sign(sa) == np.sign(sb))
        big = np.abs(sa * A) > np.percentile(np.abs(sa * A), 75)
        rel = np.linalg.norm((sa - sb) * A) / np.linalg.norm(sa * A)
        print(f"LAB car {seed} {mesh} map at {a} vs {b} steps: r {r:+.3f}, same sign {sign:.2f}"
              f" (top quarter {np.mean(np.sign(sa[big]) == np.sign(sb[big])):.2f}), relative difference {rel:.2f}")
