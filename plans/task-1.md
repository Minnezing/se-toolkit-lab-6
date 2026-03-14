# Task 1 Plan: Call an LLM from Code

## LLM Provider Choice

**Provider:** Qwen Code API (deployed on VM)

**Reason:** Already configured during setup, 1000 free requests/day, works from Russia, no credit card needed.

**Configuration:**
- `LLM_API_BASE`: `http://10.93.25.166:42005/v1`
- `LLM_API_KEY`: `qwen-proxy-key-123`
- `LLM_MODEL`: `qwen3-coder-plus`

## Agent Architecture

### Data Flow

```
Command-line argument → Parse question → Call LLM API → Parse response → Format JSON → stdout
```

### Components

1. **Argument Parser**: Read question from `sys.argv[1]`
2. **Environment Loader**: Read `.env.agent.secret` using `python-dotenv`
3. **LLM Client**: Use `httpx` or `openai` package to call the API
4. **Response Formatter**: Build JSON with `answer` and `tool_calls` fields
5. **Output Handler**: Print JSON to stdout, logs to stderr

### Error Handling

- Missing argument → exit with error message to stderr, non-zero exit code
- API error → catch exception, return error message in `answer` field
- Invalid response → return empty answer with error logged to stderr
- Timeout → use 60-second timeout on HTTP request

## Testing Strategy

**Test file:** `tests/test_agent_task1.py`

**Test case:** Run `agent.py` with a simple question, parse stdout as JSON, verify:
- Exit code is 0
- JSON has `answer` field (string)
- JSON has `tool_calls` field (empty list)

## Files to Create

1. `plans/task-1.md` — this plan
2. `agent.py` — the CLI agent
3. `AGENT.md` — documentation
4. `tests/test_agent_task1.py` — regression test

## Dependencies

Check `pyproject.toml` — should already have `httpx` and `python-dotenv` from project setup.
