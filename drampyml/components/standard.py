from .petri_net import PetriNet

from dataclasses import dataclass
from sympy import Expr


@dataclass
class Standard:
    petri_net: PetriNet
    memspec: dict[Expr, int]
