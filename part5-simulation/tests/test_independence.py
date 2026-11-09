"""The referee is independent of the cutter (Part 4 brief, Step 3):
1. legality.py and rules_constants.py import nothing from Part 1 (no masks, no body
   builder, no rule geometry);
2. the rule geometry the referee typed in from the regulations agrees with Part 1's.
   A mismatch fails here, and means one of the two read a drawing wrongly."""
import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PART5 = HERE.parent
PART1 = PART5.parent / "part1-simulation"
sys.path.insert(0, str(PART5))
sys.path.insert(0, str(PART1))

import rules_constants as rc  # noqa: E402


def _imports(path: Path) -> set:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_the_referee_imports_nothing_from_part_1():
    part1 = {p.stem for p in PART1.glob("*.py")} | {p.name for p in PART1.iterdir() if p.is_dir()}
    assert {"geometry_contract", "unified_phi", "param_body"} <= part1   # the check can see them
    for f in ("legality.py", "rules_constants.py"):
        bad = _imports(PART5 / f) & part1
        assert not bad, f"{f} imports Part 1: {sorted(bad)}"


def test_the_referees_rule_geometry_matches_part_1s():
    import geometry_contract as gc
    import halo_pocket as hp
    import virtual_cargo as vc
    import wheel_visibility_zones as wz
    pairs = {
        "block length": (rc.BLOCK_LENGTH_MM, gc.MODEL_BLOCK_LENGTH_MM),
        "block width": (rc.BLOCK_WIDTH_MM, gc.MODEL_BLOCK_WIDTH_MM),
        "block height": (rc.BLOCK_HEIGHT_MM, gc.MODEL_BLOCK_HEIGHT_MM),
        "bore diameter": (rc.BLOCK_BORE_DIA_MM, gc.MODEL_BLOCK_BORE_DIA_MM),
        "bore depth": (rc.BLOCK_BORE_DEPTH_MM, gc.MODEL_BLOCK_BORE_DEPTH_MM),
        "bore above bottom": (rc.BLOCK_BORE_ABOVE_BOTTOM_MM, gc.MODEL_BLOCK_BORE_ABOVE_BOTTOM_MM),
        "slot width": (rc.BLOCK_SLOT_WIDTH_MM, gc.MODEL_BLOCK_SLOT_WIDTH_MM),
        "slot depth": (rc.BLOCK_SLOT_DEPTH_MM, gc.MODEL_BLOCK_SLOT_DEPTH_MM),
        "Ref A offset": (rc.REF_A_AHEAD_OF_FRONT_AXLE_MM, gc.D_HALO_REF_A_OFFSET_MM),
        "cargo length": (rc.CARGO_LENGTH_MM, vc.CARGO_LENGTH_MM),
        "cargo wide end": (rc.CARGO_WIDE_MM, vc.CARGO_WIDE_WIDTH_MM),
        "cargo narrow end": (rc.CARGO_NARROW_MM, vc.CARGO_NARROW_WIDTH_MM),
        "cargo height": (rc.CARGO_HEIGHT_MM, vc.CARGO_HEIGHT_MM),
        "T7.9 width": (rc.T79_WIDTH_Y_MM, wz.T79_WIDTH_Y_MM),
        "T7.9 height": (rc.T79_HEIGHT_MM, wz.T79_ZONE_HEIGHT_MM),
        "T7.9.1 depth": (rc.T79_1_DEPTH_MM, wz.T79_RECT_DEPTH_MM),
        "T7.9.4 depth": (rc.T79_4_DEPTH_MM, wz.T79_RECT_DEPTH_MM),
        "T7.9.2 near": (rc.T79_2_NEAR_MM, wz.T79_FRONT_NEAR_X_MM),
        "T7.9.2 angle": (rc.T79_2_ANGLE_DEG, wz.T79_FRONT_ANGLE_DEG),
        "T7.9.3 near": (rc.T79_3_NEAR_MM, wz.T79_REAR_NEAR_X_MM),
        "T7.9.3 angle": (rc.T79_3_ANGLE_DEG, wz.T79_REAR_ANGLE_DEG),
        "halo floor": (rc.HALO_POCKET_FLOOR_Z_MM, gc.HALO_MIN_Z_M * 1e3),
        "halo pocket length": (rc.HALO_POCKET_LENGTH_MM, hp.HALO_POCKET_LENGTH_MM),
        "halo pocket width": (rc.HALO_POCKET_WIDTH_MM, hp.HALO_POCKET_WIDTH_MM),
        "halo pocket depth": (rc.HALO_POCKET_DEPTH_MM, hp.HALO_POCKET_DEPTH_MM),
        "ballast width": (rc.BALLAST_WIDTH_MM, hp.BALLAST_SLOT_WIDTH_MM),
        "ballast length": (rc.BALLAST_LENGTH_MM, hp.BALLAST_SLOT_LENGTH_MM),
        "ballast depth": (rc.BALLAST_DEPTH_MM, hp.BALLAST_DEPTH_MM),
        "ballast centre": (rc.BALLAST_CENTRE_FROM_POCKET_FRONT_MM, hp.BALLAST_CENTRE_FROM_POCKET_FRONT_MM),
    }
    wrong = {k: v for k, v in pairs.items() if abs(v[0] - v[1]) > 1e-9}
    assert not wrong, f"referee vs Part 1 (referee, Part 1): {wrong}"


def test_the_referees_zones_match_part_1s_on_a_car():
    import legality
    import wheel_visibility_zones as wz
    W, xf, R, fy, ry = 130.0, 50.0, 14.1, 23.25, 16.25
    mine = legality.zone_polygons_mm({"front": (xf, R, fy), "rear": (xf + W, R, ry)})
    theirs = wz.zone_polygons_mm(W, xf, R, fy, ry)
    for k in theirs:
        a = sorted(tuple(round(float(c), 6) for c in p) for p in mine[k])
        b = sorted(tuple(round(float(c), 6) for c in p) for p in theirs[k])
        assert a == b, (k, a, b)
