"""HBM2 memory specifications."""

from drampyml.timing_params.hbm2 import HBM2 as HBM2_TIMING

HBM2_STRUCT = {
    "nbrOfPseudochannels": 2,
    "nbrOfBankGroups": 2,
    "nbrOfBanks": 2,
    "defaultBurstLength": 8,
    "dataRate": 2,
}

HBM2 = {**HBM2_STRUCT, **HBM2_TIMING}
