"""Base transformer interface."""

from abc import ABC, abstractmethod

from lv_py.models.logstash_config import LogstashPlugin
from lv_py.models.vector_config import VectorComponent


class BaseTransformer(ABC):
    """Base interface for Logstash to Vector transformers."""

    @abstractmethod
    def transform(self, plugin: LogstashPlugin) -> VectorComponent:
        """
        Transform a Logstash plugin to Vector component(s).

        Args:
            plugin: Logstash plugin to transform

        Returns:
            Vector component equivalent

        Raises:
            NotImplementedError: If plugin is not supported
        """
        pass

    @abstractmethod
    def supports(self, plugin_name: str) -> bool:
        """Check if this transformer supports the given plugin."""
        pass
