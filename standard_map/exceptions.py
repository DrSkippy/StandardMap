"""Exception hierarchy for the Standard Map package.

All errors raised deliberately by this package derive from
:class:`StandardMapError`, so callers can catch package failures without
also swallowing unrelated bugs.
"""


class StandardMapError(Exception):
    """Base class for every error raised by this package."""


class ConfigError(StandardMapError, ValueError):
    """A configuration value or configuration file is invalid."""


class InvalidModeError(StandardMapError, ValueError):
    """A mode string does not name a known enum member."""


class InvalidSeedModeError(InvalidModeError):
    """An unknown initial-condition seeding strategy was requested."""


class InvalidColorModeError(InvalidModeError):
    """An unknown trajectory color scheme was requested."""


class InvalidViewportError(StandardMapError, ValueError):
    """A zoom rectangle is degenerate (zero width or height)."""


class RendererUnavailableError(StandardMapError, RuntimeError):
    """The display surface does not support direct pixel-array access."""
