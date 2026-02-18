"""DDR3 memory specifications."""

from drampyml.timing_params.ddr3 import DDR3_1600 as DDR3_1600_TIMING

DDR3_1600_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

DDR3_1600 = {**DDR3_1600_STRUCT, **DDR3_1600_TIMING}
