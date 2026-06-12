import numpy as np
import pygame


class Renderer:
    def __init__(self, surface: pygame.Surface, dim: int = 800) -> None:
        self._surface = surface
        self._dim = dim
        self._font = pygame.font.SysFont("monospace", 24)

    def clear(self, color: tuple = (0, 0, 0)) -> None:
        self._surface.fill(color)

    def draw_points(
        self,
        xs: np.ndarray,
        ys: np.ndarray,
        colors: np.ndarray,
    ) -> None:
        """
        Batch pixel write via surfarray. xs=pixel columns, ys=pixel rows,
        colors shape (M, 3) uint8. Falls back to set_at() if surfarray unavailable.
        """
        if xs.size == 0:
            return
        try:
            arr = pygame.surfarray.pixels3d(self._surface)
            arr[xs, ys] = colors
            del arr  # release surface lock
        except Exception:
            for x, y, c in zip(xs.tolist(), ys.tolist(), colors.tolist()):
                self._surface.set_at((x, y), (c[0], c[1], c[2]))

    def draw_hud(
        self,
        data_x1: float,
        data_y1: float,
        K: float,
        seed_mode: str,
        n_trajectories: int,
        fps: float,
    ) -> None:
        lines = [
            f"({data_x1:.4f}, {data_y1:.4f})",
            f"K = {K:.4f}",
            f"mode={seed_mode}  n={n_trajectories}",
            f"fps={fps:.0f}",
        ]
        # opaque background behind HUD so text stays readable over accumulated points
        pygame.draw.rect(self._surface, (0, 0, 0), (10, 10, 420, len(lines) * 30 + 10))
        color = (0, 200, 200)
        for i, line in enumerate(lines):
            surf = self._font.render(line, True, color)
            self._surface.blit(surf, (16, 16 + i * 30))

    def draw_zoom_rect(
        self,
        px1: int,
        py1: int,
        px2: int,
        py2: int,
        color: tuple = (255, 0, 0),
    ) -> None:
        x = min(px1, px2)
        y = min(py1, py2)
        w = abs(px2 - px1)
        h = abs(py2 - py1)
        pygame.draw.rect(self._surface, color, (x, y, w, h), 1)
