# StandardMap

## Project Overview

Interactive visualization of the **Chirikov Standard Map**, a canonical model in chaos theory that demonstrates the transition from regular (KAM tori) to chaotic dynamics in a Hamiltonian system.

**Original implementation**: Processing (Java-based), `StandardMap.pde`  
**Target**: Python replication with improved fractal-space coverage

## Standard Map Equations

The discrete-time map on the torus [0, 2π) × [0, 2π):

```
y_{n+1} = (y_n + K · sin(x_n))  mod 2π
x_{n+1} = (x_n + y_{n+1})       mod 2π
```

- **K** is the nonlinearity (chaos) parameter
- `K = 0.97` sits at the "edge of chaos" — the last KAM torus breaks down around `K ≈ 0.9716`
- Below this threshold: islands of stability surrounded by thin chaotic layers
- Above: globally chaotic diffusion

## Current Processing Implementation

| Parameter | Value | Notes |
|-----------|-------|-------|
| `n_trajectories` | 85 | One color per trajectory |
| `K` | 0.97 | Edge of chaos |
| Iterations per frame | 40 | Animation speed |
| Window | 800 × 800 px | Square phase-space plot |
| Initial x | `(x_max - x_min) / 2` | All trajectories start at the same x |
| Initial y | Linear grid from `y_min` to `y_max` | Uniform 1D sweep |

**Limitation**: All initial conditions share the same x-value, so trajectories only sample one vertical slice of phase space. Large regions of fractal structure — especially near the island chains and the cantori — are never seeded and never appear.

## Python Replication Goal

Rewrite the visualization in Python, preserving all existing functionality:

- Interactive zoom (click-drag rectangle)
- Double-click reset to full view
- Per-trajectory color coding (HSV)
- Real-time animated iteration
- On-screen display of coordinate bounds and K value

**Recommended stack**: `pygame` for the interactive window, or `matplotlib` with a custom event loop. `numpy` for vectorized map iteration.

### Vectorized map iteration (numpy skeleton)

```python
import numpy as np

K = 0.97

def step(x, y):
    y_new = (y + K * np.sin(x)) % (2 * np.pi)
    x_new = (x + y_new)        % (2 * np.pi)
    return x_new, y_new
```

## Improved Initial-Point Coverage

The core improvement task: seed trajectories across **both** x and y dimensions to fill the fractal structure of the phase portrait.

### Strategies (in order of priority)

1. **2D Grid sampling** — replace the 1D vertical sweep with a full grid:
   ```python
   nx, ny = 20, 20  # → 400 trajectories
   xs = np.linspace(0, 2*np.pi, nx, endpoint=False)
   ys = np.linspace(0, 2*np.pi, ny, endpoint=False)
   x0, y0 = np.meshgrid(xs, ys)
   x, y = x0.ravel(), y0.ravel()
   ```

2. **Quasi-random (low-discrepancy) sampling** — Halton or Sobol sequences give better
   uniform coverage than a regular grid (avoids aliasing with the map's periodicity):
   ```python
   from scipy.stats.qmc import Halton
   sampler = Halton(d=2, scramble=True)
   pts = sampler.random(n=500) * 2 * np.pi
   x, y = pts[:, 0], pts[:, 1]
   ```

3. **Adaptive / zoom-aware reseeding** — when the user zooms into a sub-region, reseed
   with higher density inside that viewport so the fractal detail fills in quickly.

4. **Importance sampling near island boundaries** — after a burn-in period, detect
   trajectories that wander (chaotic) vs. stay bounded (regular), and add extra seeds
   near the boundary to resolve the cantori structure.

### Trajectory count guidance

| Coverage goal | Approx. trajectories |
|---------------|----------------------|
| Reproduce original | 85 (1D sweep) |
| Basic 2D fill | 400–900 (20×20 – 30×30 grid) |
| High-resolution fractal detail | 2 000–10 000 (quasi-random) |
| Zoom-in adaptive | scale with viewport area |

## Environment Setup with uv

[uv](https://docs.astral.sh/uv/) is the recommended tool for managing the Python environment and dependencies for this project.

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create and activate the virtual environment

```bash
# Create a .venv in the project root (Python 3.11+ recommended)
uv venv --python 3.11

# Activate
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### Install dependencies

```bash
# Core dependencies
uv pip install numpy scipy pygame

# Optional: Jupyter for exploratory work
uv pip install jupyterlab matplotlib
```

### Pin dependencies with a lockfile

```bash
# Generate a requirements file from the active environment
uv pip freeze > requirements.txt

# Recreate the exact environment from the lockfile
uv pip sync requirements.txt
```

### Recommended `pyproject.toml` (once the Python source exists)

```toml
[project]
name = "standard-map"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "scipy>=1.12",
    "pygame>=2.5",
]

[tool.uv]
dev-dependencies = [
    "jupyterlab",
    "matplotlib",
]
```

With a `pyproject.toml` present, use:

```bash
uv sync          # install all deps into .venv
uv sync               # dev dependency group is included by default
uv run python standard_map.py   # run without activating manually
```

## File Map

| File | Purpose |
|------|---------|
| `StandardMap.pde` | Original Processing source — reference implementation |
| `StandardMap.png` | Reference output image |
| `data/SansSerif-12.vlw` | Processing font (not needed in Python) |
| `standard_map/config.py` | Enums (`SeedMode`, `ColorMode`) and frozen dataclasses for every tunable; TOML loading |
| `standard_map/exceptions.py` | `StandardMapError` hierarchy |
| `standard_map/seeding.py` | Seeder functions + `SEEDERS` registry |
| `standard_map/map_engine.py` | `wrap_to_torus`, `standard_map_step`, `MapEngine` state |
| `standard_map/viewport.py` | `Bounds`, `CoordTransform` (data ↔ pixel, zoom) |
| `standard_map/projection.py` | `project_and_clip` for a batch of iterations |
| `standard_map/color.py` | Per-trajectory color tables |
| `standard_map/renderer.py` | pygame drawing: points, HUD, zoom rectangle |
| `standard_map/gestures.py` | Double-click and drag state machines (pygame-free) |
| `standard_map/controls.py` | Key bindings table and window caption |
| `standard_map/app.py` | `App` orchestrator, `build_app`, `main` |
| `standard_map/cli.py` | argparse → `AppConfig` |
| `standard_map.example.toml` | All configurable values with defaults |
| `tests/` | pytest suite (headless pygame via `SDL_VIDEODRIVER=dummy`) |
| `scripts/make_screenshots.py` | Regenerates `docs/screenshots/*.png` used by README |

## Development Workflow

```bash
# Run original Processing sketch (requires Processing IDE or processing-java)
processing-java --sketch=. --run

# Set up Python environment (first time)
uv venv --python 3.11
uv sync

# Run Python replication
uv run standard-map                          # via pyproject.toml script entry
uv run python -m standard_map                # via package __main__
uv run python run.py                         # via convenience shim

# With options
uv run standard-map --seed-mode quasi_random --nx 50 --ny 50
uv run standard-map --K 1.2 --color-mode legacy_rgb
uv run standard-map --config standard_map.example.toml   # every calibration value lives here

# Tests, lint, type check (coverage gate: 80%)
uv run pytest
uv run ruff check standard_map tests
uv run mypy

# Or activate the venv and run directly
source .venv/bin/activate
python -m standard_map
```

### Keyboard shortcuts (Python version)

| Key | Action |
|-----|--------|
| Drag | Zoom into rectangle |
| Double-click | Reset to full view |
| `r` / Esc | Reset to full view |
| `s` | Cycle seed mode (grid → quasi_random → legacy) |
| `↑` / `↓` | Increase / decrease K by 0.01 (`physics.K_step`) |
| `+` / `-` | Increase / decrease seed density (±5 per axis, `seeding.density_step`) |
| `q` | Quit |

## Key References

- Chirikov (1979): original paper introducing the standard map
- Greene (1979): criterion for last KAM torus (K_c ≈ 0.9716)
- Lichtenberg & Lieberman, *Regular and Chaotic Dynamics* (2nd ed.) — canonical textbook
