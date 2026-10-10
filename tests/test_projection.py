"""Tests for batch projection and clipping."""

import numpy as np

from standard_map.projection import project_and_clip
from standard_map.viewport import CoordTransform


def test_clips_off_screen_points_and_tracks_trajectory():
    view = CoordTransform(100)
    view.zoom_to_pixel_rect(0, 0, 50, 50)  # show [0, pi) x [0, pi)
    xs = np.array([[0.5, 4.0, 1.0], [1.5, 0.1, 5.0]])
    ys = np.array([[0.5, 0.5, 1.0], [1.5, 6.0, 0.2]])
    points = project_and_clip(xs, ys, view)
    np.testing.assert_array_equal(points.trajectory_index, [0, 2, 0])
    cols, rows = view.data_to_pixel(np.array([0.5, 1.0, 1.5]), np.array([0.5, 1.0, 1.5]))
    np.testing.assert_array_equal(points.cols, cols)
    np.testing.assert_array_equal(points.rows, rows)


def test_color_lookup_matches_tiled_mask():
    rng = np.random.default_rng(0)
    view = CoordTransform(64)
    view.zoom_to_pixel_rect(10, 5, 40, 50)
    xs, ys = rng.uniform(0, 2 * np.pi, (2, 7, 30))
    colors = rng.integers(0, 255, (30, 3), dtype=np.uint8)
    points = project_and_clip(xs, ys, view)

    cols, rows = view.data_to_pixel(xs.ravel(), ys.ravel())
    mask = (cols >= 0) & (cols < 64) & (rows >= 0) & (rows < 64)
    np.testing.assert_array_equal(colors[points.trajectory_index], np.tile(colors, (7, 1))[mask])
    np.testing.assert_array_equal(points.cols, cols[mask])
