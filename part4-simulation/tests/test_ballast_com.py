"""The ballast's centre of mass is the lead in the container under the halo, filled from
the bottom (it was at the halo's centre, ~10 mm too high, before 2026-11-11)."""
import assembly


def test_ballast_sits_low_in_its_container():
    asm = {"x_front_mm": 46.0, "d_halo_mm": 43.72, "ballast_g": 2.0}
    little = assembly.ballast_com_mm(asm)
    asm["ballast_g"] = 1e6                     # more than fits: the full container
    full = assembly.ballast_com_mm(asm)
    floor = 24.0
    assert floor - 6.35 < little[2] < full[2] < floor, (little, full)
    assert abs(full[2] - (floor - 6.35 / 2)) < 0.05, full
    assert abs(little[0] - full[0]) < 0.05 and little[1] == 0.0
