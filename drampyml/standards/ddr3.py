from drampyml.constraints.queries import extra_rank, intra_bank, intra_rank
from drampyml.common.syntax import Max
from drampyml.constraints.command_timing import (
    CommandTimingConstraint,
    populate_timing_arc,
)
from drampyml.components.petri_net import (
    Place,
    Arc,
    Transition,
    InhibitorArc,
    Token,
    ResetArc,
    TimedArc,
    PetriNet,
    PlaceType,
)
from drampyml.components.standard import Standard
from enum import Enum, auto
from sympy import Expr, Symbol
import rustworkx as rx
from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    rank: int | None
    bank: int | None


class Command(Enum):
    ACT = auto()
    RD = auto()
    WR = auto()
    RDA = auto()
    WRA = auto()
    PRE = auto()
    PREA = auto()
    REF = auto()
    PDE = auto()
    PDX = auto()
    SRE = auto()
    SRX = auto()

    def __str__(self):
        return self.name


ACT = Command.ACT
RD = Command.RD
WR = Command.WR
RDA = Command.RDA
WRA = Command.WRA
PRE = Command.PRE
PREA = Command.PREA
REF = Command.REF
PDE = Command.PDE
PDX = Command.PDX
SRE = Command.SRE
SRX = Command.SRX


@dataclass
class Parameters:
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    tCCD = Symbol("tCCD")
    tCKE = Symbol("tCKE")
    tPD = Symbol("tPD")
    tCKESR = Symbol("tCKESR")
    tRAS = Symbol("tRAS")
    tRC = Symbol("tRC")
    tRCD = Symbol("tRCD")
    tRFC = Symbol("tRFC")
    tRL = Symbol("tRL")
    tRP = Symbol("tRP")
    tRRD = Symbol("tRRD")
    tRTP = Symbol("tRTP")
    tFAW = Symbol("tFAW")
    tWL = Symbol("tWL")
    tRTRS = Symbol("tRTRS")
    tWR = Symbol("tWR")
    tAL = Symbol("tAL")
    tWTR = Symbol("tWTR")
    tXP = Symbol("tXP")
    tXS = Symbol("tXS")
    tXSDLL = Symbol("tXSDLL")
    tACTPDEN = Symbol("tACTPDEN")
    tPRPDEN = Symbol("tPRPDEN")
    tREFPDEN = Symbol("tREFPDEN")
    tCK = Symbol("tCK")


def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()

    for rank in range(memspec["nbrOfRanks"]):
        rank_coord = Coordinate(rank=rank, bank=None)

        t_refab = graph.add_node(Transition(REF, coordinate=rank_coord))
        t_preab = graph.add_node(Transition(PREA, coordinate=rank_coord))

        # PDN
        p_pdn = graph.add_node(Place(PlaceType.PDN, coordinate=rank_coord))
        t_pde = graph.add_node(Transition(PDE, coordinate=rank_coord))
        t_pdx = graph.add_node(Transition(PDX, coordinate=rank_coord))
        graph.add_edge(t_pde, p_pdn, Arc())
        graph.add_edge(p_pdn, t_pdx, Arc())

        # SREF
        p_sref = graph.add_node(Place(PlaceType.SREF, coordinate=rank_coord))
        t_srefen = graph.add_node(Transition(SRE, coordinate=rank_coord))
        t_srefex = graph.add_node(Transition(SRX, coordinate=rank_coord))
        p_sref_flag = graph.add_node(Place(PlaceType.SREF_FLAG, coordinate=rank_coord))
        graph.add_edge(t_srefen, p_sref, Arc())
        graph.add_edge(p_sref, t_srefex, Arc())
        graph.add_edge(t_srefex, p_sref_flag, Arc())
        graph.add_edge(p_sref_flag, t_refab, ResetArc())

        graph.add_edge(p_pdn, t_srefen, InhibitorArc())
        graph.add_edge(p_pdn, t_pde, InhibitorArc())
        graph.add_edge(p_pdn, t_refab, InhibitorArc())
        graph.add_edge(p_pdn, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_refab, InhibitorArc())
        graph.add_edge(p_sref, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_pde, InhibitorArc())
        graph.add_edge(p_sref, t_srefen, InhibitorArc())
        graph.add_edge(p_sref_flag, t_srefen, InhibitorArc())

        # FAW
        faw = graph.add_node(
            Place(
                PlaceType.NAW_Pool,
                coordinate=Coordinate(rank=rank, bank=None),
                tokens=[Token() for _ in range(4)],
            )
        )

        for bank in range(memspec["nbrOfBanks"]):
            bank_coord = Coordinate(rank=rank, bank=bank)
            p_active = graph.add_node(Place(PlaceType.ACTIVE, coordinate=bank_coord))

            t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
            t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
            t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
            t_pre = graph.add_node(Transition(PRE, coordinate=bank_coord))
            t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
            t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))

            graph.add_edge(t_act, p_active, Arc())

            graph.add_edge(p_active, t_rd, Arc())
            graph.add_edge(t_rd, p_active, Arc())

            graph.add_edge(p_active, t_wr, Arc())
            graph.add_edge(t_wr, p_active, Arc())

            graph.add_edge(p_active, t_rda, Arc())
            graph.add_edge(p_active, t_wra, Arc())

            graph.add_edge(t_act, faw, Arc())
            graph.add_edge(faw, t_act, TimedArc(weight=1, lower_bound=p.tFAW))

            graph.add_edge(p_active, t_preab, ResetArc())
            graph.add_edge(p_active, t_pre, ResetArc())

            graph.add_edge(p_active, t_act, InhibitorArc())
            graph.add_edge(p_active, t_refab, InhibitorArc())
            graph.add_edge(p_active, t_srefen, InhibitorArc())
            graph.add_edge(p_pdn, t_act, InhibitorArc())
            graph.add_edge(p_sref, t_act, InhibitorArc())
            graph.add_edge(p_pdn, t_pre, InhibitorArc())
            graph.add_edge(p_sref, t_pre, InhibitorArc())
            graph.add_edge(p_pdn, t_rd, InhibitorArc())
            graph.add_edge(p_pdn, t_wr, InhibitorArc())
            graph.add_edge(p_pdn, t_rda, InhibitorArc())
            graph.add_edge(p_pdn, t_wra, InhibitorArc())

    # CMDBUS
    cmd_bus = graph.add_node(
        Place(
            PlaceType.CMD_BUS,
            coordinate=Coordinate(rank=None, bank=None),
            tokens=[Token()],
        )
    )
    for transition_idx in graph.filter_nodes(lambda node: isinstance(node, Transition)):
        graph.add_edge(transition_idx, cmd_bus, Arc())
        graph.add_edge(cmd_bus, transition_idx, TimedArc(weight=1, lower_bound=p.tCK))

    for constraint in command_timing_constraints(p):
        populate_timing_arc(graph, constraint)

    return PetriNet(graph, memspec)


def command_timing_constraints(p: Parameters) -> list[CommandTimingConstraint]:
    tBURST = p.defaultBurstLength / p.dataRate * p.tCK
    tRDWR = p.tRL + tBURST + p.tCK * 2 - p.tWL
    tRDWR_R = p.tRL + tBURST + p.tRTRS - p.tWL
    tWRRD = p.tWL + tBURST + p.tWTR - p.tAL
    tWRRD_R = p.tWL + tBURST + p.tRTRS - p.tRL
    tWRPRE = p.tWL + tBURST + p.tWR
    tRDPDEN = p.tRL + tBURST + p.tCK
    tWRPDEN = p.tWL + tBURST + p.tWR
    tWRAPDEN = p.tWL + tBURST + p.tWR + p.tCK

    # fmt: off
    command_timing_constraints = [
        # Bank
        CommandTimingConstraint(intra_bank, [ACT], [PRE], p.tRAS),
        CommandTimingConstraint(intra_bank, [ACT], [RD, WR, RDA, WRA], p.tRCD - p.tAL),
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRC),
        CommandTimingConstraint(intra_bank, [RD], [PRE], p.tAL + p.tRTP),
        CommandTimingConstraint(intra_bank, [RD], [WR, WRA], tRDWR),
        CommandTimingConstraint(intra_bank, [RDA], [ACT], p.tAL + p.tRTP + p.tRP),
        CommandTimingConstraint(intra_bank, [WR], [PRE], tWRPRE),
        CommandTimingConstraint(intra_bank, [WR], [WR, WRA], p.tCCD),
        CommandTimingConstraint(intra_bank, [WR], [RD], tWRRD),
        CommandTimingConstraint(intra_bank, [WR], [RDA], Max(tWRRD, tWRPRE - p.tRTP - p.tAL)),
        CommandTimingConstraint(intra_bank, [WRA], [ACT], tWRPRE + p.tRP),
        CommandTimingConstraint(intra_bank, [PRE], [ACT], p.tRP),

        # Rank
        CommandTimingConstraint(intra_rank, [ACT], [PREA], p.tRAS),
        CommandTimingConstraint(intra_rank, [ACT], [ACT], p.tRRD),
        CommandTimingConstraint(intra_rank, [ACT], [PDE], p.tACTPDEN),
        CommandTimingConstraint(intra_rank, [ACT], [REF, SRE], p.tRC),
        CommandTimingConstraint(intra_rank, [RD], [PREA], p.tAL + p.tRTP),
        CommandTimingConstraint(intra_rank, [RD, RDA], [PDE], tRDPDEN),
        CommandTimingConstraint(intra_rank, [RD, RDA], [RD, RDA], p.tCCD),
        CommandTimingConstraint(intra_rank, [RD, RDA], [WR, WRA], tRDWR),
        CommandTimingConstraint(intra_rank, [RDA], [REF], p.tAL + p.tRTP + p.tRP),
        CommandTimingConstraint(intra_rank, [RDA], [PREA], p.tAL + p.tRTP),
        CommandTimingConstraint(intra_rank, [RDA], [SRE], Max(tRDPDEN, p.tAL + p.tRTP + p.tRP)),
        CommandTimingConstraint(intra_rank, [WR], [PDE], tWRPDEN),
        CommandTimingConstraint(intra_rank, [WRA], [PDE], tWRAPDEN),
        CommandTimingConstraint(intra_rank, [WR, WRA], [WR, WRA], p.tCCD),
        CommandTimingConstraint(intra_rank, [WR, WRA], [RD, RDA], tWRRD),
        CommandTimingConstraint(intra_rank, [WRA], [REF], tWRPRE + p.tRP),
        CommandTimingConstraint(intra_rank, [WRA], [PREA], tWRPRE),
        CommandTimingConstraint(intra_rank, [WRA], [SRE], Max(tWRAPDEN, tWRPRE + p.tRP)),
        CommandTimingConstraint(intra_rank, [PRE], [REF], p.tRP),
        CommandTimingConstraint(intra_rank, [PRE], [PDE], p.tPRPDEN),
        CommandTimingConstraint(intra_rank, [PRE], [SRE], p.tRP),
        CommandTimingConstraint(intra_rank, [PREA], [ACT, REF, SRE], p.tRP),
        CommandTimingConstraint(intra_rank, [PREA], [PDE], p.tPRPDEN),
        CommandTimingConstraint(intra_rank, [PDE], [PDX], p.tPD),
        CommandTimingConstraint(intra_rank, [PDX], [PDE], p.tCKE),
        CommandTimingConstraint(intra_rank, [PDX], [ACT, REF, SRE, PRE, PREA, RD, RDA, WR, WRA], p.tXP),
        CommandTimingConstraint(intra_rank, [REF], [ACT, REF, SRE], p.tRFC),
        CommandTimingConstraint(intra_rank, [REF], [PDE], p.tREFPDEN),
        CommandTimingConstraint(intra_rank, [SRX], [ACT, REF, PDE, SRE], p.tXS),
        CommandTimingConstraint(intra_rank, [SRX], [RD, RDA, WR, WRA], p.tXSDLL),
        CommandTimingConstraint(intra_rank, [SRX], [SRX], p.tCKESR),

        # Channel
        CommandTimingConstraint(extra_rank, [RD, RDA], [RD, RDA], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [RD, RDA], [WR, WRA], tRDWR_R),
        CommandTimingConstraint(extra_rank, [WR, WRA], [WR, WRA], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [WR, WRA], [RD, RDA], tWRRD_R),
    ]
    # fmt: on
    return command_timing_constraints


def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)
