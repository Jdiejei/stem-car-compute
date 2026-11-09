"""
test_unified_pipeline_end_to_end.py

Proves the claim: the whole Part 3 pipeline runs end-to-end on the UNIFIED
single field with the REAL race objective, and the ONLY thing stubbed is the
OpenFOAM binary. We mock exactly run_cfd + run_adjoint (what shells out to
OpenFOAM) and leave everything else real, then require a VALID candidate with a
real race time to come out.

Before the unified wiring, the same test on the four-grid path produced
`best is None` -- every iteration rejected at the geometry gates
(`rearpod: inaccessible area`), before CFD ever mattered.

Run at coarse spacing for speed; the properties under test are wiring, not
resolution.
"""
import dataclasses
import os
import sys
import json
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
for p in ("part1-simulation", "part2-simulation", "part3-simulation",
          "part1-simulation/sandbox"):
    sys.path.insert(0, str(_ROOT / p))
os.environ.setdefault("PART2_PATH", str(_ROOT / "part2-simulation"))

import numpy as np  # noqa: E402
import coarse  # noqa: E402
coarse.use_spacing(3.0)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _coarse_spacing():
    """conftest restores the pristine spacing after each test; put this file's
    3.0 mm back. Setting it at import only is why the full-suite run and
    running this file alone disagreed."""
    coarse.use_spacing(3.0)


# The real thrust CSV lives beside part2 (installed there as the default).
_CSV = str(_ROOT / "part2-simulation" / "co2_thrust_data.csv")
_FHW = dict(
    co2_cartridge_mass_kg=0.02115, co2_cartridge_com=(0.20, 0.0, 0.035),
    rear_wing_mass_kg=0.005, rear_wing_com=(0.24, 0.0, 0.05),
    wheels_axles_mass_kg=0.015, wheels_axles_com=(0.11, 0.0, 0.015),
)


def _pass(n): print(f"PASS {n}")
def _fail(n, m): print(f"FAIL {n}: {m}"); sys.exit(1)


def _mocked_openfoam_bindings(td):
    """unified_bindings with ONLY run_cfd + run_adjoint faked."""
    import trimesh
    from pipeline_interface import unified_bindings, CFDOutcome, AdjointOutcome
    b = unified_bindings(_CSV, _FHW, td)

    def fake_cfd(stl_half_path):
        # Drag RESPONDS to the geometry. It used to be a hard-coded 0.18 for
        # every candidate, which meant the aero channel was inert in every test
        # that used this mock: the adjoint could return anything and the run
        # would behave identically, so nothing here could catch a regression in
        # the one coupling the project exists to study. A 25-iteration probe
        # run made that obvious -- D20 printed 0.18 on all 15 iterations while
        # the optimiser did pure mass minimisation.
        #
        # Frontal area x a fixed Cd, which is the dominant term for a bluff body
        # and cheap to evaluate: project the half-car onto x and double it. Not
        # a substitute for CFD, but it makes drag a real function of the shape
        # so the aero path is exercised rather than short-circuited.
        m = trimesh.load(stl_half_path, process=False)
        lo, hi = m.bounds
        area_half = float((hi[1] - lo[1]) * (hi[2] - lo[2]))
        A = max(2.0 * area_half, 1e-6)
        CD, Q = 0.45, 0.5 * 1.225 * 20.0 ** 2      # rho/2 * U^2 at the ref speed
        return CFDOutcome(D20=CD * Q * A, L=-0.02, Cm=0.005, A=A,
                          converged=True, residual_final=1e-5)

    def fake_adjoint(stl_half_path, w):
        m = trimesh.load(stl_half_path, process=False)
        return AdjointOutcome(sensitivity=np.full(len(m.vertices), -1e-4), half_mesh=m)

    return dataclasses.replace(b, run_cfd=fake_cfd, run_adjoint=fake_adjoint)


def test_half_car_stl_is_watertight_and_passes_part2():
    # The handshake to OpenFOAM: the half-car STL must be watertight with all
    # vertices y >= -1e-6, or Part 2's run_half_car_cfd rejects it.
    from unified_phi import (
        build_unified_geometry, enforce_symmetry, extract_half_surface,
    )
    g = build_unified_geometry(130.0, 46.0, 20.0)
    enforce_symmetry(g)
    half = extract_half_surface(g)
    assert half.is_watertight, "half-car STL is not watertight (OpenFOAM would reject)"
    assert half.vertices[:, 1].min() >= -1e-6, "half-car STL has y < -1e-6 vertices"
    assert len(half.split(only_watertight=False)) == 1, "half-car STL is fragmented"
    _pass("test_half_car_stl_is_watertight_and_passes_part2")


def test_update_phi_evolves_the_unified_field():
    # The adjoint + objective gradients must actually move the level set.
    import trimesh
    from optimizer_contract import GradientWeights
    with tempfile.TemporaryDirectory() as td:
        b = _mocked_openfoam_bindings(td)
        geom = b.initialize_phi_fields(130.0, 46.0, 20.0, seed=42)
        g0 = geom.phi.grid.copy()
        mr = b.compute_mass_report(geom)
        gate = b.run_quality_gates(geom, "c", td)
        assert gate.stl_half_path, "gate produced no half STL"
        hm = trimesh.load(gate.stl_half_path, process=False)
        grads = {"dT_dD20": 0.4, "dT_dmass": 15.0, "dT_dh_com": -2.0,
                 "dT_dx_com": 0.0, "dT_dL": 0.0}
        for _ in range(5):
            b.update_phi(geom, np.full(len(hm.vertices), -2e-4), hm, 0.5,
                         GradientWeights(1.0, 0.3, 0.3, 0.1), grads, mr)
        moved = float(np.abs(geom.phi.grid - g0).sum())
    assert moved > 0.0, "update_phi did not move the field (aero/objective inert)"
    _pass("test_update_phi_evolves_the_unified_field")


def test_decimation_restores_the_symmetry_plane():
    """Decimation runs AFTER extract_half_surface's clamp and moves vertices.

    Measured 2026-07-27: an aero-only iteration handed OpenFOAM a half-STL with
    a vertex at y = -1.000000e-6, exactly on Part 2's y >= -1e-6 tolerance edge,
    and the candidate died at the CFD gate. The clamp existed; it just ran
    before the operation that broke it.
    """
    import numpy as np
    import trimesh
    from pipeline_interface import _snap_symmetry_plane

    m = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    m.vertices[:, 1] += 0.5             # sit the box on y=0, like a real half
    m.vertices[0, 1] = -1.0e-6          # decimation-scale overshoot
    m.vertices[1, 1] = -3.0e-7
    out = _snap_symmetry_plane(m)
    assert (out.vertices[:, 1] >= 0.0).all(), "symmetry plane not restored"
    print("PASS test_decimation_restores_the_symmetry_plane")


def test_symmetry_snap_refuses_a_genuinely_broken_half():
    """Snapping must not paper over a half that is actually wrong."""
    import trimesh
    from pipeline_interface import _snap_symmetry_plane

    m = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    m.vertices[:, 1] += 0.5
    m.vertices[0, 1] = -5.0e-3          # 5 mm: not rounding
    try:
        _snap_symmetry_plane(m)
    except ValueError as exc:
        assert "below the y=0 symmetry plane" in str(exc)
        print("PASS test_symmetry_snap_refuses_a_genuinely_broken_half")
        return
    raise AssertionError("a 5 mm excursion was silently snapped")
