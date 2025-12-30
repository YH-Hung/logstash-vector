"""Data models for Logstash to Vector migration."""

from enum import Enum


class PluginType(str, Enum):
    """Type of Logstash plugin."""

    INPUT = "input"
    FILTER = "filter"
    OUTPUT = "output"


class ComponentType(str, Enum):
    """Type of Vector component."""

    SOURCE = "source"
    TRANSFORM = "transform"
    SINK = "sink"


class ErrorType(str, Enum):
    """Type of migration error."""

    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    TRANSFORMATION_ERROR = "transformation_error"


__all__ = [
    "PluginType",
    "ComponentType",
    "ErrorType",
]
