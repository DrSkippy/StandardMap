"""Drawing primitives: points, HUD overlay and the zoom rectangle."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .color import ColorTable
from .config import RGB, RenderConfig
from .exceptions import RendererUnavailableError
from .viewport import IntArray

PIXEL_ARRAY_BIT_DEPTHS = frozenset({24, 32})
"""Surface depths that ``pygame.surfarray.pixels3d`` can reference directly."""

Pixel = tuple[int, int]


@dataclass(frozen=True)
class HudStatus:
    """Values shown in the on-screen heads-up display.

    Attributes:
        x_min: Left edge of the viewport (data units).
        y_min: Top edge of the viewport (data units).
        K: Nonlinearity parameter.
        seed_mode: Name of the active seeding strategy.
        n_trajectories: Number of trajectories being iterated.
        fps: Measured frame rate.
    """

    x_min: float
    y_min: float
    K: float
    seed_mode: str
    n_trajectories: int
    fps: float


def format_hud_lines(status: HudStatus) -> list[str]:
    """Render HUD values as text lines.

    Args:
        status: Values to display.

    Returns:
        One string per HUD line, top to bottom.
    """
    return [
        f"({status.x_min:.4f}, {status.y_min:.4f})",
        f"K = {status.K:.4f}",
        f"mode={status.seed_mode}  n={status.n_trajectories}",
        f"fps={status.fps:.0f}",
    ]


class Renderer:
    """Draws onto a pygame surface.

    Args:
        surface: Target surface; must be 24- or 32-bit for batch pixel writes.
        cfg: Colors, font and HUD geometry.

    Raises:
        RendererUnavailableError: If the surface depth does not support
            direct pixel-array access.
    """

    def __init__(self, surface: pygame.Surface, cfg: RenderConfig) -> None:
        bit_depth = surface.get_bitsize()
        if bit_depth not in PIXEL_ARRAY_BIT_DEPTHS:
            raise RendererUnavailableError(
                f"{bit_depth}-bit surface; batch drawing needs one of "
                f"{sorted(PIXEL_ARRAY_BIT_DEPTHS)}"
            )
        self._surface = surface
        self._cfg = cfg
        self._font = pygame.font.SysFont(cfg.font_name, cfg.font_size)

    def clear(self) -> None:
        """Fill the whole surface with the background color."""
        self._surface.fill(self._cfg.background)

    def draw_points(self, cols: IntArray, rows: IntArray, colors: ColorTable) -> None:
        """Batch pixel write via surfarray.

        Args:
            cols: Pixel columns, all within the surface.
            rows: Pixel rows, all within the surface.
            colors: ``(M, 3)`` uint8 RGB value per point.
        """
        if cols.size == 0:
            return
        pixels = pygame.surfarray.pixels3d(self._surface)
        pixels[cols, rows] = colors
        del pixels  # release surface lock

    def draw_hud(self, status: HudStatus) -> None:
        """Draw the HUD text box in the top-left corner.

        Args:
            status: Values to display.
        """
        cfg = self._cfg
        lines = format_hud_lines(status)
        left, top = cfg.hud_origin
        height = len(lines) * cfg.hud_line_height + 2 * cfg.hud_padding
        # opaque background behind HUD so text stays readable over accumulated points
        pygame.draw.rect(self._surface, cfg.hud_background, (left, top, cfg.hud_width, height))
        for i, line in enumerate(lines):
            text = self._font.render(line, True, cfg.hud_foreground)
            position = (left + cfg.hud_padding, top + cfg.hud_padding + i * cfg.hud_line_height)
            self._surface.blit(text, position)

    def draw_zoom_rect(self, corner: Pixel, opposite: Pixel, color: RGB | None = None) -> None:
        """Outline the drag rectangle between two corners given in any order.

        Args:
            corner: One corner ``(col, row)``.
            opposite: The opposite corner ``(col, row)``.
            color: Outline color; defaults to ``RenderConfig.zoom_rect_color``.
        """
        left, right = sorted((corner[0], opposite[0]))
        top, bottom = sorted((corner[1], opposite[1]))
        outline = color or self._cfg.zoom_rect_color
        pygame.draw.rect(self._surface, outline, (left, top, right - left, bottom - top), 1)
