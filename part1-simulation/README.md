<p align="center"><img src="assets/banner.png" alt="part1-simulation" width="100%"></p>

> The car body as one precise 3D shape.

> **Status 2026-11-09:** the plan is carving from the block. How to build and test this part, with its rules and pass marks: [`BUILD_SPEC.md`](BUILD_SPEC.md). Old work is kept read-only as `archive/*` tags.

| | |
|---|---|
| **What it is** | The milled body of a STEM Racing car as one labelled shape with every rule applied. |
| **Source** | Private |
| **Public overview** | https://github.com/shawshanker18/stem-racing-overview |

**The STEM Racing set**

| Part | Repository |
|---|---|
| 1 | [part1-simulation](https://github.com/shawshanker18/part1-simulation) |
| 2 | [part2-simulation](https://github.com/shawshanker18/part2-simulation) |
| 3 | [part3-simulation](https://github.com/shawshanker18/part3-simulation) |
| 4 | [part4-simulation](https://github.com/shawshanker18/part4-simulation) |
| 5 | [part5-simulation](https://github.com/shawshanker18/part5-simulation) |

---

The milled body of a STEM Racing car as ONE labelled level-set field on a 1 mm
grid, with every rule that shapes it applied as a hard mask. The plan (2026-11-08) is
to carve this field from the full legal block, one small legal cut at a time; the
lofted parametric body still builds and can be used as a start shape.

| module | what |
|---|---|
| `cutter.py` | **the cut API other parts call**: `start_block(layout)`, `cut(geom, dT_dn, half_mesh, step_m)` returning a new field or a named refusal, `save_field` / `load_field` (see below) |
| `geometry_contract.py` | every dimension and density the parts share (grid spacing, wheel radius, cargo, densities) |
| `unified_phi.py` | the one field: the start block with the rule masks (T4.2 cargo, T5.5 cartridge wall, halo pocket, ballast area, T7.9 wheel zones, model block, plus the build rules: T8.5.1 cap, nose stub, halo floor column, pocket bridge), symmetry, pinch closing, mass from sub-cell volume fractions, half-surface extraction |
| `phi_updater.py` | the carving step: Hamilton-Jacobi update, reinitialisation, velocity extension, `apply_adjoint_to_unified` (rules, symmetry, machinability and pinch closing after every step) |
| `param_body.py` | the lofted body (8-station superellipse loft, sidepods, tunnel, 56 sculpt modes) AND `build(..., field_mm=...)`, which finishes any carved field: cut at Ref A, joins, islands dropped, machinable, sized by a uniform skin offset to the mass target |
| `machining.py` | the team's process on the grid (team spec 2026-09-27): 6.25 mm ball end from top, bottom, left and right; every concave corner gets the cutter radius, rule-required air is grown until the ball can reach it |
| `fixed_hardware.py`, `hardware_geometry.py`, `halo_pocket.py`, `virtual_cargo.py`, `wheel_visibility_zones.py`, `bounding_volumes.py` | the fixed parts (cartridge, halo, wheels, cargo) and the masks they impose; `hardware_cad/` holds the team's STLs |
| `surface_extraction.py`, `mass_com_calculator.py` | marching-cubes surfaces (retried with a larger nudge if the half body comes out open) and their quality checks, mass and centre of mass |
| `ballast.py` | the T3.6 target (48.2 g today) and the ballast rules; the team adds no ballast, the body volume carries the mass |
| `coarse.py` | run the pipeline at another grid spacing |

## The cutter

```python
import cutter
layout = {"W": 120.3, "x_front": 46.0, "d_halo": 43.72}
g = cutter.start_block(layout, spacing_mm=1.0)          # the full legal block, every rule applied
g2, rep = cutter.cut(g, dT_dn, half_mesh, step_m=5e-4,  # one carving step
                     max_substeps=6, trust_radius_m=1e-3,
                     mass_report=mr, dT_dscalars={"dT_dmass": ..., "dT_dh_com": ..., "dT_dx_com": ...})
cutter.save_field(g2, "carved_phi.npy")                 # float32 metres, this layout's grid
g3 = cutter.load_field(layout, "carved_phi.npy")        # carry on in another job
```

- `dT_dn`: Part 3's sensitivity on the vertices of `half_mesh` (s per m of outward move per m²;
  positive = growing there makes the car slower). Pass it as it is: the cutter negates it.
- A cut never changes `g`. It redistances, moves the surface in up to `max_substeps` steps
  (stopping when the 90th-percentile move reaches `trust_radius_m`), and after each one
  re-applies forced air and solid, symmetry and drops loose pieces; then makes the body
  reachable by the ball end, removes strips thinner than a cell and closes pinches.
- `rep["status"]` is `"ok"` or `"refused"` with `rep["reason"]`: `bad_input` (sensitivity not
  one finite value per vertex), `pinned_detached`, `no_motion`, `rule_air_violated`,
  `rule_solid_violated`. A refused cut returns `g` itself. `rep` also carries `substeps`,
  `dt`, `disp_median_m`, `disp_p90_m`, `machinability_filled`, `thin_cells`, `pinch_cells`.
- Mass sizing and the finished files: `param_body.build(W, x_front, d_halo, BodyParams(),
  target_body_kg=..., field_mm=g2.phi.grid * 1e3)`.

Not proven yet for carving: the full carve stress test, mass sizing on carved shapes,
the grid-size check and repeatability. See `BUILD_SPEC.md`. The rules are the 2026-27
regulations PDF in this repo (same text as 2025-26).

```bash
pip install -r requirements.txt
python -m pytest tests -q
```
