import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rank_study as rs


def test_identical_order_passes():
    f = [1.50 + 0.004 * i for i in range(10)]
    s = [x + 0.02 for x in f]                       # offset search mesh, same order
    assert rs.spearman(s, f) == pytest.approx(1.0)
    assert rs.pair_agreement(s, f) == (45, 45)
    assert "PASS" in rs.stats({str(i): (s[i], f[i]) for i in range(10)})


def test_reversed_order_fails_and_close_pairs_do_not_count():
    f = [1.500, 1.501, 1.520]                       # first two are 1 ms apart: not counted
    s = [1.53, 1.52, 1.51]
    ag, tot = rs.pair_agreement(s, f)
    assert (ag, tot) == (0, 2)
    assert "FAIL" in rs.stats({"a": (s[0], f[0]), "b": (s[1], f[1]), "c": (s[2], f[2])})


def test_cars_missing_a_mesh_are_left_out():
    out = rs.stats({"a": (1.5, 1.5), "b": (1.6, 1.6), "c": (None, 1.7), "d": (1.7, 1.7)})
    assert out.startswith("RANK n = 3 cars")
