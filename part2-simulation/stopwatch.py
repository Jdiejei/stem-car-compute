"""The stopwatch's front door: time one car folder, or compare two.

A car folder (from Part 4) holds
    car_half.stl        half car, metres, y >= 0. Solid `car` is the body; any
                        other solids (wheelF, wheelR, ...) are ignored here and
                        come from assembly.json, which says how they rotate.
    assembly.json       optional: {"extra_surfaces": [{"name", "stl", "rotating"}]}
                        (stl paths absolute or relative to the folder)
    mass_report.json    {"car_weight_kg": whole car incl. the empty cartridge
                        shell, "com_mm": [x, y, z] (z above the track),
                        "wheel_moi_kg_m2": one wheel, optional "mu"}

time_car(folder) writes folder/stopwatch.json (BUILD_SPEC section 6) and
returns it. compare(a, b) -> (dT, sd): dT = T_b - T_a in seconds (positive
means b is slower), sd its standard deviation from the measured noise.

    python stopwatch.py CAR_DIR [CAR_DIR_B] [--res medium] [--iters 1000] [--np 4]
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

import physics_contract as pc

HERE = Path(__file__).resolve().parent
# Measured thrust (team, 2026-11-09); its CO2 mass column is derived, see
# thrust_convert.py. The invented co2_thrust_data.csv is kept only for comparison.
THRUST_CSV = HERE / "thrust_measured_beta.csv"
# Race-time noise sigma of ONE car on the search mesh, seconds. Measured
# 2026-11-09 without the SIMPLE early stop (p2_noise n1b, blackwingftc-lang run
# 42654416947): 15 converged cars at skins 0.01 mm apart, residual SD 8.6 ms,
# 95 % interval 6.3 to 13.9 ms -- the cars settle on one of three drag levels.
# (The earlier 1.95 ms, run 42642036465, was taken with the early stop on and
# is not valid.) Update it when a noise fix lands.
NOISE_S = 8.645e-3
# ONE meshing frame for every car (as run_car.make_bindings): the legal envelope
# for the default scalars (x_front 46, W 120.3 mm), so background cells and boxes
# never move with the car. A car outside it raises; pass cfd={"domain_reference_bounds": ...}.
FRAME = ((-0.011, 0.0, 0.0), (0.2233, 0.0435, 0.066))
# The search mesh (part5 solver.SEARCH_CFD / SEARCH_ITERS).
SEARCH = {"resolution": "medium", "max_iterations": 1000,
          "layer_overrides": {"nSurfaceLayers": 0}, "domain_reference_bounds": FRAME}
DT_NAMES = ("drag_20_n", "car_weight_kg", "lift_20_n", "com_x_m", "com_height_m")


class StopwatchError(RuntimeError):
    """The car cannot be timed honestly (bad folder, or the CFD did not converge)."""


def body_stl(src: Path, dest: Path) -> Path:
    """Write only solid `car` of a (possibly multi-solid) ASCII STL to dest."""
    keep, out, seen = False, [], False
    for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
        st = line.strip().split()
        if st[:1] == ["solid"]:
            keep = (st[1:2] or ["car"])[0] == "car"
            seen |= keep
        if keep:
            out.append(line)
        if st[:1] == ["endsolid"]:
            keep = False
    if not seen:
        raise StopwatchError(f"{src} has no solid named 'car'")
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    return dest


def extra_surfaces(folder: Path) -> tuple:
    p = folder / "assembly.json"
    if not p.exists():
        return ()
    out = []
    for s in json.loads(p.read_text())["extra_surfaces"]:
        stl = Path(s["stl"])
        if not stl.is_absolute():
            stl = folder / stl
        rot = s.get("rotating")
        if rot:
            rot = {"origin": tuple(rot["origin"]), "axis": tuple(rot["axis"]),
                   "omega": float(rot["omega"])}
        out.append({"name": s["name"], "stl": str(stl), "rotating": rot})
    return tuple(out)


def race(D20: float, L20: float, mass: dict, assembly: dict | None = None) -> tuple:
    """(race time s, dT_d dict, model inputs) for full-car forces and a mass report.
    The time and slopes include the calibration factor TIME_COEFFICIENT and the
    centre of mass through the pitch balance (axles, cartridge and tether guides
    from `assembly` when it carries them, else the default layout)."""
    from race_objective import (build_smooth_sheet_model, geometry_from_assembly,
                                race_value_and_grad)
    from race_objective_adapter import race_value_and_grad_guarded

    mu = float(mass.get("mu", pc.DEFAULT_ROLLING_MU))
    moi = float(mass.get("wheel_moi_kg_m2", pc.DEFAULT_WHEEL_MOI_KG_M2))
    com = mass["com_mm"]          # car frame: x from the nose tip, z above the track
    tc = pc.TIME_COEFFICIENT
    params = np.array([D20, float(mass["car_weight_kg"]), mu, moi, tc, com[2] / 1e3, L20,
                       com[0] / 1e3])
    model = build_smooth_sheet_model(str(THRUST_CSV))
    geometry = "default layout"
    if assembly and "fixed_hardware_kwargs" in assembly:
        geo, gas = geometry_from_assembly(assembly)
        model = model._replace(geometry=geo, gas_xz_m=gas)
        geometry = "from assembly.json"
    T_raw, _, _ = race_value_and_grad_guarded(params, model)
    _, g = race_value_and_grad(params, model)
    inputs = {"thrust_csv": THRUST_CSV.name, "mu": mu, "wheel_moi_kg_m2": moi,
              "geometry": geometry, "mu_guide": model.geometry.mu_guide,
              "time_coefficient": tc,
              "time_coefficient_note": "calibration factor on the model time (team lead, 2026-11-09)",
              "race_time_uncalibrated_s": T_raw / tc,
              "co2_mass_curve": "derived from thrust (8 g charge), not measured",
              "placeholders": [k for k in ("mu", "wheel_moi_kg_m2") if k not in mass]
              + ["mu_guide", "bearing_load_law", "tether_drag (not modelled)"]}
    return T_raw, {k: g[k] for k in DT_NAMES}, inputs


def time_car(folder, res=None, iters=None, n_subdomains=4, cfd=None, noise_s=NOISE_S) -> dict:
    from cfd_wrapper import run_half_car_cfd

    folder = Path(folder)
    mass = json.loads((folder / "mass_report.json").read_text())
    kw = dict(SEARCH, **(cfd or {}))
    if res:
        kw["resolution"] = res
    if iters:
        kw["max_iterations"] = int(iters)
    t0 = time.time()
    body = body_stl(folder / "car_half.stl", folder / "_body_half.stl")
    half, health = run_half_car_cfd(str(body), n_subdomains=n_subdomains,
                                    extra_surfaces=extra_surfaces(folder), **kw)
    full = half.to_full_car()
    asm_path = folder / "assembly.json"
    asm = json.loads(asm_path.read_text()) if asm_path.exists() else None
    T, dT_d, inputs = race(full.D20, full.L, mass, asm)
    parts = {}
    for k, v in (health.patch_forces or {}).items():
        parts[k] = {"D_N": 2 * v["D_half_N"], "L_N": 2 * v["L_half_N"]}
    layers = (kw.get("layer_overrides") or {}).get("nSurfaceLayers")
    rec = {"D20_N": full.D20, "L20_N": full.L, "parts": parts,
           "race_time_s": T, "race_time_sd_s": noise_s, "dT_d": dT_d,
           "mesh": {"res": kw["resolution"], "cells": None, "layers": layers,
                    "iters": kw["max_iterations"]},
           "converged": bool(health.converged), "residual_p": health.residual_final,
           "force_osc_frac": health.force_oscillation,
           "force_mean_stderr": health.force_mean_stderr, "force_drift": health.force_drift,
           "seconds": round(time.time() - t0), "model_inputs": inputs,
           "note": "model race time, not a track time"}
    (folder / "stopwatch.json").write_text(json.dumps(rec, indent=1))
    return rec


def compare(car_a, car_b, noise_s=NOISE_S, **kw) -> tuple:
    """(T_b - T_a, sd) in seconds, both cars on the same mesh recipe and machine
    type. Raises StopwatchError if either solve is unconverged: never rank on it."""
    ra, rb = time_car(car_a, noise_s=noise_s, **kw), time_car(car_b, noise_s=noise_s, **kw)
    return paired(ra, rb)


def paired(ra: dict, rb: dict) -> tuple:
    bad = [n for n, r in (("a", ra), ("b", rb)) if not r["converged"]]
    if bad:
        raise StopwatchError(f"car {' and '.join(bad)} did not converge; not comparable")
    sd = math.hypot(ra["race_time_sd_s"], rb["race_time_sd_s"])
    return rb["race_time_s"] - ra["race_time_s"], sd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cars", nargs="+")
    ap.add_argument("--res")
    ap.add_argument("--iters", type=int)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--cfd-json", default="{}")
    a = ap.parse_args()
    kw = dict(res=a.res, iters=a.iters, n_subdomains=a.np, cfd=json.loads(a.cfd_json))
    if len(a.cars) == 2:
        dT, sd = compare(*a.cars, **kw)
        print(json.dumps({"dT_s": dT, "sd_s": sd}))
    else:
        print(json.dumps(time_car(a.cars[0], **kw), indent=1))


if __name__ == "__main__":
    main()
