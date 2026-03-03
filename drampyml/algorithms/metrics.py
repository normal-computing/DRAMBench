from drampyml.components.petri_net import (
    PetriNet,
    Transition,
    TimedArc,
    CustomArc,
)
from drampyml.algorithms.transitions import explore_next_transitions
from typing import Any

def jaccard_index(fm_a: PetriNet, fm_b: PetriNet, k_max: int = 4) -> float:
    """
    Computes the Jaccard index to measure the similarity between two
    `PetriNets`, checking sequences up to length `k_max`.
    """
    sequences_a = explore_next_transitions(fm_a, k_max)
    sequences_b = explore_next_transitions(fm_b, k_max)
    overlap = sequences_a & sequences_b
    total = sequences_a | sequences_b
    return len(overlap) / len(total)



def _extract_timing_constraints(pn: PetriNet) -> set[tuple[Any, ...]]:
    """
    Extracts all timing constraints from a PetriNet as a set of tuples.

    Each timing constraint is represented as:
    (source_command, target_command, timing_expression_str)

    For TimedArc: timing is on incoming edge to transition from a place
    For CustomArc: timing is between transitions (command-to-command)

    Returns a set of constraint tuples for comparison.
    """
    constraints: set[tuple[Any, ...]] = set()
    graph = pn.graph

    for edge_idx in graph.edge_indices():
        edge_data = graph.get_edge_data_by_index(edge_idx)
        endpoints = graph.get_edge_endpoints_by_index(edge_idx)
        if endpoints is None:
            continue

        src_idx, tgt_idx = endpoints
        src_node = graph[src_idx]
        tgt_node = graph[tgt_idx]

        if isinstance(edge_data, CustomArc):
            # CustomArc connects transition -> transition
            if isinstance(src_node, Transition) and isinstance(tgt_node, Transition):
                constraint = (
                    str(src_node.command),
                    str(tgt_node.command),
                    str(edge_data.time_constraint),
                )
                constraints.add(constraint)

        elif isinstance(edge_data, TimedArc):
            # TimedArc connects place -> transition
            if isinstance(tgt_node, Transition):
                constraint = (
                    "place",
                    str(tgt_node.command),
                    str(edge_data.lower_bound),
                )
                constraints.add(constraint)

    return constraints


def timing_constraint_recall(reference: PetriNet, generated: PetriNet) -> float:
    """
    Computes timing constraint recall between two PetriNets.

    Measures the fraction of timing constraints from the reference PetriNet
    that are present in the generated PetriNet.

    Args:
        reference: The ground truth PetriNet containing expected timing constraints
        generated: The generated PetriNet to evaluate

    Returns:
        Recall as a float between 0.0 and 1.0
    """
    ref_constraints = _extract_timing_constraints(reference)
    gen_constraints = _extract_timing_constraints(generated)

    matched = ref_constraints & gen_constraints

    return len(matched) / max(len(ref_constraints), 1)


