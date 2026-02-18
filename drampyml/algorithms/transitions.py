from collections import Counter
from typing import Hashable, Optional

from drampyml.common.commands import Command
from drampyml.algorithms.state import current_state, restore_state
from drampyml.components.petri_net import Arc, Coordinate, CustomArc, PetriNet, Place, PlaceType, Token, Transition
from dataclasses import dataclass
import rustworkx as rx
from sympy import N, Add, Expr, Max, Integer, Sum, simplify
import time
import statistics
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandTransition:
    command: Command
    coordinate: Coordinate
    transition_id: int = field(repr=False)
    timing: Optional[Expr] = None
    
# ------------------------------------------------------------------------
# Exploration of the Petri net (Timings)
# ------------------------------------------------------------------------

def _get_timing(petri_net: PetriNet, from_transition: int, to_transition: int):
    try:
        edge: CustomArc = petri_net.graph.get_edge_data(from_transition, to_transition)
        return edge.time_constraint
    except rx.NoEdgeBetweenNodes:
        return Integer(0)


def _get_max_timing(petri_net: PetriNet, from_transitions: tuple[CommandTransition], to_transition: int):
    if len(from_transitions) == 0:
        return Integer(0)
    direct_from_to_timings = [_get_timing(petri_net, from_transition.transition_id, to_transition) 
               for from_transition in from_transitions]
    adjusted_timings = [direct_from_to_timings[-1]]
    delta = direct_from_to_timings[-1]
    for idx, timing in enumerate(reversed(direct_from_to_timings[:-1]), 1):
        if timing == 0 or timing == adjusted_timings[0]:
            continue
        i = from_transitions[-idx].timing
        delta = delta + from_transitions[-idx].timing
        adjusted_timings.append(timing - delta)
    return Max(*adjusted_timings) if len(adjusted_timings) > 1 else adjusted_timings[0]
    

# ------------------------------------------------------------------------
# Exploration of the Petri net (Algorithms)
# ------------------------------------------------------------------------

def explore_next_transitions(
    petri_net: PetriNet, k_max: int, current_path: tuple[CommandTransition, ...] = (), include_timings: bool = False
) -> set[tuple[CommandTransition, ...]]:
    if len(current_path) == k_max:
        return {current_path}

    paths: set[tuple[CommandTransition, ...]] = set()
    for transition in petri_net.who_can_fire():
        if include_timings:
            timing_expr = _get_max_timing(petri_net, current_path, transition)
            timing = timing_expr.subs(petri_net.memspec)
        else:
            timing = None
        command_transition = CommandTransition(
            command=petri_net.graph[transition].command,
            coordinate=petri_net.graph[transition].coordinate,
            transition_id=transition,
            timing=timing
        )

        temp_state = current_state(petri_net)
        petri_net.fire_transition(transition)
        new_path = (*current_path, command_transition)
        following_paths = explore_next_transitions(petri_net, k_max, new_path, include_timings)
        restore_state(petri_net, temp_state)

        paths |= following_paths

    return paths


def explore_next_transitions_new(
    petri_net: PetriNet,
    k_max: int,
    include_timings: bool = True
) -> set[tuple[CommandTransition, ...]]:
    """
    Explore command sequences with caching and time advancement.

    This function properly advances current_time when exploring timed sequences,
    allowing it to find valid paths in both timed and untimed modes.

    - In untimed mode (ignore_timing_constraints=True): Finds all structurally valid paths
    - In timed mode (ignore_timing_constraints=False): Advances time and respects timing constraints

    Args:
        petri_net: The Petri net to explore
        k_max: Maximum depth to explore
        include_timings: Whether to include timing information in results

    Returns:
        Set of command transition paths with proper timing information

    Example:
        >>> petri_net = create_standard(DDR3_1600).petri_net
        >>> # Untimed exploration
        >>> petri_net.ignore_timing_constraints = True
        >>> untimed = explore_next_transitions_new(petri_net, k_max=3)
        >>> # Timed exploration
        >>> petri_net.ignore_timing_constraints = False
        >>> timed = explore_next_transitions_new(petri_net, k_max=3)
    """
    from drampyml.components.petri_net import TimedArc

    graph = petri_net.graph
    place_indices = sorted(graph.filter_nodes(lambda n: isinstance(n, Place)))
    transition_indices = sorted(graph.filter_nodes(lambda n: isinstance(n, Transition)))

    # Cache transition metadata
    transition_meta = {
        idx: (graph[idx].command, graph[idx].coordinate)
        for idx in transition_indices
    }

    def make_state_key() -> Hashable:
        places_sig = tuple(
            tuple(token.timestamp for token in graph[place_idx].tokens)
            for place_idx in place_indices
        )
        custom_arc_indices = [
            edge_idx for edge_idx in graph.edge_indices()
            if isinstance(graph.get_edge_data_by_index(edge_idx), CustomArc)
        ]
        edge_sig = tuple(
            graph.get_edge_data_by_index(edge_idx).timestamp
            for edge_idx in custom_arc_indices
        )
        return (petri_net.current_time, places_sig, edge_sig)

    def find_next_fireable_time():
        """Find minimum time when at least one transition becomes fireable."""
        current = petri_net.current_time
        min_times = []

        for t_idx in transition_indices:
            if graph[t_idx].active:
                continue

            in_edges = graph.in_edges(t_idx)
            for src_idx, _, edge_data in in_edges:
                if isinstance(edge_data, TimedArc):
                    src_tokens = graph[src_idx].tokens
                    if src_tokens:
                        lower_bound = edge_data.lower_bound.subs(petri_net.memspec)
                        for token in src_tokens:
                            required_time = token.timestamp + lower_bound
                            min_times.append(required_time)

        return max(current + 1, min(min_times)) if min_times else None

    cache: dict[tuple[Hashable, int], set[tuple[int, ...]]] = {}

    def dfs(depth: int) -> set[tuple[int, ...]]:
        if depth == k_max:
            return {()}

        key = (make_state_key(), depth)
        if key in cache:
            return cache[key]

        base_state = current_state(petri_net)
        petri_net.evaluate()
        enabled = [t for t in transition_indices if graph[t].active]

        results: set[tuple[int, ...]] = set()
        for t in enabled:
            petri_net.fire_transition(t)

            # Advance time for timed exploration
            if not petri_net.ignore_timing_constraints:
                next_time = find_next_fireable_time()
                if next_time and next_time > petri_net.current_time:
                    petri_net.current_time = next_time
                    petri_net.evaluate()

            suffixes = dfs(depth + 1)
            for suf in suffixes:
                results.add((t,) + suf)

            restore_state(petri_net, base_state)

        cache[key] = results
        return results

    # Explore paths
    transition_id_paths = dfs(0)

    # Convert to CommandTransition paths
    result: set[tuple[CommandTransition, ...]] = set()
    for path in transition_id_paths:
        command_transitions: list[CommandTransition] = []
        for t_id in path:
            command, coordinate = transition_meta[t_id]

            if include_timings:
                timing_expr = _get_max_timing(petri_net, tuple(command_transitions), t_id)
                timing = timing_expr.subs(petri_net.memspec)
            else:
                timing = None

            ct = CommandTransition(
                command=command,
                coordinate=coordinate,
                transition_id=t_id,
                timing=timing
            )
            command_transitions.append(ct)

        result.add(tuple(command_transitions))

    return result


# ------------------------------------------------------------------------
# Statistics and output of results
# ------------------------------------------------------------------------


def print_exploration_results(
    paths: set[tuple[CommandTransition, ...]],
    title: str = "Exploration Results",
    max_paths_to_show: Optional[int] = None,
    show_statistics: bool = True
) -> None:
    """
    Prints the exploration results in a readable format.
    
    Args:
        paths: Set of paths from explore_next_transitions
        title: Title for the output
        max_paths_to_show: Maximum number of paths to display (None = all)
        show_statistics: Whether to show summary statistics
    """
    if not paths:
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}")
        print("No paths found!")
        return
    
    # Convert to list (no sorting, since symbolic timings can't be meaningfully compared)
    path_list = list(paths)
    
    # Limit number of paths to show
    paths_to_display = path_list[:max_paths_to_show] if max_paths_to_show else path_list
    remaining_paths = len(path_list) - len(paths_to_display)
    
    # Print header
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    print(f"Total paths found: {len(paths)}")
    print(f"Displaying: {len(paths_to_display)} path(s)")
    if remaining_paths > 0:
        print(f"({remaining_paths} more path(s) not shown)")
    print(f"{'='*80}\n")
    
    # Print each path
    for idx, path in enumerate(paths_to_display, 1):
        print(f"Path {idx}:")
        print(f"{'-'*80}")
        
        if not path:
            print("  (empty path)")
        else:
            # Print each transition in the path
            for step_num, ct in enumerate(path, 1):
                print(f"  Step {step_num}:")
                print(f"    Command:    {ct.command}")
                print(f"    Coordinate: {ct.coordinate}")
                if ct.timing is not None:
                    print(f"    Timing:     {ct.timing}")
                if step_num < len(path):
                    print()
        
        print(f"{'='*80}\n")
    
    # Show statistics
    if show_statistics and paths:
        print_path_statistics(paths)


def print_path_statistics(paths: set[tuple[CommandTransition, ...]]) -> None:
    """
    Prints statistical summary of the paths.
    """
    print(f"\n{'='*80}")
    print("Statistics")
    print(f"{'='*80}")
    
    # Path length statistics
    path_lengths = [len(path) for path in paths]
    print(f"\nPath Lengths:")
    print(f"  Min:     {min(path_lengths)}")
    print(f"  Max:     {max(path_lengths)}")
    print(f"  Average: {statistics.mean(path_lengths):.2f}")
    
    # Command frequency
    all_commands = [ct.command for path in paths for ct in path]
    command_counts = Counter(all_commands)
    print(f"\nCommand Frequency:")
    for command, count in command_counts.most_common():
        print(f"  {command}: {count}")
    
    # Coordinate frequency
    all_coordinates = [ct.coordinate for path in paths for ct in path]
    coord_counts = Counter(all_coordinates)
    print(f"\nCoordinate Frequency:")
    for coord, count in coord_counts.most_common(10):  # Show top 10
        print(f"  {coord}: {count}")
    if len(coord_counts) > 10:
        print(f"  ... and {len(coord_counts) - 10} more")
    
    # Timing statistics (if available)
    if paths and any(ct.timing is not None for path in paths for ct in path):
        print(f"\nTiming Information:")
        unique_timings = set()
        for path in paths:
            for ct in path:
                if ct.timing is not None:
                    unique_timings.add(str(ct.timing))
        print(f"  Unique timing expressions: {len(unique_timings)}")
        if len(unique_timings) <= 10:
            for timing in sorted(unique_timings):
                print(f"    {timing}")
    
    print(f"{'='*80}\n")


def print_comparison_table(
    old_paths: set[tuple[CommandTransition, ...]],
    new_paths: set[tuple[CommandTransition, ...]],
    old_times: list[float],
    new_times: list[float]
) -> None:
    """
    Prints a comparison table between old and new exploration methods.
    """
    print(f"\n{'='*80}")
    print("Method Comparison")
    print(f"{'='*80}")
    
    # Results comparison
    print(f"\n{'Results':<30} {'Old Method':<20} {'New Method':<20}")
    print(f"{'-'*70}")
    print(f"{'Number of paths:':<30} {len(old_paths):<20} {len(new_paths):<20}")
    print(f"{'Results identical:':<30} {str(old_paths == new_paths):<20}")
    
    # Performance comparison
    print(f"\n{'Performance (seconds)':<30} {'Old Method':<20} {'New Method':<20}")
    print(f"{'-'*70}")
    print(f"{'Min time:':<30} {min(old_times):<20.6f} {min(new_times):<20.6f}")
    print(f"{'Mean time:':<30} {statistics.mean(old_times):<20.6f} {statistics.mean(new_times):<20.6f}")
    print(f"{'Max time:':<30} {max(old_times):<20.6f} {max(new_times):<20.6f}")
    print(f"{'Std deviation:':<30} {statistics.pstdev(old_times):<20.6f} {statistics.pstdev(new_times):<20.6f}")
    
    # Speedup
    speedup = statistics.mean(old_times) / statistics.mean(new_times)
    print(f"\n{'Speedup:':<30} {speedup:.2f}x")
    print(f"{'='*80}\n")


def print_compact_paths(paths: set[tuple[CommandTransition, ...]], max_display: int = 20) -> None:
    """
    Prints paths in a compact, one-line-per-path format with individual timings.
    """
    print(f"\n{'='*80}")
    print(f"Compact Path View ({len(paths)} paths)")
    print(f"{'='*80}\n")
    
    path_list = list(paths)
    
    for idx, path in enumerate(path_list[:max_display], 1):
        if not path:
            print(f"{idx:3d}. (empty)")
        else:
            # Build path string with timings for each command (except first which is 0)
            parts = []
            for i, ct in enumerate(path):
                if i == 0:
                    # First command, no timing shown (it's 0)
                    parts.append(str(ct.command))
                else:
                    # Subsequent commands with timing
                    if ct.timing is not None:
                        parts.append(f"[{ct.timing}] {ct.command}")
                    else:
                        parts.append(str(ct.command))
            
            path_str = " → ".join(parts)
            print(f"{idx:3d}. {path_str}")
    
    if len(path_list) > max_display:
        print(f"\n... and {len(path_list) - max_display} more paths")
    
    print(f"{'='*80}\n")


def print_timing_distribution(paths: set[tuple[CommandTransition, ...]]) -> None:
    """
    Shows distribution of timing expressions across paths.
    """
    print(f"\n{'='*80}")
    print("Timing Distribution")
    print(f"{'='*80}\n")
    
    # Collect all timing expressions
    timing_counter = Counter()
    
    for path in paths:
        for ct in path:
            if ct.timing is not None:
                timing_counter[str(ct.timing)] += 1
    
    if not timing_counter:
        print("No timing information available.")
        print(f"{'='*80}\n")
        return
    
    print(f"Unique timing expressions: {len(timing_counter)}\n")
    
    for timing_expr, count in timing_counter.most_common(20):
        percentage = (count / sum(timing_counter.values())) * 100
        print(f"{count:4d} occurrences ({percentage:5.1f}%): {timing_expr}")
    
    if len(timing_counter) > 20:
        print(f"\n... and {len(timing_counter) - 20} more unique expressions")
    
    print(f"{'='*80}\n")


# ------------------------------------------------------------------------
# Benchmark for exploartion
# ------------------------------------------------------------------------

def run_benchmark(petri_net: PetriNet, k_max: int, runs: int = 5) -> None:
    """
    Compares the speed of both exploration algorithms and prints the results.
    """
    # Snapshot of state to be fair
    snap = current_state(petri_net)

    def time_fn(fn):
        times = []
        for _ in range(runs):
            restore_state(petri_net, snap)
            t0 = time.perf_counter()
            res = fn()
            t1 = time.perf_counter()
            times.append(t1 - t0)
        return times

    for incl_timings in [False, True]:
        print(f"\n{'#'*80}")
        print(f"# Benchmark with include_timings={incl_timings}")
        print(f"{'#'*80}\n")
        
        restore_state(petri_net, snap)
        res_old = explore_next_transitions(petri_net, k_max=k_max, include_timings=incl_timings)
        restore_state(petri_net, snap)
        res_new = explore_next_transitions_new(petri_net, k_max=k_max, include_timings=incl_timings)
        same = res_old == res_new

        old_times = time_fn(lambda: explore_next_transitions(petri_net, k_max=k_max, include_timings=incl_timings))
        new_times = time_fn(lambda: explore_next_transitions_new(petri_net, k_max=k_max, include_timings=incl_timings))

        def stats(label, arr):
            print(f"{label}: runs={runs}, min={min(arr):.6f}s, mean={statistics.mean(arr):.6f}s, stdev={statistics.pstdev(arr):.6f}s")

        print(f"Num paths old: {len(res_old)}, new: {len(res_new)}, identical: {same}")
        stats("(Old) explore_next_transitions", old_times)
        stats("(New) explore_next_transitions_new", new_times)
