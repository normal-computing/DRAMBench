# DRAMpyML

**A Formal Modeling Framework for JEDEC DRAM Standards using Timed Petri Nets**

DRAMpyML is a modeling approach for DRAM standards using timed Petri nets, developed by **Fraunhofer IESE** and **Normal Computing**. It addresses the challenges emerging from formalizing increasingly complex DRAM protocols defined in JEDEC standards (DDR2-4, LPDDR2-4, GDDR5-6, HBM2-3).

Like DRAMml, DRAMpyML uses timed Petri nets to capture structure and constraints. Unlike DRAMml, DRAMpyML leverages Python for greater flexibility and direct executability, further pushing adoption amongst industry practitioneers.

## Features

- **Formal Modeling**: Mathematical representation of DRAM standards using timed Petri nets
- **Multiple Standards**: Support for DDR2, DDR3, DDR4, LPDDR2/3/4, GDDR5/6, HBM2
- **Command Sequence Generation**: Generate timed/untimed command sequences for verification
- **Similarity Analysis**: Compute Jaccard index similarity between different Petri net models
- **Modular Architecture**: Separate command sets, timing parameters, and structural specifications
- **Python-based**: Flexible, executable models with direct integration into analysis pipelines

## Ground Truth Release Policy

DRAMpyML releases ground truth Petri nets for **all but the newest JEDEC standards** to avoid polluting auto-formalization benchmarks with data that could be used to train models on recent standards. This ensures that:

- Older standards (DDR2, DDR3, early DDR4, LPDDR2/3, etc.) serve as reliable ground truth for benchmarking
- Newer standard implementations are withheld temporarily to preserve their value as evaluation targets
- All models will eventually be released as standards mature and newer versions emerge

This policy supports rigorous evaluation of automated formalization approaches while maintaining a clean benchmark suite.

## Petri Net Modeling with Rustworks

DRAMpyML leverages [rustworkx](https://github.com/Qiskit/rustworkx) (rx), a high-performance graph library, to construct and manipulate Petri nets. The framework builds timed Petri nets iteratively by adding places, transitions, and arcs with associated timing constraints.

### Example: Building a Petri Net

```python
import rustworkx as rx
from drampyml.components.petri_net import Place, Transition, ResetArc

g = rx.PyDiGraph()

for rank in range(numberOfRanks):
    for bank in range(numberOfBanks):
        # ACTIVE place with an associated bank coordinate:
        p_active = g.add_node(Place(ACTIVE, bank_coord))
        # PREA transition with an associated rank coordinate:
        t_prea = g.add_node(Transition(PREA, rank_coord))
        # Reset arc from ACTIVE to PREA:
        g.add_edge(p_active, t_prea, ResetArc())
```

In each level of hierarchy, the respective places, transitions, and arcs are added to the graph. The timing dependencies are similarly defined at this level.

## Arc Types and Constraints

DRAMpyML supports multiple arc types to model different Petri net semantics, as defined in [petri_net.py](drampyml/components/petri_net.py):

### Arc Types

1. **Standard Arc** (`Arc`):
   - Represents normal token consumption/production
   - Has a weight indicating number of tokens consumed/produced
   - Enables transition when source place has at least `weight` tokens

2. **Inhibitor Arc** (`InhibitorArc`):
   - Prevents transition firing when source place has ≥ `weight` tokens
   - Used to model exclusive access and mutual exclusion
   - Represented with a dot arrowhead in visualizations

3. **Reset Arc** (`ResetArc`):
   - Removes all tokens from source place when transition fires
   - Used for bank precharge operations and state resets
   - Shown in red with double arrowheads in visualizations

4. **Timed Arc** (`TimedArc`):
   - Includes a lower bound timing constraint
   - Tokens are only "valid" after `lower_bound` time units have elapsed
   - Uses symbolic expressions (sympy) for timing parameters
   - Shown in blue with interval notation `[lower_bound, ∞[`

5. **Custom Arc** (`CustomArc`):
   - Enforces complex timing constraints between transitions
   - Prevents transition firing until constraint is satisfied
   - Tracks timestamps for inter-command timing dependencies
   - Shown with diamond arrowheads in visualizations

### Timing Constraints

Timing constraints are applied using the `CommandTimingConstraint` class from [command_timing.py](drampyml/constraints/command_timing.py). Due to the large number of possible command transitions, timing arcs are generated in a second step:

```python
from drampyml.constraints.command_timing import CommandTimingConstraint

CommandTimingConstraint(
    intra_bank, [ACT], [RD, WR, RDA, WRA], tRCD
)
```

This example applies the timing constraint `tRCD` between the `ACT` command and the column commands `RD`, `RDA`, `WR`, and `WRA` for a specific memory bank. The commands are interpreted as a **Cartesian product** of the two lists (`{ACT} × {RD, RDA, WR, WRA}`), generating a timing arc for every combination.

Timing constraints are defined using:
- **Target selectors**: Functions that determine which coordinates (rank, bank, etc.) the constraint applies to
- **Previous commands**: List of source commands
- **Next commands**: List of target commands
- **Timing expression**: Symbolic expression (e.g., `tRCD`, `tRAS`) substituted with actual values from memspec

## Command Sequence Generation

DRAMpyML can generate both **timed** and **untimed** valid command sequences using the unrolling algorithm in [unroll.py](drampyml/algorithms/unroll.py) and [transitions.py](drampyml/algorithms/transitions.py).

### Reachability Graph Generation (Untimed)

The `unroll_petri_net` function builds a reachability graph via breadth-first search (BFS):

```python
from drampyml.algorithms.unroll import unroll_petri_net

# Generate reachability graph
graph, max_depth = unroll_petri_net(petri_net, numberOfBanks)
```

- **Nodes** represent Petri net states (markings)
- **Edges** represent transitions (commands)
- Explores all reachable states up to a maximum bound
- Returns the reachability graph and maximum BFS depth

### Command Sequence Exploration (Timed)

The `explore_next_transitions_new` function generates k-step command sequences:

```python
from drampyml.algorithms.transitions import explore_next_transitions_new

# Generate all valid k-step command sequences with timing information
paths = explore_next_transitions_new(
    petri_net,
    k_max=5,
    include_timings=True
)
```

Each path is a tuple of `CommandTransition` objects containing:
- **Command**: The DRAM command (e.g., ACT, RD, WR, PRE)
- **Coordinate**: The target location (rank, bank)
- **Timing**: The minimum delay before this command can execute (when `include_timings=True`)

### Jaccard Index Similarity

Command sequences can be used to compute similarity between two Petri nets using the **Jaccard index**:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

Where:
- `A` and `B` are sets of valid k-step command sequences from two different Petri nets
- The intersection `|A ∩ B|` represents common valid sequences
- The union `|A ∪ B|` represents all valid sequences from either model

This metric quantifies how similar two DRAM models are in terms of their legal command sequences, useful for:
- Comparing different implementations of the same standard
- Measuring differences between DRAM generations
- Validating auto-formalization results against ground truth

## Project Structure

DRAMpyML organizes specifications into modular components:

```
drampyml/
├── algorithms/          # Petri net analysis algorithms
│   ├── unroll.py       # Reachability graph generation
│   ├── transitions.py  # Command sequence exploration
│   └── state.py        # State management utilities
├── command_sets/       # Command sets for each standard
│   ├── ddr2.py
|    ...
├── components/         # Core Petri net components
│   ├── petri_net.py   # Petri net classes (Place, Transition, Arc types)
│   └── standard.py    # Standard wrapper class
├── constraints/        # Constraint definitions
│   ├── command_timing.py  # Timing constraint generation
│   ├── naw.py            # Bank group constraints
│   └── queries.py        # Coordinate selectors
├── memspecs/          # Complete memory specifications
│   ├── ddr2.py        # Combines timing + structural params
|   ...
├── standards/         # Petri net generators for each standard
│   ├── ddr2.py
|   ...
└── timing_params/     # Timing parameters only
|    ├── ddr2.py        # e.g., tRCD, tRAS, tRP, tRC, tRFC
|   ...
```

### Component Descriptions

- **`command_sets/`**: Lists of valid commands for each DRAM standard (e.g., `["ACT", "RD", "WR", "PRE", "REF"]`)
- **`timing_params/`**: Timing parameters only (e.g., `{"tRCD": 10, "tRAS": 28, "tRP": 10}`)
- **`memspecs/`**: Complete specifications combining:
  - Structural parameters (number of ranks, banks, burst length, data rate)
  - Timing parameters (imported from `timing_params/`)
  - Example: `DDR3_1600 = {**DDR3_1600_STRUCT, **DDR3_1600_TIMING}`
- **`standards/`**: Petri net construction code for each standard
- **`constraints/`**: Constraint generation utilities for timing arcs

This modular structure allows easy comparison of standards and parameter variation studies.

## Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. It's the recommended way to install DRAMpyML.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/drampyml.git
cd DRAMBench

# Create a virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

The `uv sync` command will:
- Create a virtual environment (if it doesn't exist)
- Install Python 3.13+ (if needed)
- Install all dependencies from `pyproject.toml`
- Lock dependencies in `uv.lock` for reproducibility

### Alternative: Using pip

```bash
# Clone the repository
git clone https://github.com/your-org/drampyml.git
cd DRAMBench

# Create and activate a virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # On Unix/macOS

# Install the package
pip install -e .
```

### Requirements

- **Python**: 3.13 or higher
- **Dependencies**: rustworkx, sympy, tqdm, frozendict, pydot, pillow, networkx, jinja2, pydantic, pytest

## Usage Example

```python
from drampyml.standards.ddr3 import ddr3
from drampyml.memspecs.ddr3 import DDR3_1600
from drampyml.algorithms.transitions import explore_next_transitions_new

# Create DDR3 Petri net
petri_net = ddr3(DDR3_1600)

# Generate all valid 4-step command sequences with timing
paths = explore_next_transitions_new(
    petri_net,
    k_max=4,
    include_timings=True
)

print(f"Found {len(paths)} valid 4-step command sequences")

# Example path: ACT → [tRCD] RD → [tCCD] RD → [tRTP] PRE
for path in list(paths)[:5]:
    cmd_str = " → ".join(
        f"[{ct.timing}] {ct.command}" if ct.timing else str(ct.command)
        for ct in path
    )
    print(cmd_str)
```

## Visualization

Petri nets can be exported to DOT format or rendered as images:

```python
# Export to DOT file
petri_net.write_dot("ddr3_model.dot")

# Render as PNG/SVG
petri_net.write_img("ddr3_model.png", format="png")
```

Visualization features:
- **Places**: Circles with tokens shown as dots (•)
- **Transitions**: Rectangles (green = enabled, red = disabled)
- **Arcs**: Color-coded by type (blue = timed, red = reset, black = standard)

## References

1. **DRAMpyML**
   [https://arxiv.org/abs/2602.10654](https://arxiv.org/abs/2602.10654)

2. **Autoformalizing Memory Device Specifications using Agents** (Forthcoming)

## Contributing

Contributions are welcome! Please open issues or pull requests on the GitHub repository.

## License

[What should our license be?]

## Acknowledgments

Developed by **Fraunhofer IESE** and **Normal Computing** as part of research on formal verification of memory systems.

---

For questions or support, please open an issue on the GitHub repository.
