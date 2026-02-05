"""
AI Operations Assistant - A production-quality AI-powered operations assistant.

This package provides a multi-agent architecture for processing natural language
queries and executing tasks using real API integrations.
"""

__version__ = "1.0.0"

# Import key classes for easy access
from ai_ops_assistant.config import Config, load_config

__all__ = ["Config", "load_config"]
