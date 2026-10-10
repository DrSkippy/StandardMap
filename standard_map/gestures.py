"""Pygame-independent mouse gesture state machines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

Pixel = tuple[int, int]
SnapshotT = TypeVar("SnapshotT")


class DoubleClickDetector:
    """Recognises two clicks close together in both time and space.

    Args:
        interval_ms: Maximum gap between the two clicks.
        radius_px: Maximum pointer travel between the two clicks.
    """

    def __init__(self, interval_ms: int, radius_px: int) -> None:
        self._interval_ms = interval_ms
        self._radius_sq = radius_px * radius_px
        self._last_time_ms: int | None = None
        self._last_pos: Pixel = (0, 0)

    def register_click(self, time_ms: int, pos: Pixel) -> bool:
        """Record a click and report whether it completes a double-click.

        A detected double-click is consumed, so a third click starts afresh
        instead of triggering again.

        Args:
            time_ms: Click timestamp in milliseconds.
            pos: Click position ``(col, row)``.

        Returns:
            ``True`` if this click completes a double-click.
        """
        if self._last_time_ms is not None and self._is_near(self._last_time_ms, time_ms, pos):
            self._last_time_ms = None  # consume so triple-click doesn't re-trigger
            return True
        self._last_time_ms = time_ms
        self._last_pos = pos
        return False

    def _is_near(self, last_time_ms: int, time_ms: int, pos: Pixel) -> bool:
        """Whether a click is within the double-click window of the last one.

        Args:
            last_time_ms: Timestamp of the previous click.
            time_ms: Timestamp of this click.
            pos: Position of this click.

        Returns:
            ``True`` if close enough in both time and space.
        """
        dx = pos[0] - self._last_pos[0]
        dy = pos[1] - self._last_pos[1]
        recent = time_ms - last_time_ms < self._interval_ms
        return recent and dx * dx + dy * dy < self._radius_sq


@dataclass(frozen=True)
class DragGesture(Generic[SnapshotT]):
    """A pending press-and-drag.

    Attributes:
        start: Where the button was pressed.
        snapshot: Screen contents captured at the press, restored before
            each rectangle redraw to avoid XOR-erase artifacts.
    """

    start: Pixel
    snapshot: SnapshotT


class DragController(Generic[SnapshotT]):
    """Tracks a click-drag gesture. Generic over the snapshot type so it can
    be tested without a display."""

    def __init__(self) -> None:
        self._gesture: DragGesture[SnapshotT] | None = None
        self._active = False

    @property
    def active(self) -> bool:
        """``True`` once the pointer has moved with the button held."""
        return self._active

    def begin(self, pos: Pixel, snapshot: SnapshotT) -> None:
        """Start a potential drag at ``pos`` (button pressed).

        Args:
            pos: Press position ``(col, row)``.
            snapshot: Screen contents to restore during the drag.
        """
        self._gesture = DragGesture(pos, snapshot)
        self._active = False

    def move(self) -> DragGesture[SnapshotT] | None:
        """Record pointer motion with the button held.

        Returns:
            The pending gesture, or ``None`` if the press happened elsewhere
            (e.g. outside the window, or it was consumed by a double-click).
        """
        if self._gesture is not None:
            self._active = True
        return self._gesture

    def finish(self, pos: Pixel) -> tuple[Pixel, Pixel] | None:
        """End the gesture (button released).

        Args:
            pos: Release position ``(col, row)``.

        Returns:
            ``(start, end)`` corners if the pointer was dragged, else ``None``.
        """
        rect = (self._gesture.start, pos) if self._active and self._gesture else None
        self.cancel()
        return rect

    def cancel(self) -> None:
        """Forget any pending gesture."""
        self._gesture = None
        self._active = False
