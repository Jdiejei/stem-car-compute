"""Part 4 lab: why remesh_file found no clean size for three front assemblies
(50135, 50250, 50323), where the one bad edge is, and whether repairing it gives a
clean closed solid without loosening any check."""
import glob
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pymeshlab as ml
import trimesh

sys.path.insert(0, str(Path.cwd().parent / "part4-simulation"))
from mesh_fairing import _sliver_pct

RUNS = {"50135": 43605280301, "50250": 43605313729, "50323": 43605345488}


def tm_of(ms):
    o = ms.current_mesh()
    a = trimesh.Trimesh(o.vertex_matrix(), o.face_matrix(), process=False)
    a.merge_vertices()
    if a.is_watertight and not a.is_winding_consistent:
        trimesh.repair.fix_normals(a)
    return a


def bad_edges(a):
    e = a.edges_sorted
    u, n = np.unique(e, axis=0, return_counts=True)
    return u[n != 2], n[n != 2]


for car, run in RUNS.items():
    d = Path("../out/files") / car
    subprocess.run(["gh", "run", "download", str(run), "-R", os.environ["GITHUB_REPOSITORY"], "-D", str(d)], check=False)
    f = glob.glob(str(d / "**" / "printed_front_assembly.stl"), recursive=True)[0]
    before = trimesh.load(f, force="mesh")
    print(f"CAR {car}: faces {len(before.faces)} cm3 {abs(before.volume) / 1e3:.4f} slivers {_sliver_pct(before):.2f}", flush=True)
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(before.vertices, before.faces))
    ms.apply_filter("meshing_isotropic_explicit_remeshing", iterations=15, targetlen=ml.PureValue(0.4),
                    featuredeg=25.0, adaptive=False, checksurfdist=True, maxsurfdist=ml.PureValue(0.05))
    a = tm_of(ms)
    u, n = bad_edges(a)
    for (i, j), k in zip(u, n):
        print(f"  bad edge faces {k} at mm {np.round(a.vertices[i], 3).tolist()} - {np.round(a.vertices[j], 3).tolist()}", flush=True)
    # where is that spot on the input: the nearest input faces' angles and the input's own min feature
    if len(u):
        p = a.vertices[u[0][0]]
        dist = np.linalg.norm(before.triangles_center - p, axis=1)
        near = np.argsort(dist)[:30]
        print(f"  input near it: min face angle deg {np.degrees(before.face_angles[near].min()):.3f}, "
              f"min edge mm {before.edges_unique_length.min():.5f}", flush=True)
    for name, steps in (("non-manifold edges", [("meshing_repair_non_manifold_edges", {})]),
                        ("nm edges + nm vertices", [("meshing_repair_non_manifold_edges", {}),
                                                    ("meshing_repair_non_manifold_vertices", {})]),
                        ("nm edges + close holes", [("meshing_repair_non_manifold_edges", {}),
                                                    ("meshing_close_holes", {"maxholesize": 30})])):
        m2 = ml.MeshSet()
        o = ms.current_mesh()
        m2.add_mesh(ml.Mesh(o.vertex_matrix(), o.face_matrix()))
        try:
            for flt, kw in steps:
                m2.apply_filter(flt, **kw)
            b = tm_of(m2)
            print(f"  repair [{name}]: watertight {b.is_watertight} volume {b.is_volume} pieces "
                  f"{len(b.split(only_watertight=False))} dvol_pct {100 * (abs(b.volume) / abs(before.volume) - 1):.3f} "
                  f"slivers {_sliver_pct(b):.2f} hausdorff_max_mm "
                  f"{float(np.max(trimesh.proximity.closest_point(before, b.vertices[::7])[1])):.4f}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  repair [{name}]: failed {type(exc).__name__}: {exc}", flush=True)
