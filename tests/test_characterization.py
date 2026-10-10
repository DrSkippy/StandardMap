"""Characterization tests pinning the pre-refactor numerical behaviour."""

import colorsys

import numpy as np

from standard_map.color import make_color_table
from standard_map.map_engine import MapEngine
from standard_map.viewport import CoordTransform

TWO_PI = 2.0 * np.pi
FULL = (0.0, TWO_PI)


def reference_orbit(x, y, K, n_iter):
    """Plain-loop Standard Map, recording positions before each update."""
    xs, ys = [], []
    for _ in range(n_iter):
        xs.append(x.copy())
        ys.append(y.copy())
        y = (y + K * np.sin(x)) % TWO_PI
        y[y >= TWO_PI] = 0.0
        x = (x + y) % TWO_PI
        x[x >= TWO_PI] = 0.0
    return np.array(xs), np.array(ys)


def test_grid_orbit_matches_reference():
    engine = MapEngine(K=0.97, seed_mode="grid", nx_seeds=7, ny_seeds=5)
    engine.reseed(FULL, FULL)
    x0, y0 = engine.x.copy(), engine.y.copy()
    xs, ys = engine.step(40)
    ref_xs, ref_ys = reference_orbit(x0, y0, 0.97, 40)
    np.testing.assert_array_equal(xs, ref_xs)
    np.testing.assert_array_equal(ys, ref_ys)


def test_hsv_table_matches_colorsys():
    table = make_color_table(85)
    expected = [
        [int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.75, 0.92)]
        for h in np.linspace(0.0, 1.0, 85, endpoint=False)
    ]
    np.testing.assert_array_equal(table, np.array(expected, dtype=np.uint8))


def test_legacy_rgb_table():
    table = make_color_table(4, "legacy_rgb")
    np.testing.assert_array_equal(table[:, 0], [0, 64, 128, 192])
    assert (table[:, 1] == 100).all() and (table[:, 2] == 200).all()


def test_zoom_bounds():
    view = CoordTransform()
    view.zoom_to_pixel_rect(0, 0, 800, 400)
    x1, x2, y1, y2 = view.data_bounds
    np.testing.assert_allclose([x1, x2, y1, y2], [0.0, np.pi, 0.0, np.pi / 2])
