from collections import Counter
from typing import Hashable, Optional

from drampyml.common.commands import Command
from drampyml.algorithms.state import current_state, restore_state
from drampyml.components.petri_net import Arc, Coordinate, CustomArc, PetriNet, Place, PlaceType, Token, Transition
from dataclasses import dataclass
import rustworkx as rx
from sympy import N, Add, Expr, Max, Integer, Sum, simplify
import time
import statistics
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandTransition:
    command: Command
    coordinate: Coordinate
    transition_id: int = field(repr=False)
    timing: Optional[Expr] = None
    
# ------------------------------------------------------------------------
# Exploration of the Petri net (Timings)
# ------------------------------------------------------------------------

def _get_timing(petri_net: PetriNet, from_transition: int, to_transition: int):
    try:
        edge: CustomArc = petri_net.graph.get_edge_data(from_transition, to_transition)
        return edge.time_constraint
    except rx.NoEdgeBetweenNodes:
        return Integer(0)


def _get_max_timing(petri_net: PetriNet, from_transitions: tuple[CommandTransition], to_transition: int):
    if len(from_transitions) == 0:
        return Integer(0)
    direct_from_to_timings = [_get_timing(petri_net, from_transition.transition_id, to_transition) 
               for from_transition in from_transitions]
    adjusted_timings = [direct_from_to_timings[-1]]
    delta = direct_from_to_timings[-1]
    for idx, timing in enumerate(reversed(direct_from_to_timings[:-1]), 1):
        if timing == 0 or timing == adjusted_timings[0]:
            continue
        i = from_transitions[-idx].timing
        delta = delta + from_transitions[-idx].timing
        adjusted_timings.append(timing - delta)
    return Max(*adjusted_timings) if len(adjusted_timings) > 1 else adjusted_timings[0]
    

# ------------------------------------------------------------------------
# Exploration of the Petri net (Algorithms)
# ------------------------------------------------------------------------

def explore_next_transitions(
    petri_net: PetriNet,
    k_max: int,
    include_timings: bool = True
) -> set[tuple[CommandTransition, ...]]:
    """
    Explore command sequences with caching and time advancement.

    This function properly advances current_time when exploring timed sequences,
    allowing it to find valid paths in both timed and untimed modes.

    - In untimed mode (ignore_timing_constraints=True): Finds all structurally valid paths
    - In timed mode (ignore_timing_constraints=False): Advances time and respects timing constraints

    Args:
        petri_net: The Petri net to explore
        k_max: Maximum depth to explore
        include_timings: Whether to include timing information in results

    Returns:
        Set of command transition paths with proper timing information

    Example:
        >>> petri_net = create_standard(DDR3_1600).petri_net
        >>> # Untimed exploration
        >>> petri_net.ignore_timing_constraints = True
        >>> untimed = explore_next_transitions(petri_net, k_max=3)
        >>> # Timed exploration
        >>> petri_net.ignore_timing_constraints = False
        >>> timed = explore_next_transitions(petri_net, k_max=3)
    """
    from drampyml.components.petri_net import TimedArc

    graph = petri_net.graph
    place_indices = sorted(graph.filter_nodes(lambda n: isinstance(n, Place)))
    transition_indices = sorted(graph.filter_nodes(lambda n: isinstance(n, Transition)))

    # Cache transition metadata
    transition_meta = {
        idx: (graph[idx].command, graph[idx].coordinate)
        for idx in transition_indices
    }

    def make_state_key() -> Hashable:
        places_sig = tuple(
            tuple(token.timestamp for token in graph[place_idx].tokens)
            for place_idx in place_indices
        )
        custom_arc_indices = [
            edge_idx for edge_idx in graph.edge_indices()
            if isinstance(graph.get_edge_data_by_index(edge_idx), CustomArc)
        ]
        edge_sig = tuple(
            graph.get_edge_data_by_index(edge_idx).timestamp
            for edge_idx in custom_arc_indices
        )
        return (petri_net.current_time, places_sig, edge_sig)

    def find_next_fireable_time():
        """Find minimum time when at least one transition becomes fireable."""
        current = petri_net.current_time
        min_times = []

        for t_idx in transition_indices:
            if graph[t_idx].active:
                continue

            in_edges = graph.in_edges(t_idx)
            for src_idx, _, edge_data in in_edges:
                if isinstance(edge_data, TimedArc):
                    src_tokens = graph[src_idx].tokens
                    if src_tokens:
                        lower_bound = edge_data.lower_bound.subs(petri_net.memspec)
                        for token in src_tokens:
                            required_time = token.timestamp + lower_bound
                            min_times.append(required_time)

        return max(current + 1, min(min_times)) if min_times else None

    cache: dict[tuple[Hashable, int], set[tuple[int, ...]]] = {}

    def dfs(depth: int) -> set[tuple[int, ...]]:
        if depth == k_max:
            return {()}

        key = (make_state_key(), depth)
        if key in cache:
            return cache[key]

        base_state = current_state(petri_net)
        petri_net.evaluate()
        enabled = [t for t in transition_indices if graph[t].active]

        results: set[tuple[int, ...]] = set()
        for t in enabled:
            petri_net.fire_transition(t)

            # Advance time for timed exploration
            if not petri_net.ignore_timing_constraints:
                next_time = find_next_fireable_time()
                if next_time and next_time > petri_net.current_time:
                    petri_net.current_time = next_time
                    petri_net.evaluate()

            suffixes = dfs(depth + 1)
            for suf in suffixes:
                results.add((t,) + suf)

            restore_state(petri_net, base_state)

        cache[key] = results
        return results

    # Explore paths
    transition_id_paths = dfs(0)

    # Convert to CommandTransition paths
    result: set[tuple[CommandTransition, ...]] = set()
    for path in transition_id_paths:
        command_transitions: list[CommandTransition] = []
        for t_id in path:
            command, coordinate = transition_meta[t_id]

            if include_timings:
                timing_expr = _get_max_timing(petri_net, tuple(command_transitions), t_id)
                timing = timing_expr.subs(petri_net.memspec)
            else:
                timing = None

            ct = CommandTransition(
                command=command,
                coordinate=coordinate,
                transition_id=t_id,
                timing=timing
            )
            command_transitions.append(ct)

        result.add(tuple(command_transitions))

    return result


