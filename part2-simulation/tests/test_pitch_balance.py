"""Physics checks for pitch_balance.py (run on GitHub with the Part 2 suite)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jax  # noqa: E402

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp  # noqa: E402

from pitch_balance import G, CarGeometry, axle_loads, com_with_gas, lift_threshold_offset_m  # noqa: E402

M = 0.056            # kg, car with a full cartridge
X_C = 0.110          # m, COM from the nose tip
Z_C = 0.030          # m, COM height


def geo(z_thrust=Z_C, **kw):
    base = dict(x_front_axle_m=0.046, wheelbase_m=0.1203, x_thrust_m=0.205, z_thrust_m=z_thrust)
    base.update(kw)
    return CarGeometry(**base)


def moment_residual(r, thrust, drag, lift, x_c, z_c, g_):
    """Recompute the nose-up moment of every force about the COM: must be ~0."""
    x_rear = g_.x_front_axle_m + g_.wheelbase_m
    tx, tz = thrust * jnp.cos(g_.thrust_angle_rad), thrust * jnp.sin(g_.thrust_angle_rad)
    tau = (x_c - g_.x_thrust_m) * tz - (g_.z_thrust_m - z_c) * tx + drag * ((g_.z_drag_m or z_c) - z_c)
    tau += (x_c - g_.x_front_axle_m) * r.n_front - (-z_c) * (-g_.mu_front * r.n_front)
    tau += (-(x_rear - x_c)) * r.n_rear - (-z_c) * (-g_.mu_rear * r.n_rear)
    xgf = g_.x_guide_front_m if g_.x_guide_front_m is not None else g_.x_front_axle_m
    xgr = g_.x_guide_rear_m if g_.x_guide_rear_m is not None else x_rear
    tau += (x_c - xgf) * (-r.g_front) - (g_.z_guide_m - z_c) * (-g_.mu_guide * r.g_front)
    tau += (-(xgr - x_c)) * (-r.g_rear) - (g_.z_guide_m - z_c) * (-g_.mu_guide * r.g_rear)
    vert = r.n_front + r.n_rear - r.g_front - r.g_rear + lift + tz - M * G
    return float(tau), float(vert)


def test_static_split_matches_lever_rule():
    g_ = geo(mu_front=0.0, mu_rear=0.0)
    r = axle_loads(0.0, 0.0, 0.0, M, X_C, Z_C, g_)
    d_f = X_C - g_.x_front_axle_m
    d_r = g_.x_front_axle_m + g_.wheelbase_m - X_C
    assert abs(float(r.n_front) - M * G * d_r / (d_f + d_r)) < 1e-12
    assert abs(float(r.n_rear) - M * G * d_f / (d_f + d_r)) < 1e-12
    assert float(r.g_front) == 0.0 and float(r.g_rear) == 0.0


def test_thrust_through_com_moves_no_load():
    g_ = geo(z_thrust=Z_C)
    still = axle_loads(0.0, 0.0, 0.0, M, X_C, Z_C, g_)
    for t in (1.0, 5.0, 9.0):
        r = axle_loads(t, 0.0, 0.0, M, X_C, Z_C, g_)
        assert abs(float(r.n_front - still.n_front)) < 1e-12
        assert float(r.g_front) == 0.0 and float(r.g_rear) == 0.0


def test_thrust_above_com_unloads_then_lifts_the_rear():
    small = axle_loads(9.0, 0.0, 0.0, M, X_C, Z_C, geo(z_thrust=Z_C + 0.001))
    still = axle_loads(0.0, 0.0, 0.0, M, X_C, Z_C, geo(z_thrust=Z_C + 0.001))
    assert float(small.n_rear) < float(still.n_rear) and float(small.g_rear) == 0.0
    big = axle_loads(9.0, 0.0, 0.0, M, X_C, Z_C, geo(z_thrust=Z_C + 0.010))
    assert float(big.n_rear) == 0.0 and float(big.g_rear) > 0.0 and float(big.g_front) == 0.0


def test_thrust_below_com_lifts_the_front():
    r = axle_loads(9.0, 0.0, 0.0, M, X_C, 0.045, geo(z_thrust=0.030))
    assert float(r.n_front) == 0.0 and float(r.g_front) > 0.0 and float(r.g_rear) == 0.0


def test_forces_and_moments_balance_in_every_regime():
    for zt in (Z_C, Z_C + 0.003, Z_C + 0.010, Z_C - 0.012):
        for ang in (0.0, 0.03, -0.03):
            g_ = geo(z_thrust=zt, thrust_angle_rad=ang, x_guide_front_m=0.040, x_guide_rear_m=0.171, z_drag_m=0.025)
            r = axle_loads(9.0, 0.3, 0.05, M, X_C, Z_C, g_)
            tau, vert = moment_residual(r, 9.0, 0.3, 0.05, X_C, Z_C, g_)
            assert abs(tau) < 1e-10 and abs(vert) < 1e-10, (zt, ang, tau, vert)
            assert float(r.n_front) >= 0.0 and float(r.n_rear) >= 0.0


def test_equal_mu_and_wheels_down_means_com_height_does_not_change_resistance():
    res = [float(axle_loads(2.0, 0.1, 0.0, M, X_C, z, geo(z_thrust=z)).resist) for z in (0.025, 0.030, 0.035)]
    assert max(res) - min(res) < 1e-12


def test_resistance_grows_with_misalignment_once_a_wheel_lifts():
    res = [float(axle_loads(9.0, 0.0, 0.0, M, X_C, Z_C, geo(z_thrust=Z_C + d)).resist) for d in (0.0, 0.006, 0.010, 0.015)]
    assert res[0] <= res[1] < res[2] < res[3]


def test_lift_threshold_matches_the_solver():
    g_ = geo(mu_front=0.0, mu_rear=0.0)
    above, below = lift_threshold_offset_m(9.0, M, X_C, Z_C, g_)
    assert above > 0 > below
    just_in = axle_loads(9.0, 0.0, 0.0, M, X_C, Z_C, g_._replace(z_thrust_m=Z_C + 0.99 * above))
    just_out = axle_loads(9.0, 0.0, 0.0, M, X_C, Z_C, g_._replace(z_thrust_m=Z_C + 1.01 * above))
    assert float(just_in.g_rear) == 0.0 and float(just_out.g_rear) > 0.0


def test_differentiable_in_com_height_and_x():
    def f(z, x):
        return axle_loads(9.0, 0.2, 0.0, M, x, z, geo(z_thrust=0.040)).resist
    gz, gx = jax.grad(f, argnums=(0, 1))(0.030, X_C)
    assert jnp.isfinite(gz) and jnp.isfinite(gx)
    eps = 1e-7
    fd = (f(0.030 + eps, X_C) - f(0.030 - eps, X_C)) / (2 * eps)
    assert abs(float(gz) - float(fd)) < 1e-5 * max(1.0, abs(float(fd)))
    assert float(gz) < 0.0   # thrust line above the COM: raising the COM toward it reduces resistance


def test_com_with_gas_moves_toward_the_cartridge():
    m, x, z = com_with_gas(0.048, 0.110, 0.028, 0.008, 0.180, 0.0305)
    assert abs(m - 0.056) < 1e-12 and 0.110 < x < 0.180 and 0.028 < z < 0.0305
