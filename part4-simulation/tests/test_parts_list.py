"""The parts list the team makes the car from: one row per file, the right process and material."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "part1-simulation"))

import trimesh  # noqa: E402

import joints  # noqa: E402


def test_one_row_per_file_with_process_and_material(tmp_path):
    made = {}
    for name, rho, size in (("machined_body", joints.FOAM_G_CM3, 200.0), ("printed_rwing", 1.24, 20.0),
                            ("printed_support_front", 1.01, 30.0)):
        m = trimesh.creation.box(extents=[size, 10.0, 5.0])
        f = tmp_path / f"{name}.stl"
        m.export(str(f))
        cm3 = abs(m.volume) / 1e3
        made[name] = {"file": str(f), "cm3": cm3, "g": cm3 * rho, "closed": True, "pieces": 1}
    made["supports_team_cad"] = {"cm3": 1.0, "g": 1.01}                # no file: not listed
    joints.write_parts_list(made, tmp_path / "parts_list.csv")
    rows = {r["file"]: r for r in csv.DictReader(open(tmp_path / "parts_list.csv"))}
    assert set(rows) == {"machined_body.stl", "printed_rwing.stl", "printed_support_front.stl"}
    assert rows["machined_body.stl"]["material"] == "Model Block foam"
    assert rows["machined_body.stl"]["made by"].startswith("CNC mill")
    assert rows["printed_rwing.stl"]["material"] == "PLA"
    assert rows["printed_support_front.stl"]["material"] == "PA12"
    assert rows["printed_rwing.stl"]["length x width x height mm"] == "20.0 x 10.0 x 5.0"
