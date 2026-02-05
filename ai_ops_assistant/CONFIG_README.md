# Configuration Management

This module provides centralized configuration management for the AI Operations Assistant application.

## Overview

The `Config` class handles:
- Loading environment variables from `.env` file
- Validating required API keys
- Setting up application logging
- Providing access to configuration parameters

## Quick Start

```python
from ai_ops_assistant import load_config

# Load and validate configuration
config = load_config()

# Use configuration values
print(f"Using model: {config.openai_model}")
```

## Configuration Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM access | `sk-...` |
| `OPENWEATHER_API_KEY` | OpenWeather API key for weather data | `abc123...` |

### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4` |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible endpoint | `None` |
| `GITHUB_TOKEN` | GitHub personal access token | `None` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_RETRIES` | Maximum retry attempts for API calls | `3` |
| `REQUEST_TIMEOUT` | Request timeout in seconds | `30` |

## Setup Instructions

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your API keys:**
   ```bash
   OPENAI_API_KEY=sk-your-actual-key-here
   OPENWEATHER_API_KEY=your-actual-key-here
   ```

3. **Optional: Add GitHub token for higher rate limits:**
   ```bash
   GITHUB_TOKEN=ghp_your-token-here
   ```

## Usage Examples

### Basic Usage

```python
from ai_ops_assistant.config import Config

# Create config instance
config = Config()

# Validate configuration
try:
    config.validate()
    print("Configuration is valid!")
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Using the Convenience Function

```python
from ai_ops_assistant import load_config

# Load and validate in one step
config = load_config()

# Access configuration values
api_key = config.openai_api_key
model = config.openai_model
```

### Accessing Retry Configuration

```python
config = load_config()

# Get retry configuration as a dictionary
retry_config = config.get_retry_config()
# Returns:
# {
#     "max_retries": 3,
#     "backoff_factor": 2,
#     "retry_statuses": [429, 500, 502, 503, 504],
#     "timeout": 30
# }
```

### Using in Application Components

```python
from ai_ops_assistant import load_config
from ai_ops_assistant.llm.llm_client import LLMClient
from ai_ops_assistant.tools.weather_tool import WeatherTool

def initialize_application():
    # Load configuration
    config = load_config()
    
    # Initialize LLM client
    llm_client = LLMClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
        base_url=config.openai_base_url
    )
    
    # Initialize weather tool
    weather_tool = WeatherTool(
        api_key=config.openweather_api_key
    )
    
    return llm_client, weather_tool
```

## Logging

The `Config` class automatically sets up logging when instantiated. Logs are written to:
- **Console**: Simple format with level and message
- **File**: `ai_ops_assistant.log` with detailed format including timestamp and module name

### Log Format

**Console:**
```
INFO - Configuration validated successfully
```

**File:**
```
2024-02-05 10:30:15 - root - INFO - Configuration validated successfully
```

### Using Logging in Your Code

```python
import logging
from ai_ops_assistant import load_config

# Load config (sets up logging)
config = load_config()

# Get a logger for your module
logger = logging.getLogger(__name__)

# Log messages
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

## Validation

The `validate()` method checks:

1. **Required API keys are present:**
   - `OPENAI_API_KEY`
   - `OPENWEATHER_API_KEY`

2. **API key format is valid:**
   - OpenAI key starts with `sk-`

3. **Numeric values are valid:**
   - `MAX_RETRIES` is non-negative
   - `REQUEST_TIMEOUT` is positive

4. **Log level is valid:**
   - Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL

If validation fails, a `ValueError` is raised with detailed error messages.

## Security

### API Key Protection

- API keys are **never logged** in plain text
- The `__repr__` method masks keys with `********`
- Keys are only loaded from environment variables
- No hardcoded credentials in code

### Best Practices

1. **Never commit `.env` file** - It's in `.gitignore`
2. **Use `.env.example` as template** - Share this, not actual keys
3. **Rotate keys regularly** - Especially if exposed
4. **Use minimal permissions** - GitHub token only needs read access
5. **Keep keys secure** - Don't share in chat, email, or public repos

## Error Handling

### Missing Required Keys

```python
# If OPENAI_API_KEY is not set:
ValueError: Configuration validation failed:
  - OPENAI_API_KEY is required. Get your key from: https://platform.openai.com/api-keys
```

### Invalid Key Format

```python
# If OPENAI_API_KEY doesn't start with 'sk-':
ValueError: Configuration validation failed:
  - OPENAI_API_KEY appears to be invalid (should start with 'sk-')
```

### Invalid Numeric Values

```python
# If MAX_RETRIES is negative:
ValueError: Configuration validation failed:
  - MAX_RETRIES must be a non-negative integer
```

## Testing

Run the configuration tests:

```bash
# Test with mock environment variables
python test_config_with_mocks.py

# Test with your actual .env file
python test_config.py
```

## API Key Acquisition

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add to `.env` file

### OpenWeather API Key
1. Go to https://openweathermap.org/api
2. Sign up for a free account
3. Navigate to API keys section
4. Copy your API key
5. Add to `.env` file

### GitHub Token (Optional)
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo` (read access)
4. Generate and copy token (starts with `ghp_`)
5. Add to `.env` file

**Note:** Without a GitHub token, you're limited to 60 requests/hour. With a token, you get 5000 requests/hour.

## Troubleshooting

### Issue: "OPENAI_API_KEY is required"
**Solution:** Create a `.env` file and add your OpenAI API key.

### Issue: "OPENAI_API_KEY appears to be invalid"
**Solution:** Ensure your key starts with `sk-`. Get a new key from OpenAI if needed.

### Issue: Logging not working
**Solution:** Check that `LOG_LEVEL` is set to a valid value (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### Issue: Configuration changes not taking effect
**Solution:** Restart your application. Environment variables are loaded once at startup.

## Advanced Configuration

### Custom OpenAI Endpoint

To use a custom OpenAI-compatible endpoint:

```bash
# In .env file
OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
```

### Adjusting Retry Behavior

```bash
# In .env file
MAX_RETRIES=5          # Increase retry attempts
REQUEST_TIMEOUT=60     # Increase timeout to 60 seconds
```

### Debug Logging

```bash
# In .env file
LOG_LEVEL=DEBUG        # Enable detailed debug logs
```

## Class Reference

### Config

Main configuration class.

**Methods:**

- `__init__()`: Initialize configuration from environment variables
- `validate()`: Validate required configuration and raise ValueError if invalid
- `get_retry_config()`: Get retry configuration as dictionary
- `__repr__()`: String representation with masked API keys

**Attributes:**

- `openai_api_key`: OpenAI API key
- `openai_model`: OpenAI model name
- `openai_base_url`: Custom OpenAI endpoint (optional)
- `github_token`: GitHub personal access token (optional)
- `openweather_api_key`: OpenWeather API key
- `log_level`: Logging level
- `max_retries`: Maximum retry attempts
- `request_timeout`: Request timeout in seconds

### load_config()

Convenience function to load and validate configuration.

**Returns:** Validated `Config` instance

**Raises:** `ValueError` if validation fails

## Integration with Other Components

The configuration system integrates with:

- **LLM Client** (`llm/llm_client.py`): Uses OpenAI configuration
- **GitHub Tool** (`tools/github_tool.py`): Uses GitHub token
- **Weather Tool** (`tools/weather_tool.py`): Uses OpenWeather API key
- **All Agents**: Use logging configured by Config class

## Future Enhancements

Potential improvements:

- Support for configuration files (YAML, TOML)
- Configuration validation schemas with Pydantic
- Hot-reloading of configuration
- Configuration profiles (dev, staging, prod)
- Encrypted configuration storage
- Configuration management UI
