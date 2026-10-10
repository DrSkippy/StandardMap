"""Tests for map iteration and the MapEngine state holder."""

import numpy as np
import pytest

from standard_map.config import TWO_PI, SeedingConfig, SeedMode
from standard_map.exceptions import ConfigError, InvalidSeedModeError
from standard_map.map_engine import MapEngine, standard_map_step, wrap_to_torus

FULL = (0.0, TWO_PI)


def test_wrap_to_torus_handles_fp_edge_case():
    wrapped = wrap_to_torus(np.array([-1e-17, TWO_PI, 7.0, -1.0]))
    assert ((wrapped >= 0.0) & (wrapped < TWO_PI)).all()
    np.testing.assert_allclose(wrapped, [0.0, 0.0, 7.0 - TWO_PI, TWO_PI - 1.0])


def test_standard_map_step_equations():
    x, y = np.array([1.0]), np.array([0.5])
    x_new, y_new = standard_map_step(x, y, 0.97)
    expected_y = (0.5 + 0.97 * np.sin(1.0)) % TWO_PI
    np.testing.assert_allclose(y_new, expected_y)
    np.testing.assert_allclose(x_new, (1.0 + expected_y) % TWO_PI)


def test_zero_K_is_a_shear():
    x, y = np.array([0.0]), np.array([1.0])
    x_new, y_new = standard_map_step(x, y, 0.0)
    assert y_new[0] == 1.0 and x_new[0] == 1.0


def test_step_records_pre_update_positions():
    engine = MapEngine(0.97, SeedingConfig(nx=2, ny=2))
    engine.reseed(FULL, FULL)
    x0 = engine.x.copy()
    xs, ys = engine.step(3)
    assert xs.shape == ys.shape == (3, 4)
    np.testing.assert_array_equal(xs[0], x0)
    assert not np.array_equal(engine.x, xs[-1])


def test_initial_state_and_properties():
    engine = MapEngine(1.1, SeedingConfig(nx=3, ny=4))
    assert engine.n_trajectories == 12
    assert engine.K == 1.1
    assert engine.seed_mode is SeedMode.GRID
    assert engine.density == (3, 4)
    np.testing.assert_array_equal(engine.y, 0.0)


def test_K_setter():
    engine = MapEngine(0.5, SeedingConfig())
    engine.K = 0.6
    assert engine.K == 0.6


def test_set_seed_mode_and_density_take_effect_on_reseed():
    engine = MapEngine(0.97, SeedingConfig(nx=2, ny=2))
    engine.set_density(5, 6)
    engine.reseed(FULL, FULL)
    assert engine.n_trajectories == 30
    engine.set_seed_mode("legacy")
    engine.reseed(FULL, FULL)
    assert engine.seed_mode is SeedMode.LEGACY
    assert engine.n_trajectories == 85


def test_invalid_updates_raise():
    engine = MapEngine(0.97, SeedingConfig())
    with pytest.raises(InvalidSeedModeError):
        engine.set_seed_mode("spiral")
    with pytest.raises(ConfigError):
        engine.set_density(0, 5)
