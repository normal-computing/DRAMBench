"""GDDR6 memory specifications."""

from drampyml.timing_params.gddr6 import GDDR6 as GDDR6_TIMING

GDDR6_12Gbps_x16_STRUCT = {
    "nbrOfBankGroups": 2,
    "nbrOfBanks": 2,
    "defaultBurstLength": 16,
    "dataRate": 12.0,
}

GDDR6_12Gbps_x16 = {**GDDR6_12Gbps_x16_STRUCT, **GDDR6_TIMING}