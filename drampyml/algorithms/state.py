from drampyml.components.petri_net import PetriNet, Place, CustomArc
import copy
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
