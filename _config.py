import os

from loguru import logger


def positive_float_env(name: str, default: float, *, minimum: float = 1.0) -> float:
    """Read a positive numeric environment setting without breaking imports."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return max(minimum, float(default))
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("invalid {}={!r}; using default {}", name, raw_value, default)
        return max(minimum, float(default))
    if value < minimum:
        logger.warning("{}={} is below minimum {}; using minimum", name, value, minimum)
        return minimum
    return value
