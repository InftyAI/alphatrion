"""Global plugin registry."""

from .base import Plugin, PluginRegistry

# Global plugin registry instance
_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """
    Get the global plugin registry.

    Returns:
        Global PluginRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def register_plugin(plugin: Plugin) -> None:
    """
    Register a plugin in the global registry.

    Args:
        plugin: Plugin instance to register
    """
    get_registry().register(plugin)
