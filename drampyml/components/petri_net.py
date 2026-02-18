from drampyml.common.commands import Command

import rustworkx as rx
from sympy import Expr, sympify
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol

# Base class for all IP-specific PlaceType enums 
class BasePlaceType:
    """Base class providing common string representation for all IP-specific PlaceType enums.

    All IP-specific PlaceType enums (PlaceType, UARTPlaceType, etc.) should inherit from this.
    """
    def __str__(self):
        return self.name  # type: ignore

    def __repr__(self):
        return str(self)


# DDR/Memory-specific PlaceTypes (for DDR3, DDR4, LPDDR4, etc.) 
class PlaceType(BasePlaceType, Enum):
    """PlaceType enum for DDR/memory standards."""
    ACTIVE = auto()
    PDN = auto()
    DPD = auto()
    PWR_ON = auto()
    SREF = auto()
    SREF_FLAG = auto()
    SRS = auto()
    SL = auto()
    CMD_BUS = auto()
    NAW_Pool = auto()
    REF_Flag = auto()
    REF_Pool = auto()
    CSP = auto()


# UART-specific PlaceTypes
class UARTPlaceType(BasePlaceType, Enum):
    """PlaceType enum for UART standard."""
    IDLE = auto()
    PARSING = auto()
    RD_PENDING = auto()
    WR_PENDING = auto()
    TX_RESPONSE = auto()

# AES-specific PlaceTypes
class AESPlaceType(BasePlaceType, Enum):
    """PlaceType enum for AES standard."""
    WAIT_KEY = auto()
    KEY_EXPANDING = auto()
    WAIT_DATA = auto()
    INITIAL_ROUND = auto()
    DO_ROUND = auto()
    FINAL_ROUND = auto()


class Coordinate(Protocol): ...


@dataclass(frozen=True)
class Token:
    timestamp: int = -(2**32)


@dataclass(unsafe_hash=True)
class Place:
    place_type: BasePlaceType
    coordinate: Coordinate
    tokens: list[Token] = field(default_factory=lambda: [])


@dataclass
class Transition:
    command: Command
    coordinate: Coordinate
    active: bool = False


@dataclass(frozen=True)
class Arc:
    weight: int = 1


@dataclass(frozen=True)
class InhibitorArc:
    weight: int = 1


@dataclass(frozen=True)
class TimedArc:
    weight: int = 1
    lower_bound: Expr = sympify(0)


@dataclass
class CustomArc:
    time_constraint: Expr
    timestamp: int = -(2**32)

    def active(self, time, memspec):
        return time < self.timestamp + self.time_constraint.subs(memspec)


@dataclass(frozen=True)
class ResetArc:
    pass


@dataclass
class PetriNet:
    graph: rx.PyDiGraph
    memspec: dict[Expr, int] = field(default_factory=lambda: {})
    places: dict[tuple[Coordinate, PlaceType], int] = field(init=False)
    transitions: dict[tuple[Coordinate, Command], list[int]] = field(init=False)
    current_time: int = 0
    ignore_timing_constraints = False

    def __post_init__(self):
        self.evaluate()
        self._explore_transitons()
        self._explore_places()

    def _explore_transitons(self):
        self.transitions = {}
        for i in self.graph.filter_nodes(lambda node: isinstance(node, Transition)):
            data = self.graph[i]
            self.transitions.setdefault((data.coordinate, data.command), []).append(i)

    def _explore_places(self):
        self.places = {}
        for i in self.graph.filter_nodes(lambda node: isinstance(node, Place)):
            data = self.graph[i]
            self.places[(data.coordinate, data.place_type)] = i

    def evaluate(self):
        for transition in self.graph.filter_nodes(
            lambda node: isinstance(node, Transition)
        ):
            node_data = self.graph[transition]
            node_data.active = self.can_fire_transition(transition)

    def can_fire_transition(self, transition_index: int):
        in_edges = self.graph.in_edges(transition_index)

        for src_index, _, edge_data in in_edges:
            src_node_data = self.graph[src_index]

            if isinstance(edge_data, CustomArc):
                if not self.ignore_timing_constraints and edge_data.active(
                    self.current_time, self.memspec
                ):
                    return False

                continue

            src_tokens: list[Token] = src_node_data.tokens

            if isinstance(edge_data, TimedArc):
                lower_bound = edge_data.lower_bound.subs(self.memspec)

                valid_tokens = (
                    len(src_tokens)
                    if self.ignore_timing_constraints
                    else sum(
                        1
                        for token in src_tokens
                        if lower_bound <= (self.current_time - token.timestamp)
                    )
                )

                if valid_tokens < edge_data.weight:
                    return False

            elif isinstance(edge_data, Arc) and len(src_tokens) < edge_data.weight:
                return False

            elif (
                isinstance(edge_data, InhibitorArc)
                and len(src_tokens) >= edge_data.weight
            ):
                return False

        return True

    def fire_transition(self, transition_index) -> bool:
        if not self.graph[transition_index].active:
            return False

        in_edges = self.graph.in_edges(transition_index)
        out_edges = self.graph.out_edges(transition_index)

        for src_index, _, edge_data in in_edges:
            src_node_data = self.graph[src_index]

            if isinstance(edge_data, TimedArc):
                del src_node_data.tokens[: edge_data.weight]

            elif isinstance(edge_data, Arc):
                del src_node_data.tokens[: edge_data.weight]

        for src_index, _, edge_data in in_edges:
            src_node_data = self.graph[src_index]
            if isinstance(edge_data, ResetArc):
                del src_node_data.tokens[:]

        for _, dst_index, edge_data in out_edges:
            dst_node_data = self.graph[dst_index]

            if isinstance(edge_data, Arc) or isinstance(edge_data, TimedArc):
                dst_node_data.tokens.extend(
                    [Token(self.current_time) for _ in range(edge_data.weight)]
                )

            elif isinstance(edge_data, CustomArc):
                edge_data.timestamp = self.current_time

        self.evaluate()
        return True

    def who_can_fire(self) -> set[int]:
        return {
            transition
            for transition in self.graph.filter_nodes(
                lambda node: isinstance(node, Transition)
            )
            if self.can_fire_transition(transition)
        }

    def who_cant_fire(self) -> set[int]:
        return {
            transition
            for transition in self.graph.filter_nodes(
                lambda node: isinstance(node, Transition)
            )
            if not self.can_fire_transition(transition)
        }

    def pruned_graph(self) -> rx.PyDiGraph:
        # Remove inactive CustomArcs
        temp_graph = self.graph.copy()
        for edge_idx in temp_graph.edge_indices():
            edge_data = temp_graph.get_edge_data_by_index(edge_idx)
            if isinstance(edge_data, CustomArc) and not edge_data.active(
                self.current_time, self.memspec
            ):
                temp_graph.remove_edge_from_index(edge_idx)

        # Remove CMD_BUS and NAW places
        for place_idx in temp_graph.filter_nodes(lambda node: isinstance(node, Place)):
            place_data: Place = temp_graph[place_idx]
            if (
                place_data.place_type == PlaceType.CMD_BUS
                or place_data.place_type == PlaceType.NAW_Pool
            ):
                temp_graph.remove_node(place_idx)
                
        # Remove REFSB pools and flags
        for node_idx in temp_graph.node_indices():
            
            node_data = temp_graph[node_idx]
            if (
                isinstance(node_data, Place)
                and (node_data.place_type == PlaceType.REF_Pool
                     or node_data.place_type == PlaceType.REF_Flag)
            ):
                temp_graph.remove_node(node_idx)

        return temp_graph

    def write_dot(self, filename: str):
        return self.pruned_graph().to_dot(
            filename=filename, node_attr=node_viz, edge_attr=edge_viz
        )

    def write_img(self, filename: str, **kwargs):
        from rustworkx.visualization import graphviz_draw

        graphviz_draw(
            graph=self.pruned_graph(),
            filename=filename,
            node_attr_fn=node_viz,
            edge_attr_fn=edge_viz,
            method="dot",
            **kwargs,
        )


def node_viz(node_data: Place | Transition):
    attributes: dict[str, str] = {}

    if isinstance(node_data, Place):
        attributes["label"] = "•" * len(node_data.tokens)
        attributes["xlabel"] = f"{node_data.place_type}"
        attributes["xlabelloc"] = "b"
        attributes["shape"] = "circle"

    if isinstance(node_data, Transition):
        attributes["label"] = f"{node_data.command}"
        attributes["shape"] = "rectangle"
        attributes["style"] = "filled"
        attributes["fillcolor"] = "green" if node_data.active else "red"

    return attributes


def edge_viz(edge_data: Arc | InhibitorArc | ResetArc | TimedArc | CustomArc):
    attributes: dict[str, str] = {}

    if isinstance(edge_data, ResetArc):
        attributes["color"] = "red"
        attributes["arrowhead"] = "normalnormal"

    if isinstance(edge_data, InhibitorArc):
        attributes["arrowhead"] = "dot"

    if type(edge_data) is Arc or isinstance(edge_data, InhibitorArc):
        attributes["label"] = f"{edge_data.weight}" if edge_data.weight > 1 else ""

    if isinstance(edge_data, TimedArc):
        attributes["color"] = "blue"
        attributes["fontcolor"] = "blue"

        label = f"[{edge_data.lower_bound},∞["
        if edge_data.weight > 1:
            label += f"\n{edge_data.weight}"

        attributes["label"] = label

    if isinstance(edge_data, CustomArc):
        attributes["color"] = "blue"
        attributes["fontcolor"] = "blue"
        attributes["arrowhead"] = "diamond"
        attributes["label"] = f"{edge_data.time_constraint}"

    return attributes
