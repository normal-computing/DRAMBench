# Based on JESD209-3
from drampyml.constraints.queries import extra_rank, intra_bank, intra_rank
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
from sympy import Expr, Symbol, Max
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
    REFPB = auto()
    REFAB = auto()
    PD = auto()
    PDX = auto()
    SREF = auto()
    SREFX = auto()
    DPD = auto()
    DPDX = auto()
    RESET = auto()

    def __str__(self):
        return self.name


ACT = Command.ACT
RD = Command.RD
WR = Command.WR
RDA = Command.RDA
WRA = Command.WRA
PR = Command.PR
PRA = Command.PRA
REFPB = Command.REFPB
REFAB = Command.REFAB
PD = Command.PD
PDX = Command.PDX
DPD = Command.DPD
DPDX = Command.DPDX
SREF = Command.SREF
SREFX = Command.SREFX
RESET= Command.RESET


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
    tAL = Symbol("tAL")
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
    tCKESR = Symbol("tCKESR") # (p115, tab63)
    tINIT3 = Symbol("tINIT3") # (p68, fig63)
    tDPD = Symbol("tDPD") # (p68, fig63)
    tRPab = Symbol("tRPab")
    tRPpb = Symbol("tRPpb")
    tDQSCK = Symbol("tDQSCK")
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    nbrOfBanks = Symbol("nbrOfBanks")
    nbrOfRanks = Symbol("nbrOfRanks")
    tRESET = Symbol("tRESET")
    

def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()

    for rank in range(memspec["nbrOfRanks"]):
        rank_coord = Coordinate(rank=rank, bank=None)
        p = Parameters()
        
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
        
        b0_refpb_flag = None
        prior_refpb = None

        for bank in range(memspec["nbrOfBanks"]):
            bank_coord = Coordinate(rank=rank, bank=bank)
            p_active = graph.add_node(Place(PlaceType.ACTIVE, coordinate=bank_coord))
            p_refpb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))

            t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
            t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
            t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
            t_pre = graph.add_node(Transition(PR, coordinate=bank_coord))
            t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
            t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))
            t_refpb = graph.add_node(Transition(REFPB, coordinate=bank_coord))

            graph.add_edge(t_act, p_active, Arc())

            graph.add_edge(p_active, t_rd, Arc())
            graph.add_edge(t_rd, p_active, Arc())

            graph.add_edge(p_active, t_wr, Arc())
            graph.add_edge(t_wr, p_active, Arc())

            graph.add_edge(p_active, t_rda, Arc())
            graph.add_edge(p_active, t_wra, Arc())

            graph.add_edge(t_act, faw, Arc())
            graph.add_edge(faw, t_act, TimedArc(weight=1, lower_bound=p.tFAW))
            
            graph.add_edge(t_refpb, faw, Arc())
            graph.add_edge(faw, t_refpb, TimedArc(weight=1, lower_bound=p.tFAW))
            
            # REFPB
            if memspec["nbrOfBanks"] > 1:
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
                    graph.add_edge(p_sref_flag, t_refpb, ResetArc())

                graph.add_edge(p_refpb_local, t_refab, ResetArc())
                graph.add_edge(p_refpb_local, t_srefex, ResetArc())
            
            graph.add_edge(p_active, t_preab, ResetArc())
            graph.add_edge(p_active, t_pre, ResetArc())

            graph.add_edge(p_active, t_act, InhibitorArc())
            graph.add_edge(p_active, t_refab, InhibitorArc())
            graph.add_edge(p_active, t_refpb, InhibitorArc())
            graph.add_edge(p_active, t_srefen, InhibitorArc())
            graph.add_edge(p_active, t_dpd, InhibitorArc())
            graph.add_edge(p_on, t_act, InhibitorArc())
            graph.add_edge(p_on, t_pre, InhibitorArc())
            graph.add_edge(p_on, t_refpb, InhibitorArc())
            graph.add_edge(p_sref, t_pre, InhibitorArc())
            graph.add_edge(p_sref, t_act, InhibitorArc())
            graph.add_edge(p_sref, t_refpb, InhibitorArc())
            graph.add_edge(p_dpd, t_act, InhibitorArc())
            graph.add_edge(p_dpd, t_refpb, InhibitorArc())
            graph.add_edge(p_pdn, t_act, InhibitorArc())
            graph.add_edge(p_pdn, t_refpb, InhibitorArc())
            graph.add_edge(p_pdn, t_pre, InhibitorArc())
            graph.add_edge(p_dpd, t_pre, InhibitorArc())
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
    tRDWR = p.tRL + p.tDQSCK + tBURST + p.tCK - p.tWL       # (p31, fig13)
    tRDWR_R = p.tRL + tBURST + p.tRTRS - p.tWL
    tWRRD = p.tWL + p.tCK + tBURST + p.tWTR                 # (p34, fig19)
    tWRRD_R = p.tWL + tBURST + p.tRTRS - p.tRL
    tRDPRE = tBURST + Max(4 * p.tCK, p.tRTP) - 4 * p.tCK    # (p39, tab11)
    tRDAACT = tRDPRE + p.tRPpb                              # (p39, tab11)
    tWRPRE = p.tWL + tBURST + p.tWR + p.tCK                 # (p39, tab11; p37)
    tWRAACT = p.tWL + tBURST + p.tWR + p.tCK + p.tRPpb      # (p39, tab11)
    tRDPDN = p.tRL + p.tDQSCK + tBURST + p.tCK              # (p64, fig54)
    tWRPDEN = p.tWL + p.tCK + tBURST + p.tWR                # (p65, fig56)
    tWRAPDEN = tWRPDEN + p.tCK                              # (p65, fig57)



    # fmt: off
    command_timing_constraints = [
        # Bank
        # (p25) 
        CommandTimingConstraint(intra_bank, [ACT], [PR], p.tRAS),
        # (p25)
        CommandTimingConstraint(intra_bank, [ACT], [RD, WR, RDA, WRA], p.tRCD),
        # (p25 fig3)
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRC),
        # (p40 + p41, tab12)
        CommandTimingConstraint(intra_bank, [ACT], [REFPB], p.tRRD),
        # (p39, tab11)
        CommandTimingConstraint(intra_bank, [RD], [PR], tRDPRE),
        # (p39, tab11)
        CommandTimingConstraint(intra_bank, [RDA], [ACT], tRDAACT),
        # (Delay RD->PRE + PRE->REF) 
        CommandTimingConstraint(intra_bank, [RDA], [REFPB], tRDPRE + p.tRPpb),
        # (p39, tab11)
        CommandTimingConstraint(intra_bank, [WR], [PR], tWRPRE),
        # (p34, fig19)
        CommandTimingConstraint(intra_bank, [WR], [RDA], tWRRD),
        # (p39, tab11)
        CommandTimingConstraint(intra_bank, [WRA], [ACT], tWRAACT),
        # (p38, fig25)
        CommandTimingConstraint(intra_bank, [WRA], [REFPB], tWRPRE + p.tRPpb),
        # (p25 fig3)
        CommandTimingConstraint(intra_bank, [PR], [ACT], p.tRPpb),
        # (p40)
        CommandTimingConstraint(intra_bank, [PR], [REFPB], p.tRPpb),
        # (p40)
        CommandTimingConstraint(intra_bank, [REFPB], [ACT, REFPB], p.tRFCpb),



        # Rank
        # (p25, fig3)
        CommandTimingConstraint(intra_rank, [ACT], [PRA], p.tRAS),
        # (p25, fig3)
        CommandTimingConstraint(intra_rank, [ACT], [ACT], p.tRRD),
        # [ACT->REFAB is invalid (p74, tab26, note 7). Otherwise delay RD->PRE + PRE->REFAB?]
        # CommandTimingConstraint(intra_rank, [ACT], [REFAB, SREF], tRCpb + tCK * 2),
        # (p41, tab12)
        CommandTimingConstraint(intra_rank, [ACT], [REFPB], p.tRRD),
        # (p39, tab11)
        CommandTimingConstraint(intra_rank, [RD, RDA], [PRA], tRDPRE),
        # (p64, fig54)
        CommandTimingConstraint(intra_rank, [RD, RDA], [PD, PD], tRDPDN),
        # (p39, tab11)
        CommandTimingConstraint(intra_rank, [RD, RDA], [RD, RDA], tBURST),
        # (p31, fig13)
        CommandTimingConstraint(intra_rank, [RD, RDA], [WR, WRA], tRDWR),
        # (Delay RD->PRE + PRE->REF) 
        CommandTimingConstraint(intra_rank, [RDA], [REFAB, SREF], tRDPRE + p.tRPpb),
        # (p39, tab11)
        CommandTimingConstraint(intra_rank, [WR, WRA], [PRA], tWRPRE),
        # (p65, fig 56)
        CommandTimingConstraint(intra_rank, [WR], [PD], tWRPDEN),
        # (p65, fig 57)
        CommandTimingConstraint(intra_rank, [WRA], [PD, PD], tWRAPDEN),
        # (p34, fig20)
        CommandTimingConstraint(intra_rank, [WR, WRA], [WR, WRA], p.tCCD),
        # (p34, fig19)
        CommandTimingConstraint(intra_rank, [WR, WRA], [RD, RDA], tWRRD),
        # (Delay WR->PRE + PRE->REF) 
        CommandTimingConstraint(intra_rank, [WRA], [REFAB, SREF], tWRPRE + p.tRPpb),
        
        # CommandTimingConstraint(intra_rank, [PR, PRA], [PR, PRA], tPPD), # (p39, tab11: tCK)
        CommandTimingConstraint(intra_rank, [PR], [REFAB, SREF], p.tRPpb),
        # (p25 fig3)
        CommandTimingConstraint(intra_rank, [PRA], [ACT], p.tRPab),
        # (p45 fig31)
        CommandTimingConstraint(intra_rank, [PRA], [REFAB, SREF, REFPB], p.tRPab),
        # (p6, fig51)
        CommandTimingConstraint(intra_rank, [PD], [PDX], p.tCKE),
        # (p6, fig51)
        CommandTimingConstraint(intra_rank, [PD], [PDX], p.tCKE),
        # (p6, fig51)
        CommandTimingConstraint(intra_rank, [PDX], [PD], p.tCKE),
        # (p6, fig51)
        CommandTimingConstraint(intra_rank, [PDX], [PD], p.tCKE),
        # (p63, sec4.13)
        CommandTimingConstraint(intra_rank, [PDX], [REFAB, REFPB, SREF, ACT], p.tXP),
        # (p63, sec4.13)
        CommandTimingConstraint(intra_rank, [PDX], [ACT, PR, PRA, RD, RDA, WR, WRA, REFPB], p.tXP),
        # (p40)
        CommandTimingConstraint(intra_rank, [REFAB], [ACT, REFAB, REFPB, SREF], p.tRFCab),
        # (p40)
        CommandTimingConstraint(intra_rank, [REFPB], [REFAB, REFPB], p.tRFCpb),
        # (p40)
        CommandTimingConstraint(intra_rank, [REFPB], [ACT], p.tRRD),
        # (p74/75, Tab26, Note 5)
        CommandTimingConstraint(intra_rank, [REFPB], [PRA, SREF], p.tRFCpb),
        # (p115, tab63)
        CommandTimingConstraint(intra_rank, [SREFX], [ACT, REFAB, REFPB, PD, SREF], p.tXSR),
        # (p46 + p47, fig33)
        CommandTimingConstraint(intra_rank, [SREF], [SREFX], p.tCKESR),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [PRA], [DPD], p.tRFCab),
        # based on above
        CommandTimingConstraint(intra_rank, [REFPB], [DPD], p.tRFCab),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [PR], [DPD], p.tRPpb),
        # based on above
        CommandTimingConstraint(intra_rank, [REFPB], [DPD], p.tRFCpb),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [WRA], [DPD], tWRPRE + p.tRPpb),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [RDA], [DPD], tRDPRE + p.tRPpb),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [DPD], [DPDX], p.tDPD),
        # (p68, fig63)
        CommandTimingConstraint(intra_rank, [DPDX], [RESET], p.tINIT3),
        CommandTimingConstraint(intra_rank, [RESET], [ACT, PR, PRA, SREF, REFPB], p.tRESET),
        
        # extra_rank
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
