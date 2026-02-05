# AI Operations Assistant

A production-quality AI-powered operations assistant with multi-agent architecture, real API integrations, and a professional web UI.

## Overview

The AI Operations Assistant uses specialized agents (Planner, Executor, Verifier) to understand natural language queries, execute tasks using real APIs, and verify results for completeness.

## Features

- **Natural Language Processing**: Input tasks in plain English
- **Multi-Agent Architecture**: Planner → Executor → Verifier pipeline
- **Real API Integrations**: GitHub, OpenWeather, Wikipedia
- **Comparison Queries**: Compare weather, repositories, or topics side-by-side
- **Web UI**: Clean Streamlit interface with expandable result sections
- **CLI Support**: Command-line interface for automation

## Architecture

```
User Query → Planner Agent → Executor Agent → Verifier Agent → Results
                ↓                ↓                ↓
            LLM Client      Tool APIs        LLM Client
```

**Agents:**
- **Planner**: Converts queries to structured JSON plans
- **Executor**: Executes plans using appropriate tools
- **Verifier**: Validates results and improves formatting

**Tools:**
- **GitHub**: Search repositories, get details
- **Weather**: Current weather for cities
- **Wikipedia**: Article summaries and facts

## Setup

### Prerequisites

- Python 3.8+
- API Keys (see below)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd ai-ops-assistant

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### API Keys

Get your API keys from:

1. **LLM Provider** (choose one):
   - **Gemini** (recommended for free tier): https://ai.google.dev/
   - **OpenAI**: https://platform.openai.com/api-keys

2. **OpenWeather**: https://openweathermap.org/api

3. **GitHub** (optional but recommended): https://github.com/settings/tokens

### Environment Configuration

Edit `.env` file:

```bash
# LLM Provider (gemini or openai)
LLM_PROVIDER=gemini

# Gemini Configuration (if using Gemini)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Required APIs
OPENWEATHER_API_KEY=your_openweather_api_key_here

# Optional
GITHUB_TOKEN=your_github_token_here
```

## Usage

### Web UI (Recommended)

```bash
streamlit run ai_ops_assistant/ui/app.py
```

Then open http://localhost:8501 in your browser.

### CLI

```bash
python main.py "What's the weather in Tokyo?"
python main.py "Compare weather in London and Paris"
python main.py "Find popular Python repositories on GitHub"
```

## Example Queries

**Simple Queries:**
- "What's the weather in Tokyo?"
- "Tell me about Python programming"
- "Find popular machine learning repositories"

**Comparison Queries:**
- "Compare weather in London, Paris, and Berlin"
- "Compare React and Vue repositories on GitHub"

**Multi-Step Queries:**
- "Tell me about Python and find popular Python repos"

## Project Structure

```
ai_ops_assistant/
├── agents/
│   ├── planner.py      # Planner Agent
│   ├── executor.py     # Executor Agent
│   └── verifier.py     # Verifier Agent
├── tools/
│   ├── github_tool.py  # GitHub API
│   ├── weather_tool.py # OpenWeather API
│   └── wikipedia_tool.py # Wikipedia API
├── llm/
│   └── llm_client.py   # LLM Client (Gemini/OpenAI)
├── ui/
│   └── app.py          # Streamlit UI
├── config.py           # Configuration
└── __init__.py
main.py                 # CLI entry point
requirements.txt        # Dependencies
.env.example            # Environment template
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest test_integration_workflows.py -v

# Run with output
pytest test_integration_workflows.py -v -s
```

## Limitations

- **Free API Tiers**: Gemini (20 req/day), OpenWeather (60 req/min)
- **Read-Only**: No write operations to APIs
- **Single User**: Designed for local deployment
- **No Persistence**: No database or session storage


## Future Enhancements

- Add more tools (news, stock prices, maps)
- Implement conversation history
- Add result caching
- Support async API calls

## License

MIT License - see LICENSE file for details
