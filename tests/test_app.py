"""Headless end-to-end tests for the pygame application."""

import numpy as np
import pygame
import pytest

from standard_map import app as app_module
from standard_map.app import build_app, main, step_seed_count
from standard_map.config import AppConfig, DisplayConfig, PhysicsConfig, SeedingConfig, SeedMode
from standard_map.viewport import FULL_TORUS

DIM = 200


class FakeClock:
    def __init__(self):
        self.now = 10_000

    def __call__(self):
        return self.now


@pytest.fixture
def config():
    return AppConfig(display=DisplayConfig(window_px=DIM), seeding=SeedingConfig(nx=4, ny=4))


@pytest.fixture
def app(config):
    application = build_app(config)
    clock = FakeClock()
    application._ticks_ms = clock
    application.clock = clock
    yield application
    pygame.quit()


def press(app, pos, button=1):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button))


def move(app, pos, held=True):
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, buttons=(held, 0, 0)))


def release(app, pos, button=1):
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=button))


def key(app, code):
    return app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=code))


def drag(app, start, end):
    press(app, start)
    move(app, end)
    release(app, end)


def test_step_seed_count_is_one_sided():
    assert step_seed_count(20, 5, 5, 100) == 25
    assert step_seed_count(98, 5, 5, 100) == 100
    assert step_seed_count(7, -5, 5, 100) == 5
    assert step_seed_count(200, -5, 5, 100) == 195  # out-of-range CLI value kept


def test_build_app_initial_state(app):
    assert app.viewport.bounds == FULL_TORUS
    assert app.engine.n_trajectories == 16
    assert pygame.display.get_caption()[0].startswith("Chirikov Standard Map")


def test_render_frame_draws_points(app):
    app.render_frame(30.0)
    pixels = pygame.surfarray.array3d(pygame.display.get_surface())
    assert pixels.any()


def test_drag_zooms_and_reseeds_inside_viewport(app):
    drag(app, (150, 150), (50, 50))
    b = app.viewport.bounds
    assert b.x_max - b.x_min == pytest.approx(np.pi)
    assert ((app.engine.x >= b.x_min) & (app.engine.x < b.x_max)).all()


def test_tiny_drag_does_not_zoom(app):
    drag(app, (50, 50), (51, 120))
    assert app.viewport.bounds == FULL_TORUS


def test_click_without_motion_does_not_zoom(app):
    press(app, (50, 50))
    release(app, (90, 90))
    assert app.viewport.bounds == FULL_TORUS


def test_non_left_buttons_ignored(app):
    press(app, (10, 10), button=3)
    move(app, (90, 90))
    release(app, (90, 90), button=3)
    assert app.viewport.bounds == FULL_TORUS


def test_motion_without_button_ignored(app):
    press(app, (10, 10))
    move(app, (90, 90), held=False)
    assert not app._drag.active


def test_drag_from_outside_window_does_not_crash(app):
    """Regression: motion with no prior press used to blit None."""
    move(app, (90, 90))
    release(app, (90, 90))
    assert app.viewport.bounds == FULL_TORUS


def test_double_click_resets(app):
    drag(app, (0, 0), (100, 100))
    assert app.viewport.bounds != FULL_TORUS
    app.clock.now += 1000
    press(app, (20, 20))
    release(app, (20, 20))
    app.clock.now += 100
    press(app, (21, 21))
    assert app.viewport.bounds == FULL_TORUS


def test_drag_after_double_click_does_not_reuse_stale_start(app):
    """Regression: holding the second click and dragging zoomed from an old start."""
    press(app, (20, 20))
    release(app, (20, 20))
    app.clock.now += 100
    press(app, (20, 20))  # double-click -> reset, gesture discarded
    move(app, (150, 150))
    release(app, (150, 150))
    assert app.viewport.bounds == FULL_TORUS


def test_reset_key(app):
    drag(app, (0, 0), (100, 100))
    key(app, pygame.K_r)
    assert app.viewport.bounds == FULL_TORUS


def test_seed_mode_key_cycles(app):
    key(app, pygame.K_s)
    assert app.engine.seed_mode is SeedMode.QUASI_RANDOM
    key(app, pygame.K_s)
    assert app.engine.seed_mode is SeedMode.LEGACY
    assert app.engine.n_trajectories == 85


def test_K_keys(app):
    key(app, pygame.K_UP)
    assert app.engine.K == 0.98
    key(app, pygame.K_DOWN)
    key(app, pygame.K_DOWN)
    assert app.engine.K == 0.96


def test_density_keys_clamp(app):
    key(app, pygame.K_EQUALS)
    assert app.engine.density == (9, 9)
    assert app.engine.n_trajectories == 81
    for _ in range(3):
        key(app, pygame.K_MINUS)
    assert app.engine.density == (5, 5)


def test_unbound_key_is_ignored(app):
    assert key(app, pygame.K_z) is True


def test_quit_key_posts_quit_event(app):
    pygame.event.clear()
    key(app, pygame.K_q)
    assert app.process_events() is False


def test_run_exits_on_quit(app):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.run()
    assert app.engine.K == 0.98


def test_run_skips_rendering_while_dragging(app, monkeypatch):
    frames = []
    monkeypatch.setattr(app, "render_frame", frames.append)
    press(app, (10, 10))
    move(app, (80, 80))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    app.run()
    assert frames == []


def test_main_wires_cli_to_app(monkeypatch):
    seen = {}

    class StubApp:
        def run(self):
            seen["ran"] = True

    def fake_build(config):
        seen["config"] = config
        return StubApp()

    monkeypatch.setattr(app_module, "build_app", fake_build)
    main(["--K", "1.5"])
    assert seen["ran"]
    assert seen["config"].physics == PhysicsConfig(K=1.5)


def test_run_renders_frames_until_quit(app, monkeypatch):
    frames = []

    def render_then_quit(fps):
        frames.append(fps)
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(app, "render_frame", render_then_quit)
    app.run()
    assert frames == [0.0]


def test_package_main_invokes_entry_point(monkeypatch):
    import runpy

    calls = []
    monkeypatch.setattr(app_module, "main", lambda: calls.append(True))
    runpy.run_module("standard_map", run_name="__main__")
    assert calls == [True]
