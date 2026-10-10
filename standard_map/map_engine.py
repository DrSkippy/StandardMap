"""Vectorized iteration of the Chirikov Standard Map on the torus.

The map, with all coordinates taken mod 2*pi::

    y_{n+1} = y_n + K * sin(x_n)
    x_{n+1} = x_n + y_{n+1}
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import numpy.typing as npt

from .config import TWO_PI, SeedingConfig, SeedMode, coerce_enum
from .exceptions import InvalidSeedModeError
from .seeding import Range, generate_seeds

FloatArray = npt.NDArray[np.float64]


def wrap_to_torus(values: FloatArray) -> FloatArray:
    """Reduce values into ``[0, 2*pi)``.

    Floating-point ``%`` can return exactly ``2*pi`` for tiny negative inputs
    (e.g. ``-1e-17 % (2*pi)``); those are mapped to ``0.0`` so every result
    lies strictly inside the half-open interval.

    Args:
        values: Array of angles.

    Returns:
        A new array of wrapped angles.
    """
    wrapped = values % TWO_PI
    wrapped[wrapped >= TWO_PI] = 0.0  # guard rare fp edge-case
    return wrapped


def standard_map_step(x: FloatArray, y: FloatArray, K: float) -> tuple[FloatArray, FloatArray]:
    """Apply one iteration of the Standard Map.

    Args:
        x: Angles (positions), shape ``(N,)``.
        y: Actions (momenta), shape ``(N,)``.
        K: Nonlinearity parameter.

    Returns:
        The updated ``(x, y)``, both wrapped to the torus.
    """
    y_new = wrap_to_torus(y + K * np.sin(x))
    x_new = wrap_to_torus(x + y_new)
    return x_new, y_new


class MapEngine:
    """Holds the state of every trajectory and advances it in bulk.

    Args:
        K: Nonlinearity parameter.
        seeding: Seeding strategy and density.
    """

    def __init__(self, K: float, seeding: SeedingConfig) -> None:
        self._K = K
        self._seeding = seeding
        n_seeds = seeding.nx * seeding.ny
        self._x: FloatArray = np.zeros(n_seeds)
        self._y: FloatArray = np.zeros(n_seeds)

    def reseed(self, x_range: Range, y_range: Range) -> None:
        """Replace all trajectories with fresh seeds inside the given ranges.

        Args:
            x_range: ``(x_min, x_max)`` of the viewport in data units.
            y_range: ``(y_min, y_max)`` of the viewport in data units.
        """
        self._x, self._y = generate_seeds(self._seeding.mode, x_range, y_range, self._seeding)

    def set_seed_mode(self, mode: SeedMode | str) -> None:
        """Select the strategy used by the next :meth:`reseed`.

        Args:
            mode: Seeding strategy (member or its string value).

        Raises:
            InvalidSeedModeError: If ``mode`` is not a known strategy.
        """
        seed_mode = coerce_enum(SeedMode, mode, InvalidSeedModeError)
        self._seeding = replace(self._seeding, mode=seed_mode)

    def set_density(self, nx: int, ny: int) -> None:
        """Set the per-axis seed counts used by the next :meth:`reseed`.

        Args:
            nx: Seeds along x.
            ny: Seeds along y.

        Raises:
            ConfigError: If either count is below 1.
        """
        self._seeding = replace(self._seeding, nx=nx, ny=ny)

    def step(self, n_iter: int) -> tuple[FloatArray, FloatArray]:
        """Advance all trajectories ``n_iter`` steps.

        Args:
            n_iter: Number of iterations.

        Returns:
            ``(xs, ys)``, each of shape ``(n_iter, N)``: positions BEFORE each
            update, matching the original's draw-then-advance order.
        """
        n_traj = self._x.size
        xs_out = np.empty((n_iter, n_traj))
        ys_out = np.empty((n_iter, n_traj))
        for i in range(n_iter):
            xs_out[i] = self._x
            ys_out[i] = self._y
            self._x, self._y = standard_map_step(self._x, self._y, self._K)
        return xs_out, ys_out

    @property
    def x(self) -> FloatArray:
        """Current angles of every trajectory."""
        return self._x

    @property
    def y(self) -> FloatArray:
        """Current actions of every trajectory."""
        return self._y

    @property
    def n_trajectories(self) -> int:
        """Number of trajectories currently being iterated."""
        return int(self._x.size)

    @property
    def seed_mode(self) -> SeedMode:
        """Strategy used by the next reseed."""
        return self._seeding.mode

    @property
    def density(self) -> tuple[int, int]:
        """Per-axis seed counts ``(nx, ny)`` used by the next reseed."""
        return self._seeding.nx, self._seeding.ny

    @property
    def K(self) -> float:
        """Nonlinearity parameter."""
        return self._K

    @K.setter
    def K(self, value: float) -> None:
        self._K = value
