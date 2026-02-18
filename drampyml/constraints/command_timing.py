from drampyml.common.commands import Command
from drampyml.components.petri_net import Transition, CustomArc
from drampyml.components.petri_net import Coordinate

from dataclasses import dataclass
from typing import Callable
from sympy import Expr
import rustworkx as rx
import itertools

@dataclass(frozen=True, eq=True)
class CommandTimingConstraint:
    """
    Defines a set of constraints based on a target selector, commands and conditions.
    """

    target_selector: Callable[[Coordinate, Coordinate], bool]
    previous_commands: list[Command]
    next_commands: list[Command]
    timing: Expr


def populate_timing_arc(graph: rx.PyDiGraph, constraint: CommandTimingConstraint):
    from_transitions = graph.filter_nodes(
        lambda node: isinstance(node, Transition)
        and node.command in constraint.previous_commands
    )
    to_transitions = graph.filter_nodes(
        lambda node: isinstance(node, Transition)
        and node.command in constraint.next_commands
    )
    product = itertools.product(from_transitions, to_transitions)

    for from_idx, to_idx in product:
        from_transition: Transition = graph[from_idx]
        to_transition: Transition = graph[to_idx]

        if not constraint.target_selector(
            from_transition.coordinate, to_transition.coordinate
        ):
            continue

        graph.add_edge(from_idx, to_idx, CustomArc(constraint.timing))
