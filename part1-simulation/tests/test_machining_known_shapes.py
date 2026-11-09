"""Milling on five hand-made shapes with hand-worked answers (BUILD_SPEC 12.7).

Grid 0.5 mm, so the 3.125 mm ball is r = 6.25 cells. Axes: x (i) along the car, y (j) left
and right, z (k) up. Setups: top, bottom, left, right. A block 20 x 40.5 x 30 mm, solid
everywhere except the feature cut into it; y = 0 is cell j = 40, the top face is k = 59.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

NX, NY, NZ = 40, 81, 60
D = 0.0005
MID = 40


def _run(air, forced=None):
    """Mill a block with `air` cut into it; `forced` cells are rule-required air.
    Returns (solid after, report)."""
    import coarse
    coarse.use_spacing(0.5)
    import machining
    from bounding_volumes import BoundingRegion
    from phi_grid import PhiGrid
    forced = np.zeros((NX, NY, NZ), bool) if forced is None else forced
    bv = BoundingRegion("main_body", (0.0, -MID * D, 0.020), (NX, NY, NZ))   # z from 20 mm: clear of the block's slot
    grid = np.where(air | forced, D, -D).astype(np.float32)
    phi = PhiGrid("main_body", bv, grid, np.zeros_like(forced), forced)
    g = SimpleNamespace(phi=phi, region=bv)
    rep = machining.make_machinable(g)
    return g.phi.grid < 0, rep


def _box(i, j, k):
    m = np.zeros((NX, NY, NZ), bool)
    m[i[0]:i[1] + 1, j[0]:j[1] + 1, k[0]:k[1] + 1] = True
    return m


def test_a_4mm_slot_is_filled_unless_required_then_widened_past_the_ball():
    """A slot 4.5 mm wide (9 cells), 6 mm deep from the top, the whole length. The ball
    (6.25 mm) cannot enter: as plain air it is filled; as rule-required air it is grown
    until the ball fits, so at least 6.25 mm wide."""
    slot = _box((0, NX - 1), (MID - 4, MID + 4), (NZ - 12, NZ - 1))
    S, _ = _run(slot)
    assert S[slot].all(), "a slot the ball cannot enter was left open"
    S, rep = _run(np.zeros_like(slot), forced=slot)
    assert rep["legal_air_violated"] == 0 and not S[slot].any()
    width_mm = (~S[NX // 2, :, NZ - 6]).sum() * D * 1e3
    assert width_mm >= 6.25, f"required slot only {width_mm} mm wide"


def test_an_inside_corner_gets_the_ball_radius():
    """A step: air where y > 0 and z >= 40 cells, open to the top and right. The inside
    corner is the line (j 40.5, k 39.5). A ball of r cells fits only with its centre at
    (40.5 + r, 39.5 + r), so the cell a cells out along the diagonal is filled when
    (r - a) * sqrt(2) > r, a < 0.29 r = 1.83 cells: cell (41, 40) (a = 0.5) is filled,
    cell (43, 42) (a = 2.5) stays open; every open cell near the corner is in such a ball."""
    step = np.zeros((NX, NY, NZ), bool)
    step[:, MID + 1:, 40:] = True
    S, _ = _run(step)
    i = NX // 2
    assert S[i, 41, 40], "the corner was left sharp"
    assert not S[i, 43, 42], "the fillet is bigger than the ball"
    r = 3.125 / 0.5
    c = np.array([40.5 + r, 39.5 + r])
    for j in range(41, 41 + 6):
        for k in range(40, 40 + 6):
            if not S[i, j, k] and (j - 40.5) < r and (k - 39.5) < r:
                assert np.hypot(*(np.array([j, k]) - c)) <= r + 0.75, f"open cell ({j},{k}) no ball reaches"
    assert not S[i, 60, 50] and S[i, 30, 50], "flat faces moved"


def test_an_undercut_no_side_reaches_is_filled():
    """A T-shaped cavity: an 8.5 mm throat from the top (j 32-48, k 50-59) over a 16.5 mm
    chamber (j 24-56, k 30-49), x 5-14.5 mm; plus a sealed void. The ball comes down the
    throat with its centre at |dj| <= 8 - 6.25 = 1.75 cells, so it clears the chamber to
    |dj| <= 8 cells; the chamber's sides past that, under the overhang, are filled, and so
    is the sealed void."""
    throat = _box((10, 29), (32, 48), (50, NZ - 1))
    chamber = _box((10, 29), (24, 56), (30, 49))
    void = _box((5, 8), (8, 14), (8, 14))
    S, _ = _run(throat | chamber | void)
    assert not S[20, MID, 40] and not S[20, MID, 55], "the reachable middle was filled"
    assert S[20, MID - 14, 40] and S[20, MID + 14, 40], "the undercut was left open"
    assert S[void].all(), "the sealed void was left open"


def test_a_pocket_open_to_the_top_stays_open():
    """A 10 x 10.5 x 5 mm pocket from the top: the ball reaches all of it except its bottom
    fillets (a band under 0.29 r = 0.9 mm along the floor edges)."""
    pocket = _box((10, 29), (MID - 10, MID + 10), (50, NZ - 1))
    S, _ = _run(pocket)
    assert not S[20, MID, 50:].any(), "the pocket's middle was filled"
    assert (~S[pocket]).mean() > 0.85, f"only {(~S[pocket]).mean():.0%} of the pocket left open"


def test_required_air_with_square_corners_grows_until_the_ball_reaches():
    """The same pocket as rule-required air. Its square bottom corners are out of the
    ball's reach, so the zone is grown past them: all of it ends up air, and some air
    outside it too."""
    pocket = _box((10, 29), (MID - 10, MID + 10), (50, NZ - 1))
    S, rep = _run(np.zeros_like(pocket), forced=pocket)
    assert rep["legal_air_violated"] == 0 and not S[pocket].any(), "required air left solid"
    assert rep["zone_cells_grown_for_cutter"] > 0 and (~S & ~pocket).any(), "the zone was not grown"
