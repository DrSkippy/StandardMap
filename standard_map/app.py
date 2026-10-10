"""Interactive pygame front end: wiring, main loop and event dispatch."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from .cli import parse_config
from .color import ColorTable, make_color_table
from .config import AppConfig
from .controls import build_caption, build_key_map
from .gestures import DoubleClickDetector, DragController, Pixel
from .map_engine import MapEngine
from .projection import project_and_clip
from .renderer import HudStatus, Renderer
from .viewport import CoordTransform

LEFT_MOUSE_BUTTON = 1


def step_seed_count(count: int, delta: int, lower: int, upper: int) -> int:
    """Apply a density key step to one axis's seed count.

    Increases are capped at ``upper`` and decreases floored at ``lower``,
    one-sidedly, as in the original key handlers.

    Args:
        count: Current seed count.
        delta: Signed change.
        lower: Floor applied when decreasing.
        upper: Cap applied when increasing.

    Returns:
        The new seed count.
    """
    return min(count + delta, upper) if delta > 0 else max(count + delta, lower)


class App:
    """Owns the application state and reacts to pygame events.

    Collaborators are injected so the class can be driven headlessly in
    tests; use :func:`build_app` to create a fully wired instance.

    Args:
        config: Application configuration.
        surface: Display surface.
        engine: Trajectory state.
        viewport: Data <-> pixel transform.
        renderer: Drawing primitives.
        ticks_ms: Millisecond clock used for double-click detection.
    """

    def __init__(
        self,
        config: AppConfig,
        surface: pygame.Surface,
        engine: MapEngine,
        viewport: CoordTransform,
        renderer: Renderer,
        ticks_ms: Callable[[], int] = pygame.time.get_ticks,
    ) -> None:
        self._config = config
        self._surface = surface
        self._engine = engine
        self._viewport = viewport
        self._renderer = renderer
        self._ticks_ms = ticks_ms
        self._drag: DragController[pygame.Surface] = DragController()
        self._double_click = DoubleClickDetector(
            config.input.double_click_ms, config.input.double_click_radius_px
        )
        self._key_map = build_key_map()
        self._colors: ColorTable
        self.reset()

    @property
    def engine(self) -> MapEngine:
        """Trajectory state (exposed for inspection)."""
        return self._engine

    @property
    def viewport(self) -> CoordTransform:
        """Current data <-> pixel transform (exposed for inspection)."""
        return self._viewport

    def run(self) -> None:
        """Run the main loop until the window is closed or ``q`` is pressed."""
        clock = pygame.time.Clock()
        fps = 0.0
        while self.process_events():
            if not self._drag.active:
                self.render_frame(fps)
            fps = clock.get_fps()
            clock.tick(self._config.display.fps_target)
        pygame.quit()

    # ------------------------------------------------------------------
    # State transitions (also the Controllable protocol used by key bindings)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Return to the full view and reseed."""
        self._viewport.reset()
        self._reseed_and_clear()

    def cycle_seed_mode(self) -> None:
        """Switch to the next seeding strategy and reseed."""
        self._engine.set_seed_mode(self._engine.seed_mode.next())
        self._reseed_and_clear()

    def step_K(self, direction: int) -> None:
        """Change K by one configured step and reseed.

        Args:
            direction: ``+1`` to increase, ``-1`` to decrease.
        """
        physics = self._config.physics
        new_K = self._engine.K + direction * physics.K_step
        self._engine.K = round(new_K, physics.K_round_decimals)
        self._reseed_and_clear()

    def step_density(self, direction: int) -> None:
        """Change per-axis seed density by one configured step and reseed.

        Args:
            direction: ``+1`` to increase, ``-1`` to decrease.
        """
        seeding = self._config.seeding
        delta = direction * seeding.density_step
        nx, ny = (
            step_seed_count(count, delta, seeding.density_min, seeding.density_max)
            for count in self._engine.density
        )
        self._engine.set_density(nx, ny)
        self._reseed_and_clear()

    def request_quit(self) -> None:
        """Post a QUIT event so the main loop exits after this frame."""
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def zoom_to(self, corner: Pixel, opposite: Pixel) -> None:
        """Zoom into the pixel rectangle between two corners and reseed.

        Rectangles smaller than ``min_zoom_px`` on either axis are ignored.

        Args:
            corner: One corner ``(col, row)``.
            opposite: The opposite corner ``(col, row)``.
        """
        min_px = self._config.display.min_zoom_px
        if abs(opposite[0] - corner[0]) < min_px or abs(opposite[1] - corner[1]) < min_px:
            return
        self._viewport.zoom_to_pixel_rect(*corner, *opposite)
        self._reseed_and_clear()

    def _reseed_and_clear(self) -> None:
        """Reseed inside the viewport, rebuild colors and clear the screen."""
        bounds = self._viewport.bounds
        self._engine.reseed(bounds.x_range, bounds.y_range)
        color = self._config.color
        self._colors = make_color_table(self._engine.n_trajectories, color.mode, color)
        self._renderer.clear()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render_frame(self, fps: float) -> None:
        """Advance the map, draw the new points and the HUD, and flip.

        Args:
            fps: Measured frame rate to show in the HUD.
        """
        # xs, ys: shape (iters_per_frame, N)
        xs, ys = self._engine.step(self._config.display.iters_per_frame)
        points = project_and_clip(xs, ys, self._viewport)
        self._renderer.draw_points(points.cols, points.rows, self._colors[points.trajectory_index])
        self._renderer.draw_hud(self._hud_status(fps))
        pygame.display.flip()

    def _hud_status(self, fps: float) -> HudStatus:
        """Collect the values shown in the HUD.

        Args:
            fps: Measured frame rate.

        Returns:
            The HUD snapshot.
        """
        bounds = self._viewport.bounds
        return HudStatus(
            x_min=bounds.x_min,
            y_min=bounds.y_min,
            K=self._engine.K,
            seed_mode=str(self._engine.seed_mode),
            n_trajectories=self._engine.n_trajectories,
            fps=fps,
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def process_events(self) -> bool:
        """Handle all pending pygame events.

        Returns:
            ``False`` once a QUIT event is seen, else ``True``.
        """
        # all() stops at the first QUIT, exactly like an early-return loop
        return all(self.handle_event(event) for event in pygame.event.get())

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Dispatch one event.

        Args:
            event: The pygame event.

        Returns:
            ``False`` for QUIT, else ``True``.
        """
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            self._on_key_down(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._on_mouse_down(event)
        elif event.type == pygame.MOUSEMOTION:
            self._on_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._on_mouse_up(event)
        return True

    def _on_key_down(self, event: pygame.event.Event) -> None:
        """Run the action bound to the pressed key, if any."""
        action = self._key_map.get(event.key)
        if action is not None:
            action(self)

    def _on_mouse_down(self, event: pygame.event.Event) -> None:
        """Start a drag, or reset on a double-click."""
        if event.button != LEFT_MOUSE_BUTTON:
            return
        if self._double_click.register_click(self._ticks_ms(), event.pos):
            self._drag.cancel()
            self.reset()
        else:
            self._drag.begin(event.pos, self._surface.copy())

    def _on_mouse_motion(self, event: pygame.event.Event) -> None:
        """Redraw the zoom rectangle while the left button is held."""
        if not event.buttons[0]:
            return
        gesture = self._drag.move()
        if gesture is None:
            return
        # restore pre-drag frame, then draw fresh rect — avoids XOR-erase artifacts
        self._surface.blit(gesture.snapshot, (0, 0))
        self._renderer.draw_zoom_rect(gesture.start, event.pos)
        pygame.display.flip()

    def _on_mouse_up(self, event: pygame.event.Event) -> None:
        """Zoom into the dragged rectangle, if there was one."""
        if event.button != LEFT_MOUSE_BUTTON:
            return
        rect = self._drag.finish(event.pos)
        if rect is not None:
            self.zoom_to(*rect)


def build_app(config: AppConfig) -> App:
    """Initialise pygame, open the window and wire up an :class:`App`.

    Args:
        config: Application configuration.

    Returns:
        A ready-to-run application.

    Raises:
        RendererUnavailableError: If the display surface cannot be drawn
            with batch pixel writes.
    """
    pygame.init()
    size = config.display.window_px
    surface = pygame.display.set_mode((size, size))
    pygame.display.set_caption(build_caption(config.display.title))
    return App(
        config,
        surface,
        MapEngine(config.physics.K, config.seeding),
        CoordTransform(size),
        Renderer(surface, config.render),
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Console entry point.

    Args:
        argv: Arguments excluding the program name; ``None`` reads ``sys.argv``.
    """
    build_app(parse_config(argv)).run()
