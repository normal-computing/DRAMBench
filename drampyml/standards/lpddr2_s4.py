# Based on JESD209-3
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
    PR = auto()
    PRA = auto()
    REFAB = auto()
    REFPB = auto()
    PD = auto()
    PDX = auto()
    SREF = auto()
    SREFX = auto()
    DPD = auto()
    DPDX = auto()
    RESET = auto()
    BST = auto()

    def __str__(self):
        return self.name


ACT = Command.ACT
RD = Command.RD
WR = Command.WR
RDA = Command.RDA
WRA = Command.WRA
PR = Command.PR
PRA = Command.PRA
REFAB = Command.REFAB
REFPB = Command.REFPB
PD = Command.PD
PDX = Command.PDX
DPD = Command.DPD
DPDX = Command.DPDX
SREF = Command.SREF
SREFX = Command.SREFX
RESET = Command.RESET
BST = Command.BST


@dataclass
class Parameters:
    tRAS = Symbol("tRAS")
    tRC = Symbol("tRC")
    tCCD = Symbol("tCCD")
    tRTP = Symbol("tRTP")
    tRCD = Symbol("tRCD")
    tCK = Symbol("tCK")
    tRL = Symbol("tRL")
    tWL = Symbol("tWL")
    tWTR = Symbol("tWTR")
    tRTRS = Symbol("tRTRS")
    tRRD = Symbol("tRRD")
    tWR = Symbol("tWR")
    tCKE = Symbol("tCKE")
    tXP = Symbol("tXP")
    tFAW = Symbol("tFAW")
    tCKESR = Symbol("tCKESR")
    tRFCpb = Symbol("tRFCpb")
    tRFCab = Symbol("tRFCab")
    tXSR = Symbol("tXSR")
    tCKESR = Symbol("tCKESR") 
    tINIT3 = Symbol("tINIT3") 
    tDPD = Symbol("tDPD") 
    tRPab = Symbol("tRPab")
    tRPpb = Symbol("tRPpb")
    tDQSCK = Symbol("tDQSCK")
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    nbrOfBanks = Symbol("nbrOfBanks")
    nbrOfRanks = Symbol("nbrOfRanks")


def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()
    
    for rank in range(memspec["nbrOfRanks"]):
        rank_coord = Coordinate(rank=rank, bank=None)

        t_refab = graph.add_node(Transition(REFAB, coordinate=rank_coord))
        t_preab = graph.add_node(Transition(PRA, coordinate=rank_coord))

        # PDN
        p_pdn = graph.add_node(Place(PlaceType.PDN, coordinate=rank_coord))
        t_pde = graph.add_node(Transition(PD, coordinate=rank_coord))
        t_pdx = graph.add_node(Transition(PDX, coordinate=rank_coord))
        graph.add_edge(t_pde, p_pdn, Arc())
        graph.add_edge(p_pdn, t_pdx, Arc())
        
        # DPD
        p_dpd = graph.add_node(Place(PlaceType.DPD, coordinate=rank_coord))
        p_on = graph.add_node(Place(PlaceType.PWR_ON, coordinate=rank_coord))
        t_dpd = graph.add_node(Transition(DPD, coordinate=rank_coord))
        t_dpdx = graph.add_node(Transition(DPDX, coordinate=rank_coord))
        t_reset = graph.add_node(Transition(RESET, coordinate=rank_coord))
        graph.add_edge(t_dpd, p_dpd, Arc())
        graph.add_edge(p_dpd, t_dpdx, Arc())
        graph.add_edge(t_dpdx, p_on, Arc())
        graph.add_edge(p_on, t_reset, Arc())

        # SREF
        p_sref = graph.add_node(Place(PlaceType.SREF, coordinate=rank_coord))
        t_srefen = graph.add_node(Transition(SREF, coordinate=rank_coord))
        t_srefex = graph.add_node(Transition(SREFX, coordinate=rank_coord))
        p_sref_flag = graph.add_node(Place(PlaceType.SREF_FLAG, coordinate=rank_coord))
        graph.add_edge(t_srefen, p_sref, Arc())
        graph.add_edge(p_sref, t_srefex, Arc())
        graph.add_edge(t_srefex, p_sref_flag, Arc())
        graph.add_edge(p_sref_flag, t_refab, ResetArc())

        graph.add_edge(p_pdn, t_srefen, InhibitorArc())
        graph.add_edge(p_pdn, t_pde, InhibitorArc())
        graph.add_edge(p_pdn, t_dpd, InhibitorArc())
        graph.add_edge(p_pdn, t_refab, InhibitorArc())
        graph.add_edge(p_pdn, t_preab, InhibitorArc())
        graph.add_edge(p_dpd, t_srefen, InhibitorArc())
        graph.add_edge(p_dpd, t_pde, InhibitorArc())
        graph.add_edge(p_dpd, t_dpd, InhibitorArc())
        graph.add_edge(p_dpd, t_refab, InhibitorArc())
        graph.add_edge(p_dpd, t_preab, InhibitorArc())
        graph.add_edge(p_on, t_srefen, InhibitorArc())
        graph.add_edge(p_on, t_pde, InhibitorArc())
        graph.add_edge(p_on, t_dpd, InhibitorArc())
        graph.add_edge(p_on, t_refab, InhibitorArc())
        graph.add_edge(p_on, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_refab, InhibitorArc())
        graph.add_edge(p_sref, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_pde, InhibitorArc())
        graph.add_edge(p_sref, t_dpd, InhibitorArc())
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
            t_pre = graph.add_node(Transition(PR, coordinate=bank_coord))
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
            graph.add_edge(p_active, t_dpd, InhibitorArc())
            graph.add_edge(p_pdn, t_act, InhibitorArc())
            graph.add_edge(p_dpd, t_act, InhibitorArc())
            graph.add_edge(p_on, t_act, InhibitorArc())
            graph.add_edge(p_sref, t_act, InhibitorArc())
            graph.add_edge(p_pdn, t_pre, InhibitorArc())
            graph.add_edge(p_dpd, t_pre, InhibitorArc())
            graph.add_edge(p_on, t_pre, InhibitorArc())
            graph.add_edge(p_sref, t_pre, InhibitorArc())
            graph.add_edge(p_pdn, t_rd, InhibitorArc())
            graph.add_edge(p_pdn, t_wr, InhibitorArc())
            graph.add_edge(p_pdn, t_rda, InhibitorArc())
            graph.add_edge(p_pdn, t_wra, InhibitorArc())
            
            # REFPB
            if memspec["nbrOfBanks"] == 8:
                p_refpb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))
                t_refpb = graph.add_node(Transition(REFPB, coordinate=bank_coord))

                if b0_refpb_flag:
                    graph.add_edge(p_refpb_local, t_refpb, Arc())
                    graph.add_edge(prior_refpb, p_refpb_local, Arc())
                else: 
                    b0_refpb_flag = p_refpb_local
                    graph.add_edge(t_refpb, p_refpb_local, Arc())
                    graph.add_edge(p_refpb_local, t_refpb, InhibitorArc())
                    
                prior_refpb = t_refpb
                if bank == memspec["nbrOfBanks"] - 1:
                    graph.add_edge(b0_refpb_flag, t_refpb, ResetArc())

                graph.add_edge(t_refpb, faw, Arc())
                graph.add_edge(faw, t_refpb, TimedArc(weight=1, lower_bound=p.tFAW))
                graph.add_edge(p_refpb_local, t_refab, ResetArc())
                graph.add_edge(p_refpb_local, t_srefex, ResetArc())
                graph.add_edge(p_active, t_refpb, InhibitorArc())
                graph.add_edge(p_sref, t_refpb, InhibitorArc())
                graph.add_edge(p_dpd, t_refpb, InhibitorArc())
                graph.add_edge(p_pdn, t_refpb, InhibitorArc())
                graph.add_edge(p_on, t_refpb, InhibitorArc())

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
    tRDWR = p.tRL + p.tDQSCK + tBURST + p.tCK - p.tWL   # (p90)
    tRDWR_R = p.tRL + tBURST + p.tRTRS - p.tWL
    tWRRD = p.tWL + tBURST + p.tWTR + p.tCK             # (p116, tab52)
    tWRRD_R = p.tWL + tBURST + p.tRTRS - p.tRL
    tRDPRE = tBURST + p.tRTP - p.tCK                    # (p116, tab52) [S4 specific] 
    tRDAACT = tRDPRE + p.tRPpb                          # p116, tab52) [S4 specific] 
    tWRPRE = p.tWL + tBURST + p.tWR + p.tCK             # (p116, tab52)
    tWRAACT = p.tWL + tBURST + p.tWR + p.tCK + p.tRPpb  # (p116, tab52)
    tRDPDN = p.tRL + p.tDQSCK + tBURST + p.tCK          # (p140, fig95/96, Note1)
    tWRPDEN = p.tWL + p.tCK + tBURST + p.tWR            # (p141, fig97, Note1)
    tWRAPDEN = tWRPDEN + p.tCK                          # (p142, fig99, Note1)
    

    # fmt: off
    command_timing_constraints = [
        # Bank
        # (p81, fig19)
        CommandTimingConstraint(intra_bank, [ACT], [PR], p.tRAS),
        # (p81)
        CommandTimingConstraint(intra_bank, [ACT], [RD, WR, RDA, WRA], p.tRCD),
        # (p81, fig19)
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRC),
        # (p116, tab52) [S4 specific] 
        CommandTimingConstraint(intra_bank, [RD], [PR], tRDPRE),
        # (p116, tab52) [S4 specific] 
        CommandTimingConstraint(intra_bank, [RDA], [ACT], tRDAACT),
        # TODO [PLEASE CHECK] (Delay RD->PRE + PRE->REFPB) 
        CommandTimingConstraint(intra_bank, [RDA], [REFPB], tRDPRE + p.tRRD),
        # (p116, tab52)
        CommandTimingConstraint(intra_bank, [WR], [PR], tWRPRE),
        # (p116, tab52)
        CommandTimingConstraint(intra_bank, [WR], [RDA], tWRRD),
        # (p116, tab52)
        CommandTimingConstraint(intra_bank, [WRA], [ACT], tWRAACT),
        # TODO [PLEASE CHECK] (Delay WR->PRE + PRE->REFPB) 
        CommandTimingConstraint(intra_bank, [WRA], [REFPB], tWRPRE + p.tRPpb),
        # (p81, fig19)
        CommandTimingConstraint(intra_bank, [PR], [ACT], p.tRPpb),
        # (p117/118, tab53)
        CommandTimingConstraint(intra_bank, [PR], [REFPB], p.tRPpb),
        # (p117/118 tab53)
        CommandTimingConstraint(intra_bank, [REFPB], [ACT, REFPB], p.tRFCpb),
        # (p116, tab51)
        CommandTimingConstraint(intra_bank, [BST], [PR], p.tWL + tBURST + p.tWR + p.tCK),



        # Rank
        # (p81, fig19)
        CommandTimingConstraint(intra_rank, [ACT], [PRA], p.tRAS),
        # (p81/82, fig19/20; p118, tab53)
        CommandTimingConstraint(intra_rank, [ACT], [ACT], p.tRRD),
        # (p117/118, tab53)
        CommandTimingConstraint(intra_rank, [ACT], [REFPB], p.tRRD),
        # (p116, tab52) [S4 specific] 
        CommandTimingConstraint(intra_rank, [RD, RDA], [PRA], tRDPRE),
        # (p140, fig95)
        CommandTimingConstraint(intra_rank, [RD, RDA], [PD], tRDPDN),
        # (p91)
        CommandTimingConstraint(intra_rank, [RD], [RD, RDA], Max(p.tCCD, tBURST/2)),
        # (p91, Note6)
        CommandTimingConstraint(intra_rank, [RDA], [RD, RDA], Max(p.tCCD, tBURST)),
        # (p90)
        CommandTimingConstraint(intra_rank, [RD, RDA], [WR, WRA], tRDWR),
        # TODO [PLEASE CHECK] (Delay RD->PRE + PRE->REFPB) 
        CommandTimingConstraint(intra_rank, [RDA], [REFAB, SREF], tRDPRE + p.tRPpb),
        # (p116, tab52)
        CommandTimingConstraint(intra_rank, [WR, WRA], [PRA], tWRPRE),
        # (p141, fig97, Note1)
        CommandTimingConstraint(intra_rank, [WR], [PD], tWRPDEN),
        # (p142, fig99, Note1)
        CommandTimingConstraint(intra_rank, [WRA], [PD], tWRAPDEN),
        # (p116, tab52)
        CommandTimingConstraint(intra_rank, [WR, WRA], [WR, WRA], tBURST),
        # (p116, tab52)
        CommandTimingConstraint(intra_rank, [WR, WRA], [RD, RDA], tWRRD),
        # TODO [PLEASE CHECK] (Delay WR->PRE + PRE->REFPB) 
        CommandTimingConstraint(intra_rank, [WRA], [REFAB, SREF], tWRPRE + p.tRPpb),
        # (p116, tab51)
        CommandTimingConstraint(intra_rank, [BST], [PRA], p.tWL + tBURST + p.tWR + p.tCK),
        # (p117)
        CommandTimingConstraint(intra_rank, [PR], [REFAB, SREF], p.tRPpb),
        # (p81, fig19)
        CommandTimingConstraint(intra_rank, [PRA], [ACT], p.tRPab),
        # (p123, fig76)
        CommandTimingConstraint(intra_rank, [PRA], [REFAB, SREF, REFPB], p.tRPab),
        # (p138, fig91)
        CommandTimingConstraint(intra_rank, [PD], [PDX], p.tCKE),
        # (p138, fig91)
        # CommandTimingConstraint(intra_rank, [PDEA], [PDXA], tCKE),
        # (p138, fig91)
        CommandTimingConstraint(intra_rank, [PDX], [PD], p.tCKE),
        # (p138, fig91)
        # CommandTimingConstraint(intra_rank, [PDXP], [PDEP], tCKE),
        # (p138, fig91)
        CommandTimingConstraint(intra_rank, [PDX], [REFAB, REFPB, SREF, ACT, PR, PRA, RD, RDA, WR, WRA], p.tXP),
        # (p138, fig91)
        # CommandTimingConstraint(intra_rank, [PDX], [ACT, PR, PRA, RD, RDA, WR, WRA, REFPB], tXP),
        # (p118, tab53)
        CommandTimingConstraint(intra_rank, [REFAB], [ACT, REFAB, REFPB, SREF], p.tRFCab),
        # (p118, tab53)
        CommandTimingConstraint(intra_rank, [REFPB], [REFAB, REFPB], p.tRFCpb),
        # (p118, tab53)
        CommandTimingConstraint(intra_rank, [REFPB], [ACT], p.tRRD),
        # (p117/118, indirect)
        CommandTimingConstraint(intra_rank, [REFPB], [PRA, SREF], p.tRFCpb),
        # (p125, fig78)
        CommandTimingConstraint(intra_rank, [SREFX], [ACT, REFAB, REFPB, PD, SREF], p.tXSR),
        # (p125, fig78)
        CommandTimingConstraint(intra_rank, [SREF], [SREFX], p.tCKESR),
        
        # TODO: Please check the DPD timings again
        # (p145, fig105)
        CommandTimingConstraint(intra_rank, [PRA, REFAB], [DPD], p.tRPab),
        # based on above
        CommandTimingConstraint(intra_rank, [REFAB], [DPD], p.tRFCab),
        # (p145, fig105)
        CommandTimingConstraint(intra_rank, [PR, REFPB], [DPD], p.tRPpb),
        # based on above
        CommandTimingConstraint(intra_rank, [REFAB], [DPD], p.tRFCab),
        # (p145, fig105)
        CommandTimingConstraint(intra_rank, [WRA], [DPD], tWRPRE + p.tRPpb),
        # (p145, fig105)
        CommandTimingConstraint(intra_rank, [RDA], [DPD], tRDPRE + p.tRPpb),
        # (p202, tab103)
        CommandTimingConstraint(intra_rank, [DPD], [DPDX], p.tDPD),
        # (p145, fig105)
        CommandTimingConstraint(intra_rank, [DPDX], [RESET], p.tINIT3),
        
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