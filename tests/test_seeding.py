"""Tests for the initial-condition seeders."""

import numpy as np
import pytest

from standard_map.config import TWO_PI, SeedingConfig, SeedMode
from standard_map.exceptions import InvalidSeedModeError
from standard_map.seeding import (
    SEEDERS,
    generate_seeds,
    seed_grid,
    seed_legacy,
    seed_quasi_random,
)

FULL = (0.0, TWO_PI)
ZOOM_X = (1.0, 2.0)
ZOOM_Y = (4.0, 4.5)


def test_every_mode_has_a_seeder():
    assert set(SEEDERS) == set(SeedMode)


def test_grid_layout():
    x, y = seed_grid((0.0, 4.0), (0.0, 2.0), SeedingConfig(nx=4, ny=2))
    np.testing.assert_array_equal(x, [0, 1, 2, 3, 0, 1, 2, 3])
    np.testing.assert_array_equal(y, [0, 0, 0, 0, 1, 1, 1, 1])


def test_quasi_random_in_range_and_reproducible():
    cfg = SeedingConfig(nx=10, ny=10, rng_seed=7)
    x, y = seed_quasi_random(ZOOM_X, ZOOM_Y, cfg)
    assert x.size == y.size == 100
    assert ((x >= ZOOM_X[0]) & (x < ZOOM_X[1])).all()
    assert ((y >= ZOOM_Y[0]) & (y < ZOOM_Y[1])).all()
    x2, y2 = seed_quasi_random(ZOOM_X, ZOOM_Y, cfg)
    np.testing.assert_array_equal(x, x2)
    np.testing.assert_array_equal(y, y2)


def test_legacy_full_view_matches_processing():
    x, y = seed_legacy(FULL, FULL, SeedingConfig())
    assert x.size == 85
    np.testing.assert_allclose(x, np.pi)
    np.testing.assert_allclose(y, np.arange(1, 86) * TWO_PI / 86)


def test_legacy_uses_y_range_after_zoom():
    """Regression: the y sweep previously started from x_range[0]."""
    x, y = seed_legacy(ZOOM_X, ZOOM_Y, SeedingConfig(legacy_count=9))
    np.testing.assert_allclose(x, 1.5)
    assert ((y > ZOOM_Y[0]) & (y < ZOOM_Y[1])).all()
    np.testing.assert_allclose(y, 4.0 + np.arange(1, 10) * 0.05)


@pytest.mark.parametrize("mode", [*SeedMode, "grid"])
def test_generate_seeds_dispatch(mode):
    x, y = generate_seeds(mode, FULL, FULL, SeedingConfig(nx=3, ny=3))
    assert x.shape == y.shape


def test_generate_seeds_rejects_unknown_mode():
    with pytest.raises(InvalidSeedModeError):
        generate_seeds("spiral", FULL, FULL, SeedingConfig())
