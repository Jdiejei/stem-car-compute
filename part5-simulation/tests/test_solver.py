"""The solver's logic, without CFD: slopes, the mass balance, the gradient check, and
the rule that a chain only moves on a real, repeated gain."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

import pattern
import solver


@pytest.fixture()
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(solver, "STATE", tmp_path / "search" / "state.json")
    monkeypatch.setattr(solver, "BATCH", tmp_path / "search" / "batch.json")
    return tmp_path


def _surface_points():
    """Points on the start body's drawn surface."""
    import param_body as pb
    a, b = 30.0, 222.3
    xs, zs = np.linspace(a + 5, b - 5, 40), np.linspace(5, 45, 30)
    out = []
    for x in xs:
        for z in zs:
            ys = np.linspace(0.2, 33, 300)
            phi = pb.phi_mm(pb.BodyParams(), np.full_like(ys, x), ys, np.full_like(ys, z), a, b)
            i = np.argmin(np.abs(phi))
            if abs(phi[i]) < 0.2:
                out.append((x, ys[i], z))
    return np.array(out), a, b


def test_a_setting_moves_the_surface_the_way_it_should():
    P, a, b = _surface_points()
    import param_body as pb
    d = {"params": pb.BodyParams().as_dict(), "parts": {}}
    grad = np.ones(len(P))
    v = solver.surface_speed(d, "mode6", P, grad, a, b)
    # A positive mode grows the body, at its own centre and nowhere far away.
    c = pb.mode_centres(pb.BodyParams(), a, b)[6]
    r = np.linalg.norm(P - c, axis=1)
    assert v[r < 3.0].mean() > 0.5
    assert np.abs(v[r > 30.0]).max() < 0.02
    side = pb.mode_centres(pb.BodyParams(), a, b)[pb.N_FUSELAGE_MODES + 10]    # mid-pod, on its side
    assert side[1] > 20.0                       # the sidepod modes are out on the sidepods


def test_slopes_match_the_sensitivity_they_are_built_from():
    """With a sensitivity of 1 everywhere, a setting's slope is the total surface move."""
    P, a, b = _surface_points()
    import param_body as pb
    d = {"params": pb.BodyParams().as_dict(), "parts": {}}
    s = np.ones(len(P))
    out = solver.body_slopes(d, 0.0, P, s, a, b)
    assert out["_skin"]["dD"] > 0 and out["_skin"]["dV"] > 0
    assert out["mode6"]["dD"] > 0 and out["mode6"]["dV"] > 0
    # Growing the body in a place with no sensitivity costs drag through the skin only.
    assert out["mode6"]["speed"] > 0


def test_mass_balance_prices_volume_at_the_skin():
    slopes = {"_skin": {"dD": 10.0, "dV": 1000.0, "speed": 1.0},
              "a": {"dD": 1.0, "dV": 100.0, "speed": 1.0},     # exactly a bit of skin: worth nothing
              "b": {"dD": 0.0, "dV": -100.0, "speed": 1.0}}    # removes volume, drag-free: grows the skin
    g = solver.constant_mass(slopes)
    assert abs(g["a"]) < 1e-12
    assert g["b"] == pytest.approx(1.0)


def test_a_step_goes_downhill_within_bounds_and_scales():
    import param_body as pb
    d = {"params": pb.BodyParams().as_dict(), "parts": {}}
    g = {"mode6": 1.0, "mode7": -1.0}
    speeds = {"mode6": 1.0, "mode7": 1.0}
    small, big = solver.plan_step(d, g, speeds, 0.5), solver.plan_step(d, g, speeds, 4.0)
    assert pattern.get(small, "mode6") < 0 < pattern.get(small, "mode7")
    assert abs(pattern.get(big, "mode6")) == pytest.approx(8 * abs(pattern.get(small, "mode6")))
    huge = solver.plan_step(d, g, speeds, 1000.0)
    assert pattern.get(huge, "mode6") == pattern.bounds("mode6")[0]


def test_gradient_check_judges_sign_and_correlation():
    names = solver.check_settings()
    rng = np.random.default_rng(0)
    truth = {n: float(v) for n, v in zip(names, rng.normal(size=len(names)))}
    assert solver.judge_check(truth, dict(truth))["passed"]
    flipped = solver.judge_check(truth, {k: -v for k, v in truth.items()})
    assert flipped["passed"] and flipped["sign"] == -1.0
    noise = {n: float(v) for n, v in zip(names, rng.normal(size=len(names)))}
    assert not solver.judge_check(truth, noise)["passed"]      # unrelated slopes do not pass


def _write_results(root, phase, round_, rows):
    root.mkdir(exist_ok=True)
    for i, r in enumerate(rows):
        (root / f"car_{round_}_{phase}_{i}.json").write_text(json.dumps(dict(r, round=round_, phase=phase)))


def test_a_chain_moves_only_on_a_gain_above_the_noise(tmp_state):
    solver.init(1)
    state = json.loads(solver.STATE.read_text())
    B = json.loads(solver.BATCH.read_text())
    rows = [dict(c, ok=True, T_s=1.600, skin=1.0) for c in B["cases"]]
    _write_results(tmp_state / "r0", "start", 0, rows)
    assert "check" in solver.advance(tmp_state / "r0")
    state = json.loads(solver.STATE.read_text())
    assert state["phase"] == "check_adjoint" and state["sign"] is None   # will not trust slopes yet

    # Skip to a passed check, then a step that only ties.
    state.update(phase="adjoint", sign=1.0)
    solver._save(state, [])
    sl = {k: {"dD": 1.0, "dV": 0.0, "speed": 1.0} for k in ("mode6", "mode7")}
    sl["_skin"] = {"dD": 1.0, "dV": 1000.0, "speed": 1.0}
    res = tmp_state / "r1"
    res.mkdir()
    (res / "slopes_0_0.json").write_text(json.dumps({"chain": 0, "round": 0, "phase": "adjoint", "slopes": sl}))
    solver.advance(res)
    B = json.loads(solver.BATCH.read_text())
    # The start car sits at the low end of W and x_front, so those only go up: 4 layout moves.
    assert B["phase"] == "steps" and len(B["cases"]) == 2 + len(solver.STEPS_MM) + 4
    assert {c["tag"].split("=")[0] for c in B["cases"]} >= {"step W", "step x_front", "step d_halo"}

    tie = [dict(c, ok=True, T_s=1.5995 if c["tag"].startswith("step") else 1.600, skin=1.0) for c in B["cases"]]
    _write_results(tmp_state / "r2", "steps", 0, tie)
    solver.advance(tmp_state / "r2")
    c = json.loads(solver.STATE.read_text())["chains"][0]
    assert c["history"][-1]["accepted"] is None and c["scale"] == 0.5       # 0.5 ms is inside the noise


def test_layout_survives_every_kind_of_setting_change():
    import param_body as pb
    d = {"params": pb.BodyParams().as_dict(), "parts": {}, "layout": {"W": 130.0}}
    assert pattern.get(d, "W") == 130.0 and pattern.get(d, "x_front") == pattern.LAYOUT_START["x_front"]
    for name, v in (("mode6", 1.0), ("fw.aoa_deg", 3.0), ("d_halo", 50.0)):
        d = pattern.put(d, name, v)
        assert pattern.get(d, "W") == 130.0 and pattern.get(d, name) == v
    case = solver._case(0, 0, "x", d)
    assert solver._layout_args(case["layout"]) == ["--W", "130.0", "--d-halo", "50.0"]


def test_a_layout_step_that_wins_is_kept(tmp_state):
    solver.init(1)
    state = json.loads(solver.STATE.read_text())
    state.update(phase="adjoint", sign=1.0)
    state["chains"][0].update(T=1.6, noise=5e-4)
    solver._save(state, [])
    res = tmp_state / "r1"
    res.mkdir()
    solver.advance(res)                         # no slopes this time: the layout moves still run
    B = json.loads(solver.BATCH.read_text())
    assert B["phase"] == "steps"
    rows = [dict(c, ok=True, skin=1.0, T_s=1.59 if c["tag"].startswith("step W") else 1.6) for c in B["cases"]]
    _write_results(tmp_state / "r2", "steps", 0, rows)
    solver.advance(tmp_state / "r2")
    c = json.loads(solver.STATE.read_text())["chains"][0]
    assert c["car"]["layout"]["W"] == pattern.LAYOUT_START["W"] + 2.0 and c["T"] == 1.59


def test_the_report_refuses_to_claim_a_proof(tmp_state):
    solver.init(1)
    state = json.loads(solver.STATE.read_text())
    state["chains"][0].update(T=1.55, noise=5e-4, stopped="peak: no step beat the noise")
    solver._save(state, [])
    text = solver.report()
    assert "Not established" in text and "global maximum" in text
