"""Per-trajectory color tables."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

from .config import ColorConfig, ColorMode, coerce_enum
from .exceptions import InvalidColorModeError

ColorTable = npt.NDArray[np.uint8]


def hsv_to_rgb(
    hues: npt.NDArray[np.float64], saturation: float, value: float
) -> npt.NDArray[np.float64]:
    """Vectorized equivalent of :func:`colorsys.hsv_to_rgb`.

    Uses the same arithmetic as ``colorsys`` so results are bit-identical.

    Args:
        hues: Hue values in ``[0, 1)``.
        saturation: Saturation in ``[0, 1]``.
        value: Value (brightness) in ``[0, 1]``.

    Returns:
        Array of shape ``(len(hues), 3)`` with RGB channels in ``[0, 1]``.
    """
    if saturation == 0.0:
        return np.full((hues.size, 3), value)
    sector = np.floor(hues * 6.0).astype(np.intp)
    frac = (hues * 6.0) - sector
    v = np.full(hues.shape, value)
    p = np.full(hues.shape, value * (1.0 - saturation))
    q = value * (1.0 - saturation * frac)
    t = value * (1.0 - saturation * (1.0 - frac))
    sector %= 6
    red = np.choose(sector, [v, q, p, p, t, v])
    green = np.choose(sector, [t, v, v, q, p, p])
    blue = np.choose(sector, [p, p, t, v, v, q])
    return np.stack([red, green, blue], axis=1)


def hsv_cycle_table(n: int, cfg: ColorConfig) -> ColorTable:
    """Hue cycles 0 -> 1 over all trajectories; works well for any N.

    Args:
        n: Number of trajectories.
        cfg: Color configuration (saturation and value).

    Returns:
        ``(n, 3)`` uint8 RGB table.
    """
    hues = np.linspace(0.0, 1.0, n, endpoint=False)
    rgb = hsv_to_rgb(hues, cfg.hsv_saturation, cfg.hsv_value)
    return (rgb * 255).astype(np.uint8)  # truncation matches int(c * 255)


def legacy_rgb_table(n: int, cfg: ColorConfig) -> ColorTable:
    """Exact Processing behaviour: R = j*256/n, fixed G and B.

    Args:
        n: Number of trajectories.
        cfg: Color configuration (fixed green and blue channels).

    Returns:
        ``(n, 3)`` uint8 RGB table.
    """
    red = (np.arange(n) * 256 // max(n, 1)).astype(np.uint8)
    green = np.full(n, cfg.legacy_green, dtype=np.uint8)
    blue = np.full(n, cfg.legacy_blue, dtype=np.uint8)
    return np.stack([red, green, blue], axis=1)


COLOR_BUILDERS: dict[ColorMode, Callable[[int, ColorConfig], ColorTable]] = {
    ColorMode.HSV_CYCLE: hsv_cycle_table,
    ColorMode.LEGACY_RGB: legacy_rgb_table,
}


def make_color_table(
    n: int, mode: ColorMode | str = ColorMode.HSV_CYCLE, cfg: ColorConfig | None = None
) -> ColorTable:
    """Build an RGB color for each of ``n`` trajectories.

    Args:
        n: Number of trajectories.
        mode: Color scheme (member or its string value).
        cfg: Palette parameters; defaults to :class:`ColorConfig`.

    Returns:
        ``(n, 3)`` uint8 array of ``(R, G, B)`` values.

    Raises:
        InvalidColorModeError: If ``mode`` is not a known scheme.
    """
    color_mode = coerce_enum(ColorMode, mode, InvalidColorModeError)
    return COLOR_BUILDERS[color_mode](n, cfg or ColorConfig())
