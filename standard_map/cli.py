"""Command-line parsing into an :class:`AppConfig`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import AppConfig, ColorMode, SeedMode
from .exceptions import ConfigError


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser; help text shows the configured defaults.

    Override flags default to ``None`` so that only flags actually given on
    the command line replace values from the config file.

    Returns:
        The configured parser.
    """
    defaults = AppConfig()
    parser = argparse.ArgumentParser(description="Chirikov Standard Map visualization")
    parser.add_argument(
        "--config", type=Path, help="TOML config file (see standard_map.example.toml)"
    )
    parser.add_argument(
        "--K",
        type=float,
        metavar="K",
        help=f"Nonlinearity parameter (default {defaults.physics.K} = edge of chaos)",
    )
    parser.add_argument(
        "--seed-mode",
        type=SeedMode,
        choices=list(SeedMode),
        help=f"Initial condition strategy (default {defaults.seeding.mode})",
    )
    parser.add_argument(
        "--nx",
        type=int,
        help=f"Seeds along x (default {defaults.seeding.nx}; grid and quasi_random modes)",
    )
    parser.add_argument(
        "--ny",
        type=int,
        help=f"Seeds along y (default {defaults.seeding.ny}; grid and quasi_random modes)",
    )
    parser.add_argument(
        "--color-mode",
        type=ColorMode,
        choices=list(ColorMode),
        help=f"Trajectory color scheme (default {defaults.color.mode})",
    )
    parser.add_argument(
        "--rng-seed", type=int, help="Seed for the quasi_random scramble (reproducible runs)"
    )
    return parser


def _given(**values: Any) -> dict[str, Any]:
    """Drop entries whose value is ``None`` (flag not supplied).

    Args:
        **values: Candidate overrides.

    Returns:
        Only the overrides that were supplied.
    """
    return {key: value for key, value in values.items() if value is not None}


def apply_overrides(config: AppConfig, args: argparse.Namespace) -> AppConfig:
    """Overlay command-line flags onto a configuration.

    Args:
        config: Base configuration (defaults or loaded from TOML).
        args: Parsed command-line arguments.

    Returns:
        The merged configuration.

    Raises:
        ConfigError: If an override fails validation (e.g. ``--nx 0``).
    """
    return replace(
        config,
        physics=replace(config.physics, **_given(K=args.K)),
        seeding=replace(
            config.seeding,
            **_given(mode=args.seed_mode, nx=args.nx, ny=args.ny, rng_seed=args.rng_seed),
        ),
        color=replace(config.color, **_given(mode=args.color_mode)),
    )


def parse_config(argv: Sequence[str] | None = None) -> AppConfig:
    """Parse the command line (and optional config file) into a configuration.

    Args:
        argv: Arguments excluding the program name; ``None`` reads ``sys.argv``.

    Returns:
        The resulting configuration.

    Raises:
        SystemExit: Via ``argparse`` on invalid arguments or configuration.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        base = AppConfig.from_toml(args.config) if args.config else AppConfig()
        return apply_overrides(base, args)
    except ConfigError as exc:
        parser.error(str(exc))
