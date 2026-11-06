"""Final meshes and the nose mass rollup."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _p in ("part1-simulation", "part2-simulation"):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / _p))

import numpy as np
import trimesh


def test_remesh_gives_even_triangles_on_the_same_closed_solid(tmp_path):
    import mesh_fairing
    box = trimesh.creation.box(extents=(100.0, 20.0, 10.0))       # 12 very long triangles
    p = tmp_path / "part.stl"
    box.export(str(p))
    rep = mesh_fairing.remesh_file(p, 2.0)
    out = trimesh.load(str(p), force="mesh")
    assert rep["remeshed"] and rep["closed"] and rep["pieces"] == 1 and out.is_watertight
    assert rep["max_edge_mm"] < 8.0 and rep["faces"] > 1000
    assert abs(abs(out.volume) - abs(box.volume)) < 0.002 * abs(box.volume)
    assert np.allclose(out.bounds, box.bounds, atol=0.06)


def test_solid_nose_weighs_its_volume():
    import nose as ns
    cone = trimesh.creation.cone(radius=0.012, height=0.03)
    solid = ns.NoseCone(wall_mm=99.0, material="PA12")
    m, _ = ns.nose_mass_com(solid, cone)
    assert abs(m - abs(cone.volume) * 1010.0) < 1e-9              # PA12, 1.01 g/cm3
    shell, _ = ns.nose_mass_com(ns.NoseCone(wall_mm=0.8, material="PA12"), cone)
    assert shell < m
