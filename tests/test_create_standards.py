"""Test that all DRAM standards can generate Petri nets without errors."""

import pytest

from drampyml.standards.ddr2 import create_standard as create_ddr2
from drampyml.standards.ddr3 import create_standard as create_ddr3
from drampyml.standards.ddr4 import create_standard as create_ddr4
from drampyml.standards.gddr5 import create_standard as create_gddr5
from drampyml.standards.gddr6 import create_standard as create_gddr6
from drampyml.standards.hbm2 import create_standard as create_hbm2
from drampyml.standards.lpddr2_s2 import create_standard as create_lpddr2_s2
from drampyml.standards.lpddr2_s4 import create_standard as create_lpddr2_s4
from drampyml.standards.lpddr3 import create_standard as create_lpddr3
from drampyml.standards.lpddr4 import create_standard as create_lpddr4

from drampyml.memspecs.ddr2 import DDR2
from drampyml.memspecs.ddr3 import DDR3_1600
from drampyml.memspecs.ddr4 import DDR4_1866
from drampyml.memspecs.gddr5 import GDDR5_4Gbps_x32
from drampyml.memspecs.gddr6 import GDDR6_12Gbps_x16
from drampyml.memspecs.hbm2 import HBM2
from drampyml.memspecs.lpddr2 import LPDDR2
from drampyml.memspecs.lpddr3 import LPDDR3
from drampyml.memspecs.lpddr4 import LPDDR4


@pytest.mark.parametrize(
    "name, create_fn, memspec",
    [
        ("DDR2", create_ddr2, DDR2),
        ("DDR3", create_ddr3, DDR3_1600),
        ("DDR4", create_ddr4, DDR4_1866),
        ("GDDR5", create_gddr5, GDDR5_4Gbps_x32),
        ("GDDR6", create_gddr6, GDDR6_12Gbps_x16),
        ("HBM2", create_hbm2, HBM2),
        ("LPDDR2_S2", create_lpddr2_s2, LPDDR2),
        ("LPDDR2_S4", create_lpddr2_s4, LPDDR2),
        ("LPDDR3", create_lpddr3, LPDDR3),
        ("LPDDR4", create_lpddr4, LPDDR4),
    ],
    ids=["ddr2", "ddr3", "ddr4", "gddr5", "gddr6", "hbm2", "lpddr2_s2", "lpddr2_s4", "lpddr3", "lpddr4"],
)
def test_create_standard(name, create_fn, memspec):
    """Test that create_standard produces a valid Standard with a non-empty Petri net."""
    standard = create_fn(memspec)

    assert standard is not None, f"{name}: create_standard returned None"
    assert standard.petri_net is not None, f"{name}: petri_net is None"
    assert len(standard.petri_net.graph.nodes()) > 0, f"{name}: Petri net has no nodes"
    assert len(standard.petri_net.graph.edges()) > 0, f"{name}: Petri net has no edges"
