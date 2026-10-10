"""Tests for trajectory color tables."""

import colorsys

import numpy as np
import pytest

from standard_map.color import hsv_to_rgb, make_color_table
from standard_map.config import ColorConfig, ColorMode
from standard_map.exceptions import InvalidColorModeError


def test_hsv_to_rgb_matches_colorsys():
    hues = np.linspace(0.0, 1.0, 997, endpoint=False)
    expected = np.array([colorsys.hsv_to_rgb(h, 0.6, 0.8) for h in hues])
    np.testing.assert_array_equal(hsv_to_rgb(hues, 0.6, 0.8), expected)


def test_hsv_to_rgb_zero_saturation_is_grey():
    np.testing.assert_array_equal(hsv_to_rgb(np.array([0.1, 0.7]), 0.0, 0.5), 0.5)


@pytest.mark.parametrize("n", [1, 85, 400])
def test_hsv_cycle_table(n):
    table = make_color_table(n, ColorMode.HSV_CYCLE)
    expected = [
        [int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.75, 0.92)]
        for h in np.linspace(0.0, 1.0, n, endpoint=False)
    ]
    assert table.dtype == np.uint8
    np.testing.assert_array_equal(table, expected)


def test_legacy_table_uses_config():
    table = make_color_table(2, "legacy_rgb", ColorConfig(legacy_green=1, legacy_blue=2))
    np.testing.assert_array_equal(table, [[0, 1, 2], [128, 1, 2]])


def test_empty_table_has_three_channels():
    assert make_color_table(0).shape == (0, 3)


def test_unknown_mode_raises():
    with pytest.raises(InvalidColorModeError):
        make_color_table(3, "rainbow")
