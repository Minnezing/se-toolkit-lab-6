# Task 3 Plan: The System Agent

## Overview

Extend the agent from Task 2 with a `query_api` tool that can query the deployed backend LMS API. This enables the agent to answer both static system questions (framework, ports) and data-dependent queries (item count, scores).

## Tool Design: query_api

**Purpose:** Call the deployed backend LMS API with proper authentication.

**Parameters:**
- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` (response content).

**Authentication:**
- Use `LMS_API_KEY` from `.env.docker.secret`
- Send as `Authorization: Bearer <LMS_API_KEY>` header

**Implementation:**
```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    """Query the backend LMS API."""
    url = f"{AGENT_API_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {LMS_API_KEY}",
        "Content-Type": "application/json",
    }
    # Use httpx to make request
    # Return JSON with status_code and body
```

## Environment Variables

The agent must read ALL configuration from environment variables (not hardcoded):

| Variable | Source File | Purpose |
|----------|-------------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Optional (default: `http://localhost:42002`) | Backend API base URL |

**Important:** The autochecker injects its own values at runtime. Hardcoding will cause failures.

## System Prompt Update

The system prompt must guide the LLM to choose the right tool:

- **Wiki questions** (how-to, workflows) → `list_files` + `read_file`
- **System facts** (framework, ports, status codes) → `query_api` or `read_file` (source code)
- **Data queries** (item count, scores) → `query_api`
- **Bug diagnosis** → `query_api` to reproduce, then `read_file` to find root cause

Example guidance:
```
- For questions about the running system (items count, status codes, analytics): use query_api
- For questions about source code (what framework, how it works): use read_file on relevant files
- For questions about documentation/workflows: use list_files and read_file on wiki/
```

## Tool Schema

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the backend LMS API. Use for questions about data (item count, scores) or system behavior (status codes, errors).",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
        "path": {"type": "string", "description": "API endpoint path (e.g., '/items/')"},
        "body": {"type": "string", "description": "Optional JSON request body for POST/PUT"}
      },
      "required": ["method", "path"]
    }
  }
}
```

## Output Format

Same as Task 2, but `source` is now optional (system questions may not have wiki source):

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",  // Optional for system questions
  "tool_calls": [...]
}
```

## Benchmark Strategy

Run `run_eval.py` to test against 10 questions:

1. **First run:** Identify failures
2. **Debug:** Check which tool was called, what arguments, what error
3. **Fix:** Update tool descriptions, system prompt, or implementation
4. **Iterate:** Re-run until all 10 pass

**Expected failures and fixes:**
- Wrong tool selected → Improve system prompt guidance
- API path wrong → Add example paths to tool description
- Auth error → Verify LMS_API_KEY is loaded correctly
- Null content from LLM → Handle `(msg.get("content") or "")`

## Files to Modify

| File | Changes |
|------|---------|
| `plans/task-3.md` | Create this plan |
| `agent.py` | Add `query_api` tool, load `LMS_API_KEY` and `AGENT_API_BASE_URL`, update system prompt |
| `.env.docker.secret` | Ensure `LMS_API_KEY` is set (already done in setup) |
| `AGENT.md` | Document `query_api`, auth, lessons learned, final score |
| `tests/test_agent_task1.py` | Add 2 tests for `query_api` |

## Testing Strategy

**Test 1:** System fact question
- Question: "What framework does the backend use?"
- Verify: `read_file` or `query_api` in tool_calls, `FastAPI` in answer

**Test 2:** Data query question
- Question: "How many items are in the database?"
- Verify: `query_api` in tool_calls, number > 0 in answer

## Success Criteria

- `query_api` tool works with authentication
- Agent reads all config from environment variables
- `run_eval.py` passes 10/10 questions
- 2 new regression tests pass
- AGENT.md has 200+ words documenting the solution
