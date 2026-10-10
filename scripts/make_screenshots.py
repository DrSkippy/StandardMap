"""Regenerate the README screenshots headlessly with the real application.

Usage:
    uv run python scripts/make_screenshots.py [output_dir]

Every image is rendered by ``build_app`` + ``App.render_frame``, so the
screenshots show exactly what the interactive window draws.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # imported after the SDL env vars are set

from standard_map.app import App, build_app
from standard_map.cli import parse_config

WINDOW_PX = 800
PANEL_PX = 400
PANEL_GAP_PX = 8
QUASI_RANDOM = ["--seed-mode", "quasi_random", "--nx", "50", "--ny", "50", "--rng-seed", "1"]
QUASI_RANDOM_40 = ["--seed-mode", "quasi_random", "--nx", "40", "--ny", "40", "--rng-seed", "1"]
ISLAND_ZOOM = ((20, 130), (200, 290))
"""Pixel rectangle around an island of the 1/4 resonance (y ~= pi/2), upper left."""


def make_app(argv: list[str]) -> App:
    """Build an app from CLI-style arguments at screenshot resolution."""
    cfg = parse_config(argv)
    return build_app(replace(cfg, display=replace(cfg.display, window_px=WINDOW_PX)))


def render(app: App, frames: int) -> pygame.Surface:
    """Run ``frames`` animation frames and return the display surface."""
    for _ in range(frames):
        app.render_frame(30.0)
    return pygame.display.get_surface()


def save(surface: pygame.Surface, path: Path) -> None:
    """Write a PNG and report its size."""
    pygame.image.save(surface, str(path))
    print(f"{path}  {path.stat().st_size // 1024} KB")


def shoot(path: Path, argv: list[str], frames: int, zoom=None) -> None:
    """Render one full-window screenshot, optionally after zooming."""
    app = make_app(argv)
    if zoom is not None:
        app.zoom_to(*zoom)
    save(render(app, frames), path)
    pygame.quit()


def shoot_drag(path: Path) -> None:
    """Capture the zoom rectangle mid-drag."""
    app = make_app(QUASI_RANDOM_40)
    render(app, 80)
    (x1, y1), (x2, y2) = ISLAND_ZOOM
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x1, y1), button=1))
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(x2, y2), buttons=(1, 0, 0)))
    save(pygame.display.get_surface(), path)
    pygame.quit()


def shoot_k_sweep(path: Path, k_values: tuple[str, ...] = ("0.5", "0.97", "1.5")) -> None:
    """Side-by-side panels at increasing K."""
    panels = []
    for k in k_values:
        app = make_app(["--K", k, *QUASI_RANDOM_40])
        surface = render(app, 120)
        panels.append(pygame.transform.smoothscale(surface.copy(), (PANEL_PX, PANEL_PX)))
        pygame.quit()
    pygame.init()
    width = len(panels) * PANEL_PX + (len(panels) - 1) * PANEL_GAP_PX
    sheet = pygame.Surface((width, PANEL_PX))
    sheet.fill((255, 255, 255))
    for i, panel in enumerate(panels):
        sheet.blit(panel, (i * (PANEL_PX + PANEL_GAP_PX), 0))
    save(sheet, path)
    pygame.quit()


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots")
    out.mkdir(parents=True, exist_ok=True)
    shoot(out / "quasi_random.png", QUASI_RANDOM, 120)
    shoot(out / "legacy.png", ["--seed-mode", "legacy", "--color-mode", "legacy_rgb"], 400)
    shoot(out / "grid.png", [], 200)
    shoot(out / "zoom.png", QUASI_RANDOM, 200, zoom=ISLAND_ZOOM)
    shoot_drag(out / "drag.png")
    shoot_k_sweep(out / "k_sweep.png")


if __name__ == "__main__":
    main()
