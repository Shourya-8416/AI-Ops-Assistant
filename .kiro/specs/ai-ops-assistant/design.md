# AI Operations Assistant - Design Document

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Web UI                        │
│                        (ui/app.py)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                       │
│                      (main.py)                              │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│ Planner  │─────▶│ Executor │─────▶│ Verifier │
│  Agent   │      │  Agent   │      │  Agent   │
└────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                  │
     │                 │                  │
     ▼                 ▼                  ▼
┌─────────────────────────────────────────────────┐
│            LLM Client (llm_client.py)           │
└─────────────────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │     External APIs/Tools     │
        ├─────────────────────────────┤
        │  • GitHub REST API          │
        │  • OpenWeather API          │
        │  • Wikipedia REST API       │
        └─────────────────────────────┘
```

### 1.2 Data Flow

1. User submits natural language query via UI
2. Planner Agent converts query to structured JSON plan
3. Executor Agent executes plan steps using tools
4. Verifier Agent validates results and improves formatting
5. UI displays plan, logs, results, and verification summary

## 2. Component Design

### 2.1 LLM Client (`llm/llm_client.py`)

**Purpose:** Centralized interface for all LLM interactions.

**Class: LLMClient**

```python
class LLMClient:
    """
    Centralized client for LLM API interactions.
    Supports OpenAI-compatible APIs.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4", 
                 base_url: str = None, temperature: float = 0.7)
    
    def generate_completion(self, messages: List[Dict[str, str]], 
                           max_tokens: int = 2000,
                           response_format: Dict = None) -> str
    
    def generate_json_completion(self, messages: List[Dict[str, str]], 
                                max_tokens: int = 2000) -> Dict
    
    def _log_request(self, messages: List[Dict[str, str]])
    
    def _log_response(self, response: str)
```

**Key Features:**
- Configurable model and parameters
- JSON mode support for structured outputs
- Request/response logging
- Error handling with retries
- Token usage tracking

### 2.2 Planner Agent (`agents/planner.py`)

**Purpose:** Convert natural language queries into structured execution plans.

**Class: PlannerAgent**

```python
class PlannerAgent:
    """
    Plans task execution by analyzing user queries and generating
    structured JSON plans with sequential steps.
    """
    
    def __init__(self, llm_client: LLMClient)
    
    def create_plan(self, user_query: str) -> Dict
    
    def _build_planning_prompt(self, user_query: str) -> List[Dict[str, str]]
    
    def _validate_plan(self, plan: Dict) -> bool
    
    def _detect_comparison_intent(self, user_query: str) -> bool
```

**Plan Schema:**

```json
{
  "task_description": "string",
  "intent": "search|compare|summarize|mixed",
  "steps": [
    {
      "step_number": 1,
      "action": "string",
      "tool": "github|weather|wikipedia",
      "parameters": {
        "key": "value"
      },
      "expected_output": "string"
    }
  ],
  "comparison_mode": true|false,
  "entities": ["entity1", "entity2"]
}
```

**Planning Prompt Strategy:**
- System message defines role and capabilities
- Includes tool descriptions and parameters
- Examples of single and comparison queries
- Enforces JSON output format
- Handles ambiguity with reasonable defaults

### 2.3 Executor Agent (`agents/executor.py`)

**Purpose:** Execute plans by calling appropriate tools and handling errors.

**Class: ExecutorAgent**

```python
class ExecutorAgent:
    """
    Executes plans step-by-step using registered tools.
    Handles retries, partial failures, and logging.
    """
    
    def __init__(self, tools: Dict[str, Any])
    
    def execute_plan(self, plan: Dict) -> Dict
    
    def _execute_step(self, step: Dict) -> Dict
    
    def _retry_with_backoff(self, func: Callable, max_retries: int = 3) -> Any
    
    def _log_execution(self, step_number: int, status: str, 
                      result: Any, error: str = None)
```

**Execution Result Schema:**

```json
{
  "success": true|false,
  "steps_completed": 3,
  "steps_failed": 0,
  "results": [
    {
      "step_number": 1,
      "status": "success|failed|partial",
      "data": {},
      "error": "string|null",
      "execution_time": 1.23
    }
  ],
  "execution_log": ["log entry 1", "log entry 2"]
}
```

**Error Handling Strategy:**
- Retry transient failures (network, rate limits)
- Exponential backoff: 1s, 2s, 4s
- Continue on non-critical failures
- Aggregate partial results
- Detailed error logging

### 2.4 Verifier Agent (`agents/verifier.py`)

**Purpose:** Validate execution results and improve output quality.

**Class: VerifierAgent**

```python
class VerifierAgent:
    """
    Verifies execution results for completeness and correctness.
    Uses LLM to assess quality and improve formatting.
    """
    
    def __init__(self, llm_client: LLMClient)
    
    def verify_results(self, plan: Dict, execution_result: Dict) -> Dict
    
    def _build_verification_prompt(self, plan: Dict, 
                                   execution_result: Dict) -> List[Dict[str, str]]
    
    def _check_completeness(self, plan: Dict, execution_result: Dict) -> bool
    
    def _format_for_display(self, results: Dict) -> str
```

**Verification Result Schema:**

```json
{
  "is_complete": true|false,
  "is_correct": true|false,
  "confidence_score": 0.95,
  "issues": ["issue1", "issue2"],
  "formatted_output": "string",
  "summary": "string",
  "recommendations": ["rec1", "rec2"]
}
```

**Verification Prompt Strategy:**
- Check all expected outputs present
- Validate data consistency
- Flag anomalies (e.g., negative temperatures)
- Improve readability
- Suggest follow-up actions

### 2.5 GitHub Tool (`tools/github_tool.py`)

**Purpose:** Search and retrieve GitHub repository information.

**Class: GitHubTool**

```python
class GitHubTool:
    """
    Interacts with GitHub REST API for repository search and metadata.
    """
    
    def __init__(self, api_token: str = None)
    
    def search_repositories(self, query: str, sort: str = "stars", 
                           limit: int = 5) -> List[Dict]
    
    def get_repository_details(self, owner: str, repo: str) -> Dict
    
    def compare_repositories(self, repo_queries: List[str]) -> List[Dict]
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict
    
    def _handle_rate_limit(self, response: requests.Response)
```

**API Endpoints:**
- `GET /search/repositories` - Search repos
- `GET /repos/{owner}/{repo}` - Get repo details

**Output Format:**

```json
{
  "name": "repo-name",
  "full_name": "owner/repo-name",
  "description": "string",
  "stars": 1234,
  "forks": 567,
  "language": "Python",
  "url": "https://github.com/owner/repo",
  "created_at": "2024-01-01",
  "updated_at": "2024-02-01"
}
```

### 2.6 Weather Tool (`tools/weather_tool.py`)

**Purpose:** Fetch current weather data for cities.

**Class: WeatherTool**

```python
class WeatherTool:
    """
    Interacts with OpenWeather API for current weather data.
    """
    
    def __init__(self, api_key: str)
    
    def get_current_weather(self, city: str, units: str = "metric") -> Dict
    
    def compare_weather(self, cities: List[str], units: str = "metric") -> List[Dict]
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict
    
    def _parse_weather_data(self, raw_data: Dict) -> Dict
```

**API Endpoints:**
- `GET /data/2.5/weather` - Current weather

**Output Format:**

```json
{
  "city": "London",
  "country": "GB",
  "temperature": 15.5,
  "feels_like": 14.2,
  "conditions": "Cloudy",
  "humidity": 72,
  "wind_speed": 5.2,
  "timestamp": "2024-02-05T10:30:00Z"
}
```

### 2.7 Wikipedia Tool (`tools/wikipedia_tool.py`)

**Purpose:** Fetch article summaries and factual information.

**Class: WikipediaTool**

```python
class WikipediaTool:
    """
    Interacts with Wikipedia REST API for article summaries.
    """
    
    def __init__(self)
    
    def get_summary(self, topic: str, sentences: int = 3) -> Dict
    
    def search_articles(self, query: str, limit: int = 5) -> List[Dict]
    
    def compare_topics(self, topics: List[str]) -> List[Dict]
    
    def _make_request(self, endpoint: str) -> Dict
    
    def _handle_disambiguation(self, topic: str) -> str
```

**API Endpoints:**
- `GET /api/rest_v1/page/summary/{title}` - Article summary
- `GET /w/api.php?action=opensearch` - Search articles

**Output Format:**

```json
{
  "title": "Python (programming language)",
  "summary": "Python is a high-level...",
  "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
  "thumbnail": "https://...",
  "extract": "First 3 sentences..."
}
```

### 2.8 Streamlit UI (`ui/app.py`)

**Purpose:** Provide professional web interface for user interaction.

**Key Components:**

```python
def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="AI Operations Assistant", layout="wide")
    
    # Header
    render_header()
    
    # Input section
    user_query = render_input_section()
    
    # Execution
    if st.button("Run Task"):
        with st.spinner("Processing..."):
            result = execute_task(user_query)
            render_results(result)

def render_input_section() -> str:
    """Render input text area and examples."""
    
def render_results(result: Dict):
    """Render expandable sections for plan, logs, results, verification."""
    
def render_comparison_table(data: List[Dict], entity_type: str):
    """Render side-by-side comparison table."""
    
def render_error_panel(error: str):
    """Display error messages with helpful context."""
```

**UI Layout:**

```
┌─────────────────────────────────────────────────────┐
│  🤖 AI Operations Assistant                         │
├─────────────────────────────────────────────────────┤
│  Enter your task:                                   │
│  ┌───────────────────────────────────────────────┐ │
│  │ Compare weather in London and Paris          │ │
│  └───────────────────────────────────────────────┘ │
│  [Run Task]                                         │
├─────────────────────────────────────────────────────┤
│  ▼ Execution Plan (JSON)                           │
│  ▼ Execution Logs                                  │
│  ▼ API Responses                                   │
│  ▼ Verification Summary                            │
│  ▼ Results                                         │
│     ┌─────────────┬─────────────┐                  │
│     │   London    │    Paris    │                  │
│     ├─────────────┼─────────────┤                  │
│     │   15°C      │    18°C     │                  │
│     └─────────────┴─────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### 2.9 Main Orchestrator (`main.py`)

**Purpose:** Coordinate agent interactions and provide CLI interface.

```python
class AIOperationsAssistant:
    """
    Main orchestrator coordinating all agents and tools.
    """
    
    def __init__(self, config: Dict):
        self.llm_client = LLMClient(...)
        self.planner = PlannerAgent(self.llm_client)
        self.executor = ExecutorAgent(self._initialize_tools())
        self.verifier = VerifierAgent(self.llm_client)
    
    def process_query(self, user_query: str) -> Dict:
        """Main execution pipeline."""
        # Step 1: Plan
        plan = self.planner.create_plan(user_query)
        
        # Step 2: Execute
        execution_result = self.executor.execute_plan(plan)
        
        # Step 3: Verify
        verification = self.verifier.verify_results(plan, execution_result)
        
        return {
            "plan": plan,
            "execution": execution_result,
            "verification": verification
        }
    
    def _initialize_tools(self) -> Dict:
        """Initialize all tools with API keys."""
```

## 3. API Integration Details

### 3.1 GitHub API

**Authentication:** Optional token via `GITHUB_TOKEN` env var
**Rate Limits:** 60 req/hour (unauthenticated), 5000 req/hour (authenticated)
**Base URL:** `https://api.github.com`

**Error Handling:**
- 403: Rate limit exceeded → wait and retry
- 404: Repository not found → return empty result
- 422: Invalid query → simplify search terms

### 3.2 OpenWeather API

**Authentication:** Required API key via `OPENWEATHER_API_KEY`
**Rate Limits:** 60 calls/minute (free tier)
**Base URL:** `https://api.openweathermap.org`

**Error Handling:**
- 401: Invalid API key → fail with clear message
- 404: City not found → suggest alternatives
- 429: Rate limit → exponential backoff

### 3.3 Wikipedia API

**Authentication:** None required
**Rate Limits:** Reasonable use (< 200 req/s)
**Base URL:** `https://en.wikipedia.org`

**Error Handling:**
- 404: Article not found → search for alternatives
- Disambiguation pages → select most relevant
- Network errors → retry with backoff

## 4. Configuration Management

### 4.1 Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional

GITHUB_TOKEN=ghp_...  # Optional but recommended

OPENWEATHER_API_KEY=abc123...

LOG_LEVEL=INFO
MAX_RETRIES=3
REQUEST_TIMEOUT=30
```

### 4.2 Configuration Class

```python
class Config:
    """Application configuration from environment variables."""
    
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
    def validate(self):
        """Validate required configuration."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        if not self.openweather_api_key:
            raise ValueError("OPENWEATHER_API_KEY is required")
```

## 5. Error Handling Strategy

### 5.1 Error Categories

**Transient Errors (Retry):**
- Network timeouts
- Rate limits (429)
- Temporary service unavailability (503)

**Permanent Errors (Fail Fast):**
- Invalid API keys (401)
- Malformed requests (400)
- Resource not found (404)

**Partial Failures (Continue):**
- One city in comparison fails
- Optional data missing
- Non-critical tool failures

### 5.2 Retry Configuration

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_factor": 2,  # 1s, 2s, 4s
    "retry_statuses": [429, 500, 502, 503, 504],
    "timeout": 30
}
```

## 6. Logging Strategy

### 6.1 Log Levels

- **DEBUG:** LLM prompts/responses, API requests/responses
- **INFO:** Agent transitions, step completions
- **WARNING:** Retries, partial failures
- **ERROR:** Critical failures, invalid configurations

### 6.2 Log Format

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_ops_assistant.log'),
        logging.StreamHandler()
    ]
)
```

## 7. Testing Strategy

### 7.1 Unit Tests

**Framework:** pytest

**Coverage:**
- Each agent class
- Each tool class
- LLM client
- Configuration validation

**Mocking:**
- Mock LLM responses
- Mock API responses
- Use fixtures for test data

### 7.2 Integration Tests

**Scenarios:**
- End-to-end query processing
- Real API calls (with test keys)
- Error handling flows
- Comparison queries

### 7.3 Property-Based Tests

**Framework:** Hypothesis

**Properties to Test:**

#### Property 7.3.1: Plan Validity
**Validates: Requirements 2.2**

For any valid user query, the planner must produce a plan that:
- Contains at least one step
- Each step has required fields (step_number, action, tool, parameters)
- Step numbers are sequential starting from 1
- Tool names are valid (github, weather, wikipedia)

```python
@given(user_query=st.text(min_size=5))
def test_plan_validity(user_query):
    plan = planner.create_plan(user_query)
    assert "steps" in plan
    assert len(plan["steps"]) > 0
    for i, step in enumerate(plan["steps"]):
        assert step["step_number"] == i + 1
        assert step["tool"] in ["github", "weather", "wikipedia"]
```

#### Property 7.3.2: Execution Idempotency
**Validates: Requirements 3.1.2**

Executing the same plan multiple times with the same tool state should produce equivalent results (ignoring timestamps).

```python
@given(plan=valid_plan_strategy())
def test_execution_idempotency(plan):
    result1 = executor.execute_plan(plan)
    result2 = executor.execute_plan(plan)
    assert normalize_result(result1) == normalize_result(result2)
```

#### Property 7.3.3: Comparison Symmetry
**Validates: Requirements 2.4**

Comparing entities [A, B] should produce the same data as comparing [B, A], just in different order.

```python
@given(entities=st.lists(st.text(min_size=1), min_size=2, max_size=2, unique=True))
def test_comparison_symmetry(entities):
    result1 = tool.compare_entities(entities)
    result2 = tool.compare_entities(entities[::-1])
    assert set(r["name"] for r in result1) == set(r["name"] for r in result2)
```

#### Property 7.3.4: Partial Failure Resilience
**Validates: Requirements 3.4.2**

If N steps are planned and M steps fail (M < N), the executor should return results for (N - M) successful steps.

```python
@given(
    num_steps=st.integers(min_value=2, max_value=5),
    fail_indices=st.lists(st.integers(min_value=0, max_value=4), unique=True)
)
def test_partial_failure_resilience(num_steps, fail_indices):
    plan = create_plan_with_steps(num_steps)
    inject_failures(fail_indices)
    result = executor.execute_plan(plan)
    expected_success = num_steps - len([i for i in fail_indices if i < num_steps])
    assert result["steps_completed"] == expected_success
```

#### Property 7.3.5: Verification Completeness
**Validates: Requirements 2.5**

The verifier must check all steps in the execution result and flag any missing expected outputs.

```python
@given(plan=valid_plan_strategy(), execution=valid_execution_strategy())
def test_verification_completeness(plan, execution):
    verification = verifier.verify_results(plan, execution)
    expected_outputs = len(plan["steps"])
    actual_outputs = len(execution["results"])
    if actual_outputs < expected_outputs:
        assert verification["is_complete"] == False
        assert len(verification["issues"]) > 0
```

## 8. Performance Considerations

### 8.1 Optimization Strategies

**Parallel API Calls:**
- Use `concurrent.futures.ThreadPoolExecutor` for comparison queries
- Execute independent steps in parallel when possible

**Caching:**
- Cache LLM responses for identical queries (optional)
- Cache API responses with TTL (optional)

**Token Efficiency:**
- Minimize prompt sizes
- Use structured outputs to reduce parsing
- Limit context to relevant information

### 8.2 Performance Targets

- Simple query (1 API call): < 5 seconds
- Comparison query (2-3 API calls): < 10 seconds
- Complex multi-step query: < 15 seconds

## 9. Security Considerations

### 9.1 API Key Protection

- Never log API keys
- Use environment variables only
- Validate keys on startup
- Mask keys in error messages

### 9.2 Input Validation

- Sanitize user queries
- Validate plan parameters
- Limit query length
- Prevent injection attacks

### 9.3 Rate Limiting

- Respect API rate limits
- Implement client-side throttling
- Queue requests when necessary

## 10. Extensibility

### 10.1 Adding New Tools

To add a new tool:

1. Create tool class in `tools/` directory
2. Implement standard interface:
   - `__init__(self, **config)`
   - `execute(self, **parameters) -> Dict`
3. Register tool in executor
4. Update planner prompt with tool description
5. Add configuration to `.env.example`

### 10.2 Adding New Agents

To add a new agent:

1. Create agent class in `agents/` directory
2. Implement standard interface:
   - `__init__(self, llm_client: LLMClient)`
   - `process(self, input_data: Dict) -> Dict`
3. Integrate into orchestration pipeline
4. Update UI to display agent output

## 11. Dependencies

### 11.1 Core Dependencies

```
openai>=1.0.0           # LLM API client
requests>=2.31.0        # HTTP requests
python-dotenv>=1.0.0    # Environment variables
streamlit>=1.28.0       # Web UI
pydantic>=2.0.0         # Data validation
```

### 11.2 Development Dependencies

```
pytest>=7.4.0           # Testing framework
hypothesis>=6.92.0      # Property-based testing
black>=23.0.0           # Code formatting
mypy>=1.7.0             # Type checking
```

## 12. Deployment

### 12.1 Local Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run Streamlit UI
streamlit run ui/app.py

# Or use CLI
python main.py "Compare weather in London and Paris"
```

### 12.2 Production Considerations

- Use production-grade LLM endpoints
- Implement request queuing
- Add authentication to UI
- Set up monitoring and alerting
- Use secrets management service
- Deploy behind reverse proxy

## 13. Correctness Properties Summary

The system must satisfy these key properties:

1. **Plan Validity:** All generated plans are well-formed and executable
2. **Execution Idempotency:** Same plan produces same results
3. **Comparison Symmetry:** Entity order doesn't affect comparison data
4. **Partial Failure Resilience:** System continues with partial results
5. **Verification Completeness:** All outputs are validated

These properties are tested using property-based testing with Hypothesis.

## 14. Future Enhancements

### 14.1 Potential Improvements

- Add more tools (news, stock prices, maps)
- Implement conversation history
- Add result caching layer
- Support multi-turn interactions
- Add voice input/output
- Implement user preferences
- Add result export (PDF, CSV)
- Support custom tool plugins

### 14.2 Scalability Improvements

- Async API calls with asyncio
- Redis caching layer
- Database for query history
- Load balancing for multiple users
- Distributed task queue

## 15. Success Metrics

The implementation is successful when:

- ✅ All three APIs return real data
- ✅ Agents coordinate without errors
- ✅ UI displays results clearly
- ✅ Comparison queries work correctly
- ✅ Error handling prevents crashes
- ✅ All property-based tests pass
- ✅ End-to-end tests pass
- ✅ Documentation is complete
- ✅ Code meets quality standards
- ✅ System runs without manual intervention
