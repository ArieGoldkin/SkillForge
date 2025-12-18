"""Unit tests for API key configuration validation."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.api_key_validation import (
    get_available_models_for_configured_providers,
    get_configured_providers,
    log_api_key_configuration,
    validate_llm_model_api_key,
)


@pytest.mark.unit
class TestGetConfiguredProviders:
    """Tests for get_configured_providers function."""

    @patch("app.core.api_key_validation.settings")
    def test_returns_dict_of_provider_status(self, mock_settings):
        """Test that function returns dict mapping providers to bool."""
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = "google-key"
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None

        result = get_configured_providers()

        assert isinstance(result, dict)
        assert result["openai"] is True
        assert result["anthropic"] is False
        assert result["google_genai"] is True

    @patch("app.core.api_key_validation.settings")
    def test_no_keys_configured(self, mock_settings):
        """Test when no API keys are configured."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None

        result = get_configured_providers()

        assert all(not v for v in result.values())


class TestGetAvailableModels:
    """Tests for get_available_models_for_configured_providers."""

    @patch("app.core.api_key_validation.settings")
    def test_returns_models_with_configured_keys(self, mock_settings):
        """Test that only models with configured API keys are returned."""
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None

        result = get_available_models_for_configured_providers()

        # Should include OpenAI models
        assert "gpt-4o" in result
        assert "gpt-4o-mini" in result
        # Should not include Anthropic models
        assert "claude-sonnet-4-20250514" not in result


class TestValidateLlmModelApiKey:
    """Tests for validate_llm_model_api_key."""

    @patch("app.core.api_key_validation.get_model_info")
    @patch("app.core.api_key_validation.settings")
    def test_valid_model_with_key(self, mock_settings, mock_get_info):
        """Test validation passes when API key is configured."""
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_get_info.return_value = MagicMock(api_key_field="OPENAI_API_KEY")

        is_valid, error = validate_llm_model_api_key()

        assert is_valid is True
        assert error is None

    @patch("app.core.api_key_validation.get_model_info")
    @patch("app.core.api_key_validation.settings")
    def test_model_missing_api_key(self, mock_settings, mock_get_info):
        """Test validation fails when API key is missing."""
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.OPENAI_API_KEY = None
        mock_get_info.return_value = MagicMock(api_key_field="OPENAI_API_KEY")

        is_valid, error = validate_llm_model_api_key()

        assert is_valid is False
        assert "OPENAI_API_KEY" in error
        assert "gpt-4o" in error

    @patch("app.core.api_key_validation.get_model_info")
    @patch("app.core.api_key_validation.settings")
    def test_unknown_model_infers_provider(self, mock_settings, mock_get_info):
        """Test validation for model not in registry but with inferable provider."""
        mock_settings.LLM_MODEL = "gpt-custom"
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.resolved_llm_provider.return_value = "openai"
        mock_get_info.return_value = None  # Model not in registry

        is_valid, error = validate_llm_model_api_key()

        assert is_valid is True
        assert error is None


class TestLogApiKeyConfiguration:
    """Tests for log_api_key_configuration."""

    @patch("app.core.api_key_validation.logger")
    @patch("app.core.api_key_validation.validate_llm_model_api_key")
    @patch("app.core.api_key_validation.get_available_models_for_configured_providers")
    @patch("app.core.api_key_validation.get_configured_providers")
    @patch("app.core.api_key_validation.settings")
    def test_logs_configuration_status(
        self,
        mock_settings,
        mock_get_providers,
        mock_get_models,
        mock_validate,
        mock_logger,
    ):
        """Test that function logs configuration status."""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.JINA_API_KEY = "jina-key"
        mock_get_providers.return_value = {"openai": True, "anthropic": False}
        mock_get_models.return_value = ["gpt-4o", "gpt-4o-mini"]
        mock_validate.return_value = (True, None)

        log_api_key_configuration()

        # Should log api_key_configuration event
        mock_logger.info.assert_any_call(
            "api_key_configuration",
            environment="development",
            llm_model="gpt-4o",
            configured_providers=1,
            total_providers=2,
            provider_status={"openai": "configured", "anthropic": "NOT SET"},
            available_model_count=2,
        )

    @patch("app.core.api_key_validation.logger")
    @patch("app.core.api_key_validation.validate_llm_model_api_key")
    @patch("app.core.api_key_validation.get_available_models_for_configured_providers")
    @patch("app.core.api_key_validation.get_configured_providers")
    @patch("app.core.api_key_validation.settings")
    def test_warns_on_missing_key_in_dev(
        self,
        mock_settings,
        mock_get_providers,
        mock_get_models,
        mock_validate,
        mock_logger,
    ):
        """Test warning is logged in dev when API key is missing."""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.JINA_API_KEY = None
        mock_settings.is_development.return_value = True
        mock_settings.is_e2e.return_value = False
        mock_get_providers.return_value = {"openai": False}
        mock_get_models.return_value = []
        mock_validate.return_value = (False, "OPENAI_API_KEY is required")

        log_api_key_configuration()

        # Should log warning for missing LLM model key
        mock_logger.warning.assert_any_call(
            "llm_model_api_key_missing",
            llm_model="gpt-4o",
            error="OPENAI_API_KEY is required",
            hint=(
                "The workflow will fail when trying to use this model. "
                "Either configure the required API key or change LLM_MODEL."
            ),
        )
