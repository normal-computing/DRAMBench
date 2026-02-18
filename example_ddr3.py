#!/usr/bin/env python3
"""
DRAMBench DDR3 Example

Demonstrates:
- Loading DDR3 memory standard
- Exploring command sequences (timed and untimed)
- Visualizing Petri net state machine
"""

from drampyml.standards.ddr3 import create_standard
from drampyml.memspecs.ddr3 import DDR3_1600
from drampyml.algorithms.transitions import (
    explore_next_transitions_new,
    print_compact_paths,
)
from drampyml.algorithms.state import current_state, restore_state


def main():
    print("=" * 80)
    print("DRAMBench DDR3 Example")
    print("=" * 80)

    # ========================================================================
    # 1. Load DDR3-1600 Standard
    # ========================================================================
    print("\n[1] Loading DDR3-1600 standard...")

    standard = create_standard(DDR3_1600)
    petri_net = standard.petri_net

    print(f"    Loaded: {len(petri_net.graph.nodes())} nodes, {len(petri_net.graph.edges())} edges")
    print(f"    Config: {DDR3_1600['nbrOfRanks']} rank(s), {DDR3_1600['nbrOfBanks']} bank(s)")

    # ========================================================================
    # 2. Check Available Commands
    # ========================================================================
    print("\n" + "=" * 80)
    print("[2] Available Commands")
    print("=" * 80)

    fireable = petri_net.who_can_fire()

    print(f"\n    {len(fireable)} commands can fire:\n")
    for idx in fireable:
        cmd = petri_net.graph[idx]
        coord_str = f"Rank{cmd.coordinate.rank}"
        if cmd.coordinate.bank is not None:
            coord_str += f" Bank{cmd.coordinate.bank}"
        print(f"    - {cmd.command:6s} @ {coord_str}")

    # ========================================================================
    # 3. Explore Untimed Command Sequences
    # ========================================================================
    print("\n" + "=" * 80)
    print("[3] Untimed Command Sequences")
    print("=" * 80)
    print("\n    Note: Ignores timing constraints, shows structural possibilities\n")

    initial = current_state(petri_net)

    petri_net.ignore_timing_constraints = True
    untimed_paths = explore_next_transitions_new(petri_net, k_max=3, include_timings=False)

    print(f"    Found {len(untimed_paths)} sequences (k=3)\n")
    print_compact_paths(untimed_paths, max_display=20)

    petri_net.ignore_timing_constraints = False
    restore_state(petri_net, initial)

    # ========================================================================
    # 4. Explore Timed Command Sequences (FIXED!)
    # ========================================================================
    print("\n" + "=" * 80)
    print("[4] Timed Command Sequences (Fixed)")
    print("=" * 80)
    print("\n    Note: Uses explore_next_transitions_new() with time advancement\n")

    timed_paths = explore_next_transitions_new(petri_net, k_max=3, include_timings=True)

    print(f"    Found {len(timed_paths)} sequences (k=3)\n")

    if len(timed_paths) > 0:
        print_compact_paths(timed_paths, max_display=20)
    else:
        print("    No timed paths found for k=3. Trying k=2...\n")
        timed_k2 = explore_next_transitions_new(petri_net, k_max=2, include_timings=True)
        print(f"    Found {len(timed_k2)} sequences (k=2)\n")
        if timed_k2:
            for i, path in enumerate(list(timed_k2)[:10], 1):
                parts = [str(ct.command) if j == 0 else f"[{ct.timing}] {ct.command}"
                         for j, ct in enumerate(path)]
                print(f"    {i:2d}. {' -> '.join(parts)}")

    restore_state(petri_net, initial)

    # ========================================================================
    # 5. Visualize Petri Net
    # ========================================================================
    print("\n" + "=" * 80)
    print("[5] Petri Net Visualization")
    print("=" * 80)

    restore_state(petri_net, initial)
    petri_net.write_img("ddr3_initial.svg", image_type='svg')

    print("\n    Initial State:")
    print(f"    - Time: {petri_net.current_time}")
    print(f"    - Fireable: {len(petri_net.who_can_fire())} transitions")
    print("    - Saved: ddr3_initial.svg")

    # ========================================================================
    # 6. Execute Commands
    # ========================================================================
    print("\n" + "=" * 80)
    print("[6] Command Execution Example")
    print("=" * 80)

    restore_state(petri_net, initial)

    act_transitions = [idx for idx in petri_net.who_can_fire()
                       if petri_net.graph[idx].command.name == 'ACT'
                       and petri_net.graph[idx].coordinate.bank == 0]

    if act_transitions:
        print("\n    Firing: ACT to Bank 0")

        petri_net.ignore_timing_constraints = True
        petri_net.fire_transition(act_transitions[0])

        petri_net.write_img("ddr3_after_act.svg", image_type='svg')

        print(f"    After ACT (untimed mode):")
        print(f"    - Fireable: {len(petri_net.who_can_fire())} transitions")
        print("    - Saved: ddr3_after_act.svg")

        fireable_after = petri_net.who_can_fire()
        if fireable_after:
            print("\n    Now available:")
            for idx in list(fireable_after)[:12]:
                cmd = petri_net.graph[idx]
                coord_str = f"R{cmd.coordinate.rank}"
                if cmd.coordinate.bank is not None:
                    coord_str += f"B{cmd.coordinate.bank}"
                print(f"    - {cmd.command:6s} @ {coord_str}")

        petri_net.ignore_timing_constraints = False

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"""
Results:
  - Untimed sequences: {len(untimed_paths)}
  - Timed sequences:   {len(timed_paths)}
  - SVG files: ddr3_initial.svg, ddr3_after_act.svg

Key Functions:
  - explore_next_transitions_new()   : Original (finds 0 timed for k>1)
  - explore_next_transitions_new() : Fixed (advances time, finds {len(timed_paths)} for k=3)

DDR3 Commands:
  ACT  - Activate row
  RD   - Read  
  WR   - Write
  PRE  - Precharge
  REF  - Refresh

Timing Parameters (DDR3-1600):
  tRCD = 10  (ACT to RD/WR delay)
  tRAS = 28  (Min row active time)
  tRP  = 10  (Row precharge time)
  tRC  = 38  (Row cycle time)
""")

    print("=" * 80)
    print("Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
