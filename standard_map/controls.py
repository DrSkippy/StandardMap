"""Keyboard bindings and the window caption generated from them."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

import pygame


class Controllable(Protocol):
    """Actions the keyboard can trigger."""

    def reset(self) -> None:
        """Return to the full view and reseed."""

    def cycle_seed_mode(self) -> None:
        """Switch to the next seeding strategy and reseed."""

    def step_K(self, direction: int) -> None:
        """Change K by one configured step in ``direction`` (+1 or -1)."""

    def step_density(self, direction: int) -> None:
        """Change seed density by one configured step in ``direction``."""

    def request_quit(self) -> None:
        """Ask the main loop to exit."""


Action = Callable[[Controllable], None]


@dataclass(frozen=True)
class KeyBinding:
    """Keys that trigger one action.

    Attributes:
        keys: pygame key codes.
        action: Callable invoked with the controllable target.
        hint: Caption text for this binding, or ``None`` to omit it (used
            when a paired binding already describes both keys).
    """

    keys: tuple[int, ...]
    action: Action
    hint: str | None


MOUSE_HINTS: tuple[str, ...] = ("drag=zoom", "dbl-click=reset")

KEY_BINDINGS: tuple[KeyBinding, ...] = (
    KeyBinding((pygame.K_r, pygame.K_ESCAPE), lambda c: c.reset(), "r=reset"),
    KeyBinding((pygame.K_s,), lambda c: c.cycle_seed_mode(), "s=cycle-seed"),
    KeyBinding((pygame.K_UP,), lambda c: c.step_K(+1), "↑↓=K"),
    KeyBinding((pygame.K_DOWN,), lambda c: c.step_K(-1), None),
    KeyBinding(
        (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS),
        lambda c: c.step_density(+1),
        "+-=density",
    ),
    KeyBinding((pygame.K_MINUS, pygame.K_KP_MINUS), lambda c: c.step_density(-1), None),
    KeyBinding((pygame.K_q,), lambda c: c.request_quit(), "q=quit"),
)


def build_key_map(bindings: Iterable[KeyBinding] = KEY_BINDINGS) -> dict[int, Action]:
    """Flatten bindings into a key-code lookup table.

    Args:
        bindings: Key bindings to index.

    Returns:
        Mapping of pygame key code to action.
    """
    return {key: binding.action for binding in bindings for key in binding.keys}


def build_caption(title: str, bindings: Iterable[KeyBinding] = KEY_BINDINGS) -> str:
    """Compose the window caption from the title and binding hints.

    Args:
        title: Window title.
        bindings: Key bindings whose hints are listed.

    Returns:
        e.g. ``"Chirikov Standard Map  [drag=zoom  ...  q=quit]"``.
    """
    hints = [*MOUSE_HINTS, *(b.hint for b in bindings if b.hint is not None)]
    return f"{title}  [{'  '.join(hints)}]"
