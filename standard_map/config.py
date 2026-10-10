"""Central configuration: enums, tunable constants and TOML loading.

Every calibration value used by the application lives in one of the frozen
dataclasses below. Defaults reproduce the original behaviour; any of them can
be overridden from a TOML file (see ``standard_map.example.toml``) or from
the command line.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field, fields, replace
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, TypeVar

from .exceptions import ConfigError, InvalidModeError

TWO_PI: float = 2.0 * math.pi
"""Period of the torus in both x and y."""

RGB = tuple[int, int, int]

EnumT = TypeVar("EnumT", bound=StrEnum)


class SeedMode(StrEnum):
    """Initial-condition seeding strategy; declaration order is the ``s`` key cycle."""

    GRID = "grid"
    QUASI_RANDOM = "quasi_random"
    LEGACY = "legacy"

    def next(self) -> SeedMode:
        """Return the mode that follows this one, wrapping around at the end.

        Returns:
            The next seed mode in declaration order.
        """
        modes = list(SeedMode)
        return modes[(modes.index(self) + 1) % len(modes)]


class ColorMode(StrEnum):
    """Trajectory color scheme."""

    HSV_CYCLE = "hsv_cycle"
    LEGACY_RGB = "legacy_rgb"


def coerce_enum(enum_cls: type[EnumT], value: str, error_cls: type[InvalidModeError]) -> EnumT:
    """Convert a string into a member of ``enum_cls``.

    Args:
        enum_cls: The target ``StrEnum`` class.
        value: A member or the string value of a member.
        error_cls: Exception type raised when ``value`` is unknown.

    Returns:
        The matching enum member.

    Raises:
        InvalidModeError: (as ``error_cls``) if ``value`` names no member.
    """
    try:
        return enum_cls(value)
    except ValueError as exc:
        choices = ", ".join(member.value for member in enum_cls)
        message = f"unknown {enum_cls.__name__} {value!r}; expected one of: {choices}"
        raise error_cls(message) from exc


@dataclass(frozen=True)
class PhysicsConfig:
    """Parameters of the map itself.

    Attributes:
        K: Nonlinearity (chaos) parameter; 0.97 is the "edge" of chaos,
            just below Greene's critical value K_c ~= 0.9716.
        K_step: Increment applied by the up/down arrow keys.
        K_round_decimals: Decimals ``K`` is rounded to after each key step,
            which keeps repeated float additions from drifting.
    """

    K: float = 0.97
    K_step: float = 0.01
    K_round_decimals: int = 4


@dataclass(frozen=True)
class SeedingConfig:
    """How initial conditions are placed in the current viewport.

    Attributes:
        mode: Seeding strategy.
        nx: Grid seeds along x (quasi-random mode uses ``nx * ny`` points).
        ny: Grid seeds along y.
        density_step: Per-axis change applied by the ``+``/``-`` keys.
        density_min: Lower bound enforced by the ``-`` key.
        density_max: Upper bound enforced by the ``+`` key.
        legacy_count: Trajectory count of the original Processing sketch.
        rng_seed: Seed for the scrambled Halton sampler; ``None`` draws a
            fresh scramble on every reseed (the original behaviour).
    """

    mode: SeedMode = SeedMode.GRID
    nx: int = 20
    ny: int = 20
    density_step: int = 5
    density_min: int = 5
    density_max: int = 100
    legacy_count: int = 85
    rng_seed: int | None = None

    def __post_init__(self) -> None:
        """Validate counts and bounds.

        Raises:
            ConfigError: If any count is non-positive or the density bounds
                are inverted.
        """
        if min(self.nx, self.ny, self.legacy_count, self.density_step) < 1:
            raise ConfigError("seed counts and density_step must be >= 1")
        if not 1 <= self.density_min <= self.density_max:
            raise ConfigError("require 1 <= density_min <= density_max")


@dataclass(frozen=True)
class DisplayConfig:
    """Window and animation timing.

    Attributes:
        window_px: Side length of the square window in pixels.
        fps_target: Frame-rate cap passed to ``pygame.time.Clock.tick``.
        iters_per_frame: Map iterations drawn per frame (animation speed).
        min_zoom_px: Drag rectangles narrower or shorter than this are
            ignored, so a slightly wobbly click does not zoom.
        title: Window title; key hints are appended automatically.
    """

    window_px: int = 1600
    fps_target: int = 30
    iters_per_frame: int = 40
    min_zoom_px: int = 2
    title: str = "Chirikov Standard Map"

    def __post_init__(self) -> None:
        """Validate sizes and rates.

        Raises:
            ConfigError: If any value is non-positive.
        """
        if min(self.window_px, self.fps_target, self.iters_per_frame, self.min_zoom_px) < 1:
            raise ConfigError("display sizes and rates must be >= 1")


@dataclass(frozen=True)
class InputConfig:
    """Mouse gesture thresholds.

    Attributes:
        double_click_ms: Maximum gap between clicks of a double-click.
        double_click_radius_px: Maximum pointer travel between those clicks.
    """

    double_click_ms: int = 400
    double_click_radius_px: int = 5


@dataclass(frozen=True)
class ColorConfig:
    """Trajectory color scheme parameters.

    Attributes:
        mode: Which scheme to use.
        hsv_saturation: Saturation of the ``hsv_cycle`` palette.
        hsv_value: Value (brightness) of the ``hsv_cycle`` palette.
        legacy_green: Fixed green channel of the Processing palette.
        legacy_blue: Fixed blue channel of the Processing palette.
    """

    mode: ColorMode = ColorMode.HSV_CYCLE
    hsv_saturation: float = 0.75
    hsv_value: float = 0.92
    legacy_green: int = 100
    legacy_blue: int = 200


@dataclass(frozen=True)
class RenderConfig:
    """Colors, font and HUD geometry used by the renderer.

    Attributes:
        background: Fill color after a reseed.
        zoom_rect_color: Outline color of the drag rectangle.
        font_name: System font for the HUD.
        font_size: HUD font size in points.
        hud_origin: Top-left corner of the HUD box.
        hud_width: Width of the opaque HUD box.
        hud_line_height: Vertical spacing between HUD lines.
        hud_padding: Inset of the text inside the HUD box.
        hud_foreground: HUD text color.
        hud_background: HUD box color.
    """

    background: RGB = (0, 0, 0)
    zoom_rect_color: RGB = (255, 0, 0)
    font_name: str = "monospace"
    font_size: int = 12
    hud_origin: tuple[int, int] = (10, 10)
    hud_width: int = 210
    hud_line_height: int = 16
    hud_padding: int = 4
    hud_foreground: RGB = (0, 200, 200)
    hud_background: RGB = (0, 0, 0)


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration bundle."""

    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    seeding: SeedingConfig = field(default_factory=SeedingConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    input: InputConfig = field(default_factory=InputConfig)
    color: ColorConfig = field(default_factory=ColorConfig)
    render: RenderConfig = field(default_factory=RenderConfig)

    @classmethod
    def from_toml(cls, path: str | Path) -> AppConfig:
        """Load a configuration file, using defaults for anything it omits.

        Each top-level TOML table (``[physics]``, ``[seeding]``, ...) maps to
        the attribute of the same name.

        Args:
            path: Path to a TOML file.

        Returns:
            The merged configuration.

        Raises:
            ConfigError: If the file cannot be read or parsed, or contains an
                unknown section, key or enum value.
        """
        try:
            with Path(path).open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"cannot load config {path}: {exc}") from exc
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> AppConfig:
        """Build a configuration from nested dictionaries.

        Args:
            data: Mapping of section name to a mapping of overrides.

        Returns:
            The merged configuration.

        Raises:
            ConfigError: On unknown sections, keys or enum values.
        """
        base = cls()
        sections = {f.name for f in fields(cls)}
        unknown = set(data) - sections
        if unknown:
            raise ConfigError(f"unknown config section(s): {sorted(unknown)}")
        updates = {
            name: _merge_section(getattr(base, name), values) for name, values in data.items()
        }
        return replace(base, **updates)


SectionT = TypeVar("SectionT")


def _merge_section(defaults: SectionT, values: dict[str, Any]) -> SectionT:
    """Overlay ``values`` onto a section dataclass, coercing enums and tuples.

    Args:
        defaults: A section dataclass instance providing defaults and types.
        values: Raw overrides from TOML.

    Returns:
        A new section instance.

    Raises:
        ConfigError: On unknown keys or invalid enum values.
    """
    known = {f.name for f in fields(defaults)}  # type: ignore[arg-type]
    unknown = set(values) - known
    if unknown:
        section = type(defaults).__name__
        raise ConfigError(f"unknown key(s) in {section}: {sorted(unknown)}")
    coerced = {key: _coerce_value(getattr(defaults, key), raw) for key, raw in values.items()}
    return replace(defaults, **coerced)  # type: ignore[type-var]


def _coerce_value(default: object, raw: Any) -> Any:
    """Convert a raw TOML value to the type of its default.

    Args:
        default: The default value, used only for its type.
        raw: The value read from TOML.

    Returns:
        ``raw`` converted to an enum member or tuple where the default is one.

    Raises:
        ConfigError: If ``raw`` is not a valid member of the default's enum.
    """
    if isinstance(default, Enum):
        try:
            return type(default)(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid value {raw!r} for {type(default).__name__}") from exc
    if isinstance(default, tuple):
        return tuple(raw)
    return raw
