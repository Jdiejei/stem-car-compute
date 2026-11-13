"""
JAX differentiable race-time objective for a STEM Racing / F1 in Schools car.

Version 4 (2026-11-09): the centre of mass acts through physics (pitch_balance),
not through placeholder penalties.

Purpose
-------
This file is meant to be the optimizer/adjoint-facing race model, not just a
post-processing simulator.

It converts the CSV thrust/mass sheet into smooth analytic functions, then
integrates the car dynamics in distance-domain:

    independent variable: x from 0 m to 20 m
    state: [t, q]
        t = elapsed race time
        q = v^2

The equations are:

    dt/dx = 1 / v
    dq/dx = 2a

where:

    a = [T_x(t) - D20*q/20^2 - R(t, q)] / [m(t) + N*I/r^2]

T_x is the forward thrust component and R the rolling and guide resistance,
both from pitch_balance.axle_loads: the pitch moment of the thrust line, drag,
lift and weight about the COM (car + unspent CO2) sets the front and rear axle
loads; a pair that would lift is held down by its tether guide, which rubs.
See acceleration() and wheel_resistance().

Using q = v^2 avoids the old timestep loop and avoids a branch-based finish
event. Race time is simply t at x = 20 m, so JAX can differentiate it.

Inputs to the differentiable objective:
    D20              drag force at 20 m/s, N
    car_weight_kg    entered car weight, kg
    mu               rolling friction coefficient
    wheel_moi_kg_m2  MOI of one wheel, kg*m^2
    time_coefficient coefficient multiplier; use 1.0 for normal time
    com_height_m     car COM (without CO2) height above the TRACK, m
    lift_20_n        lift at 20 m/s, N, + up
    com_x_m          car COM (without CO2) x from the NOSE TIP, + towards the tail, m

Outputs:
    race time in seconds
    gradients wrt every input above; the COM slopes are gradients of the same time

Notes
-----
- Mass logic (CORRECTED 2026-07-24, see car_mass_from_time for the full
  rationale). car_weight_kg carries everything permanently on the car,
  INCLUDING the empty cartridge shell; this file adds only the unspent CO2:
      m_car(t) = car_weight_kg + (m_sheet(t) - m_sheet_final)
  The previous form added a second cartridge shell (`+ 0.021`) on top of the
  one already in car_weight_kg, inflating a 50 g car to 78.9 g.
- Wheel inertia is converted into effective mass:
      m_eff = m_car + N*I/r^2
- The CSV is not used as a lookup table inside the objective. A smooth RBF
  surrogate is fitted once, then evaluated with pure JAX.
- This is single-point aero for now: D(v)=D20*(v/20)^2.
- Version 2 uses a non-uniform distance grid clustered near launch so the
  distance-domain singularity at v=0 is resolved without needing 20k steps.
- Version 3's placeholder COM penalties were removed in version 4.
- Placeholders still to measure: mu (rolling), the guide-on-line friction
  mu_guide = 0.25, the bearing load law exponent, tether drag (absent).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp

from pitch_balance import CarGeometry, axle_loads, com_with_gas
from physics_contract import DRAG_BIAS


G = 9.81
TRACK_LENGTH = 20.0
REFERENCE_SPEED = 20.0
N_WHEELS = 4
# 14.13 mm, measured on hardware_cad/front_wheel.stl (28.26 mm diameter,
# inside T7.5's 28.0-32.0). Was 0.015 -- a round number, 0.87 mm larger than
# the wheel actually being run. It divides the rotational inertia term in
# m_eff, so an oversized radius understates how much the wheels resist
# spinning up. Must stay equal to geometry_contract.R_WHEEL_M.
R_WHEEL = 0.01413

# CENTRE OF MASS (2026-11-09). The placeholder COM penalties are gone; the COM
# now acts through physics (pitch_balance.py): wheel and tether-guide loads from
# the pitch moment of the thrust line about the COM, plus drag, lift and weight.
#   com_x_m       x of the car's COM from the NOSE TIP, positive towards the tail
#                 (the car frame of Parts 1 and 4), WITHOUT the CO2 charge
#   com_height_m  z of the car's COM above the TRACK, WITHOUT the CO2 charge
# The unspent CO2 is added at the cartridge centre at every instant (com_with_gas).
# COM_TARGET_HEIGHT_M is kept only as a nominal default height; it is no longer a
# target and nothing is penalised for leaving it.
COM_TARGET_HEIGHT_M = 0.030

# Default geometry: Part 4's start car (mass_report.json, 2026-11-09): front axle
# 46 mm from the nose tip, wheelbase 120.3 mm, tether guides 5 mm outside each
# axle; the line runs through the guides' centres 6.0 mm above the track, and a
# guide catches it there when its wheel pair lifts; the 65 mm cartridge's axis
# at 31.0 mm with its rear centre at 235.3 mm, so its centre (where the CO2 is)
# 32.5 mm ahead of that. A car folder's own files override it.
CARTRIDGE_LENGTH_M = 0.065
DEFAULT_GEOMETRY = CarGeometry(
    x_front_axle_m=0.046, wheelbase_m=0.1203, x_thrust_m=0.2353, z_thrust_m=0.031,
    x_guide_front_m=0.041, x_guide_rear_m=0.1713, z_guide_m=0.0060)
DEFAULT_GAS_XZ_M = (0.2353 - CARTRIDGE_LENGTH_M / 2, 0.031)
# Wheel bearing load law (see wheel_resistance): 1.0 = plain Coulomb rolling
# resistance; > 1 makes friction grow faster than the load on an axle.
DEFAULT_BEARING_P = 1.0


def geometry_from_assembly(asm: dict, mass_report: dict | None = None, mu_guide: float = 0.25):
    """(CarGeometry, (x_gas, z_gas)) in metres from a car folder's assembly.json
    and, when given, Part 4's mass_report.json, which carries the cartridge's
    rear centre and axis height and the tether line height as built."""
    xf = asm["x_front_mm"] / 1e3
    wb = asm["W_mm"] / 1e3
    guides = sorted(asm["info"]["tethers"], key=lambda t: t["x_mm"])
    gx, _gy, gz = asm["fixed_hardware_kwargs"]["co2_cartridge_com"]
    x_thrust, z_thrust = gx + 0.026, gz                  # bore mid-depth -> rear face
    z_line = (guides[0]["bottom_mm"] + guides[0]["od_mm"] / 2.0) / 1e3     # guide centre
    if mass_report and "cartridge_rear_centre_x_mm" in mass_report:
        x_thrust = mass_report["cartridge_rear_centre_x_mm"] / 1e3
        z_thrust = mass_report["cartridge_axis_z_mm"] / 1e3
        z_line = mass_report["tether_line_z_mm"] / 1e3
        gx, gz = x_thrust - CARTRIDGE_LENGTH_M / 2, z_thrust
    geo = CarGeometry(x_front_axle_m=xf, wheelbase_m=wb, x_thrust_m=x_thrust, z_thrust_m=z_thrust,
                      x_guide_front_m=guides[0]["x_mm"] / 1e3, x_guide_rear_m=guides[-1]["x_mm"] / 1e3,
                      z_guide_m=z_line, mu_guide=mu_guide)
    return geo, (gx, gz)


# Parameter order for the optimizer-facing vector.
PARAM_NAMES = (
    "drag_20_n",
    "car_weight_kg",
    "mu",
    "wheel_moi_kg_m2",
    "time_coefficient",
    "com_height_m",
    "lift_20_n",
    "com_x_m",
)


class SmoothSheetModel(NamedTuple):
    centers: jnp.ndarray
    width: jnp.ndarray
    force_coeffs: jnp.ndarray
    mass_coeffs: jnp.ndarray
    t_min: jnp.ndarray
    t_max: jnp.ndarray
    mass_sheet_final: jnp.ndarray
    tail_tau: jnp.ndarray
    x_start: jnp.ndarray
    x_grid_power: jnp.ndarray
    n_steps: int
    geometry: CarGeometry = DEFAULT_GEOMETRY
    gas_xz_m: tuple = DEFAULT_GAS_XZ_M
    bearing_p: float = DEFAULT_BEARING_P
    # CFD drag reads high against the wind tunnel (Ahmed 25°: +3 to +13 %, 35°:
    # +5 %; PROOF.md "Drag bias"). Reviewer Q11 = A: the race model uses
    # D_true = D_cfd / drag_bias, with drag_bias 1.09 +- 0.04 (check the best
    # body at 1.05 and 1.13). drag_20_n stays the CFD value everywhere else.
    drag_bias: float = DRAG_BIAS


@dataclass(frozen=True)
class BuildSettings:
    n_basis: int = 80
    ridge: float = 1e-8
    tail_tau: float = 0.025
    x_start: float = 1e-4
    x_grid_power: float = 2.0
    n_steps: int = 1000


def _clean_csv_arrays(csv_path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path, comment="#")   # sheets may carry a "# ..." provenance header
    required = ["time (s)", "force (N)", "mass (kg)"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    clean = df[required].copy()
    clean = clean.apply(pd.to_numeric, errors="coerce").dropna()
    clean = clean.sort_values("time (s)")
    clean = clean.groupby("time (s)", as_index=False).mean()

    t = clean["time (s)"].to_numpy(dtype=np.float64)
    force = clean["force (N)"].to_numpy(dtype=np.float64)
    mass = clean["mass (kg)"].to_numpy(dtype=np.float64)

    if len(t) < 4:
        raise ValueError("CSV needs at least 4 valid data points.")
    if not np.all(np.diff(t) > 0):
        raise ValueError("Time column must be strictly increasing after cleaning.")

    return t, force, mass


def _rbf_design(t: np.ndarray, centers: np.ndarray, width: float) -> np.ndarray:
    z = (t[:, None] - centers[None, :]) / width
    rbf = np.exp(-0.5 * z * z)
    # Add constant + linear term so the fit handles the slow mass tail better.
    t_scaled = (t - t[0]) / max(t[-1] - t[0], 1e-12)
    return np.column_stack([rbf, np.ones_like(t), t_scaled])


def _ridge_fit(Phi: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
    b = Phi.T @ y
    return np.linalg.solve(A, b)


def build_smooth_sheet_model(
    csv_path: str | Path = Path(__file__).resolve().parent / "thrust_measured_beta.csv",
    settings: BuildSettings = BuildSettings(),
) -> SmoothSheetModel:
    """Fit smooth JAX-evaluable thrust and mass-sheet functions from the CSV."""
    t, force, mass_sheet = _clean_csv_arrays(csv_path)

    centers = np.linspace(float(t[0]), float(t[-1]), settings.n_basis)
    spacing = centers[1] - centers[0] if len(centers) > 1 else (t[-1] - t[0])
    width = max(2.5 * spacing, 1e-6)

    Phi = _rbf_design(t, centers, width)
    force_coeffs = _ridge_fit(Phi, force, settings.ridge)
    mass_coeffs = _ridge_fit(Phi, mass_sheet, settings.ridge)

    return SmoothSheetModel(
        centers=jnp.asarray(centers, dtype=jnp.float64),
        width=jnp.asarray(width, dtype=jnp.float64),
        force_coeffs=jnp.asarray(force_coeffs, dtype=jnp.float64),
        mass_coeffs=jnp.asarray(mass_coeffs, dtype=jnp.float64),
        t_min=jnp.asarray(float(t[0]), dtype=jnp.float64),
        t_max=jnp.asarray(float(t[-1]), dtype=jnp.float64),
        mass_sheet_final=jnp.asarray(float(mass_sheet[-1]), dtype=jnp.float64),
        tail_tau=jnp.asarray(settings.tail_tau, dtype=jnp.float64),
        x_start=jnp.asarray(settings.x_start, dtype=jnp.float64),
        x_grid_power=jnp.asarray(settings.x_grid_power, dtype=jnp.float64),
        n_steps=settings.n_steps,
    )


def _smooth_positive(x: jnp.ndarray, scale: float = 1e-6) -> jnp.ndarray:
    """Smooth approximation of max(x, 0), retaining gradients."""
    s = jnp.asarray(scale, dtype=x.dtype)
    return s * jax.nn.softplus(x / s)


def _eval_rbf_model(t: jnp.ndarray, model: SmoothSheetModel, coeffs: jnp.ndarray) -> jnp.ndarray:
    z = (t - model.centers) / model.width
    rbf = jnp.exp(-0.5 * z * z)
    t_scaled = (t - model.t_min) / jnp.maximum(model.t_max - model.t_min, 1e-12)
    features = jnp.concatenate([rbf, jnp.array([1.0, t_scaled], dtype=t.dtype)])
    return jnp.dot(features, coeffs)


def thrust_force(t: jnp.ndarray, model: SmoothSheetModel) -> jnp.ndarray:
    """
    Smooth thrust function F(t).

    The RBF fit handles the in-sheet curve. A smooth logistic tail turns thrust
    off after the sheet's final time instead of using a hard if-statement.

    Past the sheet the fit is held at its last value instead of extrapolated:
    its constant and linear terms otherwise pushed on after the burn (+2.4 %
    impulse on the measured sheet, worse for a slow car still running at 4 s).
    """
    raw = _eval_rbf_model(jnp.minimum(t, model.t_max), model, model.force_coeffs)
    nonnegative = _smooth_positive(raw, scale=1e-4)
    end_gate = jax.nn.sigmoid((model.t_max - t) / model.tail_tau)
    return nonnegative * end_gate


def sheet_mass(t: jnp.ndarray, model: SmoothSheetModel) -> jnp.ndarray:
    """
    Smooth version of the CSV mass column.

    After the CSV ends, it smoothly approaches the final sheet mass instead of
    branching to a constant value.
    """
    raw = _eval_rbf_model(t, model, model.mass_coeffs)
    end_gate = jax.nn.sigmoid((model.t_max - t) / model.tail_tau)
    return model.mass_sheet_final + end_gate * (raw - model.mass_sheet_final)


def car_mass_from_time(
    t: jnp.ndarray,
    car_weight_kg: jnp.ndarray,
    model: SmoothSheetModel,
) -> jnp.ndarray:
    """Instantaneous vehicle mass: the entered car weight plus the propellant
    still on board.

    UNLOCKED AND CORRECTED 2026-07-24 (project owner authorised). Was:

        m = car_weight_kg + 0.021 + sheet_mass(t) - 0.048

    which added +28.9 g at the line decaying to +21.0 g on top of
    car_weight_kg. The 0.021 term is a CARTRIDGE SHELL mass, and
    car_weight_kg already contains one: Part 2's mass_com_ingest sums
    CO2_CARTRIDGE_MASS_KG (23 g) into the total it passes in. So the cartridge
    hardware was counted TWICE -- a 50 g car entered the integrator at 78.9 g,
    roughly +23 g of phantom mass on a vehicle whose regulated minimum is 48 g.
    At dT/dmass ~ 17.9 s/kg that is ~0.41 s of fictitious race time, larger
    than anything the shape optimiser can win back.

    The split of responsibility is now unambiguous:

      car_weight_kg   everything PERMANENTLY on the car, from the geometry
                      mass rollup -- machined body, wheels/axles, rear wing,
                      and the EMPTY cartridge shell (CO2_CARTRIDGE_MASS_KG).
      this function   adds only the CO2 PROPELLANT still unspent at time t,
                      which no geometry model can represent because it leaves
                      the vehicle during the run.

    The propellant term is `sheet_mass(t) - mass_sheet_final`, i.e. the CSV's
    own mass curve measured from its own endpoint: 7.89 g at t=0 falling to 0.
    It reads mass_sheet_final off the model instead of the hardcoded 0.048 so
    it stays exactly zero at the end for ANY thrust CSV, rather than depending
    on that constant matching the data.
    """
    # Clamped on the PROPELLANT, not on the total.
    #
    # _smooth_positive used to wrap `m = car_weight_kg + propellant_kg`, which
    # is ~0.149 kg and never anywhere near zero, so the clamp did nothing. The
    # quantity that actually goes negative is the propellant term: the RBF fit
    # rings slightly below its own endpoint, so `sheet_mass(t) - mass_sheet_final`
    # is negative for t in [0.177, 2.433] s -- 49.7% of a 3.0 s race, starting
    # INSIDE the data range rather than only in extrapolation -- with a mean
    # deficit of 2.8 ug and a worst case of 42.3 ug. It also rises again around
    # t=1.61 s, i.e. spent propellant flowing back into the car.
    #
    # This is the same shape as the COM-penalty well fixed the same day: a
    # fitted model breaking an invariant the arithmetic around it assumes. It
    # never crashed anything because nothing checks the sign of a mass, it just
    # made the car up to 42 ug too light for half the race.
    #
    # Small: dT/dmass * 42.3 ug is 0.74 ms worst case, about 5% of the +/-15 ms
    # drag noise, so no ranking moves. Fixed because "propellant remaining" being
    # negative is not a thing, and because the docstring above already says this
    # term falls to zero.
    propellant_kg = _smooth_positive(
        sheet_mass(t, model) - model.mass_sheet_final, scale=1e-9)
    return car_weight_kg + propellant_kg


def unpack_params(params: jnp.ndarray) -> dict[str, jnp.ndarray]:
    return {name: params[i] for i, name in enumerate(PARAM_NAMES)}


def wheel_resistance(pr, weight_n, x_com_m, mu, geo: CarGeometry, bearing_p):
    """Backward force from both axles and both guides, N.

    Per axle, F = mu * N0 * (N / N0)**p, with N0 that axle's share of the net
    load if the car were not pitching (lever rule about the COM). p = 1 is plain
    Coulomb rolling resistance, mu * N, and then the total does not depend on
    how the load is split. p > 1 is a bearing whose drag grows faster than its
    load, so moving weight onto one axle costs time even before a wheel lifts.
    Guides: mu_guide times the line's pull."""
    x_rear = geo.x_front_axle_m + geo.wheelbase_m
    n0_f = weight_n * (x_rear - x_com_m) / geo.wheelbase_m
    n0_r = weight_n * (x_com_m - geo.x_front_axle_m) / geo.wheelbase_m

    def axle(n, n0):
        return mu * n0 * jnp.power(jnp.maximum(n, 0.0) / n0, bearing_p)

    return (axle(pr.n_front, n0_f) + axle(pr.n_rear, n0_r)
            + geo.mu_guide * (pr.g_front + pr.g_rear))


def acceleration(t: jnp.ndarray, q: jnp.ndarray, params: jnp.ndarray,
                 model: SmoothSheetModel) -> jnp.ndarray:
    """dv/dt at time t and speed^2 q.

    Thrust, drag, lift and weight (car + unspent CO2 at the cartridge centre)
    set the pitch moment about the COM; pitch_balance turns that into axle and
    guide loads, and those into rolling and guide friction. Thrust counts only
    its forward component. Lift L(v) = lift_20_n (v/20)^2, + up; drag likewise.
    """
    p = unpack_params(params)
    m = car_mass_from_time(t, p["car_weight_kg"], model)
    gas = m - p["car_weight_kg"]
    gx, gz = model.gas_xz_m
    m_tot, xc, zc = com_with_gas(p["car_weight_kg"], p["com_x_m"], p["com_height_m"], gas, gx, gz)
    m_eff = m_tot + N_WHEELS * p["wheel_moi_kg_m2"] / (R_WHEEL ** 2)

    F_thrust = thrust_force(t, model)
    F_drag = p["drag_20_n"] / model.drag_bias * q / (REFERENCE_SPEED ** 2)
    L_v = p["lift_20_n"] * q / (REFERENCE_SPEED ** 2)
    geo = model.geometry._replace(mu_front=p["mu"], mu_rear=p["mu"])
    pr = axle_loads(F_thrust, F_drag, L_v, m_tot, xc, zc, geo)
    w = m_tot * G - L_v - F_thrust * jnp.sin(geo.thrust_angle_rad)
    resist = wheel_resistance(pr, w, xc, p["mu"], geo, model.bearing_p)
    return (pr.thrust_x - F_drag - resist) / m_eff


def initial_state(params: jnp.ndarray, model: SmoothSheetModel) -> tuple[jnp.ndarray, jnp.ndarray]:
    """
    Start slightly after x=0 using a local constant-acceleration launch estimate.

    Distance-domain dynamics has dt/dx = 1/v, which is singular exactly at
    v=0. The singularity is physically integrable, but numerically awkward.
    We therefore initialize at x_start using:

        x = 0.5*a0*t^2
        q = v^2 = 2*a0*x

    where a0 is the acceleration at t=0, v=0 (same physics as the run).
    """
    t0 = jnp.asarray(0.0, dtype=params.dtype)
    a0 = acceleration(t0, jnp.asarray(0.0, dtype=params.dtype), params, model)

    # Valid cars should have positive launch acceleration. The smooth floor keeps
    # gradients finite for bad inputs instead of crashing.
    a0_safe = _smooth_positive(a0, scale=1e-4) + 1e-8

    q0 = 2.0 * a0_safe * model.x_start
    t_start = jnp.sqrt(2.0 * model.x_start / a0_safe)
    return t_start, q0


def distance_derivatives(
    state: tuple[jnp.ndarray, jnp.ndarray],
    _x: jnp.ndarray,
    params: jnp.ndarray,
    model: SmoothSheetModel,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    """Return dt/dx and dq/dx at the current distance location."""
    t, q = state
    # q = v^2. Keep it positive smoothly so invalid designs become slow/penalized
    # instead of producing NaNs.
    q_safe = _smooth_positive(q, scale=1e-6) + 1e-10
    a = acceleration(t, q_safe, params, model)
    return 1.0 / jnp.sqrt(q_safe), 2.0 * a


def rk4_step(
    state: tuple[jnp.ndarray, jnp.ndarray],
    x: jnp.ndarray,
    dx: jnp.ndarray,
    params: jnp.ndarray,
    model: SmoothSheetModel,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    def add_state(s, k, factor):
        return (s[0] + factor * dx * k[0], s[1] + factor * dx * k[1])

    k1 = distance_derivatives(state, x, params, model)
    k2 = distance_derivatives(add_state(state, k1, 0.5), x + 0.5 * dx, params, model)
    k3 = distance_derivatives(add_state(state, k2, 0.5), x + 0.5 * dx, params, model)
    k4 = distance_derivatives(add_state(state, k3, 1.0), x + dx, params, model)

    t_new = state[0] + (dx / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
    q_new = state[1] + (dx / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
    return t_new, q_new


def race_time_seconds(params: jnp.ndarray, model: SmoothSheetModel) -> jnp.ndarray:
    """Differentiable predicted race time in seconds."""
    p = unpack_params(params)

    x0 = model.x_start
    x1 = jnp.asarray(TRACK_LENGTH, dtype=params.dtype)

    # Non-uniform distance grid.
    # The distance-domain equations contain dt/dx = 1/v, which is singular
    # near launch. Uniform dx needs many steps to resolve the first few
    # centimeters. A powered grid clusters points near x=0 while keeping the
    # whole integration fixed-shape and JAX-differentiable.
    u_edges = jnp.linspace(0.0, 1.0, model.n_steps + 1, dtype=params.dtype)
    x_edges = x0 + (x1 - x0) * (u_edges ** model.x_grid_power)
    xs = x_edges[:-1]
    dxs = x_edges[1:] - x_edges[:-1]

    state0 = initial_state(params, model)

    def scan_body(state, step_data):
        x, dx = step_data
        new_state = rk4_step(state, x, dx, params, model)
        return new_state, new_state

    final_state, history = jax.lax.scan(scan_body, state0, (xs, dxs))
    t_finish, q_finish = final_state

    # Smooth penalty if final v^2 is near/below zero. For normal finishing cars,
    # this is approximately zero.
    q_safe_finish = _smooth_positive(q_finish, scale=1e-6)
    low_speed_penalty = 0.05 * _smooth_positive(0.01 - q_safe_finish, scale=1e-4)

    # No COM penalty: the COM acts through the wheel and guide loads above.
    return p["time_coefficient"] * (t_finish + low_speed_penalty)


# Built once rather than per call. This is tidiness, NOT a fix -- and an earlier
# version of this comment claimed otherwise, which was wrong.
#
# THE LEAK, for whoever meets it next. Every call to this function TRACES the
# objective, and each trace leaks JIT code mappings: measured 2026-07-27 at
# ~3,300 per Stage-1 evaluation against a default vm.max_map_count of 65,530
# (5 evals -> 17,643 mappings, 16 -> 52,573, and production's 32 over the
# ceiling). mmap then fails, LLVM reports "Cannot allocate memory", and the
# process segfaults -- on a box with 16 GB free, which is why it read as
# anything but a mapping leak. Stage 1 died at roughly evaluation 20 every time.
#
# WHY HOISTING DOES NOT FIX IT. `jax.value_and_grad` is not a caching transform;
# only `jax.jit` is. value_and_grad re-traces on every call wherever it is
# constructed. Measured: hoisted 999 ms/call, rebuilt-per-call 1017 ms/call --
# no difference.
#
# WHAT ACTUALLY FIXES IT, if it ever matters:
#     jax.jit(lambda pv: jax.value_and_grad(race_time_seconds)(pv, model))
# with the model captured as a closure constant, so jnp.linspace's `num` stays
# concrete (passing the model as an argument raises ConcretizationTypeError).
# Measured 1040 ms -> 23.8 ms per call, a 44x speedup and no further traces.
# NOT applied, deliberately: it is not bit-identical (value delta 7e-10 s,
# worst gradient delta 4.5e-4), Stage 1 runs ONCE per sweep at ~8 minutes while
# CFD costs 25 minutes per pair hundreds of times, and this objective is what
# ranks candidates. Perturbing it to speed up a step that is not the bottleneck
# is a bad trade.
#
# MITIGATION IN PLACE: vm.max_map_count raised to 1,048,576 on the VM and
# persisted in /etc/sysctl.d/99-stem-maps.conf -- roughly 300 Stage-1
# evaluations of headroom against the 32 production uses. Revisit if a run ever
# needs materially more.
_RACE_VALUE_AND_GRAD = jax.value_and_grad(race_time_seconds)


def race_value_and_grad(params: np.ndarray, model: SmoothSheetModel) -> tuple[float, dict[str, float]]:
    params_jax = jnp.asarray(params, dtype=jnp.float64)
    value, grad_vec = _RACE_VALUE_AND_GRAD(params_jax, model)
    return float(value), {name: float(grad_vec[i]) for i, name in enumerate(PARAM_NAMES)}


def finite_difference_check(
    params: np.ndarray,
    model: SmoothSheetModel,
    relative_eps: float = 1e-4,
) -> list[dict[str, float]]:
    """Compare JAX gradients to central finite differences."""
    base = np.asarray(params, dtype=np.float64)
    value, grads = race_value_and_grad(base, model)
    rows = []

    fallback_steps = {
        "drag_20_n": 1e-5,
        "car_weight_kg": 1e-6,
        "mu": 1e-6,
        "wheel_moi_kg_m2": 1e-11,
        "time_coefficient": 1e-5,
        "com_height_m": 1e-6,
        "lift_20_n": 1e-5,
        "com_x_m": 1e-6,
    }

    for i, name in enumerate(PARAM_NAMES):
        # Use a scale-aware perturbation. Some parameters, especially wheel MOI
        # in kg*m^2, are around 1e-7, so max(abs(x), 1) would be catastrophically
        # too large for a finite-difference test.
        step = max(relative_eps * abs(base[i]), fallback_steps[name])
        p_plus = base.copy()
        p_minus = base.copy()
        p_plus[i] += step
        p_minus[i] -= step

        f_plus = float(race_time_seconds(jnp.asarray(p_plus), model))
        f_minus = float(race_time_seconds(jnp.asarray(p_minus), model))
        fd = (f_plus - f_minus) / (2.0 * step)
        jg = grads[name]
        rows.append(
            {
                "param": name,
                "jax_grad": jg,
                "finite_diff": fd,
                "abs_error": abs(jg - fd),
                "base_value": base[i],
                "race_time_s": value,
            }
        )

    return rows


def make_param_vector(
    drag_20_n: float,
    car_weight_g: float,
    mu: float,
    wheel_moi_g_mm2: float,
    time_coefficient_percent: float = 100.0,
    com_height_mm: float = 30.0,
    lift_20_n: float = 0.0,
    com_x_mm: float = 110.0,          # from the nose tip (car frame)
) -> np.ndarray:
    """Helper matching the old script's user-facing units."""
    return np.array(
        [
            drag_20_n,
            car_weight_g / 1000.0,
            mu,
            wheel_moi_g_mm2 * 1e-9,
            time_coefficient_percent / 100.0,
            com_height_mm / 1000.0,
            lift_20_n,
            com_x_mm / 1000.0,
        ],
        dtype=np.float64,
    )


def main() -> None:
    # Enable float64 for better gradient checks and physics accuracy.
    # If your install disables this globally, run with:
    #   export JAX_ENABLE_X64=True
    jax.config.update("jax_enable_x64", True)

    csv_path = Path(input("CSV path [co2_thrust_data.csv]: ").strip() or "co2_thrust_data.csv")
    model = build_smooth_sheet_model(csv_path)

    params = make_param_vector(
        drag_20_n=float(input("Enter drag force at 20 m/s (N): ")),
        car_weight_g=float(input("Weight of car (g): ")),
        mu=float(input("Enter rolling friction coefficient: ")),
        wheel_moi_g_mm2=float(input("Enter wheel MOI (g·mm^2): ")),
        time_coefficient_percent=float(input("Enter Time Coefficient (in %) [100 = unchanged]: ") or "100"),
        com_height_mm=float(input("Enter COM height (mm) [30 = ideal]: ") or "30"),
        lift_20_n=float(input("Enter lift force at 20 m/s (N) [0 = none]: ") or "0"),
        com_x_mm=float(input("Enter COM x position (mm) [0 = reference]: ") or "0"),
    )

    T, grads = race_value_and_grad(params, model)
    print("\nPredicted differentiable race time:")
    print(f"  T = {T:.6f} s")
    params_jax = jnp.asarray(params, dtype=jnp.float64)
    print(f"  COM penalty = {float(com_height_time_penalty(params_jax)):.6f} s")

    print("\nGradients:")
    for name, grad in grads.items():
        print(f"  dT/d{name:>18s} = {grad:.9e}")

    print("\nFinite-difference check:")
    for row in finite_difference_check(params, model):
        print(
            f"  {row['param']:>18s}: "
            f"JAX={row['jax_grad']:.9e}, "
            f"FD={row['finite_diff']:.9e}, "
            f"abs_err={row['abs_error']:.3e}"
        )


if __name__ == "__main__":
    main()
