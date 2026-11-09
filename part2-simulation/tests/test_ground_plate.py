"""Ground plate (benchmarks): the floor upstream of a plate's leading edge is slip."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openfoam_case as oc


def test_dicts_select_lowerwall_faces_upstream_of_the_edge():
    topo, create = oc.ground_plate_dicts(-1.33)
    assert "patch lowerWall" in topo and "box (-1e6 -1e6 -1e6) (-1.33 1e6 1e6)" in topo
    assert "name groundUpstream" in create and "set upstreamFloor" in create


def test_every_field_gets_a_slip_or_zero_gradient_entry(tmp_path):
    cfg = oc.OpenFOAMRunConfig(reference_speed_mps=60.0, moving_ground=False)
    oc._write_initial_fields(tmp_path, cfg, 1.0)
    oc.add_upstream_ground_entries(tmp_path)
    oc.add_upstream_ground_entries(tmp_path)                 # idempotent
    for f in tmp_path.iterdir():
        text = f.read_text()
        assert text.count("groundUpstream") == 1, f.name
        want = "slip" if f.name == "U" else "zeroGradient"
        assert f"groundUpstream {{ type {want}; }}" in text
    assert "lowerWall   { type noSlip; }" in (tmp_path / "U").read_text()


def test_mesh_stage_splits_the_floor_with_fields_held_aside(tmp_path, monkeypatch):
    cfg = oc.OpenFOAMRunConfig(moving_ground=False, ground_plate_start_m=-1.33)
    oc._write_initial_fields(tmp_path / "0", cfg, 1.0)
    calls = []

    def fake_run(cmd, cwd, *a):
        calls.append((cmd, (cwd / "0").exists()))
        return ""

    monkeypatch.setattr(oc, "_run", fake_run)
    oc._mesh(tmp_path, cfg, "bashrc", 60)
    assert [c for c, _ in calls] == ["snappyHexMesh -overwrite", "topoSet", "createPatch -overwrite", "checkMesh"]
    assert dict(calls)["createPatch -overwrite"] is False      # 0/ was out of createPatch's reach
    assert "groundUpstream" in (tmp_path / "0" / "U").read_text()
    assert not (tmp_path / "0.held").exists()


def test_rolling_road_or_no_plate_leaves_the_floor_alone(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(oc, "_run", lambda cmd, *a: calls.append(cmd) or "")
    oc._mesh(tmp_path, oc.OpenFOAMRunConfig(ground_plate_start_m=-1.33), "bashrc", 60)   # rolling
    assert calls == ["snappyHexMesh -overwrite", "checkMesh"]
