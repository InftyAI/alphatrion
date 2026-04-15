"""Tests for pricing utilities."""

from unittest import mock

import pytest

from alphatrion.utils import pricing


@pytest.fixture(autouse=True)
def reset_pricing_cache():
    """Reset pricing cache before each test."""
    pricing._PRICING_CACHE = None
    yield
    pricing._PRICING_CACHE = None


def test_load_pricing_config_dev_mode():
    """Test loading pricing config in development mode (relative path)."""
    # Clear cache to force reload
    pricing._PRICING_CACHE = None

    config = pricing.load_pricing_config()

    assert isinstance(config, dict)
    assert "anthropic" in config or "deepinfra" in config
    # Verify it's cached
    assert pricing._PRICING_CACHE is not None


def test_load_pricing_config_cached():
    """Test that pricing config is cached after first load."""
    # First load
    config1 = pricing.load_pricing_config()

    # Second load should return cached value
    config2 = pricing.load_pricing_config()

    assert config1 is config2


def test_load_pricing_config_as_installed_package(tmp_path, monkeypatch):
    """Test loading pricing config when installed as a library."""
    # Create a mock package structure
    mock_config_content = """
anthropic:
  models: []

deepinfra:
  models:
    test-model:
      description: "Test model"
      input_tokens_price: 0.1
      output_tokens_price: 0.5
      cache_read_input_tokens_price: 0.05
      cache_creation_input_tokens_price: 0.1
"""

    # Mock importlib.resources to simulate installed package
    mock_file = mock.MagicMock()
    mock_file.read_text.return_value = mock_config_content

    mock_files = mock.MagicMock()
    mock_files.joinpath.return_value = mock_file

    with mock.patch(
        "alphatrion.utils.pricing.resources.files", return_value=mock_files
    ):
        config = pricing.load_pricing_config()

    assert isinstance(config, dict)
    assert "anthropic" in config
    assert "deepinfra" in config
    assert "test-model" in config["deepinfra"]["models"]
    mock_files.joinpath.assert_called_once_with("config/modelspec.yaml")


def test_load_pricing_config_fallback_to_relative_path(monkeypatch):
    """Test fallback to relative path when package resources fail."""

    def mock_files_error(*args, **kwargs):
        raise ModuleNotFoundError("Package not found")

    with mock.patch(
        "alphatrion.utils.pricing.resources.files", side_effect=mock_files_error
    ):
        # Should fall back to relative path
        config = pricing.load_pricing_config()

    assert isinstance(config, dict)
    # Should successfully load from relative path
    assert "anthropic" in config or "deepinfra" in config


def test_load_pricing_config_missing_file_raises_error(tmp_path, monkeypatch):
    """Test that missing config file raises appropriate error."""

    def mock_files_error(*args, **kwargs):
        raise FileNotFoundError("Config not found")

    # Mock both package resources and file path to fail
    with mock.patch(
        "alphatrion.utils.pricing.resources.files", side_effect=mock_files_error
    ):
        # Also mock Path to point to non-existent location
        with mock.patch("alphatrion.utils.pricing.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                tmp_path / "nonexistent.yaml"
            )

            with pytest.raises(Exception):
                pricing.load_pricing_config()


def test_get_model_pricing():
    """Test getting pricing for a specific model."""
    # First ensure config is loaded
    config = pricing.load_pricing_config()

    # Find a model from the loaded config
    provider = None
    model = None
    for prov, prov_data in config.items():
        models = prov_data.get("models", {})
        if models:
            provider = prov
            model = next(iter(models.keys()))
            break

    if provider and model:
        pricing_info = pricing.get_model_pricing(provider, model)

        assert isinstance(pricing_info, dict)
        assert "input_tokens_price" in pricing_info
        assert "output_tokens_price" in pricing_info
        assert "cache_creation_input_tokens_price" in pricing_info
        assert "cache_read_input_tokens_price" in pricing_info


def test_get_model_pricing_fallback_to_default():
    """Test fallback to default pricing for unknown model."""
    pricing_info = pricing.get_model_pricing("unknown-provider", "unknown-model")

    assert isinstance(pricing_info, dict)
    assert pricing_info["input_tokens_price"] == 3.3
    assert pricing_info["output_tokens_price"] == 16.5
    assert pricing_info["cache_creation_input_tokens_price"] == 3.3
    assert pricing_info["cache_read_input_tokens_price"] == 3.3


def test_calculate_cost():
    """Test cost calculation."""
    cost = pricing.calculate_cost(
        provider="deepinfra",
        model="test-model",
        input_tokens=1_000_000,  # 1M tokens
        output_tokens=500_000,  # 0.5M tokens
        cache_creation_input_tokens=200_000,  # 0.2M tokens
        cache_read_input_tokens=100_000,  # 0.1M tokens
    )

    assert isinstance(cost, dict)
    assert "total_cost" in cost
    assert "input_cost" in cost
    assert "output_cost" in cost
    assert "cache_creation_input_cost" in cost
    assert "cache_read_input_cost" in cost

    # All costs should be non-negative
    assert cost["total_cost"] >= 0
    assert cost["input_cost"] >= 0
    assert cost["output_cost"] >= 0

    # Total should be sum of all components
    expected_total = (
        cost["input_cost"]
        + cost["output_cost"]
        + cost["cache_creation_input_cost"]
        + cost["cache_read_input_cost"]
    )
    assert abs(cost["total_cost"] - expected_total) < 0.00000001


def test_calculate_cost_zero_tokens():
    """Test cost calculation with zero tokens."""
    cost = pricing.calculate_cost(
        provider="deepinfra",
        model="test-model",
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    assert cost["total_cost"] == 0
    assert cost["input_cost"] == 0
    assert cost["output_cost"] == 0
    assert cost["cache_creation_input_cost"] == 0
    assert cost["cache_read_input_cost"] == 0


def test_calculate_cost_precision():
    """Test that costs are rounded to 8 decimal places."""
    cost = pricing.calculate_cost(
        provider="deepinfra",
        model="test-model",
        input_tokens=1,  # Very small number
        output_tokens=1,
    )

    # Check that all values are rounded to 8 decimal places
    for key, value in cost.items():
        # Convert to string and check decimal places
        str_value = str(value)
        if "." in str_value:
            decimal_places = len(str_value.split(".")[1])
            assert decimal_places <= 8, f"{key} has {decimal_places} decimal places"
