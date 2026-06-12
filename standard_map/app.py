import numpy as np
import pygame

from .map_engine import MapEngine
from .viewport import CoordTransform
from .renderer import Renderer
from .color import make_color_table

TWO_PI = 2.0 * np.pi


class App:
    DIM = 1600
    FPS_TARGET = 30
    ITERS_PER_FRAME = 40
    DOUBLE_CLICK_MS = 400
    DOUBLE_CLICK_DIST_SQ = 25  # pixels²

    def __init__(
        self,
        K: float = 0.97,
        seed_mode: str = "grid",
        nx_seeds: int = 20,
        ny_seeds: int = 20,
        color_mode: str = "hsv_cycle",
    ) -> None:
        self._K = K
        self._seed_mode = seed_mode
        self._nx = nx_seeds
        self._ny = ny_seeds
        self._color_mode = color_mode

        self._dragging = False
        self._drag_start = (0, 0)
        self._drag_clean: pygame.Surface | None = None
        self._last_click_time = 0
        self._last_click_pos = (-999, -999)

        self._surface: pygame.Surface | None = None
        self._engine: MapEngine | None = None
        self._viewport: CoordTransform | None = None
        self._renderer: Renderer | None = None
        self._colors: np.ndarray | None = None

    def run(self) -> None:
        pygame.init()
        self._surface = pygame.display.set_mode((self.DIM, self.DIM))
        pygame.display.set_caption("Chirikov Standard Map  [drag=zoom  dbl-click=reset  r=reset  s=cycle-seed  ↑↓=K  q=quit]")
        self._renderer = Renderer(self._surface, self.DIM)
        self._viewport = CoordTransform()
        self._engine = MapEngine(
            K=self._K,
            seed_mode=self._seed_mode,
            nx_seeds=self._nx,
            ny_seeds=self._ny,
        )
        self._reset()
        clock = pygame.time.Clock()
        fps = 0.0
        while True:
            if not self._handle_events():
                break
            if not self._dragging:
                self._render_frame(fps)
            fps = clock.get_fps()
            clock.tick(self.FPS_TARGET)
        pygame.quit()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._viewport.reset()
        self._reseed_and_clear()

    def _do_zoom(self, px1: int, py1: int, px2: int, py2: int) -> None:
        if px2 < px1:
            px1, px2 = px2, px1
        if py2 < py1:
            py1, py2 = py2, py1
        if abs(px2 - px1) < 2 or abs(py2 - py1) < 2:
            return
        self._viewport.zoom_to_pixel_rect(px1, py1, px2, py2)
        self._reseed_and_clear()

    def _reseed_and_clear(self) -> None:
        x1, x2, y1, y2 = self._viewport.data_bounds
        self._engine.reseed((x1, x2), (y1, y2))
        self._colors = make_color_table(self._engine.n_trajectories, self._color_mode)
        self._renderer.clear()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render_frame(self, fps: float) -> None:
        xs_raw, ys_raw = self._engine.step(self.ITERS_PER_FRAME)
        # xs_raw, ys_raw: shape (ITERS_PER_FRAME, N)
        n_iter, N = xs_raw.shape

        xs_flat = xs_raw.ravel()   # (n_iter*N,)
        ys_flat = ys_raw.ravel()

        px_col, px_row = self._viewport.data_to_pixel(xs_flat, ys_flat)

        mask = (
            (px_col >= 0) & (px_col < self.DIM) &
            (px_row >= 0) & (px_row < self.DIM)
        )
        px_col = px_col[mask]
        px_row = px_row[mask]

        # tile colors so each trajectory keeps its color across all iterations
        # np.tile((N,3), (n_iter,1)) → (n_iter*N, 3), then apply same mask
        colors_tiled = np.tile(self._colors, (n_iter, 1))
        colors_masked = colors_tiled[mask]

        self._renderer.draw_points(px_col, px_row, colors_masked)

        x1, _x2, y1, _y2 = self._viewport.data_bounds
        self._renderer.draw_hud(x1, y1, self._engine.K, self._seed_mode,
                                 self._engine.n_trajectories, fps)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                self._on_key_down(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._on_mouse_down(event)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._on_mouse_up(event)
        return True

    def _on_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button != 1:
            return
        now = pygame.time.get_ticks()
        dx = event.pos[0] - self._last_click_pos[0]
        dy = event.pos[1] - self._last_click_pos[1]
        if (now - self._last_click_time < self.DOUBLE_CLICK_MS and
                dx * dx + dy * dy < self.DOUBLE_CLICK_DIST_SQ):
            self._reset()
            self._last_click_time = 0  # consume so triple-click doesn't re-trigger
        else:
            self._last_click_time = now
            self._last_click_pos = event.pos
            self._drag_start = event.pos
            self._dragging = False
            self._drag_clean = self._surface.copy()

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        if not event.buttons[0]:
            return
        self._dragging = True
        # restore pre-drag frame, then draw fresh rect — avoids XOR-erase artifacts
        self._surface.blit(self._drag_clean, (0, 0))
        self._renderer.draw_zoom_rect(
            self._drag_start[0], self._drag_start[1],
            event.pos[0], event.pos[1],
        )
        pygame.display.flip()

    def _on_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button != 1:
            return
        if self._dragging:
            self._do_zoom(
                self._drag_start[0], self._drag_start[1],
                event.pos[0], event.pos[1],
            )
            self._dragging = False

    def _on_key_down(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_r, pygame.K_ESCAPE):
            self._reset()

        elif event.key == pygame.K_q:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        elif event.key == pygame.K_s:
            modes = ["grid", "quasi_random", "legacy"]
            idx = (modes.index(self._seed_mode) + 1) % len(modes)
            self._seed_mode = modes[idx]
            self._engine._seed_mode = self._seed_mode
            self._reseed_and_clear()

        elif event.key == pygame.K_UP:
            self._engine.K = round(self._engine.K + 0.01, 4)
            self._reseed_and_clear()

        elif event.key == pygame.K_DOWN:
            self._engine.K = round(self._engine.K - 0.01, 4)
            self._reseed_and_clear()

        elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._nx = min(self._nx + 5, 100)
            self._ny = min(self._ny + 5, 100)
            self._engine._nx = self._nx
            self._engine._ny = self._ny
            self._reseed_and_clear()

        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._nx = max(self._nx - 5, 5)
            self._ny = max(self._ny - 5, 5)
            self._engine._nx = self._nx
            self._engine._ny = self._ny
            self._reseed_and_clear()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Chirikov Standard Map visualization")
    p.add_argument("--K", type=float, default=0.97, metavar="K",
                   help="Nonlinearity parameter (default 0.97 = edge of chaos)")
    p.add_argument("--seed-mode", choices=["grid", "quasi_random", "legacy"],
                   default="grid", help="Initial condition strategy")
    p.add_argument("--nx", type=int, default=20,
                   help="Grid seeds along x (default 20; grid mode only)")
    p.add_argument("--ny", type=int, default=20,
                   help="Grid seeds along y (default 20; grid mode only)")
    p.add_argument("--color-mode", choices=["hsv_cycle", "legacy_rgb"],
                   default="hsv_cycle", help="Trajectory color scheme")
    args = p.parse_args()
    App(
        K=args.K,
        seed_mode=args.seed_mode,
        nx_seeds=args.nx,
        ny_seeds=args.ny,
        color_mode=args.color_mode,
    ).run()
