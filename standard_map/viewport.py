"""Mapping between data coordinates on the torus and window pixels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .config import TWO_PI
from .exceptions import InvalidViewportError

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]


@dataclass(frozen=True)
class Bounds:
    """Axis-aligned data-space rectangle shown in the window.

    Attributes:
        x_min: Left edge (data units).
        x_max: Right edge (data units).
        y_min: Top edge (data units).
        y_max: Bottom edge (data units).
    """

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def x_range(self) -> tuple[float, float]:
        """``(x_min, x_max)``."""
        return self.x_min, self.x_max

    @property
    def y_range(self) -> tuple[float, float]:
        """``(y_min, y_max)``."""
        return self.y_min, self.y_max


FULL_TORUS = Bounds(0.0, TWO_PI, 0.0, TWO_PI)
"""The unzoomed view: the whole torus [0, 2*pi) x [0, 2*pi)."""


class CoordTransform:
    """Affine data <-> pixel transform for a square window.

    Args:
        dim: Window side length in pixels.
    """

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self.reset()

    def reset(self) -> None:
        """Return to the full-torus view."""
        self._bounds = FULL_TORUS
        self._scalex = self._dim / TWO_PI
        self._scaley = self._dim / TWO_PI
        self._xoff = 0
        self._yoff = 0

    @property
    def bounds(self) -> Bounds:
        """Data-space rectangle currently mapped onto the window."""
        return self._bounds

    @property
    def dim(self) -> int:
        """Window side length in pixels."""
        return self._dim

    def data_to_pixel(self, xd: FloatArray, yd: FloatArray) -> tuple[IntArray, IntArray]:
        """Vectorized data -> pixel conversion.

        Coordinates are floored (not truncated toward zero), so points just
        left of or above the window map to pixel -1 and are clipped rather
        than piling up in column/row 0. int64 avoids overflow at deep zoom.

        Args:
            xd: Data x-coordinates (any shape).
            yd: Data y-coordinates (same shape as ``xd``).

        Returns:
            ``(px_col, px_row)`` integer arrays with the input shape.
        """
        px_col = np.floor(xd * self._scalex + self._xoff).astype(np.int64)
        px_row = np.floor(yd * self._scaley + self._yoff).astype(np.int64)
        return px_col, px_row

    def pixel_to_data(self, px: float, py: float) -> tuple[float, float]:
        """Convert a pixel position to data coordinates.

        Args:
            px: Pixel column.
            py: Pixel row.

        Returns:
            ``(x, y)`` in data units.
        """
        xd = (px - self._xoff) / self._scalex
        yd = (py - self._yoff) / self._scaley
        return xd, yd

    def zoom_to_pixel_rect(self, px1: int, py1: int, px2: int, py2: int) -> None:
        """Zoom so the given pixel rectangle fills the window.

        Direct translation of Processing's ``setScale()``. Corners may be
        given in any order. x and y are scaled independently, as in the
        original, so a non-square rectangle stretches the view.

        Args:
            px1: Column of one corner.
            py1: Row of one corner.
            px2: Column of the opposite corner.
            py2: Row of the opposite corner.

        Raises:
            InvalidViewportError: If the rectangle has zero width or height.
        """
        left, right = sorted((px1, px2))
        top, bottom = sorted((py1, py2))
        if left == right or top == bottom:
            raise InvalidViewportError(f"degenerate zoom rectangle {(px1, py1, px2, py2)}")

        new_dx1, new_dy1 = self.pixel_to_data(left, top)
        new_dx2, new_dy2 = self.pixel_to_data(right, bottom)

        self._scalex = self._dim / abs(new_dx2 - new_dx1)
        self._scaley = self._dim / abs(new_dy2 - new_dy1)

        self._xoff = int((-(new_dx1 + new_dx2) * self._scalex + self._dim) / 2)
        self._yoff = int((-(new_dy1 + new_dy2) * self._scaley + self._dim) / 2)

        self._bounds = Bounds(new_dx1, new_dx2, new_dy1, new_dy2)
