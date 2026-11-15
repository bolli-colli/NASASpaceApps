"""Domain-specific exceptions, so callers can react to precise failure causes."""


class EarthTrailError(Exception):
    """Base class of all errors raised on purpose by this application."""


class CatalogError(EarthTrailError):
    """The YAML catalog is missing, malformed or inconsistent."""


class SeriesFormatError(EarthTrailError):
    """A table does not follow the common data format (spec 10.4)."""


class UnitConversionError(EarthTrailError):
    """No conversion is known between two units."""


class InsufficientDataError(EarthTrailError):
    """A series is too short or too sparse for a trend analysis."""


class LiveAccessError(EarthTrailError):
    """Live retrieval from NASA Earthdata failed or is not possible."""
