"""The print minimum: one value, every printed wall at least that, a blunt wing trailing edge."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "part1-simulation"))

import numpy as np  # noqa: E402

import beam_support as bsm  # noqa: E402
import component_contract as cc  # noqa: E402
import nose as ns  # noqa: E402
import wings as wg  # noqa: E402


def test_naca_trailing_edge_is_as_thick_as_asked():
    for te in (0.0, 0.7, 1.2):
        s = wg.naca4(15.3, 0.15, te_mm=te)
        tail = s[s[:, 0] > 15.3 - 1e-9]
        assert abs((tail[:, 1].max() - tail[:, 1].min()) - te) < 1e-9, (te, tail)
    # the LE is untouched, and the section is still closed and ordered
    a, b = wg.naca4(15.3, 0.15), wg.naca4(15.3, 0.15, te_mm=1.0)
    assert np.allclose(a[0], b[0])


def test_every_printed_minimum_follows_the_one_value():
    m = cc.MIN_WALL_MM
    assert bsm.PRINT_MIN_MM == m
    bs = bsm.BeamSupport()
    assert min(bs.disc_t_mm, bs.hubcap_t_mm, bs.pod_wall_mm, bs.beam_h_mm, bs.strip_h_mm) >= m
    assert ns.NoseCone().wall_mm >= m
    assert (cc.TETHER_GUIDE_OD - cc.TETHER_GUIDE_ID) / 2 >= m
