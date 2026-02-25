"""Base plugin interface and registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PluginMetadata:
    """Metadata for a plugin displayed in sidebar and UI."""

    id: str  # Unique identifier (e.g., "cloud-ide")
    name: str  # Display name (e.g., "Cloud IDE")
    description: str  # Short description
    icon: str  # Icon name for sidebar (lucide-react icon name)
    version: str  # Plugin version
    author: str | None = None
    route: str = ""  # Frontend route (e.g., "/cloud-ide")
    sidebar_position: int = 100  # Position in sidebar (lower = higher)
    enabled: bool = True  # Whether plugin is globally enabled
    open_in_new_tab: bool = False  # Whether to open in new browser tab


class Plugin(ABC):
    """
    Base class for all plugins.

    Plugins are isolated modules that extend Alphatrion functionality.
    Each plugin provides:
    - Backend API routes (FastAPI router)
    - Frontend React component (full page)
    - Sidebar navigation item
    """

    def __init__(self):
        self._metadata: PluginMetadata | None = None
        self._initialized: bool = False

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Return plugin metadata for sidebar and routing.

        Returns:
            PluginMetadata with display info and routing
        """
        pass

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the plugin with optional configuration.

        Called once when the plugin is registered at server startup.

        Args:
            config: Plugin-specific configuration dictionary
        """
        pass

    def get_api_router(self):
        """
        Get FastAPI router for plugin API endpoints.

        Returns:
            Optional FastAPI APIRouter with plugin routes
            Return None if plugin has no backend routes
        """
        return None

    def get_frontend_bundle_path(self) -> str | None:
        """
        Get path to plugin's frontend JavaScript bundle.

        The bundle should export a default React component that
        renders the full plugin page.

        Returns:
            Path to JS bundle file, or None if using embedded component
        """
        return None

    def shutdown(self) -> None:
        """
        Cleanup hook called when plugin is unregistered or server shuts down.

        Use this to close connections, cleanup resources, etc.
        """
        pass


class PluginRegistry:
    """Registry for managing available plugins."""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If plugin with same ID already registered
        """
        metadata = plugin.get_metadata()
        if metadata.id in self._plugins:
            raise ValueError(f"Plugin with id '{metadata.id}' is already registered")
        self._plugins[metadata.id] = plugin

    def unregister(self, plugin_id: str) -> None:
        """
        Unregister a plugin and call its shutdown hook.

        Args:
            plugin_id: ID of plugin to unregister
        """
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]
            plugin.shutdown()
            del self._plugins[plugin_id]

    def get(self, plugin_id: str) -> Plugin | None:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[Plugin]:
        """
        List all registered plugins.

        Returns:
            List of all plugin instances
        """
        return list(self._plugins.values())

    def list_enabled(self) -> list[Plugin]:
        """
        List all enabled plugins sorted by sidebar position.

        Returns:
            List of enabled plugin instances sorted by sidebar_position
        """
        enabled = [p for p in self._plugins.values() if p.get_metadata().enabled]
        return sorted(enabled, key=lambda p: p.get_metadata().sidebar_position)
