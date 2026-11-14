"""Part 4 lab: why remesh_file found no clean size for three front assemblies
(50135, 50250, 50323: 68-82 % of faces under 5 deg after its fallback)."""
import glob
import subprocess
import os
import sys
from pathlib import Path

import numpy as np
import pymeshlab as ml
import trimesh

sys.path.insert(0, str(Path.cwd().parent / "part4-simulation"))
from mesh_fairing import _sliver_pct

RUNS = {"50135": 43605280301, "50250": 43605313729, "50323": 43605345488}
for car, run in RUNS.items():
    d = Path("../out/files") / car
    subprocess.run(["gh", "run", "download", str(run), "-R", os.environ["GITHUB_REPOSITORY"], "-D", str(d)], check=False)
    f = glob.glob(str(d / "**" / "printed_front_assembly.stl"), recursive=True)[0]
    before = trimesh.load(f, force="mesh")
    print(f"CAR {car}: faces {len(before.faces)} volume {before.is_volume} pieces {len(before.split(only_watertight=False))} "
          f"cm3 {abs(before.volume) / 1e3:.4f} slivers {_sliver_pct(before):.2f} max_edge {before.edges_unique_length.max():.2f}", flush=True)
    for target in (0.4, 0.5, 0.32, 0.24, 0.64):
        ms = ml.MeshSet()
        ms.add_mesh(ml.Mesh(before.vertices, before.faces))
        ms.apply_filter("meshing_isotropic_explicit_remeshing", iterations=15, targetlen=ml.PureValue(target),
                        featuredeg=25.0, adaptive=False, checksurfdist=True, maxsurfdist=ml.PureValue(0.05))
        o = ms.current_mesh()
        a = trimesh.Trimesh(o.vertex_matrix(), o.face_matrix(), process=False)
        a.merge_vertices()
        if a.is_watertight and not a.is_winding_consistent:
            trimesh.repair.fix_normals(a)
        print(f"  target {target}: watertight {a.is_watertight} winding {a.is_winding_consistent} volume {a.is_volume} "
              f"pieces {len(a.split(only_watertight=False))} dvol_pct {100 * (abs(a.volume) / abs(before.volume) - 1):.3f} "
              f"slivers {_sliver_pct(a):.2f} max_edge {a.edges_unique_length.max():.2f}", flush=True)
        if not a.is_watertight:
            e = a.edges_sorted
            _, n = np.unique(e, axis=0, return_counts=True)
            print(f"    open/bad edges {(n != 2).sum()}", flush=True)
