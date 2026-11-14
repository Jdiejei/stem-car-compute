"""A carving-loop timing must never run on the medium (or coarse) mesh, and no timing may pick a mesh by default."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "part3-simulation" / "checks"))
sys.path.insert(0, str(ROOT / "part5-simulation"))


def _cm(monkeypatch, res, loop):
    monkeypatch.setenv("P3_RES", res)
    if loop:
        monkeypatch.setenv("P5_LOOP", "1")
    else:
        monkeypatch.delenv("P5_LOOP", raising=False)
    import car_modes
    return importlib.reload(car_modes)


@pytest.mark.parametrize("res", ["", "coarse", "medium"])
def test_loop_timing_refuses_low_mesh(monkeypatch, res):
    with pytest.raises(SystemExit):
        _cm(monkeypatch, res, True).mesh()


@pytest.mark.parametrize("res", ["fine", "resolved"])
def test_loop_timing_allows_high_mesh(monkeypatch, res):
    assert _cm(monkeypatch, res, True).mesh() == res


def test_no_default_mesh(monkeypatch):
    with pytest.raises(SystemExit):
        _cm(monkeypatch, "", False).mesh()


@pytest.mark.parametrize("res", ["", "medium"])
def test_solver_eval_refuses_low_mesh(monkeypatch, tmp_path, res):
    monkeypatch.setenv("P5_RES", res)
    import solver
    monkeypatch.setattr(solver, "BATCH", tmp_path / "b.json")
    (tmp_path / "b.json").write_text('{"cases": [{"id": 0, "params": {}}]}')
    with pytest.raises(SystemExit):
        solver.evaluate(0, tmp_path)
