"""Shared by Part 1's labs: one random, reproducible carved body through the cutter.

carve(seed, k, spacing_mm=1.0) -> (layout, geom, cut verdicts). The same (seed, k) gives the
same body on any machine: numpy's seeded generator, no other randomness.
"""
import warnings

import numpy as np


def carve(seed: int, k: int, spacing_mm: float = 1.0):
    import cutter
    from unified_phi import extract_half_surface
    rng = np.random.default_rng(seed * 1000 + k)
    W = float(rng.uniform(120.3, 140.0))
    lay = {"W": W, "x_front": float(rng.uniform(46.0, 56.0)),
           "d_halo": float(rng.uniform(25.0, min(75.0, W - 34.5)))}
    hard = rng.random() < 0.25
    g = cutter.start_block(lay, spacing_mm=spacing_mm)
    verdicts = []
    for _ in range(int(rng.integers(4, 7) if hard else rng.integers(1, 7))):
        v = np.asarray(extract_half_surface(g).vertices)
        dT = np.full(len(v), rng.uniform(0.6, 1.0) if hard else rng.uniform(-0.2, 0.5))
        for _b in range(int(rng.integers(3, 15))):
            c = v[rng.integers(len(v))]
            s = rng.uniform(0.005, 0.020)
            dT += rng.uniform(-1.0, 1.0) * np.exp(-((v - c) ** 2).sum(1) / (2 * s * s))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g, rep = cutter.cut(g, dT, type("M", (), {"vertices": v})(), step_m=1.0,
                                max_substeps=6, trust_radius_m=1e-3)
        verdicts.append(rep["status"] if rep["status"] == "ok" else rep["reason"])
    return lay, g, verdicts
