from drampyml.components.petri_net import Coordinate


def intra_bank(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    return from_coord == to_coord

def intra_bank_group(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    if from_coord.bank_group != to_coord.bank_group: 
        return False
    if intra_rank(from_coord, to_coord) or intra_pseudochannel(from_coord, to_coord): 
        return True
    return False

def intra_rank(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    # Support both 'rank' and 'logical_rank' attributes (DDR5 uses logical_rank)
    if hasattr(from_coord, "rank"):
        return from_coord.rank == to_coord.rank
    elif hasattr(from_coord, "logical_rank"):
        return from_coord.logical_rank == to_coord.logical_rank
    return False

def intra_pseudochannel(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    return hasattr(from_coord, "pseudochannel") and from_coord.pseudochannel == to_coord.pseudochannel

def extra_rank(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    # Support both 'rank' and 'logical_rank' attributes (DDR5 uses logical_rank)
    if hasattr(from_coord, "rank"):
        return from_coord.rank != to_coord.rank
    elif hasattr(from_coord, "logical_rank"):
        return from_coord.logical_rank != to_coord.logical_rank
    return False

def extra_pseudochannel(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    if hasattr(from_coord, "pseudochannel") and from_coord.pseudochannel != to_coord.pseudochannel:
        return True
