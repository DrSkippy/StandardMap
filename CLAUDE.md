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

## File Map

| File | Purpose |
|------|---------|
| `StandardMap.pde` | Original Processing source — reference implementation |
| `StandardMap.png` | Reference output image |
| `data/SansSerif-12.vlw` | Processing font (not needed in Python) |

## Development Workflow

```bash
# Run original Processing sketch (requires Processing IDE or processing-java)
processing-java --sketch=. --run

# Python replication (once created)
python standard_map.py
```

## Key References

- Chirikov (1979): original paper introducing the standard map
- Greene (1979): criterion for last KAM torus (K_c ≈ 0.9716)
- Lichtenberg & Lieberman, *Regular and Chaotic Dynamics* (2nd ed.) — canonical textbook
