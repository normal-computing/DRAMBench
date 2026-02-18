"""GDDR5 memory specifications."""

from drampyml.timing_params.gddr5 import GDDR5 as GDDR5_TIMING

GDDR5_4Gbps_x32_STRUCT = {
    "nbrOfBankGroups": 2,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 4.0,
}

GDDR5_4Gbps_x32 = {**GDDR5_4Gbps_x32_STRUCT, **GDDR5_TIMING}