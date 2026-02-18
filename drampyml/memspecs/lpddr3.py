"""LPDDR3 memory specifications."""

from drampyml.timing_params.lpddr3 import LPDDR3 as LPDDR3_TIMING

LPDDR3_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

LPDDR3 = {**LPDDR3_STRUCT, **LPDDR3_TIMING}
