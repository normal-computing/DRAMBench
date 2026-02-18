from drampyml.common.commands import Command
from drampyml.components.petri_net import Coordinate

from dataclasses import dataclass
from typing import Callable
from sympy import Expr


@dataclass(frozen=True)
class FAWConstraint:
    """
    Four-active window constraint affecting a component
    level and a set of commands.
    """

    commands: list[Command]
    target_selector: Callable[[Coordinate], bool]
    timing: Expr
