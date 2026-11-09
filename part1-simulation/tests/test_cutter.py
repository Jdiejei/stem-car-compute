"""The cut API (cutter.py): sign, refusals, rules after a cut, the caller's field untouched,
and the save/load hand-off. Real block at 2 mm, so it stays quick."""
import copy
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from scipy.ndimage import label

LAYOUT = {"W": 120.3, "x_front": 46.0, "d_halo": 43.72}
_CACHE = {}


def _block():
    import coarse
    import cutter
    from unified_phi import extract_half_surface
    coarse.use_spacing(2.0)                          # every call: conftest resets it after each test
    if "g" not in _CACHE:
        g = _CACHE["g"] = cutter.start_block(LAYOUT, spacing_mm=2.0)
        _CACHE["mesh"] = SimpleNamespace(vertices=np.asarray(extract_half_surface(g).vertices))
    return _CACHE["g"], _CACHE["mesh"]


def _cut(g, mesh, value, **kw):
    import cutter
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cutter.cut(g, np.full(len(mesh.vertices), value), mesh, step_m=1.0, **kw)


def _solid(g):
    return int((g.phi.grid < 0).sum())


def test_positive_dT_dn_shrinks_and_negative_grows():
    """BUILD_SPEC 12.3 sign trap: dT_dn > 0 everywhere (growing costs time) must shrink the
    body; then dT_dn < 0 must grow it back."""
    from unified_phi import extract_half_surface
    g, mesh = _block()
    g1, rep = _cut(g, mesh, +1.0)
    assert rep["status"] == "ok", rep
    assert _solid(g1) < _solid(g), "dT_dn > 0 did not shrink the body: sign flipped"
    m1 = SimpleNamespace(vertices=np.asarray(extract_half_surface(g1).vertices))
    g2, rep2 = _cut(g1, m1, -1.0)
    assert rep2["status"] == "ok", rep2
    assert _solid(g2) > _solid(g1), "dT_dn < 0 did not grow the body: sign flipped"


def test_cut_never_changes_the_callers_field():
    g, mesh = _block()
    before = g.phi.grid.copy()
    _cut(g, mesh, +1.0)
    assert np.array_equal(g.phi.grid, before)


def test_every_body_rule_holds_after_a_cut():
    """Forced air and solid, exact symmetry, one piece."""
    g, mesh = _block()
    g1, rep = _cut(g, mesh, +1.0, max_substeps=6, trust_radius_m=3e-3)
    assert rep["status"] == "ok", rep
    assert rep["rule_air_violated"] == 0 and rep["rule_solid_violated"] == 0, rep
    S = g1.phi.grid < 0
    mid = S.shape[1] // 2
    assert np.array_equal(g1.phi.grid[:, mid:, :], g1.phi.grid[:, :mid + 1, :][:, ::-1, :]), "not symmetric"
    assert label(S)[1] == 1, "the body is not one piece"


def test_refusals_are_named_and_leave_the_field():
    g, mesh = _block()
    import cutter
    out, rep = cutter.cut(g, np.ones(3), mesh, step_m=1.0)
    assert out is g and rep["status"] == "refused" and rep["reason"].startswith("bad_input"), rep
    out, rep = cutter.cut(g, np.array([np.nan] * len(mesh.vertices)), mesh, step_m=1.0)
    assert out is g and rep["reason"].startswith("bad_input"), rep
    out, rep = _cut(g, mesh, 0.0)
    assert out is g and rep == {**rep, "status": "refused", "reason": "no_motion"}, rep


def test_loose_pinned_material_is_refused():
    """A forced-solid cell off the body: the input is not one piece (T4.1)."""
    import cutter
    g, mesh = _block()
    g = copy.deepcopy(g)
    S = g.phi.grid < 0
    mid = S.shape[1] // 2
    # an air cell on the centre plane with no solid within 2 cells, made forced solid
    from scipy.ndimage import binary_dilation
    far = ~S & ~binary_dilation(S, iterations=2)
    i, k = np.argwhere(far[:, mid, :])[0]
    g.phi.hard_mask_air[i, mid, k] = False
    g.phi.hard_mask_solid[i, mid, k] = True
    g.phi.apply_hard_constraints()
    out, rep = _cut(g, mesh, +1.0)
    assert out is g and rep["status"] == "refused" and rep["reason"] == "pinned_detached", rep


def test_save_and_load_round_trip(tmp_path):
    import cutter
    g, mesh = _block()
    g1, _ = _cut(g, mesh, +1.0)
    cutter.save_field(g1, tmp_path / "carved_phi.npy")
    g2 = cutter.load_field(LAYOUT, tmp_path / "carved_phi.npy", spacing_mm=2.0)
    assert np.array_equal(g2.phi.grid, g1.phi.grid)


def test_finish_writes_a_sized_body_and_its_files(tmp_path):
    """Start block -> one cut -> finish: a closed half body, the field and cut.json, the mass
    on target within the sizing tolerance (or a named refusal, never a crash)."""
    import json

    import cutter
    import trimesh
    g, mesh = _block()
    g1, _ = _cut(g, mesh, +1.0)
    res = cutter.finish(g1, LAYOUT, 48.2, tmp_path)
    assert json.loads((tmp_path / "cut.json").read_text())["status"] == res["status"]
    assert (tmp_path / "carved_phi.npy").exists()
    assert res["status"] == "ok", res["reason"]
    assert abs(res["mass_g"] - 48.2) <= 0.05, res["mass_g"]
    half = trimesh.load(tmp_path / "body_half.stl")
    assert half.is_watertight and half.vertices[:, 1].min() >= -1e-9
    assert (tmp_path / "body.stl").exists()
