"""Tests for command-line parsing."""

import pytest

from standard_map.cli import parse_config
from standard_map.config import AppConfig, ColorMode, SeedMode


def test_no_args_gives_defaults():
    assert parse_config([]) == AppConfig()


def test_flags_override_defaults():
    cfg = parse_config(
        ["--K", "1.2", "--seed-mode", "quasi_random", "--nx", "50", "--ny", "40",
         "--color-mode", "legacy_rgb", "--rng-seed", "3"]
    )
    assert cfg.physics.K == 1.2
    assert cfg.seeding.mode is SeedMode.QUASI_RANDOM
    assert (cfg.seeding.nx, cfg.seeding.ny, cfg.seeding.rng_seed) == (50, 40, 3)
    assert cfg.color.mode is ColorMode.LEGACY_RGB


def test_flags_override_config_file(tmp_path):
    path = tmp_path / "cfg.toml"
    path.write_text('[physics]\nK = 0.5\n[seeding]\nnx = 7\nmode = "legacy"\n')
    cfg = parse_config(["--config", str(path), "--nx", "9"])
    assert cfg.physics.K == 0.5
    assert cfg.seeding.nx == 9
    assert cfg.seeding.mode is SeedMode.LEGACY


@pytest.mark.parametrize(
    "argv",
    [["--seed-mode", "spiral"], ["--color-mode", "rainbow"], ["--nx", "0"]],
)
def test_invalid_arguments_exit(argv, capsys):
    with pytest.raises(SystemExit) as excinfo:
        parse_config(argv)
    assert excinfo.value.code == 2
    assert "error" in capsys.readouterr().err


def test_bad_config_file_exits(tmp_path):
    path = tmp_path / "cfg.toml"
    path.write_text("[nope]\n")
    with pytest.raises(SystemExit):
        parse_config(["--config", str(path)])
