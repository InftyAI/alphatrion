"""Server runtime initialization for plugins and server components."""

import logging

logger = logging.getLogger(__name__)

def init():
    """Initialize and register all plugins."""
    from alphatrion.plugins import register_plugin
    from alphatrion.plugins.ai_studio import AIStudioPlugin

    # AI Studio plugin
    ai_studio = AIStudioPlugin()
    ai_studio.initialize()
    register_plugin(ai_studio)
    logger.info("AI Studio plugin registered")
