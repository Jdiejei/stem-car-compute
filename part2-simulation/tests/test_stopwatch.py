"""stopwatch.py without OpenFOAM: the CFD call is replaced by fixed forces."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cfd_wrapper
import stopwatch as sw
from physics_contract import HalfCarQuantities

TRI = "facet normal 0 0 1\n outer loop\n vertex 0 0 0\n vertex 1 0 0\n vertex 0 1 0\n endloop\nendfacet\n"


def _car(d: Path, D_half=0.06, L_half=-0.01, converged=True, weight=0.0563):
    d.mkdir()
    (d / "car_half.stl").write_text(f"solid car\n{TRI}endsolid car\nsolid wheelF\n{TRI}{TRI}endsolid wheelF\n")
    (d / "mass_report.json").write_text(json.dumps({"car_weight_kg": weight, "com_mm": [80, 0, 30]}))
    (d / "assembly.json").write_text(json.dumps({"extra_surfaces": [
        {"name": "wheelF", "stl": "wheelF.stl",
         "rotating": {"origin": [0.05, 0.03, 0.014], "axis": [0, 1, 0], "omega": 1415.4}}]}))
    return d, (D_half, L_half, converged)


@pytest.fixture
def fake_cfd(monkeypatch):
    calls = []
    forces = {}

    def run(stl, **kw):
        calls.append((stl, kw))
        D, L, conv = forces[Path(stl).parent.name]
        health = cfd_wrapper.CFDHealthReport(converged=conv, residual_final=1e-3, negative_volume_cells=0,
                                             y_plus_min=1.0, y_plus_max=30.0, force_oscillation=0.01,
                                             patch_forces={"car": {"D_half_N": D, "L_half_N": L}})
        return HalfCarQuantities(D20=D, L=L, A=1e-3, pitching_moment_half=0.0), health

    monkeypatch.setattr(cfd_wrapper, "run_half_car_cfd", run)
    monkeypatch.setattr(sw, "frozen_ref", lambda: Path("/frozen_ref"))
    return calls, forces


def test_cars_start_from_the_frozen_reference(tmp_path, fake_cfd):
    calls, forces = fake_cfd
    d, forces["a"] = _car(tmp_path / "a")
    rec = sw.time_car(d)
    kw = calls[0][1]
    assert kw["morph_from"] == kw["warm_from"] == str(Path("/frozen_ref"))
    assert rec["race_time_sd_s"] == sw.NOISE_FROZEN_S and rec["reference_case"] == sw.FROZEN_REF
    assert rec["state_uncertainty_s"] == sw.STATE_UNCERTAINTY_S
    rec2 = sw.time_car(d, frozen=False)
    assert "morph_from" not in calls[1][1] and rec2["race_time_sd_s"] == sw.NOISE_S


def test_body_stl_keeps_only_the_car_solid(tmp_path):
    d, _ = _car(tmp_path / "a")
    out = sw.body_stl(d / "car_half.stl", tmp_path / "b.stl").read_text()
    assert out.count("facet normal") == 1 and "wheelF" not in out


def test_stopwatch_json_has_the_contract_fields(tmp_path, fake_cfd):
    calls, forces = fake_cfd
    d, f = _car(tmp_path / "a")
    forces["a"] = f
    rec = sw.time_car(d)
    on_disk = json.loads((d / "stopwatch.json").read_text())
    assert on_disk == json.loads(json.dumps(rec))
    for k in ("D20_N", "L20_N", "parts", "race_time_s", "race_time_sd_s", "dT_d", "mesh",
              "converged", "residual_p", "force_osc_frac", "seconds", "model_inputs"):
        assert k in rec
    assert rec["D20_N"] == pytest.approx(0.12) and rec["L20_N"] == pytest.approx(-0.02)
    assert set(rec["dT_d"]) == set(sw.DT_NAMES)
    mi = rec["model_inputs"]
    assert mi["thrust_csv"] == "thrust_measured_beta.csv" and mi["time_coefficient"] == 0.802
    assert rec["race_time_s"] == pytest.approx(0.802 * mi["race_time_uncalibrated_s"])
    assert 0.4 < rec["race_time_s"] < 1.8
    # slower with more drag and more mass, by amounts of the right order
    assert 0.05 < rec["dT_d"]["drag_20_n"] < 0.7 and 2 < rec["dT_d"]["car_weight_kg"] < 25
    assert rec["model_inputs"]["placeholders"][:3] == ["mu", "wheel_moi_kg_m2", "mu_guide"]
    # search mesh by default, wheel from assembly.json resolved against the folder
    kw = calls[0][1]
    assert kw["resolution"] == "medium" and kw["max_iterations"] == 1000
    assert kw["extra_surfaces"][0]["stl"] == str(d / "wheelF.stl")
    assert kw["extra_surfaces"][0]["rotating"]["omega"] == 1415.4


def test_compare_sign_and_sd(tmp_path, fake_cfd):
    _, forces = fake_cfd
    a, forces["a"] = _car(tmp_path / "a", D_half=0.060)
    b, forces["b"] = _car(tmp_path / "b", D_half=0.061)       # 2 mN more full-car drag
    dT, sd = sw.compare(a, b, noise_s=3e-4)
    ra = json.loads((a / "stopwatch.json").read_text())
    assert dT == pytest.approx(ra["dT_d"]["drag_20_n"] * 0.002, rel=0.05)   # 2 mN x the slope
    assert sd == pytest.approx(3e-4 * math.sqrt(2))


def test_compare_refuses_an_unconverged_car(tmp_path, fake_cfd):
    _, forces = fake_cfd
    a, forces["a"] = _car(tmp_path / "a")
    b, forces["b"] = _car(tmp_path / "b", converged=False)
    with pytest.raises(sw.StopwatchError):
        sw.compare(a, b)
