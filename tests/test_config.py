"""Tests for configuration dataclasses, enums and TOML loading."""

from pathlib import Path

import pytest

from standard_map.config import (
    AppConfig,
    ColorMode,
    DisplayConfig,
    SeedingConfig,
    SeedMode,
    coerce_enum,
)
from standard_map.exceptions import ConfigError, InvalidSeedModeError

EXAMPLE = Path(__file__).resolve().parents[1] / "standard_map.example.toml"


def test_seed_mode_cycle_wraps():
    assert SeedMode.GRID.next() is SeedMode.QUASI_RANDOM
    assert SeedMode.QUASI_RANDOM.next() is SeedMode.LEGACY
    assert SeedMode.LEGACY.next() is SeedMode.GRID


def test_coerce_enum_accepts_value_and_rejects_unknown():
    assert coerce_enum(SeedMode, "legacy", InvalidSeedModeError) is SeedMode.LEGACY
    with pytest.raises(InvalidSeedModeError, match="expected one of"):
        coerce_enum(SeedMode, "spiral", InvalidSeedModeError)


def test_defaults_reproduce_original_constants():
    cfg = AppConfig()
    assert cfg.physics.K == 0.97
    assert (cfg.seeding.nx, cfg.seeding.ny) == (20, 20)
    assert cfg.display.window_px == 1600
    assert cfg.display.iters_per_frame == 40
    assert cfg.input.double_click_ms == 400
    assert cfg.color.mode is ColorMode.HSV_CYCLE


def test_example_file_round_trips_to_defaults():
    assert AppConfig.from_toml(EXAMPLE) == AppConfig()


def test_from_toml_overrides_and_coerces(tmp_path):
    path = tmp_path / "cfg.toml"
    path.write_text(
        '[physics]\nK = 1.2\n[seeding]\nmode = "legacy"\n'
        '[color]\nmode = "legacy_rgb"\n[render]\nbackground = [1, 2, 3]\n'
    )
    cfg = AppConfig.from_toml(path)
    assert cfg.physics.K == 1.2
    assert cfg.seeding.mode is SeedMode.LEGACY
    assert cfg.color.mode is ColorMode.LEGACY_RGB
    assert cfg.render.background == (1, 2, 3)
    assert cfg.display == DisplayConfig()


@pytest.mark.parametrize(
    "text",
    [
        "[bogus]\nx = 1\n",
        "[physics]\nkay = 1\n",
        '[seeding]\nmode = "spiral"\n',
        "not = [valid",
    ],
)
def test_from_toml_rejects_bad_input(tmp_path, text):
    path = tmp_path / "cfg.toml"
    path.write_text(text)
    with pytest.raises(ConfigError):
        AppConfig.from_toml(path)


def test_from_toml_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="cannot load"):
        AppConfig.from_toml(tmp_path / "missing.toml")


@pytest.mark.parametrize(
    "kwargs",
    [{"nx": 0}, {"legacy_count": 0}, {"density_min": 50, "density_max": 10}],
)
def test_seeding_validation(kwargs):
    with pytest.raises(ConfigError):
        SeedingConfig(**kwargs)


def test_display_validation():
    with pytest.raises(ConfigError):
        DisplayConfig(window_px=0)
