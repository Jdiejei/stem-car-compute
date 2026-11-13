"""Draw the real CFD cells of one meshed case: symmetry plane (side view of the cells
around the car) and the car surface faces. Usage: mesh_view.py <vtk_dir> <label> <outdir>"""
import sys, glob, os, numpy as np, meshio, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
vdir, label, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
def polys(path, drop):
    m = meshio.read(path); P = m.points * 1000.0; res = []
    for cb in m.cells:
        for c in cb.data: res.append(np.delete(P[c], drop, axis=1))
    return res, P
sym = [f for f in glob.glob(vdir + "/**/*.vtk", recursive=True) if "symmetry" in os.path.basename(os.path.dirname(f)) or "symmetry" in os.path.basename(f)]
car = [f for f in glob.glob(vdir + "/**/*.vtk", recursive=True) if os.path.basename(os.path.dirname(f)) == "car" or os.path.basename(f).startswith("car")]
print("files", sym, car)
cp, cP = polys(car[0], 1)            # car faces in (x, z)
x0, x1 = cP[:, 0].min(), cP[:, 0].max(); z0, z1 = cP[:, 2].min(), cP[:, 2].max()
sp, _ = polys(sym[0], 1)             # symmetry plane cells in (x, z)
for name, (xa, xb, za, zb) in {"whole": (x0 - 40, x1 + 160, z0 - 10, z1 + 50),
                               "nose": (x0 - 10, x0 + 40, z0 - 5, z1 + 5),
                               "tail": (x1 - 40, x1 + 40, z0 - 5, z1 + 10)}.items():
    keep = [p for p in sp if p[:, 0].max() > xa and p[:, 0].min() < xb and p[:, 1].max() > za and p[:, 1].min() < zb]
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.add_collection(PolyCollection(keep, facecolors="none", edgecolors="k", linewidths=0.15))
    ax.add_collection(PolyCollection(cp, facecolors="#e4572e", edgecolors="none", alpha=0.35))
    ax.set_xlim(xa, xb); ax.set_ylim(za, zb); ax.set_aspect("equal")
    ax.set_title(f"{label}: CFD cells on the centre plane ({name}), mm; {len(keep)} cells in view")
    fig.savefig(f"{out}/{label}_{name}.png", dpi=170, bbox_inches="tight"); plt.close(fig)
cp3, cP3 = polys(car[0], 2)          # car surface faces, top view (x, y)
fig, ax = plt.subplots(figsize=(16, 6))
ax.add_collection(PolyCollection(cp3, facecolors="#d9dde3", edgecolors="k", linewidths=0.1))
ax.set_xlim(cP3[:, 0].min() - 5, cP3[:, 0].max() + 5); ax.set_ylim(cP3[:, 1].min() - 5, cP3[:, 1].max() + 5); ax.set_aspect("equal")
ax.set_title(f"{label}: car surface faces, top view ({len(cp3)} faces)")
fig.savefig(f"{out}/{label}_surface_top.png", dpi=170, bbox_inches="tight"); plt.close(fig)
