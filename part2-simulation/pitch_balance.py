"""
pitch_balance.py -- wheel loads, tether-guide loads and rolling resistance of a STEM
Racing car from the pitch-moment balance. Replaces the placeholder centre-of-mass (COM)
penalties in race_objective.py with physics.

Frame (same as the rest of the project): x from the nose tip towards the tail (m),
z up from the track (m). The car is symmetric, so only the x-z plane matters.

Forces on the car at one instant (quasi-static in pitch: the car does not rotate):
  thrust  T along the cartridge axis, tilted by `thrust_angle_rad` (+ = thrust vector
          points up and forward), acting through the cartridge's rear centre
          (x_thrust, z_thrust); T5.2: z_thrust 30-40 mm; T5.4: angle within +-3 deg
  drag    D horizontal, backwards, at height z_drag
  lift    L vertical, at x_lift
  weight  m g at the COM (x_c, z_c)
  wheels  normal loads N_f (front axle) and N_r (rear axle), rolling resistance
          mu_f N_f and mu_r N_r backwards at track level
  guides  if a wheel pair would leave the track, the tether guide at that end catches
          the line, which pulls that end down with G_f or G_r and rubs with friction
          mu_guide G (backwards). T6.1: guides within 10 mm of each axle.

Pitch moments are taken about the COM (nose-up positive). For a force (Fx, Fz) at a
point (dx, dz) relative to the COM, with x pointing FORWARD: tau = dx_fwd*Fz - dz*Fx.

Result: with both axles on the track and mu_f == mu_r, rolling resistance is
mu (m g - L - T_z) whatever the COM height: the COM matters only through (a) wheel
lift, which brings in guide friction, (b) different front/rear rolling resistance, and
(c) the vertical thrust component. A thrust line through the COM gives zero thrust
torque, so no load transfer and no lift at any thrust.

Everything is plain jax.numpy, so race_objective can differentiate through it.
"""
from __future__ import annotations

from typing import NamedTuple

import jax.numpy as jnp

G = 9.81


class CarGeometry(NamedTuple):
    """Where things are on the assembled car (car frame, metres). From Part 4's assembly."""
    x_front_axle_m: float
    wheelbase_m: float
    x_thrust_m: float            # rear centre of the cartridge (where T5.2 is measured)
    z_thrust_m: float            # T5.2: 0.030-0.040
    thrust_angle_rad: float = 0.0   # T5.4: within +-3 deg; + = thrust tilted upward
    x_guide_front_m: float | None = None   # default: on the front axle
    x_guide_rear_m: float | None = None    # default: on the rear axle
    z_guide_m: float = 0.0045    # height of the line where it touches a guide
    z_drag_m: float | None = None    # centre of pressure height; default: at the COM
    x_lift_m: float | None = None    # where lift acts; default: at the COM
    mu_front: float = 0.010      # rolling resistance per axle (placeholder until measured)
    mu_rear: float = 0.010
    mu_guide: float = 0.25       # guide sliding on the tether line: PLACEHOLDER, measure it


class PitchResult(NamedTuple):
    n_front: jnp.ndarray     # N, wheel load on the front axle (both wheels)
    n_rear: jnp.ndarray
    g_front: jnp.ndarray     # N, downward pull of the line on the front guide (0 unless the front lifts)
    g_rear: jnp.ndarray
    resist: jnp.ndarray      # N, total backward force from wheels and guides
    thrust_x: jnp.ndarray    # N, forward component of thrust
    tau_ext: jnp.ndarray     # N m, nose-up moment of thrust, drag and lift about the COM


def axle_loads(thrust_n, drag_n, lift_n, mass_kg, x_com_m, z_com_m, geo: CarGeometry, g: float = G) -> PitchResult:
    x_rear = geo.x_front_axle_m + geo.wheelbase_m
    x_gf = geo.x_front_axle_m if geo.x_guide_front_m is None else geo.x_guide_front_m
    x_gr = x_rear if geo.x_guide_rear_m is None else geo.x_guide_rear_m
    z_drag = z_com_m if geo.z_drag_m is None else geo.z_drag_m
    x_lift = x_com_m if geo.x_lift_m is None else geo.x_lift_m

    # forward distances from the COM (x points rearward, so forward = x_com - x)
    d_f = x_com_m - geo.x_front_axle_m          # front axle ahead of the COM  (> 0)
    d_r = x_rear - x_com_m                      # rear axle behind the COM     (> 0)
    d_gf = x_com_m - x_gf
    d_gr = x_gr - x_com_m
    fwd_thrust = x_com_m - geo.x_thrust_m       # thrust point is behind the COM, so < 0
    fwd_lift = x_com_m - x_lift

    th = geo.thrust_angle_rad
    tx = thrust_n * jnp.cos(th)
    tz = thrust_n * jnp.sin(th)
    # nose-up moments about the COM:  tau = dx_fwd * Fz - dz * Fx
    tau = (fwd_thrust * tz - (geo.z_thrust_m - z_com_m) * tx
           + (z_drag - z_com_m) * drag_n          # drag Fx = -D
           + fwd_lift * lift_n)

    w = mass_kg * g - lift_n - tz                 # net load the track and guides must carry
    a_f = d_f - z_com_m * geo.mu_front            # front wheel: (dx, dz) = (d_f, -z_c), F = (-mu N, N)
    a_r = d_r + z_com_m * geo.mu_rear             # rear wheel:  (-d_r, -z_c)
    # both axles down: a_f N_f - a_r N_r = -tau,  N_f + N_r = w
    nf_u = (a_r * w - tau) / (a_f + a_r)
    nr_u = w - nf_u

    # a guide, pulled down by the line with G and rubbing backwards with mu_guide G
    b_r = d_gr + (geo.z_guide_m - z_com_m) * geo.mu_guide     # rear guide moment arm (nose-up per unit G)
    b_f = d_gf - (geo.z_guide_m - z_com_m) * geo.mu_guide     # front guide (nose-down per unit G)
    g_r_lift = (a_f + a_r) / (a_f + b_r) * (-nr_u)            # rear wheels up: N_r = 0
    g_f_lift = (a_f + a_r) / (a_r + b_f) * (-nf_u)            # front wheels up: N_f = 0

    rear_up = nr_u < 0.0
    front_up = nf_u < 0.0
    g_r = jnp.where(rear_up, g_r_lift, 0.0)
    g_f = jnp.where(front_up, g_f_lift, 0.0)
    n_f = jnp.where(rear_up, w + g_r, jnp.where(front_up, 0.0, nf_u))
    n_r = jnp.where(front_up, w + g_f, jnp.where(rear_up, 0.0, nr_u))

    resist = geo.mu_front * n_f + geo.mu_rear * n_r + geo.mu_guide * (g_f + g_r)
    return PitchResult(n_f, n_r, g_f, g_r, resist, tx, tau)


def com_with_gas(car_mass_kg, x_com_m, z_com_m, gas_mass_kg, x_gas_m, z_gas_m):
    """COM of the car plus the CO2 still in the cartridge (the gas sits in the cartridge,
    near the rear, so the COM moves forward and down a little as it empties)."""
    m = car_mass_kg + gas_mass_kg
    return m, (car_mass_kg * x_com_m + gas_mass_kg * x_gas_m) / m, (car_mass_kg * z_com_m + gas_mass_kg * z_gas_m) / m


def lift_threshold_offset_m(thrust_n, mass_kg, x_com_m, z_com_m, geo: CarGeometry, g: float = G):
    """How far (m) the thrust line may sit above (+) or below (-) the COM before a wheel
    pair leaves the track at this thrust, with no drag or lift. Useful for design."""
    d_f = x_com_m - geo.x_front_axle_m
    d_r = geo.x_front_axle_m + geo.wheelbase_m - x_com_m
    w = mass_kg * g
    # rear lifts when tau <= -(a_f w); front lifts when tau >= a_r w   (mu terms are tiny)
    return (d_f * w) / thrust_n, -(d_r * w) / thrust_n
