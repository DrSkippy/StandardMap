"""Initial-condition strategies for seeding trajectories in a viewport.

Each seeder is a pure function ``(x_range, y_range, cfg) -> (x, y)`` and is
registered in :data:`SEEDERS` under its :class:`SeedMode`.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt
from scipy.stats.qmc import Halton

from .config import SeedingConfig, SeedMode, coerce_enum
from .exceptions import InvalidSeedModeError

FloatArray = npt.NDArray[np.float64]
Range = tuple[float, float]
Seeds = tuple[FloatArray, FloatArray]
Seeder = Callable[[Range, Range, SeedingConfig], Seeds]


def seed_grid(x_range: Range, y_range: Range, cfg: SeedingConfig) -> Seeds:
    """Place ``nx * ny`` seeds on a regular grid covering the viewport.

    Args:
        x_range: ``(x_min, x_max)`` of the viewport in data units.
        y_range: ``(y_min, y_max)`` of the viewport in data units.
        cfg: Seeding configuration (uses ``nx`` and ``ny``).

    Returns:
        Flattened ``(x, y)`` arrays of length ``nx * ny``.
    """
    xs = np.linspace(x_range[0], x_range[1], cfg.nx, endpoint=False)
    ys = np.linspace(y_range[0], y_range[1], cfg.ny, endpoint=False)
    x_grid, y_grid = np.meshgrid(xs, ys)
    return x_grid.ravel(), y_grid.ravel()


def seed_quasi_random(x_range: Range, y_range: Range, cfg: SeedingConfig) -> Seeds:
    """Place ``nx * ny`` seeds from a scrambled 2-D Halton sequence.

    Low-discrepancy points avoid aliasing between a regular grid and the
    map's own periodic structure.

    Args:
        x_range: ``(x_min, x_max)`` of the viewport in data units.
        y_range: ``(y_min, y_max)`` of the viewport in data units.
        cfg: Seeding configuration (uses ``nx``, ``ny`` and ``rng_seed``).

    Returns:
        ``(x, y)`` arrays of length ``nx * ny``.
    """
    sampler = Halton(d=2, scramble=True, seed=cfg.rng_seed)
    unit_points = sampler.random(cfg.nx * cfg.ny)
    x = unit_points[:, 0] * (x_range[1] - x_range[0]) + x_range[0]
    y = unit_points[:, 1] * (y_range[1] - y_range[0]) + y_range[0]
    return x, y


def seed_legacy(x_range: Range, y_range: Range, cfg: SeedingConfig) -> Seeds:
    """Replicate the original Processing seeding: fixed x, linear y sweep.

    The Processing sketch used ``x = (dataX2 - dataX1) / 2`` (half the
    viewport width, which is only the midpoint at full view); the midpoint is
    used here so the sweep stays inside a zoomed viewport. The y sweep
    excludes both endpoints, exactly as in the original.

    Args:
        x_range: ``(x_min, x_max)`` of the viewport in data units.
        y_range: ``(y_min, y_max)`` of the viewport in data units.
        cfg: Seeding configuration (uses ``legacy_count``).

    Returns:
        ``(x, y)`` arrays of length ``legacy_count``.
    """
    count = cfg.legacy_count
    x_mid = (x_range[0] + x_range[1]) / 2.0
    x: FloatArray = np.full(count, x_mid, dtype=np.float64)
    sweep = np.arange(1, count + 1) * (y_range[1] - y_range[0]) / float(count + 1)
    y = np.asarray(y_range[0] + sweep, dtype=np.float64)
    return x, y


SEEDERS: dict[SeedMode, Seeder] = {
    SeedMode.GRID: seed_grid,
    SeedMode.QUASI_RANDOM: seed_quasi_random,
    SeedMode.LEGACY: seed_legacy,
}


def generate_seeds(
    mode: SeedMode | str, x_range: Range, y_range: Range, cfg: SeedingConfig
) -> Seeds:
    """Generate initial conditions with the strategy named by ``mode``.

    Args:
        mode: Seeding strategy (member or its string value).
        x_range: ``(x_min, x_max)`` of the viewport in data units.
        y_range: ``(y_min, y_max)`` of the viewport in data units.
        cfg: Seeding configuration.

    Returns:
        ``(x, y)`` arrays of initial conditions.

    Raises:
        InvalidSeedModeError: If ``mode`` is not a known strategy.
    """
    seed_mode = coerce_enum(SeedMode, mode, InvalidSeedModeError)
    return SEEDERS[seed_mode](x_range, y_range, cfg)
