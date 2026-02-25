"""
Plugin system for Alphatrion.

Plugins extend experiment functionality by providing additional tools and interfaces.
Each plugin can be enabled per-experiment and provides its own UI and backend logic.
"""

from .base import Plugin, PluginRegistry
from .registry import get_registry, register_plugin

__all__ = ["Plugin", "PluginRegistry", "get_registry", "register_plugin"]
