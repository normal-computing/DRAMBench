# Based on JESD79-2F
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
    tRP = Symbol("tRP")
    tRRD = Symbol("tRRD")
    tWR = Symbol("tWR")
    tPD = Symbol("tPD")
    tXP = Symbol("tXP")
    tFAW = Symbol("tFAW")
    tRFC = Symbol("tRFC")
    tXARD = Symbol("tXARD")
    tXSRD = Symbol("tXSRD")
    tXSNR = Symbol("tXSNR")
    defaultBurstLength = Symbol("defaultBurstLength")
    dataRate = Symbol("dataRate")
    nbrOfBanks = Symbol("nbrOfBanks")
    nbrOfPseudochannels = Symbol("nbrOfPseudochannels")


def create_petri_net(memspec: dict[Expr, int]) -> PetriNet:
    graph = rx.PyDiGraph()
    p = Parameters()

    for rank in range(memspec["nbrOfRanks"]):
        rank_coord = Coordinate(rank=rank, bank=None)

        t_REF = graph.add_node(Transition(REF, coordinate=rank_coord))
        t_PREA = graph.add_node(Transition(PREA, coordinate=rank_coord))

        # PDN
        p_pdn = graph.add_node(Place(PlaceType.PDN, coordinate=rank_coord))
        t_pde = graph.add_node(Transition(PDE, coordinate=rank_coord))
        t_pdx = graph.add_node(Transition(PDX, coordinate=rank_coord))
        graph.add_edge(t_pde, p_pdn, Arc())
        graph.add_edge(p_pdn, t_pdx, Arc())

        # SREF
        p_sref = graph.add_node(Place(PlaceType.SREF, coordinate=rank_coord))
        t_SRE = graph.add_node(Transition(SRE, coordinate=rank_coord))
        t_SRX = graph.add_node(Transition(SRX, coordinate=rank_coord))
        p_sref_flag = graph.add_node(Place(PlaceType.SREF_FLAG, coordinate=rank_coord))
        graph.add_edge(t_SRE, p_sref, Arc())
        graph.add_edge(p_sref, t_SRX, Arc())
        graph.add_edge(t_SRX, p_sref_flag, Arc())
        graph.add_edge(p_sref_flag, t_REF, ResetArc())

        graph.add_edge(p_pdn, t_SRE, InhibitorArc())
        graph.add_edge(p_pdn, t_pde, InhibitorArc())
        graph.add_edge(p_pdn, t_REF, InhibitorArc())
        graph.add_edge(p_pdn, t_PREA, InhibitorArc())
        graph.add_edge(p_sref, t_REF, InhibitorArc())
        graph.add_edge(p_sref, t_PREA, InhibitorArc())
        graph.add_edge(p_sref, t_pde, InhibitorArc())
        graph.add_edge(p_sref, t_SRE, InhibitorArc())
        graph.add_edge(p_sref_flag, t_SRE, InhibitorArc())

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

            graph.add_edge(p_active, t_PREA, ResetArc())
            graph.add_edge(p_active, t_pre, ResetArc())

            graph.add_edge(p_active, t_act, InhibitorArc())
            graph.add_edge(p_active, t_REF, InhibitorArc())
            graph.add_edge(p_active, t_SRE, InhibitorArc())
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
    tRDWR_R = p.tRL + tBURST + p.tRTRS - p.tWL
    tWRRD = p.tWL - p.tAL + tBURST + p.tWTR
    tWRRD_R = p.tWL + tBURST + p.tRTRS - p.tRL
    tWRPRE = p.tWL + tBURST + p.tWR
    tRDPDEN = p.tRL + tBURST + p.tCK
    tWRPDEN = p.tWL + tBURST + p.tWR
    tWRAPDEN = p.tWL + tBURST + p.tWR + p.tCK
    tRCDmin = p.tRCD - p.tAL
    tRDPRE = p.tAL + tBURST + Max(p.tRTP, 2 * p.tCK) - 2 * p.tCK
    tXARDS = 6 * p.tCK - p.tAL
    tRTW = p.tRL + tBURST + p.tCK - p.tWL


    # fmt: off
    command_timing_constraints = [
        ### Bank ##
        CommandTimingConstraint(intra_bank, [ACT], [PRE], p.tRAS),
        CommandTimingConstraint(intra_bank, [ACT], [RD, WR, RDA, WRA,], tRCDmin),
        CommandTimingConstraint(intra_bank, [ACT], [ACT], p.tRC),
        
        CommandTimingConstraint(intra_bank, [RD], [PRE], tRDPRE),
        # Read-> Write: (p36, Fig.35)
        CommandTimingConstraint(intra_bank, [RD], [WR, WRA,], tRTW),
        # (p46)
        CommandTimingConstraint(intra_bank, [RDA], [ACT], tRDPRE + p.tRP),
        
        CommandTimingConstraint(intra_bank, [WR], [PRE], tWRPRE),
        CommandTimingConstraint(intra_bank, [WR], [WR, WRA,], p.tCCD),
        CommandTimingConstraint(intra_bank, [WR], [RD, RDA], tWRRD),
        CommandTimingConstraint(intra_bank, [WRA,], [ACT], tWRPRE + p.tRP),
        
        CommandTimingConstraint(intra_bank, [PRE], [ACT], p.tRP),   
        
        
        ### Rank ###
        CommandTimingConstraint(intra_rank, [ACT], [PRE], p.tRAS),
        CommandTimingConstraint(intra_rank, [ACT], [ACT], p.tRRD),
        # (p55, Fig.68)
        CommandTimingConstraint(intra_rank, [ACT], [PDE], p.tCK),
        # ACT -> REF: not found; (sec 3.9 p50: All intra_banks of p.the DDR2 SDRAM must be precharged and idle for a minimum of p.the Precharge p.time)
        # CommandTimingConstraint(intra_rank, [ACT], [REF, SRE], p.tRC),
        
        # Read -> Precharge all
        CommandTimingConstraint(intra_rank, [RD, RDA], [PREA], tRDPRE),
        # Read -> Power down
        CommandTimingConstraint(intra_rank, [RD, RDA], [PDE, PDE], tRDPDEN),
        # Read -> Read (p33) 
        CommandTimingConstraint(intra_rank, [RD, RDA], [RD, RDA], p.tCCD),
        # Read-> Write: (p36, Fig.35)
        CommandTimingConstraint(intra_rank, [RD, RDA], [WR, WRA,], tRTW),
        # Also not explicitly found, but makes sense
        CommandTimingConstraint(intra_rank, [RDA], [REF], p.tAL + p.tRTP + p.tRP),
        # ----> Why is p.this one different? Where does p.the max(.) come from? <---- bitte mal draufschauen
        # CommandTimingConstraint(intra_rank, [RDA], [SRE], Max(tRDPDEN, p.tAL + p.tRTP + p.tRP)),
        
        
        # Write -> RD, WR
        CommandTimingConstraint(intra_rank, [WR], [WR, WRA], p.tCCD),
        CommandTimingConstraint(intra_rank, [WR, WRA,], [RD, RDA], tWRRD),
        # Write -> Power down
        CommandTimingConstraint(intra_rank, [WR], [PDE], tWRPDEN),
        # Write with auto precharge -> power down
        CommandTimingConstraint(intra_rank, [WRA], [PDE, PDE], tWRAPDEN),
        # Write -> refresh
        CommandTimingConstraint(intra_rank, [WRA], [REF], tWRPRE + p.tRP),
        
        # Write -> Precharge (p49, p.tab 12) <---- bitte nachprüfenm vgl. mit (p80, cmp. p.tWR<>tDAL)
        CommandTimingConstraint(intra_rank, [WR, WRA,], [PREA], tWRPRE),
        # Write w.AP -> Refresh (p49, 50): not explicitly found in p.the standard, but makes sense
        CommandTimingConstraint(intra_rank, [WRA,], [REF], tWRPRE + p.tRP),
        # Why p.the max(.)?  <---- bitte mal draufschauen
        CommandTimingConstraint(intra_rank, [WRA,], [SRE], Max(tWRAPDEN, tWRPRE + p.tRP)),
        
        # Precharge -> ...
        CommandTimingConstraint(intra_rank, [PRE], [SRE], p.tRP),
        CommandTimingConstraint(intra_rank, [PRE], [REF], p.tRP),
        
        CommandTimingConstraint(intra_rank, [PREA], [ACT, REF, SRE], p.tRP),
        # (p55, Fig.69)
        CommandTimingConstraint(intra_rank, [PREA], [PDE], p.tCK),
        CommandTimingConstraint(intra_rank, [PRE], [PDE, PDE], p.tCK),
        
        # PD entry -> exit
        CommandTimingConstraint(intra_rank, [PDE], [PDX], p.tPD),
        CommandTimingConstraint(intra_rank, [PDE], [PDX], p.tPD),
        # PD exit -> entry
        CommandTimingConstraint(intra_rank, [PDX], [PDE], p.tCK),
        CommandTimingConstraint(intra_rank, [PDX], [PDE], p.tCK),
        # PD exit -> ...
        CommandTimingConstraint(intra_rank, [PDX], [REF, SRE, ACT], p.tXP),
        CommandTimingConstraint(intra_rank, [PDX], [ACT, PRE, PREA, WR, WRA,], p.tXP),
        CommandTimingConstraint(intra_rank, [PDX], [ACT, PRE, PREA,WR, WRA,], p.tXP),
        # PD exit -> Read (Fast or slow (lower power))
        CommandTimingConstraint(intra_rank, [PDX], [RD, RDA], p.tXARD),
        CommandTimingConstraint(intra_rank, [PDX], [RD, RDA], tXARDS),
        
        # Refresh p.to Power down
        CommandTimingConstraint(intra_rank, [REF], [ACT, REF, SRE], p.tRFC),
        CommandTimingConstraint(intra_rank, [REF], [PDE], p.tCK),
        # Exit self refresh -> Read or non-read cmd (p80 or p51)
        CommandTimingConstraint(intra_rank, [SRX], [ACT, REF, PDE, SRE, WR, WRA,], p.tXSNR),
        CommandTimingConstraint(intra_rank, [SRX], [RD, RDA], p.tXSRD),
        
        
        # Channel
        CommandTimingConstraint(extra_rank, [RD, RDA], [RD, RDA], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [RD, RDA], [WR, WRA,], tRDWR_R),
        CommandTimingConstraint(extra_rank, [WR, WRA,], [WR, WRA,], tBURST + p.tRTRS),
        CommandTimingConstraint(extra_rank, [WR, WRA,], [RD, RDA], tWRRD_R),
        ]
    # fmt: on
    return command_timing_constraints

def create_standard(memspec) -> Standard:
    petri_net = create_petri_net(memspec)
    return Standard(petri_net, memspec)
