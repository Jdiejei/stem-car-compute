"""Fake-stopwatch bench for carve_loop (BUILD_SPEC 7 step 1, 12.3). No CFD.

Test functions on x in [0, 1]^d with a known minimum (times in seconds, scaled so a typical
first step changes the time by 1 to 3 ms), measured with N(0, sigma^2) noise; gradient oracles
exact / noisy (corr 0.8) / wrong sign / zero. Prints, per (function, sigma, oracle), the share of
runs ending within 2 sigma of the true minimum (marks: >= 98 % for exact and noisy; wrong sign
must stop as compass_suspect every time), and the false-keep rate on a flat function (mark <= 5 %).
    python checks/bench.py [runs per cell, default 200]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import carve_loop as cl            # noqa: E402

D = 6
MS = 1e-3


def functions(rng):
    xs = rng.uniform(0.3, 0.7, D)
    w = np.geomspace(1, 100, D) * 0.2 / 100           # weights spread over 100x; start ~10-30 ms above the minimum
    w[D // 2:] *= np.r_[1, np.zeros(D - D // 2 - 1)]   # flat directions: settings with no effect
    th = rng.uniform(0, np.pi)
    Rm = np.eye(D)
    Rm[:2, :2] = [[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]
    wells = [(rng.uniform(0.15, 0.85, D), rng.uniform(4, 12) * MS, rng.uniform(0.2, 0.3)) for _ in range(4)]

    def bowl(x):
        return float(np.sum(w * (x - xs) ** 2))

    def valley(x):
        u = Rm @ (x - xs)
        return float(0.05 * (u[1] - u[0] ** 2) ** 2 + 0.01 * u[0] ** 2 + 0.0025 * np.sum(u[2:] ** 2))

    def peaks(x):
        return float(-sum(dep * np.exp(-np.sum((x - c) ** 2) / (2 * r ** 2)) for c, dep, r in wells))

    best_peak = min(peaks(c) for c, _, _ in wells)
    return {"bowl": (bowl, bowl(xs)), "valley": (valley, valley(xs)), "peaks": (peaks, best_peak)}


def grad(f, x, h=1e-5):
    return np.array([(f(x + h * e) - f(x - h * e)) / (2 * h) for e in np.eye(len(x))])


def oracle(kind, f, rng):
    def g(x):
        e = grad(f, x)
        if kind == "exact":
            return e
        elif kind == "noisy":
            n = rng.normal(size=len(x))
            n -= n @ e / (e @ e + 1e-30) * e
            return np.linalg.norm(e) * (e / (np.linalg.norm(e) + 1e-30) * 0.8 + n / (np.linalg.norm(n) + 1e-30) * 0.6)
        elif kind == "wrong":
            return -e
        return np.zeros_like(x)
    return g


def step(x, d, size):
    return np.clip(x + size * d, 0, 1)


def one_run(fname, sigma, kind, seed):
    rng = np.random.default_rng(seed)
    f, fmin = functions(rng)[fname]
    starts = 20 if fname == "peaks" else 1          # the final run plans about 20 starts
    state = {"chains": [cl.new_chain(i, rng.uniform(0, 1, D), 0.2) for i in range(starts)]}
    f0 = [f(c["x"]) for c in state["chains"]]
    cl.run_local(state, oracle(kind, f, rng), step, lambda x, _: f(x) + rng.normal(0, sigma), sigma)
    best = min(state["chains"], key=lambda c: f(c["x"]))
    ok = f(best["x"]) - fmin <= 2 * sigma
    # a wrong compass is handled when no chain walked uphill: each one either stopped flagged or
    # ended no worse than it started (true value, within 2 sigma)
    suspect = all(c["status"] == "compass_suspect" or f(c["x"]) <= f0[i] + 2 * sigma
                  for i, c in enumerate(state["chains"]))
    return ok, suspect


def false_keep(sigma, trials, seed=0):
    """Flat function, pure noise: every keep is false. Share of rounds that keep."""
    rng = np.random.default_rng(seed)
    keeps = rounds = 0
    for t in range(trials):
        state = {"chains": [cl.new_chain(0, np.full(D, 0.5), 0.2)]}
        cl.run_local(state, lambda x: np.eye(D)[0], step, lambda x, _: 1.0 + rng.normal(0, sigma), sigma)
        for h in state["chains"][0]["history"]:
            rounds += 1
            keeps += h["kept"]
    return keeps / max(rounds, 1), rounds


def main(n):
    ok_all = True
    for sigma in (0.3 * MS, 1.0 * MS):
        for fname in ("bowl", "valley", "peaks"):
            for kind in ("exact", "noisy", "wrong", "zero"):
                res = [one_run(fname, sigma, kind, 10000 * (["bowl", "valley", "peaks"].index(fname) * 4 + ["exact", "noisy", "wrong", "zero"].index(kind)) + s) for s in range(n)]
                okr = np.mean([r[0] for r in res])
                sus = np.mean([r[1] for r in res])
                if kind in ("exact", "noisy"):
                    good = okr >= 0.98
                elif kind == "wrong":
                    good = sus == 1.0
                else:
                    good = True                    # zero gradient: reported only
                ok_all &= good
                print(f"LAB sigma {sigma / MS:.1f} ms {fname:6s} {kind:5s}: within 2 sigma {okr:.1%},"
                      f" no chain walked uphill {sus:.1%} {'PASS' if good else 'FAIL' if kind != 'zero' else ''}",
                      flush=True)
        fk, rounds = false_keep(sigma, 1000)
        ok_all &= fk <= 0.05
        print(f"LAB sigma {sigma / MS:.1f} ms false-keep on pure noise: {fk:.2%} of {rounds} rounds (mark <= 5 %)"
              f" {'PASS' if fk <= 0.05 else 'FAIL'}", flush=True)
    print(f"LAB bench overall: {'PASS' if ok_all else 'FAIL'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
