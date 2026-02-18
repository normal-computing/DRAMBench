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
    WR32 = auto()
    WRA32 = auto()
    PRE = auto()
    PREA = auto()
    REFAB = auto()
    REFPB = auto()
    REFPB_LAST = auto()
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
WR32 = Command.WR32
WRA32 = Command.WRA32
PRE = Command.PRE
PREA = Command.PREA
REFPB = Command.REFPB
REFAB = Command.REFAB
PDE = Command.PDE
PDX = Command.PDX
SRE = Command.SRE
SRX = Command.SRX


@dataclass
class Parameters:
    tRAS = Symbol("tRAS")
    tRCpb = Symbol("tRCpb")
    tCCD = Symbol("tCCD")
    tRTP = Symbol("tRTP")
    tRCD = Symbol("tRCD")
    tCK = Symbol("tCK")
    tRL = Symbol("tRL")
    tWL = Symbol("tWL")
    tWTR = Symbol("tWTR")
    tWPRE = Symbol("tWPRE")
    tRTRS = Symbol("tRTRS")
    tRRD = Symbol("tRRD")
    tWR = Symbol("tWR")
    tCKE = Symbol("tCKE")
    tXP = Symbol("tXP")
    tFAW = Symbol("tFAW")
    tSR = Symbol("tSR")
    tRFCpb = Symbol("tRFCpb")
    tRFCab = Symbol("tRFCab")
    tXSR = Symbol("tXSR")
    tPPD = Symbol("tPPD")
    tCMDCKE = Symbol("tCMDCKE")
    tDQSS = Symbol("tDQSS")
    tDQS2DQ = Symbol("tDQS2DQ")
    tRPST = Symbol("tRPST") 
    tRPab = Symbol("tRPab")
    tRPpb = Symbol("tRPpb")
    tDQSCK = Symbol("tDQSCK")
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")


def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()

    for rank in range(memspec["nbrOfRanks"]):
        rank_coord = Coordinate(rank=rank, bank=None)

        t_refab = graph.add_node(Transition(REFAB, coordinate=rank_coord))
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
        
        # REFPB
        p_refpb_pool = graph.add_node(Place(PlaceType.REF_Pool, coordinate=rank_coord))
        graph.add_edge(p_refpb_pool, t_refab, ResetArc())
        graph.add_edge(p_refpb_pool, t_srefen, ResetArc())
        refpb_last_set: set[int] = set()

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
            p_refpb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))
            
            t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
            t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
            t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
            t_wr32 = graph.add_node(Transition(WR32, coordinate=bank_coord))
            t_pre = graph.add_node(Transition(PRE, coordinate=bank_coord))
            t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
            t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))
            t_wra32 = graph.add_node(Transition(WRA32, coordinate=bank_coord))
            t_refpb = graph.add_node(Transition(REFPB, coordinate=bank_coord))
            t_refpb_last = graph.add_node(Transition(REFPB, coordinate=bank_coord))
            refpb_last_set.add(t_refpb_last)
            
            graph.add_edge(t_act, p_active, Arc())

            graph.add_edge(p_active, t_rd, Arc())
            graph.add_edge(t_rd, p_active, Arc())

            graph.add_edge(p_active, t_wr, Arc())
            graph.add_edge(p_active, t_wr32, Arc())
            graph.add_edge(t_wr, p_active, Arc())
            graph.add_edge(t_wr32, p_active, Arc())

            graph.add_edge(p_active, t_rda, Arc())
            graph.add_edge(p_active, t_wra, Arc())
            graph.add_edge(p_active, t_wra32, Arc())

            graph.add_edge(t_act, faw, Arc())
            graph.add_edge(faw, t_act, TimedArc(weight=1, lower_bound=p.tFAW))
            
            graph.add_edge(t_refpb, faw, Arc())
            graph.add_edge(faw, t_refpb, TimedArc(weight=1, lower_bound=p.tFAW))
            
            # REFPB
            graph.add_edge(p_refpb_pool, t_refpb, InhibitorArc(memspec["nbrOfBanks"] - 1))
            graph.add_edge(p_refpb_pool, t_refpb_last, Arc(memspec["nbrOfBanks"] - 1))
            graph.add_edge(t_refpb, p_refpb_pool, Arc())
            graph.add_edge(p_refpb_local, t_refpb_last, InhibitorArc())
            graph.add_edge(t_refpb, p_refpb_local, Arc())
            graph.add_edge(p_refpb_local, t_refpb, InhibitorArc())
            graph.add_edge(p_refpb_local, t_refab, ResetArc())
            graph.add_edge(p_refpb_local, t_srefen, ResetArc())
            graph.add_edge(p_sref_flag, t_refpb_last, ResetArc())
            # Intentionally commented out; gets done later
            # graph.add_edge(t_refpb_last, p_refpb_local, ResetArc())

            graph.add_edge(p_active, t_preab, ResetArc())
            graph.add_edge(p_active, t_pre, ResetArc())

            graph.add_edge(p_active, t_act, InhibitorArc())
            graph.add_edge(p_active, t_refab, InhibitorArc())
            graph.add_edge(p_active, t_refpb, InhibitorArc())
            graph.add_edge(p_active, t_srefen, InhibitorArc())
            graph.add_edge(p_sref, t_act, InhibitorArc())
            graph.add_edge(p_sref, t_pre, InhibitorArc())
            graph.add_edge(p_sref, t_refpb, InhibitorArc())
            graph.add_edge(p_pdn, t_act, InhibitorArc())
            graph.add_edge(p_pdn, t_refpb, InhibitorArc())
            graph.add_edge(p_pdn, t_pre, InhibitorArc())
            graph.add_edge(p_pdn, t_rd, InhibitorArc())
            graph.add_edge(p_pdn, t_wr, InhibitorArc())
            graph.add_edge(p_pdn, t_rda, InhibitorArc())
            graph.add_edge(p_pdn, t_wra, InhibitorArc())
            graph.add_edge(p_pdn, t_wr32, InhibitorArc())
            graph.add_edge(p_pdn, t_wra32, InhibitorArc())
            
        # Set the reset arcs for the local flags within the same rank
        for flag_idx in graph.filter_nodes(
            lambda node: isinstance(node, Place) 
            and node.place_type == PlaceType.REF_Flag
            and node.coordinate.rank == rank
        ):
            for trans_idx in refpb_last_set:
                graph.add_edge(flag_idx, trans_idx, ResetArc())

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
    tRDWR = p.tRL + p.tDQSCK + tBURST - p.tWL + p.tWPRE + p.tRPST
    tRDWR_R = p.tRL + tBURST + p.tRTRS - p.tWL
    tWRRD = p.tWL + p.tCK + tBURST + p.tWTR
    tWRRD_R = p.tWL + tBURST + p.tRTRS - p.tRL
    tRDPRE = p.tRTP + tBURST - p.tCK * 6
    tRDAACT = p.tRTP + p.tRPpb + tBURST - p.tCK * 8
    tWRPRE = p.tCK * 2 + p.tWL + p.tCK + tBURST + p.tWR
    tWRAACT = p.tWL + tBURST + p.tWR + p.tCK + p.tRPpb
    tACTPDEN = p.tCK * 3 + p.tCMDCKE
    tPRPDEN = p.tCK + p.tCMDCKE
    tRDPDEN = p.tCK * 3 + p.tRL + p.tDQSCK + tBURST + p.tRPST
    tWRPDEN = p.tCK * 3 + p.tWL + p.tDQSS + p.tDQS2DQ + tBURST + p.tWR
    tWRAPDEN = p.tCK * 3 + p.tWL + p.tDQSS + p.tDQS2DQ  + tBURST + p.tWR + p.tCK * 2
    tREFPDEN = p.tCK + p.tCMDCKE

    # fmt: off
    command_timing_constraints = [
        # intra_bank
        CommandTimingConstraint(intra_bank, [ACT], [PRE], p.tRAS + p.tCK * 2),
        CommandTimingConstraint(intra_bank, [ACT], [RD, WR, RDA, WRA, WR32, WRA32], p.tRCD),
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRCpb),
        CommandTimingConstraint(intra_bank, [ACT], [REFPB], p.tRCpb + p.tCK * 2),
        CommandTimingConstraint(intra_bank, [RD], [PRE], p.tRRD + p.tCK * 2),
        CommandTimingConstraint(intra_bank, [RDA, ], [ACT], tRDAACT),
        CommandTimingConstraint(intra_bank, [RDA, ], [REFPB], tRDPRE + p.tRPpb),
        CommandTimingConstraint(intra_bank, [WR, WR32], [PRE], tWRPRE),
        # CommandTimingConstraint(intra_bank, [WR, WRA], [MWR], tCCDMW, [LastBurstLength(32, inversed=True)]),
        # CommandTimingConstraint(intra_bank, [WR, WRA], [MWR], tCCDMW + tCK * 8, [LastBurstLength(32)]),
        CommandTimingConstraint(intra_bank, [WR, WR32], [RDA, ], Max(tWRRD, tWRPRE - tRDPRE)),
        CommandTimingConstraint(intra_bank, [WRA, WRA32], [ACT], tWRAACT),
        CommandTimingConstraint(intra_bank, [WRA, WRA32], [REFPB], tWRPRE + p.tRPpb),
        CommandTimingConstraint(intra_bank, [PRE], [ACT], p.tRPpb - p.tCK * 2),
        CommandTimingConstraint(intra_bank, [PRE], [REFPB], p.tRPpb),
        CommandTimingConstraint(intra_bank, [REFPB], [ACT], p.tRFCpb - p.tCK * 2),

        # intra_rank
        CommandTimingConstraint(intra_rank, [ACT], [PREA], p.tRAS + p.tCK * 2),
        CommandTimingConstraint(intra_rank, [ACT], [ACT], p.tRRD),
        CommandTimingConstraint(intra_rank, [ACT], [REFPB, SRE], p.tRCpb + p.tCK * 2),
        CommandTimingConstraint(intra_rank, [ACT], [REFAB], p.tRRD + p.tCK * 2), 
        CommandTimingConstraint(intra_rank, [ACT], [PDE], tACTPDEN),
        CommandTimingConstraint(intra_rank, [RD, RDA], [PREA], tRDPRE),
        CommandTimingConstraint(intra_rank, [RD, RDA], [PDE, PDE], tRDPDEN),
        CommandTimingConstraint(intra_rank, [RD, RDA], [RD, RDA], p.tCCD),
        CommandTimingConstraint(intra_rank, [RD, RDA], [WR, WRA, WR32, WRA32], tRDWR),
        CommandTimingConstraint(intra_rank, [RDA], [REFAB], tRDPRE + p.tRPpb),
        CommandTimingConstraint(intra_rank, [RDA], [SRE], Max(tRDPDEN, tRDPRE + p.tRPpb)),
        CommandTimingConstraint(intra_rank, [WR, WRA, WR32, WRA32], [PREA], tWRPRE),
        CommandTimingConstraint(intra_rank, [WR, WR32], [PDE], tWRPDEN),
        CommandTimingConstraint(intra_rank, [WRA, WRA32], [PDE, PDE], tWRAPDEN),
        CommandTimingConstraint(intra_rank, [WR, WRA], [WR, WRA, WR32, WRA32], p.tCCD), # Can the compiler optimize this better?
        CommandTimingConstraint(intra_rank, [WR32, WRA32], [WR, WRA, WR32, WRA32], p.tCCD + p.tCK * 8),
        CommandTimingConstraint(intra_rank, [WR, WRA, WR32, WRA32], [RD, RDA], tWRRD),
        CommandTimingConstraint(intra_rank, [WRA, WRA32], [REFAB], tWRPRE + p.tRPpb),
        CommandTimingConstraint(intra_rank, [WRA, WRA32], [SRE], Max(tWRAPDEN, tWRPRE + p.tRPpb)),
        CommandTimingConstraint(intra_rank, [PRE], [PRE, PREA], p.tPPD),
        CommandTimingConstraint(intra_rank, [PRE], [REFAB, SRE], p.tRPpb),
        CommandTimingConstraint(intra_rank, [PRE], [PDE, PDE], tPRPDEN),
        CommandTimingConstraint(intra_rank, [PREA], [ACT], p.tRPab - p.tCK * 2),
        CommandTimingConstraint(intra_rank, [PREA], [REFAB, SRE, REFPB], p.tRPab),
        CommandTimingConstraint(intra_rank, [PREA], [PDE], tPRPDEN),
        CommandTimingConstraint(intra_rank, [PDE], [PDX], p.tCKE),
        CommandTimingConstraint(intra_rank, [PDE], [PDX], p.tCKE),
        CommandTimingConstraint(intra_rank, [PDX], [PDE], p.tCKE),
        CommandTimingConstraint(intra_rank, [PDX], [PDE], p.tCKE),
        CommandTimingConstraint(intra_rank, [PDX], [REFAB, REFPB, SRE, ACT], p.tXP),
        CommandTimingConstraint(intra_rank, [PDX], [ACT, PRE, PREA, RD, RDA, WR, WRA, WR32, WRA32, REFPB], p.tXP),
        CommandTimingConstraint(intra_rank, [REFAB], [ACT], p.tRFCab - p.tCK * 2),
        CommandTimingConstraint(intra_rank, [REFAB], [PDE], tREFPDEN),
        CommandTimingConstraint(intra_rank, [REFAB], [REFAB, REFPB, SRE], p.tRFCab),
        CommandTimingConstraint(intra_rank, [REFPB], [REFAB, REFPB], p.tRFCpb),
        CommandTimingConstraint(intra_rank, [REFPB], [ACT], p.tRRD - p.tCK * 2),
        CommandTimingConstraint(intra_rank, [REFPB], [PREA, SRE], p.tRFCpb),
        CommandTimingConstraint(intra_rank, [REFPB], [PDE, PDE], tREFPDEN),
        CommandTimingConstraint(intra_rank, [SRX], [ACT], p.tXSR - p.tCK * 2),
        CommandTimingConstraint(intra_rank, [SRX], [REFAB, REFPB, PDE, SRE], p.tXSR),
        CommandTimingConstraint(intra_rank, [SRE], [SRX], p.tSR),

        # extra_rank
        CommandTimingConstraint(extra_rank, [RD, RDA], [RD, RDA], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [RD, RDA], [WR, WRA, WR32, WRA32], tRDWR_R),
        CommandTimingConstraint(extra_rank, [WR, WRA, WR32, WRA32], [WR, WRA, WR32, WRA32], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [WR, WRA, WR32, WRA32], [RD, RDA], tWRRD_R),
    ]
    # fmt: on
    return command_timing_constraints


def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)
