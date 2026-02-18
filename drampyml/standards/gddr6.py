from drampyml.constraints.queries import extra_rank, intra_bank, intra_bank_group
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
    PREPB = auto()
    PREAB = auto()
    RD = auto()
    RDA = auto()
    REFAB = auto()
    REFPB = auto()
    SREFEN = auto()
    SREFEX = auto()
    WR = auto()
    WRA = auto()
    LDFF = auto()
    WRTR = auto()
    RDTR = auto()
    MRS = auto()
    
    # Simplified commands
    PDE = auto() 
    PDX = auto()
    
    REFPB_LAST = auto()
    REFP2B = auto()
    REFP2B_LAST = auto()

    def __str__(self):
        return self.name


ACT = Command.ACT
PDEA = Command.PDEA
PDEP = Command.PDEP
PDXA = Command.PDXA
PDXP = Command.PDXP
PREPB = Command.PREPB
PREAB = Command.PREAB
RD = Command.RD
RDA = Command.RDA
REFAB = Command.REFAB
REFPB = Command.REFPB
SREFEN = Command.SREFEN
SREFEX = Command.SREFEX
WR = Command.WR
WRA = Command.WRA
LDFF = Command.LDFF
WRTR = Command.WRTR
RDTR = Command.RDTR
MRS = Command.MRS
PDE = Command.PDE
PDX = Command.PDX
REFPB_LAST = Command.REFPB_LAST
REFP2B = Command.REFP2B
REFP2B_LAST = Command.REFP2B_LAST

# Links to simplified commands
PDEA = PDE
PDEP = PDE
PDXA = PDX
PDXP = PDX


@dataclass
class Parameters:
    tRAS: Symbol = Symbol("tRAS")
    tRCDRD: Symbol = Symbol("tRCDRD")
    tRCDWR: Symbol = Symbol("tRCDWR")
    tRCDLTR: Symbol = Symbol("tRCDLTR")
    tRCDWTR: Symbol = Symbol("tRCDWTR")
    tRCDRTR: Symbol = Symbol("tRCDRTR")
    tRP: Symbol = Symbol("tRP")
    tRTP: Symbol = Symbol("tRTP")
    tCCDL: Symbol = Symbol("tCCDL")
    tRTW: Symbol = Symbol("tRTW")
    tRDTLT: Symbol = Symbol("tRDTLT")
    tRDSRE: Symbol = Symbol("tRDSRE")
    tRFCpb: Symbol = Symbol("tRFCpb")
    tXS: Symbol = Symbol("tXS")
    tWRTLT: Symbol = Symbol("tWRTLT")
    tWRWTR: Symbol = Symbol("tWRWTR")
    tWRRTR: Symbol = Symbol("tWRRTR")
    tWRSRE: Symbol = Symbol("tWRSRE")
    tLTLTR: Symbol = Symbol("tLTLTR")
    tLTRTR: Symbol = Symbol("tLTRTR")
    tWTRTR0: Symbol = Symbol("tWTRTR0")
    tCCDS: Symbol = Symbol("tCCDS")
    tMOD: Symbol = Symbol("tMOD")
    tMRD: Symbol = Symbol("tMRD")
    tRREFD: Symbol = Symbol("tRREFD")
    tACTPDE: Symbol = Symbol("tACTPDE")
    tPD: Symbol = Symbol("tPD")
    tXP: Symbol = Symbol("tXP")
    tRFCab: Symbol = Symbol("tRFCab")
    tREFTR: Symbol = Symbol("tREFTR")
    tRDWR_R: Symbol = Symbol("tRDWR_R")
    tWLmrs: Symbol = Symbol("tWLmrs")
    tWTRL: Symbol = Symbol("tWTRL")
    tCCD: Symbol = Symbol("tCCD")
    tRTRS: Symbol = Symbol("tRTRS")
    tWTRS: Symbol = Symbol("tWTRS")
    # Is this (tWR) a generic placeholder?
    tWR: Symbol = Symbol("tWR")
    tCK: Symbol = Symbol("tCK")
    tFAW: Symbol = Symbol("tFAW")
    
    
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    paired_banks_mode = None
    bank_group_offset = None
    bank_offset = None



def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()
    
    banksPerGroup = int(memspec["nbrOfBanks"] // memspec["nbrOfBankGroups"])
    ref_map: dict[Coordinate, tuple[int, int, int]] = {}

    base_coord = Coordinate(bank_group=None, bank=None)

    t_refab = graph.add_node(Transition(REFAB, coordinate=base_coord))
    t_preab = graph.add_node(Transition(PREAB, coordinate=base_coord))

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

    for bank_group in range(memspec["nbrOfBankGroups"]):
        
        ref_command, ref_last_command = _determine_ref_commands(memspec, bank_group, p)
        
        for bank in range(banksPerGroup):
            bank_coord = Coordinate(bank_group=bank_group, bank=bank)
            p_active = graph.add_node(Place(PlaceType.ACTIVE, coordinate=bank_coord))
            p_refpb_local = graph.add_node(Place(PlaceType.REF_Flag, coordinate=bank_coord))

            t_act = graph.add_node(Transition(ACT, coordinate=bank_coord))
            t_rd = graph.add_node(Transition(RD, coordinate=bank_coord))
            t_wr = graph.add_node(Transition(WR, coordinate=bank_coord))
            t_pre = graph.add_node(Transition(PREPB, coordinate=bank_coord))
            t_rda = graph.add_node(Transition(RDA, coordinate=bank_coord))
            t_wra = graph.add_node(Transition(WRA, coordinate=bank_coord))
            t_refpb = graph.add_node(Transition(ref_command, coordinate=bank_coord))
            t_refpb_last = graph.add_node(Transition(ref_last_command, coordinate=bank_coord))

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
            graph.add_edge(faw, t_refpb, TimedArc(weight=1 if not p.paired_banks_mode else 2, lower_bound=p.tFAW))
            
            # REFPB
            refpb_weight = memspec["nbrOfBanks"] - 1 if not p.paired_banks_mode else (memspec["nbrOfBanks"] // 2) - 1
            graph.add_edge(p_refpb_pool, t_refpb, InhibitorArc(refpb_weight))
            graph.add_edge(p_refpb_pool, t_refpb_last, Arc(refpb_weight))
            graph.add_edge(t_refpb, p_refpb_pool, Arc())
            graph.add_edge(p_refpb_local, t_refpb_last, InhibitorArc())
            graph.add_edge(t_refpb, p_refpb_local, Arc())
            graph.add_edge(p_refpb_local, t_refpb, InhibitorArc())
            graph.add_edge(p_refpb_local, t_refab, ResetArc())
            graph.add_edge(p_refpb_local, t_srefen, ResetArc())
            graph.add_edge(p_sref_flag, t_refpb_last, ResetArc())
            # Intentionally commented out; gets done later
            # graph.add_edge(p_refpb_local, t_refpb_last, ResetArc())
            ref_map[bank_coord] = (p_refpb_local, t_refpb, t_refpb_last)

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
        
    # If using Bank Group Mode, create a link the REFP2B commands 
    if p.paired_banks_mode:
        _handle_paired_banks_mode(graph, ref_map, p)
                  
    # Set the reset arcs for the local pools within the same rank
    # NOTE: This must be done AFTER the possible bank linking  
    for trans_idx in graph.filter_nodes(
        lambda node: isinstance(node, Transition) 
        and (node.command == REFP2B_LAST 
            or node.command == REFPB_LAST)
    ):
        for pool_idx in graph.filter_nodes(
            lambda node: isinstance(node, Place)
            and (node.place_type == PlaceType.REF_Pool 
                    or node.place_type == PlaceType.REF_Flag)
        ):
            graph.add_edge(pool_idx, trans_idx, ResetArc())

    # Map REFSB_LAST to REFSB
    for trans_idx in graph.filter_nodes(
        lambda node: isinstance(node, Transition) 
        and node.command in (REFPB_LAST, REFP2B, REFP2B_LAST)
    ):
        graph[trans_idx].command = REFPB

    return PetriNet(graph, memspec)


def _determine_ref_commands(memspec: dict[Expr, int], bank_group: int, p: Parameters) -> tuple[str, str]:
    """Determine which refresh commands to use based on memory specification and bank group configuration."""
    if ((bank_group is not None and memspec["nbrOfBankGroups"] % 2 == 0) or 
        (memspec["nbrOfBanks"] > 8 and memspec["nbrOfBanks"] % 2 == 0)):
        
        if bank_group is not None and memspec["nbrOfBankGroups"] % 2 == 0:
            p.bank_group_offset = memspec.get("nbrOfBankGroups", 0) // 2
        else:
            p.bank_offset = memspec["nbrOfBanks"] // 2
        p.paired_banks_mode = True
        
        return REFP2B, REFP2B_LAST
    else:
        return REFPB, REFPB_LAST


def _handle_paired_banks_mode(graph: rx.PyDiGraph, ref_map: dict[Coordinate, tuple[int, int, int]], p: Parameters) -> None:
    """Handle paired banks mode by linking REFP2B commands across bank groups or banks."""
    for coord, (p_1, t_1, t_1_last) in ref_map.items():
        # Stop after half of the bank groups/banks
        if (coord.bank_group == p.bank_group_offset 
            or coord.bank == p.bank_offset): 
            break
        
        # Get the nodes to be fused
        offset_coord = Coordinate(
            bank_group=coord.bank_group + (p.bank_group_offset or 0),
            bank=coord.bank + (p.bank_offset or 0)
        )
        (p_2, t_2, t_2_last) = ref_map[offset_coord]
                    
        # Transfer the edges to the shared nodes 
        _transfer_edges(graph, p_2, p_1)
        _transfer_edges(graph, t_2, t_1)
        _transfer_edges(graph, t_2_last, t_1_last)
        
        # Remove the old nodes
        graph.remove_node(p_2)
        graph.remove_node(t_2)
        graph.remove_node(t_2_last)


def _transfer_edges(graph: rx.PyDiGraph, from_node: int, to_node: int) -> None:
    """Transfer all incoming and outgoing edges from one node to another."""
    in_edges = graph.in_edges(from_node)
    out_edges = graph.out_edges(from_node)
    
    for edge in in_edges:
        if not graph.has_edge(edge[0], to_node):
            graph.add_edge(edge[0], to_node, edge[2])
    for edge in out_edges:
        if not graph.has_edge(to_node, edge[1]):
            graph.add_edge(to_node, edge[1], edge[2])


def intra_paired_bank(p: Parameters):
    def check_pair(from_coord: Coordinate, to_coord: Coordinate):
        if from_coord.bank_group is None or to_coord.bank_group is None:
            return False
        if from_coord.bank is None or to_coord.bank is None:
            return False
        return (
            from_coord.bank_group + (p.bank_group_offset or 0) == to_coord.bank_group
            and from_coord.bank + (p.bank_offset or 0) == to_coord.bank)
    return check_pair if p.paired_banks_mode else lambda _, __: False


def intra_bank_group(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    if from_coord.bank_group != to_coord.bank_group: 
        return False
    return True


def command_timing_constraints(p: Parameters) -> list[CommandTimingConstraint]:
    tBURST = p.defaultBurstLength / p.dataRate * p.tCK
    t0 = p.tRTP + p.tRP
    t1 = p.tWLmrs+ tBURST + p.tWR
    t2 = p.tWLmrs+ tBURST + p.tWTRL
    t3 = p.tWLmrs+ (tBURST / 8) + p.tRP
    t4 = p.tWLmrs+ (tBURST / 8) + p.tWR + p.tRP
    t5 = Max( p.tRREFD, p.tRFCpb)
    t6 = 3*p.tCK
    t7 = Max(p.tCCD, 3*p.tCK)
    t8 = p.tWLmrs+ tBURST + p.tWTRS
    t9 = tBURST + p.tRTRS


    # fmt: off
    command_timing_constraints = [

        # Bank
        CommandTimingConstraint(intra_bank, [ACT], [PREPB], p.tRAS),
        CommandTimingConstraint(intra_bank, [ACT], [RD,RDA], p.tRCDRD),
        CommandTimingConstraint(intra_bank, [ACT], [WR,WRA], p.tRCDWR),
        CommandTimingConstraint(intra_bank, [ACT], [LDFF], p.tRCDLTR),
        CommandTimingConstraint(intra_bank, [ACT], [WRTR], p.tRCDWTR),
        CommandTimingConstraint(intra_bank, [ACT], [RDTR], p.tRCDRTR),
        CommandTimingConstraint(intra_bank, [PREPB], [ACT,REFPB,REFAB,SREFEN,MRS], p.tRP),
        CommandTimingConstraint(intra_bank, [RD], [PREPB], p.tRTP),
        CommandTimingConstraint(intra_bank, [RD], [RD,RDA,RDTR], p.tCCDL),
        CommandTimingConstraint(intra_bank, [RD], [WR,WRA,WRTR], p.tRTW),
        CommandTimingConstraint(intra_bank, [RD], [LDFF], p.tRDTLT),
        CommandTimingConstraint(intra_bank, [RDA], [SREFEN], p.tRDSRE),
        CommandTimingConstraint(intra_bank, [RDA], [ACT,REFPB,MRS], t0),
        CommandTimingConstraint(intra_bank, [REFPB], [SREFEN,ACT,REFPB,MRS], p.tRFCpb),
        CommandTimingConstraint(intra_bank, [SREFEN], [SREFEX], p.tXS),
        CommandTimingConstraint(intra_bank, [SREFEX], [ACT,REFPB,PDEP,SREFEN,MRS], p.tXS),
        CommandTimingConstraint(intra_bank, [WR], [PREPB], t1),
        CommandTimingConstraint(intra_bank, [WR], [WR,WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank, [WR], [RDA,RD], t2),
        CommandTimingConstraint(intra_bank, [WR], [LDFF], p.tWRTLT),
        CommandTimingConstraint(intra_bank, [WR], [WRTR], p.tWRWTR),
        CommandTimingConstraint(intra_bank, [WR], [RDTR], p.tWRRTR),
        CommandTimingConstraint(intra_bank, [WRA], [SREFEN], p.tWRSRE),
        CommandTimingConstraint(intra_bank, [WRA], [ACT,MRS], t3),
        CommandTimingConstraint(intra_bank, [WRA], [REFPB], t4),
        CommandTimingConstraint(intra_bank, [LDFF], [LDFF], p.tLTLTR),
        CommandTimingConstraint(intra_bank, [LDFF], [RDTR], p.tLTRTR),
        CommandTimingConstraint(intra_bank, [MRS], [SREFEN,ACT,REFAB,REFPB], p.tMOD),
        CommandTimingConstraint(intra_bank, [MRS], [MRS], p.tMRD),
        
        # Second Bank
        CommandTimingConstraint(intra_paired_bank(p), [PREPB], [ACT,REFPB,REFAB,SREFEN,MRS], p.tRP),
        CommandTimingConstraint(intra_paired_bank(p), [RDA], [ACT,REFPB,MRS], t0),
        CommandTimingConstraint(intra_paired_bank(p), [REFPB], [SREFEN,ACT,REFPB,MRS], p.tRFCpb),
        CommandTimingConstraint(intra_paired_bank(p), [SREFEX], [ACT,REFPB,PDEP,SREFEN,MRS], p.tXS),
        CommandTimingConstraint(intra_paired_bank(p), [WRA], [REFPB], t4),
        CommandTimingConstraint(intra_paired_bank(p), [MRS], [SREFEN,ACT,REFAB,REFPB], p.tMOD),
        
        # BankGroup
        CommandTimingConstraint(intra_bank_group, [RD], [RD,RDA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [RD], [WR,WRA], p.tRTW),
        CommandTimingConstraint(intra_bank_group, [REFPB], [ACT], p.tRREFD),
        CommandTimingConstraint(intra_bank_group, [REFPB], [REFPB], t5),
        CommandTimingConstraint(intra_bank_group, [WR], [WR,WRA], p.tCCDL),
        CommandTimingConstraint(intra_bank_group, [WR], [RDA,RD], t2),
        CommandTimingConstraint(intra_bank_group, [WRA], [ACT], t6),
        CommandTimingConstraint(intra_bank_group, [WRA], [REFPB], t7),

        # Rank
        CommandTimingConstraint(lambda _, __: True, [ACT], [PREAB], p.tRAS),
        CommandTimingConstraint(lambda _, __: True, [ACT], [PDEA], p.tACTPDE),
        CommandTimingConstraint(lambda _, __: True, [PDEA], [PDXA], p.tPD),
        CommandTimingConstraint(lambda _, __: True, [PDEP], [PDXP], p.tPD),
        CommandTimingConstraint(lambda _, __: True, [PDXA], [PDEA,LDFF,RDTR,WRTR,PREPB,PREAB,RD,RDA,WR,WRA], p.tXP),
        CommandTimingConstraint(lambda _, __: True, [PDXP], [PDEP,REFAB,REFPB,SREFEN,ACT,MRS], p.tXP),
        CommandTimingConstraint(lambda _, __: True, [PREAB], [ACT,REFAB,REFPB,SREFEN,MRS], p.tRP),
        CommandTimingConstraint(lambda _, __: True, [RD], [PREAB], p.tRTP),
        CommandTimingConstraint(lambda _, __: True, [RD], [RD,RDA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [RD], [WR,WRA], p.tRTW),
        CommandTimingConstraint(lambda _, __: True, [RD], [PDEA], p.tRDSRE),
        CommandTimingConstraint(lambda _, __: True, [RDA], [PDEP], p.tRDSRE),
        CommandTimingConstraint(lambda _, __: True, [RDA], [REFAB], t0),
        CommandTimingConstraint(lambda _, __: True, [REFAB], [ACT,REFAB,REFPB,SREFEN,MRS], p.tRFCab),
        CommandTimingConstraint(lambda _, __: True, [REFAB], [LDFF,RDTR,WRTR], p.tREFTR),
        CommandTimingConstraint(lambda _, __: True, [REFPB], [REFAB], p.tRFCpb),
        CommandTimingConstraint(lambda _, __: True, [REFPB], [ACT], p.tRREFD),
        CommandTimingConstraint(lambda _, __: True, [REFPB], [REFPB], t5),
        CommandTimingConstraint(lambda _, __: True, [SREFEX], [REFAB], p.tXS),
        CommandTimingConstraint(lambda _, __: True, [WR], [PREAB], t1),
        CommandTimingConstraint(lambda _, __: True, [WR], [PDEA], p.tWRSRE),
        CommandTimingConstraint(lambda _, __: True, [WR], [WR,WRA], p.tCCDS),
        CommandTimingConstraint(lambda _, __: True, [WR], [RDA,RD], t8),
        CommandTimingConstraint(lambda _, __: True, [WRA], [ACT], t6),
        CommandTimingConstraint(lambda _, __: True, [WRA], [REFAB], t3),
        CommandTimingConstraint(lambda _, __: True, [WRA], [PDEP], p.tWRSRE),
        CommandTimingConstraint(lambda _, __: True, [WRA], [REFPB], t7),
        CommandTimingConstraint(lambda _, __: True, [MRS], [PDEP], p.tMOD),

        # Channel
        # CommandTimingConstraint(extra_rank, [RD], [RD,RDA], t9),
        # CommandTimingConstraint(extra_rank, [RD], [WR,WRA], p.tRDWR_R),
        # CommandTimingConstraint(extra_rank, [WR], [WR,WRA], t9)
    ]
    # fmt: on
    return command_timing_constraints


def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)