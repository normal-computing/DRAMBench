import copy
import rustworkx as rx

from collections import deque
from typing import Any
from drampyml.components.petri_net import PetriNet, Place, CustomArc
from tqdm import tqdm
from frozendict import frozendict


def current_state(
    petri_net: PetriNet,
) -> frozendict[str, frozenset[Place] | frozendict[int, CustomArc] | int]:
    places: set[Place] = set()
    custom_arcs: set[tuple[int, CustomArc]] = set()
    for node_data in petri_net.graph.nodes():
        if not isinstance(node_data, Place):
            continue
        place = copy.deepcopy(node_data)
        place.tokens = tuple(place.tokens)
        places.add(place)

    custom_arc_indices = petri_net.graph.filter_edges(
        lambda edge: isinstance(edge, CustomArc)
    )
    custom_arcs = {
        idx: petri_net.graph.get_edge_data_by_index(idx).timestamp
        for idx in custom_arc_indices
    }

    return frozendict(
        {
            "places": frozenset(places),
            "custom_arcs": frozendict(custom_arcs),
            "current_time": petri_net.current_time,
        }
    )


def restore_state(
    petri_net: PetriNet,
    state: frozendict[str, frozenset[Place] | frozendict[int, CustomArc] | int],
):
    for place in state["places"]:
        place_index = petri_net.places[(place.coordinate, place.place_type)]
        petri_net.graph[place_index].tokens = list(place.tokens)

    for edge_idx, timestamp in state["custom_arcs"].items():
        petri_net.graph.get_edge_data_by_index(edge_idx).timestamp = timestamp

    petri_net.current_time = state["current_time"]

    petri_net.evaluate()


def unroll_petri_net(
    petri_net: PetriNet,
    numberOfBanks: int,
) -> tuple[rx.PyDiGraph, int]:
    """
    Build the reachability graph via BFS (frontier).
    - Nodes represent states (keyed by state["places"])
    - Edges are transitions (edge data: transition_index)
    - Node creation stops when max_states is reached, but we keep processing
      the frontier to add edges to already known nodes
    - Returns: (graph, max BFS depth)
    """

    def _state_key(state: dict[str, Any]) -> object:
        # Use places directly as the key (must be hashable/immutable, e.g., frozenset)
        return state["places"]

    def _add_edge_unique(g: rx.PyDiGraph, u: int, v: int, label: int) -> None:
        # Add edge only if the same label between u->v does not exist yet
        if g.has_edge(u, v):
            existing = g.get_all_edge_data(u, v)
            if label not in existing:
                g.add_edge(u, v, label)
        else:
            g.add_edge(u, v, label)

    # Save original state and initialize initial marking
    original_state = current_state(petri_net)
    petri_net.current_time = -(2**32)
    init_state = current_state(petri_net)

    max_states = 2 ** (numberOfBanks + 1) + 1

    graph = rx.PyDiGraph()
    init_key = _state_key(init_state)
    init_idx = graph.add_node(init_key)

    # visited: state_key -> (graph_index, full_state_snapshot)
    visited: dict[object, tuple[int, dict[str, Any]]] = {
        init_key: (init_idx, init_state)
    }
    depth: dict[object, int] = {init_key: 0}
    frontier = deque([init_key])

    # Progress bar: counts created states (nodes)
    with tqdm(total=max_states, desc="Unroll Petri net", unit="states") as pbar:
        pbar.update(1)  # initial state already added

        # BFS: keep processing frontier; only gate node creation by max_states
        while frontier:
            cur_key = frontier.popleft()
            cur_idx, cur_state = visited[cur_key]

            # Restore net to current node's state and compute fireable transitions
            restore_state(petri_net, cur_state)
            fireable = petri_net.who_can_fire()

            for t_idx in fireable:
                # Try fire -> get successor state -> then revert
                snap = current_state(petri_net)
                petri_net.fire_transition(t_idx)
                succ_state = current_state(petri_net)
                succ_key = _state_key(succ_state)
                restore_state(petri_net, snap)

                if succ_key in visited:
                    succ_idx = visited[succ_key][0]
                    _add_edge_unique(graph, cur_idx, succ_idx, t_idx)
                else:
                    # Stop creating new nodes once the limit is reached,
                    # but continue to process remaining frontier nodes
                    if len(visited) < max_states:
                        succ_idx = graph.add_node(succ_key)
                        visited[succ_key] = (succ_idx, succ_state)
                        depth[succ_key] = depth[cur_key] + 1
                        frontier.append(succ_key)
                        _add_edge_unique(graph, cur_idx, succ_idx, t_idx)
                        pbar.update(1)
                    # Else: skip creating the node (and thus the edge), continue BFS

    # Compute maximum BFS depth reached
    k_deeps = max(depth.values()) if depth else 0

    # Restore original net state
    restore_state(petri_net, original_state)
    return graph, k_deeps
