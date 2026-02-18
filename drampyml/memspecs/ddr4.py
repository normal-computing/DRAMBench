"""DDR4 memory specifications."""

from drampyml.timing_params.ddr4 import DDR4_1866 as DDR4_1866_TIMING

DDR4_1866_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBankGroups": 2,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

DDR4_1866 = {**DDR4_1866_STRUCT, **DDR4_1866_TIMING}

# Alias for backward compatibility
DDR4_1866M = DDR4_1866
