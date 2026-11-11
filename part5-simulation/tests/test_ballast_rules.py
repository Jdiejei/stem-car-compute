"""T1.22 test cars: ballast only in the container under the halo (user's decision
2026-11-11: a short layout carries ballast, legal only with every check passed)."""
import trimesh

import legality as lg

POCKET = {"x0": 80.0, "x1": 130.0, "half_w": 12.5, "z0": 24.0, "z1": 27.175}


def _block(cut: bool):
    b = trimesh.creation.box(bounds=[[40.0, -30.0, 5.0], [200.0, 30.0, 24.0]])
    if cut:
        b = trimesh.boolean.difference([b, lg.ballast_capsule_mm(POCKET)], engine="manifold")
    return b


def test_no_ballast_no_check():
    assert lg.ballast_checks(_block(False), POCKET, 0.0) == {}


def test_ballast_in_an_open_container_passes():
    r = lg.ballast_checks(_block(True), POCKET, 10.0)
    assert r["T1.22_ballast_fits_container"]["pass"] and r["T1.22_ballast_container_open"]["pass"], r


def test_container_not_cut_fails():
    r = lg.ballast_checks(_block(False), POCKET, 10.0)
    assert not r["T1.22_ballast_container_open"]["pass"], r


def test_more_lead_than_the_container_holds_fails():
    cap = abs(lg.ballast_capsule_mm(POCKET, above_floor_mm=0.0).volume) * 1e-3 * lg.LEAD_G_CM3
    assert lg.ballast_checks(_block(True), POCKET, cap - 0.1)["T1.22_ballast_fits_container"]["pass"]
    assert not lg.ballast_checks(_block(True), POCKET, cap + 0.1)["T1.22_ballast_fits_container"]["pass"]
