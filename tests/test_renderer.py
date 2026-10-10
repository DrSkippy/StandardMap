"""Headless tests for the pygame renderer."""

import numpy as np
import pygame
import pytest

from standard_map.config import RenderConfig
from standard_map.exceptions import RendererUnavailableError
from standard_map.renderer import HudStatus, Renderer, format_hud_lines

STATUS = HudStatus(x_min=0.5, y_min=1.25, K=0.97, seed_mode="grid", n_trajectories=400, fps=29.6)


@pytest.fixture
def surface():
    pygame.init()
    yield pygame.Surface((64, 64), depth=32)
    pygame.quit()


def test_format_hud_lines():
    assert format_hud_lines(STATUS) == [
        "(0.5000, 1.2500)",
        "K = 0.9700",
        "mode=grid  n=400",
        "fps=30",
    ]


def test_rejects_unsupported_bit_depth(surface):
    with pytest.raises(RendererUnavailableError, match="8-bit"):
        Renderer(pygame.Surface((4, 4), depth=8), RenderConfig())


def test_clear_uses_background(surface):
    Renderer(surface, RenderConfig(background=(1, 2, 3))).clear()
    assert surface.get_at((10, 10))[:3] == (1, 2, 3)


def test_draw_points_writes_pixels(surface):
    renderer = Renderer(surface, RenderConfig())
    renderer.clear()
    cols, rows = np.array([1, 5]), np.array([2, 7])
    colors = np.array([[255, 0, 0], [0, 255, 0]], dtype=np.uint8)
    renderer.draw_points(cols, rows, colors)
    assert surface.get_at((1, 2))[:3] == (255, 0, 0)
    assert surface.get_at((5, 7))[:3] == (0, 255, 0)
    assert surface.get_locked() is False


def test_draw_points_empty_is_noop(surface):
    renderer = Renderer(surface, RenderConfig())
    renderer.clear()
    empty = np.array([], dtype=np.int64)
    renderer.draw_points(empty, empty, np.empty((0, 3), dtype=np.uint8))
    assert surface.get_at((0, 0))[:3] == (0, 0, 0)


def test_draw_hud_paints_box(surface):
    cfg = RenderConfig(hud_origin=(0, 0), hud_width=60, hud_background=(9, 9, 9))
    Renderer(surface, cfg).draw_hud(STATUS)
    assert surface.get_at((59, 0))[:3] == (9, 9, 9)


def test_draw_zoom_rect_any_corner_order(surface):
    renderer = Renderer(surface, RenderConfig(zoom_rect_color=(0, 0, 255)))
    renderer.clear()
    renderer.draw_zoom_rect((40, 30), (10, 5))
    assert surface.get_at((10, 5))[:3] == (0, 0, 255)
    assert surface.get_at((20, 20))[:3] == (0, 0, 0)
    renderer.draw_zoom_rect((10, 5), (40, 30), color=(7, 7, 7))
    assert surface.get_at((10, 5))[:3] == (7, 7, 7)
