"""LLM pricing utilities for cost calculation."""

import logging
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Cache pricing config in memory
_PRICING_CACHE: dict[str, Any] | None = None


def load_pricing_config() -> dict[str, Any]:
    """Load pricing config from YAML file.

    Returns:
        Dict with model pricing information
    """
    global _PRICING_CACHE

    if _PRICING_CACHE is not None:
        return _PRICING_CACHE

    try:
        # Try to load from package resources (when installed)
        try:
            if hasattr(resources, "files"):
                # Python 3.9+
                config_file = resources.files("alphatrion").joinpath(
                    "config/modelspec.yaml"
                )
                config_data = config_file.read_text()
            else:
                # Python 3.7-3.8 fallback
                import importlib.resources as pkg_resources

                config_data = pkg_resources.read_text(
                    "alphatrion.config", "modelspec.yaml"
                )

            config = yaml.safe_load(config_data)
            logger.info("Loaded pricing config from package resources")
        except (FileNotFoundError, ModuleNotFoundError):
            # Fall back to relative path (for development)
            config_path = (
                Path(__file__).parent.parent.parent / "config" / "modelspec.yaml"
            )
            with open(config_path) as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded pricing config from {config_path}")

        _PRICING_CACHE = config
        return config
    except Exception as e:
        logger.error(f"Failed to load pricing config: {e}")
        raise


def get_model_pricing(provider: str, model: str) -> dict[str, float]:
    """Get pricing for a specific model.

    Args:
        provider: Provider name (e.g., "anthropic", "zai-org")
        model: Model name (e.g., "claude-4-sonnet", "GLM-4.7-Flash")

    Returns:
        Dict with keys: input, output, cache_creation, cache_read (all in USD per MTok)
    """
    config = load_pricing_config()

    # Search through all providers
    provider_config = config.get(provider, {})
    models = provider_config.get("models", {})
    if model in models:
        model_config = models[model]
        # Map new field names to expected names
        return {
            "input_tokens_price": model_config["input_tokens_price"],
            "output_tokens_price": model_config["output_tokens_price"],
            "cache_creation_input_tokens_price": model_config[
                "cache_creation_input_tokens_price"
            ],
            "cache_read_input_tokens_price": model_config[
                "cache_read_input_tokens_price"
            ],
        }

    # Fall back to default
    logger.warning(f"No pricing found for model '{model}', using default")
    # default to anthropic/claude-4-sonnet.
    return {
        "input_tokens_price": 3.3,
        "output_tokens_price": 16.5,
        "cache_creation_input_tokens_price": 3.3,
        "cache_read_input_tokens_price": 3.3,
    }


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> dict[str, float]:
    """Calculate cost from token usage.

    Args:
        provider: Provider name (e.g., "anthropic", "deepinfra")
        model: Model name (e.g., "claude-4-sonnet", "GLM-4.7-Flash")
        input_tokens: Regular input tokens
        output_tokens: Output tokens
        cache_creation_input_tokens: Tokens written to cache
        cache_read_input_tokens: Tokens read from cache

    Returns:
        Dict with keys: input_cost, output_cost, cache_creation_cost,
                       cache_read_cost, total_cost (all in USD)
    """
    pricing = get_model_pricing(provider, model)

    # Convert tokens to millions and multiply by price per MTok
    input_cost = (input_tokens / 1_000_000) * pricing["input_tokens_price"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_tokens_price"]
    cache_creation_cost = (cache_creation_input_tokens / 1_000_000) * pricing[
        "cache_creation_input_tokens_price"
    ]
    cache_read_cost = (cache_read_input_tokens / 1_000_000) * pricing[
        "cache_read_input_tokens_price"
    ]

    total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost

    return {
        "total_cost": round(total_cost, 8),
        "input_cost": round(input_cost, 8),
        "output_cost": round(output_cost, 8),
        "cache_creation_input_cost": round(cache_creation_cost, 8),
        "cache_read_input_cost": round(cache_read_cost, 8),
    }
