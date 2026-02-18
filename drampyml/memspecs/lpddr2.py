"""LPDDR2 memory specifications."""

from drampyml.timing_params.lpddr2 import LPDDR2 as LPDDR2_TIMING

LPDDR2_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

LPDDR2 = {**LPDDR2_STRUCT, **LPDDR2_TIMING}
