"""Tests for the data <-> pixel transform."""

import numpy as np
import pytest

from standard_map.config import TWO_PI
from standard_map.exceptions import InvalidViewportError
from standard_map.viewport import FULL_TORUS, Bounds, CoordTransform

DIM = 800


def test_reset_shows_full_torus():
    view = CoordTransform(DIM)
    assert view.bounds == FULL_TORUS
    assert view.dim == DIM
    cols, rows = view.data_to_pixel(np.array([0.0, np.pi]), np.array([0.0, np.pi]))
    np.testing.assert_array_equal(cols, [0, DIM // 2])
    np.testing.assert_array_equal(rows, [0, DIM // 2])


def test_bounds_ranges():
    bounds = Bounds(1.0, 2.0, 3.0, 4.0)
    assert bounds.x_range == (1.0, 2.0)
    assert bounds.y_range == (3.0, 4.0)


def test_zoom_then_reset():
    view = CoordTransform(DIM)
    view.zoom_to_pixel_rect(200, 200, 600, 600)
    assert view.bounds == Bounds(np.pi / 2, 3 * np.pi / 2, np.pi / 2, 3 * np.pi / 2)
    view.reset()
    assert view.bounds == FULL_TORUS


def test_zoom_accepts_corners_in_any_order():
    a, b = CoordTransform(DIM), CoordTransform(DIM)
    a.zoom_to_pixel_rect(100, 50, 300, 400)
    b.zoom_to_pixel_rect(300, 400, 100, 50)
    assert a.bounds == b.bounds


def test_nested_zoom_maps_bounds_onto_window():
    view = CoordTransform(DIM)
    view.zoom_to_pixel_rect(100, 100, 500, 300)
    view.zoom_to_pixel_rect(80, 80, 720, 720)
    b = view.bounds
    cols, rows = view.data_to_pixel(np.array([b.x_min, b.x_max]), np.array([b.y_min, b.y_max]))
    np.testing.assert_allclose(cols, [0, DIM], atol=1)
    np.testing.assert_allclose(rows, [0, DIM], atol=1)


def test_pixel_data_round_trip():
    view = CoordTransform(DIM)
    view.zoom_to_pixel_rect(123, 77, 456, 701)
    xd, yd = view.pixel_to_data(250.5, 400.5)  # pixel centre
    cols, rows = view.data_to_pixel(np.array([xd]), np.array([yd]))
    assert (cols[0], rows[0]) == (250, 400)


def test_negative_coordinates_floor_off_screen():
    """Regression: truncation used to map pixel -0.5 onto column 0."""
    view = CoordTransform(DIM)
    tiny = -0.5 * TWO_PI / DIM
    cols, rows = view.data_to_pixel(np.array([tiny]), np.array([tiny]))
    assert cols[0] == -1 and rows[0] == -1


def test_deep_zoom_does_not_overflow():
    view = CoordTransform(DIM)
    for _ in range(4):
        view.zoom_to_pixel_rect(0, 0, 1, 1)
    cols, _ = view.data_to_pixel(np.array([TWO_PI]), np.array([0.0]))
    assert cols.dtype == np.int64 and cols[0] > DIM


@pytest.mark.parametrize("rect", [(10, 10, 10, 50), (10, 10, 50, 10)])
def test_degenerate_zoom_raises(rect):
    with pytest.raises(InvalidViewportError):
        CoordTransform(DIM).zoom_to_pixel_rect(*rect)
