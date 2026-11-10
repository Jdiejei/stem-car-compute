"""Timing noise against run length and averaging window (BUILD_SPEC 12.3).

No new CFD: from each ladder car's kept force history, the drag is re-averaged
over the last `f` of its first `n` iterations (what an n-iteration run with
window f would have reported; SIMPLE is deterministic, so a truncated history
IS the shorter run). Race time is moved by dT/dD20 and the ladder statistics
of noise_stats are redone for every (n, f).

The cars kept are those the summary called converged at the run's own
settings; the converged test is not redone per window.

    python noise_window.py got
    # got/noise-<label>-<skin>/summary.json  +  got/forces-<label>-<skin>/**/force.dat
"""
import json
import math
import sys
from pathlib import Path

import noise_stats
import openfoam_case as oc

FRACTIONS = (0.2, 0.4, 0.6, 0.8)
LENGTHS = (1000, 1500, 2000, 3000)


def remean(text: str, n: int, f: float) -> tuple:
    """(mean Fx, stderr fraction) over the last f of the first n data rows."""
    rows = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    cut = "\n".join(rows[:n])
    return oc.parse_total_vector_dat(cut, f)[0], oc.force_mean_convergence(cut, f)[0]


def n_rows(text: str) -> int:
    return sum(1 for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#"))


def load(root: str) -> list:
    """[(skin, T, D20, dT_dD20, history text)] for converged cars with a history."""
    cars = []
    for d in sorted(Path(root).glob("noise-*")):
        label, _, skin = d.name[len("noise-"):].rpartition("-")
        hists = list(Path(root, f"forces-{label}-{skin}").rglob("force.dat"))
        try:
            c = json.loads((d / "summary.json").read_text())["cfd_initial"]
            row = (float(skin), float(c["T_at_target_s"]), float(c["D20_N"]),
                   float(c["gradients"]["dT_dD20"]))
        except (OSError, KeyError, ValueError, TypeError) as e:
            print(f"skipped {d.name}: {e!r}")
            continue
        if not hists or not c.get("converged"):
            print(f"skipped {d.name}: {'no force history' if not hists else 'not converged'}")
            continue
        cars.append(row + (max(hists, key=lambda p: p.stat().st_size).read_text(errors="replace"),))
    return cars


def sweep(cars: list, lengths=LENGTHS, fractions=FRACTIONS) -> list:
    """[(n, f, sigma, lo, hi, rms averaging error)] in seconds."""
    full = min(n_rows(c[4]) for c in cars)
    base = [remean(c[4], n_rows(c[4]), oc.FORCE_AVERAGE_FRACTION)[0] for c in cars]
    out = []
    for n in sorted({m for m in lengths if m < full} | {full}):
        for f in fractions:
            got = [remean(c[4], n, f) for c in cars]
            T = [c[1] + c[3] * c[2] * (m / b - 1.0) for c, (m, _), b in zip(cars, got, base)]
            s, lo, hi, _ = noise_stats.residual_sd([c[0] for c in cars], T)
            rms = math.sqrt(sum((se * c[2] * c[3]) ** 2 for c, (_, se) in zip(cars, got)) / len(cars))
            out.append((n, f, s, lo, hi, rms))
    return out


def main(root: str) -> None:
    cars = load(root)
    if len(cars) < 4:
        print(f"only {len(cars)} cars with a history; need 4")
        return
    print(f"\n{len(cars)} cars. Pass mark 0.3 ms.\n")
    print("| iterations | window | sigma ms | 95 % | averaging error ms |\n|---|---|---|---|---|")
    for n, f, s, lo, hi, rms in sweep(cars):
        print(f"| {n} | last {f:.0%} | {s*1e3:.3f} | {lo*1e3:.3f} to {hi*1e3:.3f} | {rms*1e3:.3f} |")


if __name__ == "__main__":
    main(sys.argv[1])
