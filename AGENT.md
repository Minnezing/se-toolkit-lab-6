# Agent Architecture

## Overview

This agent is a CLI tool that calls an LLM API and returns structured JSON answers. It is the foundation for the AI-powered coding assistant built across Tasks 1-3.

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Command-line    │ ──> │ Environment  │ ──> │ LLM API     │ ──> │ JSON Response│
│ Argument        │     │ Config       │     │ (Qwen)      │     │ to stdout    │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Argument Parser | `agent.py` | Read question from `sys.argv[1]` |
| Settings Loader | `agent.py:AgentSettings` | Load `.env.agent.secret` using `pydantic-settings` |
| LLM Client | `agent.py:call_llm()` | HTTP POST to LLM API using `httpx` |
| Response Formatter | `agent.py:main()` | Build JSON with `answer` and `tool_calls` |
| Output Handler | `agent.py:main()` | JSON to stdout, logs to stderr |

## LLM Provider

**Provider:** Qwen Code API (OpenAI-compatible)

**Configuration:**
- **Endpoint:** `http://10.93.25.166:42005/v1` (deployed on VM)
- **Model:** `qwen3-coder-plus`
- **Authentication:** Bearer token via `LLM_API_KEY`

**Why Qwen Code:**
- 1000 free requests per day
- Works from Russia (no VPN needed)
- No credit card required
- OpenAI-compatible API

## Environment Variables

The agent reads from `.env.agent.secret`:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for Qwen proxy | `qwen-proxy-key-123` |
| `LLM_API_BASE` | Base URL of LLM API | `http://10.93.25.166:42005/v1` |
| `LLM_MODEL` | Model name | `qwen3-coder-plus` |

## Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"

# Output (JSON to stdout)
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Output Format

The agent always outputs a single JSON line to stdout:

```json
{
  "answer": "<string>",
  "tool_calls": []
}
```

- `answer`: The LLM's response (string)
- `tool_calls`: Empty array (will be populated in Task 2 with tool invocations)

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing argument | Print usage to stderr, exit code 1 |
| Settings load failure | Print error to stderr, exit code 1 |
| API error | Include error in `answer`, exit code 0 |
| Timeout (60s) | Exception caught, error in `answer` |

## Logging

- **stdout**: Only valid JSON (for parsing by tests and scripts)
- **stderr**: All debug/progress messages (question, API calls, errors)

## Testing

Run the regression test:

```bash
pytest tests/test_agent_task1.py
```

The test verifies:
- Exit code is 0
- stdout is valid JSON
- `answer` field exists and is a string
- `tool_calls` field exists and is an empty list

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Implementation plan |
| `tests/test_agent_task1.py` | Regression test |

## Future Work (Tasks 2-3)

- **Task 2:** Add tools (`read_file`, `list_files`, `query_api`)
- **Task 3:** Add agentic loop (plan → act → observe → repeat)
