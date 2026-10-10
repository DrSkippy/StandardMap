"""Tests for key bindings and caption generation."""

import pygame
import pytest

from standard_map.controls import KEY_BINDINGS, build_caption, build_key_map


class Recorder:
    def __init__(self):
        self.calls = []

    def reset(self):
        self.calls.append("reset")

    def cycle_seed_mode(self):
        self.calls.append("cycle")

    def step_K(self, direction):
        self.calls.append(("K", direction))

    def step_density(self, direction):
        self.calls.append(("density", direction))

    def request_quit(self):
        self.calls.append("quit")


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (pygame.K_r, "reset"),
        (pygame.K_ESCAPE, "reset"),
        (pygame.K_s, "cycle"),
        (pygame.K_UP, ("K", 1)),
        (pygame.K_DOWN, ("K", -1)),
        (pygame.K_PLUS, ("density", 1)),
        (pygame.K_EQUALS, ("density", 1)),
        (pygame.K_KP_PLUS, ("density", 1)),
        (pygame.K_MINUS, ("density", -1)),
        (pygame.K_KP_MINUS, ("density", -1)),
        (pygame.K_q, "quit"),
    ],
)
def test_key_map_dispatch(key, expected):
    target = Recorder()
    build_key_map()[key](target)
    assert target.calls == [expected]


def test_keys_are_unique():
    keys = [key for binding in KEY_BINDINGS for key in binding.keys]
    assert len(keys) == len(set(keys))


def test_caption_lists_all_hints():
    assert build_caption("Chirikov Standard Map") == (
        "Chirikov Standard Map  [drag=zoom  dbl-click=reset  r=reset  "
        "s=cycle-seed  ↑↓=K  +-=density  q=quit]"
    )
