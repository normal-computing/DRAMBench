"""LPDDR4 memory specifications."""

from drampyml.timing_params.lpddr4 import LPDDR4 as LPDDR4_TIMING

LPDDR4_STRUCT = {
    "nbrOfRanks": 1,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

LPDDR4 = {**LPDDR4_STRUCT, **LPDDR4_TIMING}
