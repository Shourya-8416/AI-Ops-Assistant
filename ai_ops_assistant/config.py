"""
Configuration management for AI Operations Assistant.

This module handles loading and validating environment variables,
and sets up logging configuration for the application.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv


class Config:
    """
    Application configuration from environment variables.
    
    Loads configuration from .env file and validates required API keys.
    Provides centralized access to all configuration parameters.
    """
    
    def __init__(self):
        """
        Initialize configuration by loading environment variables.
        
        Loads variables from .env file if present, then reads from environment.
        Also supports Streamlit secrets for cloud deployment.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Try to load from Streamlit secrets if available (for cloud deployment)
        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                secrets = st.secrets
            else:
                secrets = None
        except (ImportError, FileNotFoundError):
            secrets = None
        
        # Helper function to get config value from secrets or env
        def get_config(key: str, default: str = "") -> str:
            if secrets and key in secrets:
                return secrets[key]
            return os.getenv(key, default)
        
        # LLM Provider Configuration
        self.llm_provider: str = get_config("LLM_PROVIDER", "openai")
        
        # OpenAI Configuration
        self.openai_api_key: str = get_config("OPENAI_API_KEY", "")
        self.openai_model: str = get_config("OPENAI_MODEL", "gpt-4")
        self.openai_base_url: Optional[str] = get_config("OPENAI_BASE_URL") or None
        
        # Gemini Configuration
        self.gemini_api_key: str = get_config("GEMINI_API_KEY", "")
        self.gemini_model: str = get_config("GEMINI_MODEL", "gemini-1.5-pro")
        
        # GitHub Configuration (Optional but recommended)
        self.github_token: Optional[str] = get_config("GITHUB_TOKEN") or None
        
        # OpenWeather Configuration (Required)
        self.openweather_api_key: str = get_config("OPENWEATHER_API_KEY", "")
        
        # Application Configuration
        self.log_level: str = get_config("LOG_LEVEL", "INFO")
        self.max_retries: int = int(get_config("MAX_RETRIES", "3"))
        self.request_timeout: int = int(get_config("REQUEST_TIMEOUT", "30"))
        
        # Setup logging
        self._setup_logging()
    
    def validate(self) -> None:
        """
        Validate that all required configuration is present.
        
        Raises:
            ValueError: If any required configuration is missing or invalid.
        """
        errors = []
        
        # Check required API keys based on provider
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                errors.append("OPENAI_API_KEY is required when using OpenAI provider. Get your key from: https://platform.openai.com/api-keys")
            # Validate OpenAI API key format (basic check)
            if self.openai_api_key and not self.openai_api_key.startswith("sk-"):
                errors.append("OPENAI_API_KEY appears to be invalid (should start with 'sk-')")
        elif self.llm_provider == "gemini":
            if not self.gemini_api_key:
                errors.append("GEMINI_API_KEY is required when using Gemini provider. Get your key from: https://aistudio.google.com/app/apikey")
        else:
            errors.append(f"Invalid LLM_PROVIDER: {self.llm_provider}. Must be 'openai' or 'gemini'")
        
        if not self.openweather_api_key:
            errors.append("OPENWEATHER_API_KEY is required. Get your key from: https://openweathermap.org/api")
        
        # Validate numeric configurations
        if self.max_retries < 0:
            errors.append("MAX_RETRIES must be a non-negative integer")
        
        if self.request_timeout <= 0:
            errors.append("REQUEST_TIMEOUT must be a positive integer")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")
        
        # If there are any errors, raise with all messages
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_message)
        
        logging.info("Configuration validated successfully")
    
    def _setup_logging(self) -> None:
        """
        Set up logging configuration for the application.
        
        Configures logging with both file and console handlers,
        using the log level specified in configuration.
        """
        # Convert log level string to logging constant
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # File handler - detailed logging
        file_handler = logging.FileHandler('ai_ops_assistant.log', mode='a')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler - simpler format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # Log initial message
        logging.info("Logging configured successfully")
    
    def get_retry_config(self) -> dict:
        """
        Get retry configuration as a dictionary.
        
        Returns:
            dict: Retry configuration with max_retries, backoff_factor, 
                  retry_statuses, and timeout.
        """
        return {
            "max_retries": self.max_retries,
            "backoff_factor": 2,  # 1s, 2s, 4s exponential backoff
            "retry_statuses": [429, 500, 502, 503, 504],
            "timeout": self.request_timeout
        }
    
    def __repr__(self) -> str:
        """
        String representation of configuration (with masked secrets).
        
        Returns:
            str: Configuration summary with API keys masked.
        """
        return (
            f"Config(\n"
            f"  openai_api_key={'*' * 8 if self.openai_api_key else 'NOT SET'},\n"
            f"  openai_model={self.openai_model},\n"
            f"  openai_base_url={self.openai_base_url or 'default'},\n"
            f"  github_token={'*' * 8 if self.github_token else 'NOT SET'},\n"
            f"  openweather_api_key={'*' * 8 if self.openweather_api_key else 'NOT SET'},\n"
            f"  log_level={self.log_level},\n"
            f"  max_retries={self.max_retries},\n"
            f"  request_timeout={self.request_timeout}\n"
            f")"
        )


# Convenience function to load and validate configuration
def load_config() -> Config:
    """
    Load and validate application configuration.
    
    Returns:
        Config: Validated configuration instance.
    
    Raises:
        ValueError: If configuration validation fails.
    """
    config = Config()
    config.validate()
    return config
