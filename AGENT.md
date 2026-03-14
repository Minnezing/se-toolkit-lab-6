# Agent Architecture

## Overview

This agent is a CLI tool with an **agentic loop** that calls an LLM and uses tools (`read_file`, `list_files`) to gather information from the project wiki before answering questions.

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Command-line    │ ──> │ Agentic Loop │ ──> │ LLM API     │ ──> │ JSON Response│
│ Argument        │     │ + Tools      │     │ (Qwen)      │     │ to stdout    │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ File System │
                       │ (wiki/)     │
                       └─────────────┘
```

### Agentic Loop

```
1. Send user question + tool definitions to LLM
2. Parse response:
   - If tool_calls present:
     a. Execute each tool (read_file, list_files)
     b. Append tool results to messages
     c. Loop back to step 1 (max 10 iterations)
   - If no tool_calls:
     a. Extract final answer
     b. Determine source from conversation
     c. Output JSON and exit
```

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Argument Parser | `agent.py` | Read question from `sys.argv[1]` |
| Settings Loader | `agent.py:AgentSettings` | Load `.env.agent.secret` using `pydantic-settings` |
| Tool Executor | `agent.py:execute_tool()` | Run `read_file` or `list_files` |
| Path Validator | `agent.py:validate_path()` | Prevent path traversal attacks |
| LLM Client | `agent.py:call_llm()` | HTTP POST to LLM API using `httpx` |
| Agentic Loop | `agent.py:run_agentic_loop()` | Coordinate LLM calls and tool execution |
| Response Formatter | `agent.py:main()` | Build JSON with `answer`, `source`, and `tool_calls` |
| Output Handler | `agent.py:main()` | JSON to stdout, logs to stderr |

## Tools

### read_file

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git.md`)

**Returns:** File contents as string, or error message.

**Security:**
- Rejects absolute paths
- Rejects path traversal (`..`)
- Verifies resolved path is within project root

### list_files

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated list of entries, or error message.

**Security:**
- Same path validation as `read_file`

### Tool Schema (OpenAI Function Calling)

Tools are defined as JSON schemas sent to the LLM:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read the contents of a file...",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path..."}
      },
      "required": ["path"]
    }
  }
}
```

## LLM Provider

**Provider:** Qwen Code API (OpenAI-compatible)

**Configuration:**
- **Endpoint:** `http://10.93.25.166:42005/v1` (deployed on VM)
- **Model:** `qwen3-coder-plus`
- **Authentication:** Bearer token via `LLM_API_KEY`

## Environment Variables

The agent reads from `.env.agent.secret`:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for Qwen proxy | `qwen-proxy-key-123` |
| `LLM_API_BASE` | Base URL of LLM API | `http://10.93.25.166:42005/v1` |
| `LLM_MODEL` | Model name | `qwen3-coder-plus` |

## System Prompt

The system prompt instructs the LLM to:
1. Use `list_files` to discover relevant wiki files
2. Use `read_file` to read specific files
3. Find the exact section that answers the question
4. Include the source as `path/to/file.md#section-anchor`
5. Only give final answer after gathering enough information

**Key instruction:** All paths must include the directory prefix (e.g., `wiki/git.md` not just `git.md`).

## Usage

```bash
# Run with a question
uv run agent.py "How do you resolve a merge conflict?"

# Output (JSON to stdout)
{
  "answer": "A merge conflict occurs when two branches modify the same lines...",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git.md"}, "result": "..."}
  ]
}
```

## Output Format

The agent always outputs a single JSON line to stdout:

```json
{
  "answer": "<final answer from LLM>",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git.md"}, "result": "..."}
  ]
}
```

- `answer`: The LLM's final response (string)
- `source`: Wiki section reference that answers the question (string)
- `tool_calls`: Array of all tool calls made during the agentic loop

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing argument | Print usage to stderr, exit code 1 |
| Settings load failure | Print error to stderr, exit code 1 |
| API error | Include error in `answer`, exit code 0 |
| Path traversal attempt | Return error message in tool result |
| Timeout (60s) | Exception caught, error in `answer` |
| Max tool calls (10) | Return partial answer with tool_calls so far |

## Path Security

The `validate_path()` function prevents directory traversal:

```python
def validate_path(path: str) -> Path:
    # Reject absolute paths
    if Path(path).is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Reject path traversal
    if ".." in path:
        raise ValueError("Path traversal not allowed")
    
    # Resolve and verify within project root
    full_path = (PROJECT_ROOT / path).resolve()
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Path outside project root")
    
    return full_path
```

## Logging

- **stdout**: Only valid JSON (for parsing by tests and scripts)
- **stderr**: All debug/progress messages (question, API calls, tool execution)

## Testing

Run the regression tests:

```bash
uv run pytest tests/test_agent_task1.py -v
```

Tests verify:
- Exit code is 0
- stdout is valid JSON
- Required fields exist (`answer`, `source`, `tool_calls`)
- Tool calls are populated when tools are used
- Source references are correctly extracted

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent with agentic loop |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `tests/test_agent_task1.py` | Regression tests |

## Future Work (Task 3)

- **Task 3:** Add more tools (`query_api` to query the backend LMS API)
- Expand agentic loop capabilities
- Improve source extraction with section anchors
