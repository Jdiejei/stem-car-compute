"""mass_report.json: every made part, the wheels, the halo and the cartridge, summed right."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "part1-simulation"))

import trimesh  # noqa: E402

import assembly  # noqa: E402


def test_masses_and_centre_add_up(tmp_path):
    body = trimesh.creation.box(bounds=[[50, -20, 5], [210, 20, 40]])
    wing = trimesh.creation.box(bounds=[[200, -26, 50], [216, 26, 53]])
    made = {}
    for k, m, g in (("machined_body", body, 30.0), ("printed_rwing", wing, 2.0)):
        f = tmp_path / f"{k}.stl"
        m.export(str(f))
        made[k] = {"file": str(f), "g": g}
    made["supports_team_cad"] = {"g": 9.9}                     # no file: not in the car as made
    asm = {"x_front_mm": 50.0, "W_mm": 130.0, "ballast_g": 1.0, "wheel_moi_kg_m2": 1e-7,
           "joints": {"manufactured": made},
           "wheel_design": {"front": {"R_mm": 14.0, "mass_g": 1.0}, "rear": {"R_mm": 14.0, "mass_g": 1.5}},
           "fixed_hardware_kwargs": {"halo_mass_kg": 2e-3, "halo_com": (0.12, 0.0, 0.03),
                                     "co2_cartridge_mass_kg": 0.02, "co2_cartridge_com": (0.23, 0.0, 0.031)}}
    r = assembly.write_mass_report(asm, tmp_path / "mass_report.json")
    assert json.loads((tmp_path / "mass_report.json").read_text()) == json.loads(json.dumps(r))
    # 30 + 2 + 2x1 + 2x1.5 + 2 halo + 1 ballast
    assert abs(r["mass_g_without_cartridge"] - 40.0) < 1e-9
    assert abs(r["mass_g_with_cartridge"] - 60.0) < 1e-9 and abs(r["car_weight_kg"] - 0.060) < 1e-12
    x = (30 * 130 + 2 * 208 + 2 * 50 + 3 * 180 + 2 * 120 + 1 * 120) / 40.0
    assert abs(r["com_mm_without_cartridge"][0] - x) < 1e-6
    assert abs(r["com_mm"][0] - (40 * x + 20 * 230) / 60) < 1e-6
    assert "supports_team_cad" not in r["parts"]
