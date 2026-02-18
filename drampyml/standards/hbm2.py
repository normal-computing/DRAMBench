from drampyml.constraints.queries import extra_pseudochannel, intra_bank, intra_bank_group, intra_pseudochannel
from drampyml.common.syntax import Max
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
from sympy import Expr, Symbol
import rustworkx as rx
from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate:
    pseudochannel: int | None
    bank_group: int | None
    bank: int | None


class Command(Enum):
    RNOP = auto()
    ACT = auto()
    PRE = auto()
    PREA = auto()
    REFSB = auto()
    REF = auto()
    PDE = auto()
    PDX = auto()
    SRE = auto()
    SRX = auto()
    RD = auto()
    RDA = auto()
    WR = auto()
    WRA = auto()
    REFSB_LAST = auto()

    def __str__(self):
        return self.name


RNOP = Command.RNOP
ACT = Command.ACT
PRE = Command.PRE
PREA = Command.PREA
REF = Command.REF
REFSB = Command.REFSB
REFSB_LAST = Command.REFSB_LAST
PDE = Command.PDE
PDX = Command.PDX
SRE = Command.SRE
SRX = Command.SRX
RD = Command.RD
WR = Command.WR
RDA = Command.RDA
WRA = Command.WRA


@dataclass
class Parameters:
    tRAS = Symbol("tRAS")
    tRC = Symbol("tRC")
    tRTP = Symbol("tRTP")
    tCK = Symbol("tCK")
    tRL = Symbol("tRL")
    tWL = Symbol("tWL")
    tWTRS = Symbol("tWTRS")
    tWTRL = Symbol("tWTRL")
    tRP = Symbol("tRP")
    tWR = Symbol("tWR")
    tRCDRD = Symbol("tRCDRD")
    tRCDWR = Symbol("tRCDWR")
    tRFCSB = Symbol("tRFCSB")
    tRRDL = Symbol("tRRDL")
    tRRDS = Symbol("tRRDS")
    tCCDL = Symbol("tCCDL")
    tCCDS = Symbol("tCCDS")
    tCCDR = Symbol("tCCDR")
    tPD = Symbol("tPD")
    tCKE = Symbol("tCKE")
    tXP = Symbol("tXP")
    tXS = Symbol("tXS")
    tPL = Symbol("tPL")
    tFAW = Symbol("tFAW")
    tCKESR = Symbol("tCKESR")
    tRFC = Symbol("tRFC")
    tRREFD = Symbol("tRREFD")
    tRTW = Symbol("tRTW")
    tRDPDE = Symbol("tRDPDE")
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    

def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()
    
    banksPerGroup = memspec["nbrOfBanks"] // (memspec["nbrOfBankGroups"]) 

    global_coord = Coordinate(pseudochannel=None, bank_group=None, bank=None)
    # PDN
    p_pdn = graph.add_node(Place(PlaceType.PDN, coordinate=global_coord))
    t_pde = graph.add_node(Transition(PDE, coordinate=global_coord))
    t_pdx = graph.add_node(Transition(PDX, coordinate=global_coord))
    graph.add_edge(t_pde, p_pdn, Arc())
    graph.add_edge(p_pdn, t_pdx, Arc())

    # SREF
    p_sref = graph.add_node(Place(PlaceType.SREF, coordinate=global_coord))
    t_srefen = graph.add_node(Transition(SRE, coordinate=global_coord))
    t_srefex = graph.add_node(Transition(SRX, coordinate=global_coord))
    
    graph.add_edge(t_srefen, p_sref, Arc())
    graph.add_edge(p_sref, t_srefex, Arc())

        
    for pc in range(memspec["nbrOfPseudochannels"]):
        pc_coord = Coordinate(pseudochannel=pc, bank_group=None, bank=None)

        t_refab = graph.add_node(Transition(REF, coordinate=pc_coord))
        t_preab = graph.add_node(Transition(PREA, coordinate=pc_coord))
        
        # SREF flag
        p_sref_flag = graph.add_node(Place(PlaceType.SREF_FLAG, coordinate=global_coord))
        graph.add_edge(t_srefex, p_sref_flag, Arc())
        graph.add_edge(p_sref_flag, t_srefen, InhibitorArc())
        graph.add_edge(p_sref_flag, t_refab, ResetArc())
        
        # REFSB
        p_refsb_pool = graph.add_node(Place(PlaceType.REF_Pool, coordinate=pc_coord))
        graph.add_edge(p_refsb_pool, t_refab, ResetArc())
        graph.add_edge(p_refsb_pool, t_srefen, ResetArc())

        graph.add_edge(p_pdn, t_srefen, InhibitorArc())
        graph.add_edge(p_pdn, t_pde, InhibitorArc())
        graph.add_edge(p_pdn, t_refab, InhibitorArc())
        graph.add_edge(p_pdn, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_refab, InhibitorArc())
        graph.add_edge(p_sref, t_preab, InhibitorArc())
        graph.add_edge(p_sref, t_pde, InhibitorArc())
        graph.add_edge(p_sref, t_srefen, InhibitorArc())
        

        # FAW
        faw = graph.add_node(
            Place(
                PlaceType.NAW_Pool,
                coordinate=Coordinate(pseudochannel=pc, bank_group=None, bank=None),
                tokens=[Token() for _ in range(4)],
            )
        )
        for bank_group in range(memspec["nbrOfBankGroups"]):
            for bank in range(banksPerGroup):
                bank_coord = Coordinate(pseudochannel=pc, bank_group=bank_group, bank=bank)
                p_active = graph.add_node(Place(PlaceType.ACTIVE, coordinate=bank_coord))
                p_refsb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))

                t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
                t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
                t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
                t_pre = graph.add_node(Transition(PRE, coordinate=bank_coord))
                t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
                t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))
                t_refsb = graph.add_node(Transition(REFSB, coordinate=bank_coord))
                t_refsb_last = graph.add_node(Transition(REFSB_LAST, coordinate=bank_coord))

                graph.add_edge(t_act, p_active, Arc())

                graph.add_edge(p_active, t_rd, Arc())
                graph.add_edge(t_rd, p_active, Arc())

                graph.add_edge(p_active, t_wr, Arc())
                graph.add_edge(t_wr, p_active, Arc())

                graph.add_edge(p_active, t_rda, Arc())
                graph.add_edge(p_active, t_wra, Arc())

                graph.add_edge(t_act, faw, Arc())
                graph.add_edge(t_refsb, faw, Arc())
                graph.add_edge(faw, t_act, TimedArc(weight=1, lower_bound=p.tFAW))
                graph.add_edge(faw, t_refsb, TimedArc(weight=1, lower_bound=p.tFAW))
                
                # REFSB
                graph.add_edge(p_refsb_pool, t_refsb, InhibitorArc(memspec["nbrOfBanks"] - 1))
                graph.add_edge(p_refsb_pool, t_refsb_last, Arc(memspec["nbrOfBanks"] - 1))
                graph.add_edge(t_refsb, p_refsb_pool, Arc())
                graph.add_edge(p_refsb_local, t_refsb_last, InhibitorArc())
                graph.add_edge(t_refsb, p_refsb_local, Arc())
                graph.add_edge(p_refsb_local, t_refsb, InhibitorArc())
                graph.add_edge(p_refsb_local, t_refab, ResetArc())
                graph.add_edge(p_refsb_local, t_srefen, ResetArc())
                graph.add_edge(p_sref_flag, t_refsb_last, ResetArc())
                # Intentionally commented out; gets done later
                # graph.add_edge(p_refsb_local, t_refsb_last, ResetArc())          

                graph.add_edge(p_active, t_preab, ResetArc())
                graph.add_edge(p_active, t_pre, ResetArc())

                graph.add_edge(p_active, t_act, InhibitorArc())
                graph.add_edge(p_active, t_refab, InhibitorArc())
                graph.add_edge(p_active, t_refsb, InhibitorArc())
                graph.add_edge(p_active, t_refsb_last, InhibitorArc())
                graph.add_edge(p_active, t_srefen, InhibitorArc())
                graph.add_edge(p_pdn, t_act, InhibitorArc())
                graph.add_edge(p_pdn, t_pre, InhibitorArc())
                graph.add_edge(p_pdn, t_refsb, InhibitorArc())
                graph.add_edge(p_pdn, t_refsb_last, InhibitorArc())
                graph.add_edge(p_pdn, t_rd, InhibitorArc())
                graph.add_edge(p_pdn, t_wr, InhibitorArc())
                graph.add_edge(p_pdn, t_rda, InhibitorArc())
                graph.add_edge(p_pdn, t_wra, InhibitorArc())
                graph.add_edge(p_sref, t_act, InhibitorArc())
                graph.add_edge(p_sref, t_pre, InhibitorArc())
                graph.add_edge(p_sref, t_refsb, InhibitorArc())
                graph.add_edge(p_sref, t_refsb_last, InhibitorArc())
                
        # Set the reset arcs for the local pools within the same PC
        for trans_idx in graph.filter_nodes(
            lambda node: isinstance(node, Transition) 
            and node.command == REFSB_LAST
            and node.coordinate.pseudochannel == pc
        ):
            for pool_idx in graph.filter_nodes(
                lambda node: isinstance(node, Place)
                and node.coordinate.pseudochannel == pc
                and (node.place_type == PlaceType.REF_Pool 
                     or node.place_type == PlaceType.REF_Flag)
            ):
                graph.add_edge(pool_idx, trans_idx, ResetArc())

    # CMDBUS
    ras_commands = {
        ACT,
        PRE,
        PREA,
        REFSB,
        REF,
        PDE,
        PDX,
        PDE,
        PDX,
        SRE,
        SRX,
    }

    cas_commands = {
        RD,
        RDA,
        WR,
        WRA,
        # MWR,
        # MWRA,
        PDE,
        PDX,
        PDE,
        PDX,
        SRE,
        SRX,
    }
    ras_cmd_bus = graph.add_node(
        Place(
            PlaceType.CMD_BUS,
            coordinate=Coordinate(pseudochannel=None, bank_group=None, bank=None),
            tokens=[Token()],
        )
    )
    cas_cmd_bus = graph.add_node(
        Place(
            PlaceType.CMD_BUS,
            coordinate=Coordinate(pseudochannel=None, bank_group=None, bank=None),
            tokens=[Token()],
        )
    )
    for transition_idx in graph.filter_nodes(lambda node: isinstance(node, Transition)):
        transition_cmd = graph.get_node_data(transition_idx).command
        if transition_cmd in ras_commands:
            graph.add_edge(transition_idx, ras_cmd_bus, Arc())
            graph.add_edge(ras_cmd_bus, transition_idx, TimedArc(weight=1, lower_bound=p.tCK))
        if transition_cmd in cas_commands:
            graph.add_edge(transition_idx, cas_cmd_bus, Arc())
            graph.add_edge(cas_cmd_bus, transition_idx, TimedArc(weight=1, lower_bound=p.tCK)) 

    for constraint in command_timing_constraints(p):
        populate_timing_arc(graph, constraint)
        
    # Map REFSB_LAST to REFSB
    for trans_idx in graph.filter_nodes(
        lambda node: isinstance(node, Transition) 
        and node.command == REFSB_LAST
    ):
        graph[trans_idx].command = REFSB

    return PetriNet(graph, memspec)


def command_timing_constraints(p: Parameters) -> list[CommandTimingConstraint]:
    tBURST = p.defaultBurstLength / p.dataRate * p.tCK
    tRDPDE = p.tRL + p.tPL + tBURST + p.tCK
    tRDSRE = tRDPDE
    tWRPRE = p.tWL + tBURST + p.tWR
    tWRPDE = p.tWL + p.tPL + tBURST + p.tCK + p.tWR
    tWRAPDE = p.tWL + p.tPL + tBURST + p.tCK + p.tWR
    tWRRDS = p.tWL + tBURST + p.tWTRS
    tWRRDL = p.tWL + tBURST + p.tWTRL

    # fmt: off
    command_timing_constraints = [
        # intra_bank
        CommandTimingConstraint(intra_bank, [ACT], [PRE], p.tRAS + p.tCK),
        CommandTimingConstraint(intra_bank, [ACT], [RD, RDA], p.tRCDRD + p.tCK),
        CommandTimingConstraint(intra_bank, [ACT], [WR, WRA], p.tRCDWR + p.tCK),
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRC),
        CommandTimingConstraint(intra_bank, [ACT], [REFSB, REFSB_LAST], p.tRC + p.tCK),
        CommandTimingConstraint(intra_bank, [RD], [PRE], p.tRTP),
        CommandTimingConstraint(intra_bank, [RDA], [ACT], p.tRTP + p.tRP - p.tCK),
        CommandTimingConstraint(intra_bank, [RDA], [REFSB, REFSB_LAST], p.tRTP + p.tRP),
        CommandTimingConstraint(intra_bank, [WR], [PRE], tWRPRE),
        CommandTimingConstraint(intra_bank, [WR], [RDA], p.tWL + tBURST + Max(p.tWR - p.tRTP, p.tWTRL)),
        CommandTimingConstraint(intra_bank, [WRA], [ACT], tWRPRE + p.tRP - p.tCK),
        CommandTimingConstraint(intra_bank, [WRA], [REFSB, REFSB_LAST], tWRPRE + p.tRP),
        CommandTimingConstraint(intra_bank, [PRE], [ACT], p.tRP - p.tCK),
        CommandTimingConstraint(intra_bank, [PRE], [REFSB, REFSB_LAST], p.tRP),
        CommandTimingConstraint(intra_bank, [REFSB, REFSB_LAST], [ACT], p.tRFCSB - p.tCK),
        CommandTimingConstraint(intra_bank, [REFSB, REFSB_LAST], [REFSB, REFSB_LAST], p.tRFCSB),

        # intra_bank_group
        CommandTimingConstraint(intra_bank_group, [ACT], [ACT], p.tRRDL),
        CommandTimingConstraint(intra_bank_group, [ACT], [REFSB, REFSB_LAST], p.tRRDL + p.tCK),
        CommandTimingConstraint(intra_bank_group, [RD, RDA], [RD, RDA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [WR, WRA], [WR, WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [WR], [RD], tWRRDL),
        CommandTimingConstraint(intra_bank_group, [WR], [RDA], tWRRDL),
        CommandTimingConstraint(intra_bank_group, [WRA], [RD, RDA], tWRRDL),
        CommandTimingConstraint(intra_bank_group, [REFSB, REFSB_LAST], [REFSB, REFSB_LAST], p.tRREFD),
        CommandTimingConstraint(intra_bank_group, [REFSB, REFSB_LAST], [REF, PREA, SRE], p.tRFCSB),

        # intra_pseudochannel
        CommandTimingConstraint(intra_pseudochannel, [ACT], [ACT], p.tRRDS),
        CommandTimingConstraint(intra_pseudochannel, [ACT], [REF, SRE], p.tRC + p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [ACT], [PREA], p.tRAS + p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [ACT], [REFSB, REFSB_LAST], p.tRRDS + p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [RD], [PREA], p.tRTP),
        CommandTimingConstraint(intra_pseudochannel, [RD, RDA], [PDE, PDE], p.tRDPDE),
        CommandTimingConstraint(intra_pseudochannel, [RD, RDA], [RD, RDA], p.tCCDS),
        CommandTimingConstraint(intra_pseudochannel, [RD, RDA], [WR, WRA], p.tRTW),
        CommandTimingConstraint(intra_pseudochannel, [RDA], [REF], p.tRTP + p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [RDA], [PREA], p.tRTP),
        CommandTimingConstraint(intra_pseudochannel, [RDA], [SRE], Max(p.tRTP + p.tRP, tRDSRE)),
        CommandTimingConstraint(intra_pseudochannel, [WR], [PREA], tWRPRE),
        CommandTimingConstraint(intra_pseudochannel, [WR], [PDE], tWRPDE),
        CommandTimingConstraint(intra_pseudochannel, [WRA], [PDE, PDE], tWRAPDE),
        CommandTimingConstraint(intra_pseudochannel, [WR, WRA], [WR, WRA], p.tCCDS),
        CommandTimingConstraint(intra_pseudochannel, [WR], [RD], tWRRDS),
        CommandTimingConstraint(intra_pseudochannel, [WR], [RDA], tWRRDS),
        CommandTimingConstraint(intra_pseudochannel, [WRA], [RD, RDA], tWRRDS),
        CommandTimingConstraint(intra_pseudochannel, [WRA], [REF], tWRPRE + p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [WRA], [PREA], tWRPRE),
        CommandTimingConstraint(intra_pseudochannel, [WRA], [SRE], tWRPRE + p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [PRE], [REF], p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [PRE], [SRE], p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [PREA], [ACT], p.tRP - p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [PREA], [REF, REFSB, REFSB_LAST, SRE], p.tRP),
        CommandTimingConstraint(intra_pseudochannel, [PDE], [PDX], p.tPD),
        CommandTimingConstraint(intra_pseudochannel, [PDE], [PDX], p.tPD),
        CommandTimingConstraint(intra_pseudochannel, [PDX], [PDE], p.tCKE),
        CommandTimingConstraint(intra_pseudochannel, [PDX], [PDE], p.tCKE),
        CommandTimingConstraint(intra_pseudochannel, [PDX], [REF, REFSB, REFSB_LAST, SRE], p.tXP),
        CommandTimingConstraint(intra_pseudochannel, [PDX], [REFSB, REFSB_LAST, PRE, PREA, RD, RDA, WR, WRA], p.tXP),
        CommandTimingConstraint(intra_pseudochannel, [PDX, PDX], [ACT], p.tXP - p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [REF], [ACT], p.tRFC - p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [REF], [REF, REFSB, REFSB_LAST, SRE], p.tRFC),
        CommandTimingConstraint(intra_pseudochannel, [REFSB, REFSB_LAST], [ACT], p.tRREFD - p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [REFSB, REFSB_LAST], [REFSB, REFSB_LAST], p.tRFCSB),
        # Intentionally only REFSB_LAST
        CommandTimingConstraint(intra_pseudochannel, [REFSB_LAST], [REFSB, REFSB_LAST], p.tRREFD),
        CommandTimingConstraint(intra_pseudochannel, [SRX], [ACT], p.tXS - p.tCK),
        CommandTimingConstraint(intra_pseudochannel, [SRX], [REFSB, REF, PDE, SRE], p.tXS),
        CommandTimingConstraint(intra_pseudochannel, [SRX], [SRX], p.tCKESR),
        
        # Channel
        CommandTimingConstraint(extra_pseudochannel, [RD, RDA], [RD, RDA], p.tCCDR),
    ]
    # fmt: on
    return command_timing_constraints


def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)
