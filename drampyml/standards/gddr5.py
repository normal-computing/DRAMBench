from drampyml.constraints.queries import extra_rank, intra_bank
from drampyml.constraints.command_timing import CommandTimingConstraint, populate_timing_arc
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
    bank_group: int | None
    bank: int | None


class Command(Enum):
    ACT = auto()
    PDEA = auto()
    PDEP = auto()
    PDXA = auto()
    PDXP = auto()
    PREA = auto()
    REFA = auto()
    SREFEN = auto()
    SREFEX = auto()
    
    PRE = auto()
    RD = auto()
    RDA = auto()
    WR = auto()
    WRA = auto()
    REFB = auto()
    
    # Simplified commands
    PDE = auto() 
    PDX = auto()
    
    REFB_LAST = auto()

    def __str__(self):
        return self.name


ACT = Command.ACT
PDE = Command.PDE
PDX = Command.PDX
PRE = Command.PRE
PREA = Command.PREA
RD = Command.RD
RDA = Command.RDA
REFA = Command.REFA
REFB = Command.REFB
SREFEN = Command.SREFEN
SREFEX = Command.SREFEX
WR = Command.WR
WRA = Command.WRA
REFB_LAST = Command.REFB_LAST

# Links to simplified commands
PDEA = PDE
PDEP = PDE
PDXA = PDX
PDXP = PDX


@dataclass
class Parameters:
    tRAS = Symbol("tRAS")
    tRCDRD = Symbol("tRCDRD")
    tRCDWR = Symbol("tRCDWR")
    tRC = Symbol("tRC")
    tRP = Symbol("tRP")
    tRTP = Symbol("tRTP")
    tCCDL = Symbol("tCCDL")
    tRTW = Symbol("tRTW")
    tRFCPB = Symbol("tRFCPB")
    tWRPRE = Symbol("tWRPRE")
    tWRRD_L = Symbol("tWRRD_L")
    tRRDL = Symbol("tRRDL")
    tPPD = Symbol("tPPD")
    tRREFD = Symbol("tRREFD")
    tRRDS = Symbol("tRRDS")
    tPD = Symbol("tPD")
    tXPN = Symbol("tXPN")
    tRDSRE = Symbol("tRDSRE")
    tCCDS = Symbol("tCCDS")
    tRFC = Symbol("tRFC")
    tCKE = Symbol("tCKE")
    tLK = Symbol("tLK")
    tXS = Symbol("tXS")
    tWRSRE = Symbol("tWRSRE")
    tWRRD_S = Symbol("tWRRD_S")
    tRDWR_R = Symbol("tRDWR_R")
    tWRRD_R = Symbol("tWRRD_R")
    tRTRS = Symbol("tRTRS")
    tFAW = Symbol("tFAW")
    t32AW = Symbol("t32AW")
    tCK = Symbol("tCK")
    
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")


def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()
    
    banksPerGroup = int(memspec["nbrOfBanks"] // memspec["nbrOfBankGroups"])

    base_coord = Coordinate(bank_group=None, bank=None)

    t_refab = graph.add_node(Transition(REFA, coordinate=base_coord))
    t_preab = graph.add_node(Transition(PREA, coordinate=base_coord))

    # PDN
    p_pdn = graph.add_node(Place(PlaceType.PDN, coordinate=base_coord))
    t_pde = graph.add_node(Transition(PDE, coordinate=base_coord))
    t_pdx = graph.add_node(Transition(PDX, coordinate=base_coord))
    graph.add_edge(t_pde, p_pdn, Arc())
    graph.add_edge(p_pdn, t_pdx, Arc())

    # SREF
    p_sref = graph.add_node(Place(PlaceType.SREF, coordinate=base_coord))
    t_srefen = graph.add_node(Transition(SREFEN, coordinate=base_coord))
    t_srefex = graph.add_node(Transition(SREFEX, coordinate=base_coord))
    p_sref_flag = graph.add_node(Place(PlaceType.SREF_FLAG, coordinate=base_coord))
    graph.add_edge(t_srefen, p_sref, Arc())
    graph.add_edge(p_sref, t_srefex, Arc())
    graph.add_edge(t_srefex, p_sref_flag, Arc())
    graph.add_edge(p_sref_flag, t_refab, ResetArc())
    
    # REFPB
    p_refpb_pool = graph.add_node(Place(PlaceType.REF_Pool, coordinate=base_coord))
    graph.add_edge(p_refpb_pool, t_refab, ResetArc())
    graph.add_edge(p_refpb_pool, t_srefen, ResetArc())

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
            coordinate=Coordinate(bank_group=None, bank=None),
            tokens=[Token() for _ in range(4)],
        )
    )
    
    # NAW32
    naw32 = graph.add_node(
        Place(
            PlaceType.NAW_Pool,
            coordinate=Coordinate(bank_group=None, bank=None),
            tokens=[Token() for _ in range(32)],
        )
    )

    for group in range(memspec["nbrOfBankGroups"]):
        for bank in range(banksPerGroup):
            bank_coord = Coordinate(bank_group=group, bank=bank)
            p_active = graph.add_node(Place(PlaceType.ACTIVE, coordinate=bank_coord))
            p_refpb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))

            t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
            t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
            t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
            t_pre = graph.add_node(Transition(PRE, coordinate=bank_coord))
            t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
            t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))
            t_refpb = graph.add_node(Transition(REFB, coordinate=bank_coord))
            t_refpb_last = graph.add_node(Transition(REFB_LAST, coordinate=bank_coord))

            graph.add_edge(t_act, p_active, Arc())

            graph.add_edge(p_active, t_rd, Arc())
            graph.add_edge(t_rd, p_active, Arc())

            graph.add_edge(p_active, t_wr, Arc())
            graph.add_edge(t_wr, p_active, Arc())

            graph.add_edge(p_active, t_rda, Arc())
            graph.add_edge(p_active, t_wra, Arc())

            graph.add_edge(t_act, faw, Arc())
            graph.add_edge(faw, t_act, TimedArc(weight=1, lower_bound=p.tFAW))
            graph.add_edge(naw32, t_act, TimedArc(weight=1, lower_bound=p.t32AW))
            
            graph.add_edge(t_refpb, faw, Arc())
            graph.add_edge(faw, t_refpb, TimedArc(weight=1, lower_bound=p.tFAW))
            graph.add_edge(naw32, t_refpb, TimedArc(weight=1, lower_bound=p.t32AW))
            
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
            # graph.add_edge(p_refpb_local, t_refpb_last, ResetArc())

            graph.add_edge(p_active, t_preab, ResetArc())
            graph.add_edge(p_active, t_pre, ResetArc())

            graph.add_edge(p_active, t_act, InhibitorArc())
            graph.add_edge(p_active, t_refab, InhibitorArc())
            graph.add_edge(p_active, t_srefen, InhibitorArc())
            graph.add_edge(p_active, t_refpb, InhibitorArc())
            graph.add_edge(p_sref, t_act, InhibitorArc())
            graph.add_edge(p_sref, t_refpb, InhibitorArc())
            graph.add_edge(p_sref, t_pre, InhibitorArc())
            graph.add_edge(p_pdn, t_act, InhibitorArc())
            graph.add_edge(p_pdn, t_pre, InhibitorArc())
            graph.add_edge(p_pdn, t_refpb, InhibitorArc())
            graph.add_edge(p_pdn, t_rd, InhibitorArc())
            graph.add_edge(p_pdn, t_wr, InhibitorArc())
            graph.add_edge(p_pdn, t_rda, InhibitorArc())
            graph.add_edge(p_pdn, t_wra, InhibitorArc())
                
    # Set the reset arcs for the local pools within the same PC
    for trans_idx in graph.filter_nodes(
        lambda node: isinstance(node, Transition) 
        and node.command == REFB_LAST
    ):
        for pool_idx in graph.filter_nodes(
            lambda node: isinstance(node, Place)
            and (node.place_type == PlaceType.REF_Pool 
                or node.place_type == PlaceType.REF_Flag)
        ):
            graph.add_edge(pool_idx, trans_idx, ResetArc())
                
    # CMDBUS
    cmd_bus = graph.add_node(
        Place(
            PlaceType.CMD_BUS,
            coordinate=Coordinate(bank_group=None, bank=None),
            tokens=[Token()],
        )
    )
    for transition_idx in graph.filter_nodes(lambda node: isinstance(node, Transition)):
        graph.add_edge(transition_idx, cmd_bus, Arc())
        graph.add_edge(cmd_bus, transition_idx, TimedArc(weight=1, lower_bound=p.tCK))

    for constraint in command_timing_constraints(p):
        populate_timing_arc(graph, constraint)
        
    # Map REFB_LAST to REFB
    for trans_idx in graph.filter_nodes(
        lambda node: isinstance(node, Transition) 
        and node.command == REFB_LAST
    ):
        graph[trans_idx].command = REFB

    return PetriNet(graph, memspec)


def intra_bank_group(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    if from_coord.bank_group != to_coord.bank_group: 
        return False
    return True


def command_timing_constraints(p: Parameters) -> list[CommandTimingConstraint]:
    tBURST = p.defaultBurstLength / p.dataRate * p.tCK
    t0 = p.tRTP + p.tRP
    t1 = Max(p.tWRPRE - p.tRTP, p.tWRRD_L)
    t2 = p.tWRPRE + p.tRP
    t3 = Max(p.tRTP + p.tRP, p.tRDSRE)
    t4 = Max(p.tWRPRE + p.tRP, p.tWRSRE)
    t5 = tBURST + p.tRTRS


    # fmt: off
    command_timing_constraints = [

        # Bank
        CommandTimingConstraint(intra_bank, [ACT], [PRE], p.tRAS),
        CommandTimingConstraint(intra_bank, [ACT], [RD,RDA], p.tRCDRD),
        CommandTimingConstraint(intra_bank, [ACT], [WR,WRA], p.tRCDWR),
        CommandTimingConstraint(intra_bank, [ACT], [ACT,REFB], p.tRC),
        CommandTimingConstraint(intra_bank, [PRE], [ACT,REFB], p.tRP),
        CommandTimingConstraint(intra_bank, [RD], [PRE], p.tRTP),
        CommandTimingConstraint(intra_bank, [RD], [RD,RDA], p.tCCDL),
        CommandTimingConstraint(intra_bank, [RD], [WR,WRA], p.tRTW),
        CommandTimingConstraint(intra_bank, [RDA], [ACT,REFB], t0),
        CommandTimingConstraint(intra_bank, [REFB], [ACT,REFB], p.tRFCPB),
        CommandTimingConstraint(intra_bank, [WR], [PRE], p.tWRPRE),
        CommandTimingConstraint(intra_bank, [WR], [WR,WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank, [WR], [RDA], t1),
        CommandTimingConstraint(intra_bank, [WR], [RD], p.tWRRD_L),
        CommandTimingConstraint(intra_bank, [WRA], [ACT,REFB], t2),

        # BankGroup
        CommandTimingConstraint(intra_bank_group, [ACT], [ACT,REFB], p.tRRDL),
        CommandTimingConstraint(intra_bank_group, [PRE], [PRE], p.tPPD),
        CommandTimingConstraint(intra_bank_group, [RD], [RD,RDA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [RD], [WR,WRA], p.tRTW),
        CommandTimingConstraint(intra_bank_group, [RDA], [RD,RDA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [RDA], [WR,WRA], p.tRTW),
        CommandTimingConstraint(intra_bank_group, [REFB], [ACT,REFB], p.tRREFD),
        CommandTimingConstraint(intra_bank_group, [WR], [WR,WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [WR], [RDA,RD], p.tWRRD_L),
        CommandTimingConstraint(intra_bank_group, [WRA], [WR,WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [WRA], [RD,RDA], p.tWRRD_L),

        # Rank
        CommandTimingConstraint(lambda _, __: True, [ACT], [PREA], p.tRAS),
        CommandTimingConstraint(lambda _, __: True, [ACT], [REFA,SREFEN], p.tRC),
        CommandTimingConstraint(lambda _, __: True, [ACT], [ACT,REFB], p.tRRDS),
        CommandTimingConstraint(lambda _, __: True, [PDEA], [PDXA], p.tPD),
        CommandTimingConstraint(lambda _, __: True, [PDEP], [PDXP], p.tPD),
        CommandTimingConstraint(lambda _, __: True, [PDXA], [PDEA,REFB,ACT,PRE,PREA,RD,RDA,WR,WRA], p.tXPN),
        CommandTimingConstraint(lambda _, __: True, [PDXP], [PDEP,REFA,REFB,SREFEN,ACT], p.tXPN),
        CommandTimingConstraint(lambda _, __: True, [PRE], [PRE,PREA], p.tPPD),
        CommandTimingConstraint(lambda _, __: True, [PRE], [REFA,SREFEN], p.tRP),
        CommandTimingConstraint(lambda _, __: True, [PREA], [ACT,REFA,REFB,SREFEN], p.tRP),
        CommandTimingConstraint(lambda _, __: True, [RD], [PDEA,PDEP,SREFEN], p.tRDSRE),
        CommandTimingConstraint(lambda _, __: True, [RD], [PREA], p.tRTP),
        CommandTimingConstraint(lambda _, __: True, [RD], [RD,RDA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [RD], [WR,WRA], p.tRTW),
        CommandTimingConstraint(lambda _, __: True, [RDA], [SREFEN], t3),
        CommandTimingConstraint(lambda _, __: True, [RDA], [PDEA,PDEP], p.tRDSRE),
        CommandTimingConstraint(lambda _, __: True, [RDA], [PREA], p.tRTP),
        CommandTimingConstraint(lambda _, __: True, [RDA], [REFA], t0),
        CommandTimingConstraint(lambda _, __: True, [RDA], [RD,RDA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [RDA], [WR,WRA], p.tRTW),
        CommandTimingConstraint(lambda _, __: True, [REFA], [ACT,REFA,REFB,SREFEN], p.tRFC),
        CommandTimingConstraint(lambda _, __: True, [REFB], [REFA,PREA,SREFEN], p.tRFCPB),
        CommandTimingConstraint(lambda _, __: True, [REFB], [ACT,REFB], p.tRREFD),
        CommandTimingConstraint(lambda _, __: True, [SREFEN], [SREFEX], p.tCKE),
        CommandTimingConstraint(lambda _, __: True, [SREFEX], [RD,RDA,WR,WRA], p.tLK),
        CommandTimingConstraint(lambda _, __: True, [SREFEX], [ACT,REFB,REFA,PDEP,SREFEN], p.tXS),
        CommandTimingConstraint(lambda _, __: True, [WR], [PREA], p.tWRPRE),
        CommandTimingConstraint(lambda _, __: True, [WR], [PDEA,PDEP,SREFEN], p.tWRSRE),
        CommandTimingConstraint(lambda _, __: True, [WR], [WR,WRA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [WR], [RDA,RD], p.tWRRD_S),
        CommandTimingConstraint(lambda _, __: True, [WRA], [SREFEN], t4),
        CommandTimingConstraint(lambda _, __: True, [WRA], [PREA], p.tWRPRE),
        CommandTimingConstraint(lambda _, __: True, [WRA], [REFA], t2),
        CommandTimingConstraint(lambda _, __: True, [WRA], [PDEA,PDEP], p.tWRSRE),
        CommandTimingConstraint(lambda _, __: True, [WRA], [WR,WRA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [WRA], [RD,RDA], p.tWRRD_S),

        # Channel
        # CommandTimingConstraint(extra_rank, [RD], [RD,RDA], t5),
        # CommandTimingConstraint(extra_rank, [RD], [WR,WRA], p.tRDWR_R),
        # CommandTimingConstraint(extra_rank, [RDA], [RD,RDA], t5),
        # CommandTimingConstraint(extra_rank, [RDA], [WR,WRA], p.tRDWR_R),
        # CommandTimingConstraint(extra_rank, [WR], [WR,WRA], t5),
        # CommandTimingConstraint(extra_rank, [WR], [RDA,RD], p.tWRRD_R),
        # CommandTimingConstraint(extra_rank, [WRA], [WR,WRA], t5),
        # CommandTimingConstraint(extra_rank, [WRA], [RD,RDA], p.tWRRD_R)
    ]
    # fmt: on
    return command_timing_constraints


def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)