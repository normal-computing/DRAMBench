from drampyml.components.petri_net import PetriNet
from drampyml.algorithms.transitions import explore_next_transitions


def jaccard_index(fm_a: PetriNet, fm_b: PetriNet, k_max: int = 4) -> float:
    """Computes the Jaccard index to measure the similarity between two
    `PetriNets`, checking sequences up to length `k_max`."""
    sequences_a = explore_next_transitions(fm_a, k_max)
    sequences_b = explore_next_transitions(fm_b, k_max)
    overlap = sequences_a & sequences_b
    total = sequences_a | sequences_b
    # print(f"The sequences they agree on are: {overlap}")
    # print(f"The sequences we miss are: {sequences_b - overlap}")
    return len(overlap) / len(total)
