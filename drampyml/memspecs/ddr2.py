"""DDR2 memory specifications."""

from drampyml.timing_params.ddr2 import DDR2 as DDR2_TIMING

DDR2_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

DDR2 = {**DDR2_STRUCT, **DDR2_TIMING}

# Alias for backward compatibility
DDR2_800C_1GB = DDR2
