"""Tests for the pygame-free gesture state machines."""

from standard_map.gestures import DoubleClickDetector, DragController


def test_double_click_detected_and_consumed():
    detector = DoubleClickDetector(interval_ms=400, radius_px=5)
    assert detector.register_click(1000, (10, 10)) is False
    assert detector.register_click(1200, (12, 13)) is True
    # third click must not re-trigger
    assert detector.register_click(1300, (12, 13)) is False


def test_slow_or_distant_clicks_are_not_double():
    detector = DoubleClickDetector(interval_ms=400, radius_px=5)
    detector.register_click(0, (0, 0))
    assert detector.register_click(400, (0, 0)) is False  # exactly the interval
    assert detector.register_click(500, (3, 4)) is False  # distance exactly 5


def test_first_click_never_double_even_at_time_zero():
    assert DoubleClickDetector(400, 5).register_click(0, (0, 0)) is False


def test_drag_lifecycle():
    drag = DragController[str]()
    drag.begin((5, 6), "snapshot")
    assert not drag.active
    gesture = drag.move()
    assert gesture is not None
    assert (gesture.start, gesture.snapshot) == ((5, 6), "snapshot")
    assert drag.active
    assert drag.finish((50, 60)) == ((5, 6), (50, 60))
    assert not drag.active


def test_click_without_motion_is_not_a_drag():
    drag = DragController[str]()
    drag.begin((5, 6), "snapshot")
    assert drag.finish((5, 6)) is None


def test_motion_without_press_is_ignored():
    """Regression: a drag starting outside the window used to blit None."""
    drag = DragController[str]()
    assert drag.move() is None
    assert not drag.active
    assert drag.finish((1, 1)) is None


def test_cancel_discards_pending_gesture():
    drag = DragController[str]()
    drag.begin((5, 6), "snapshot")
    drag.cancel()
    assert drag.move() is None
