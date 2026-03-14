# Agent Architecture

## Overview

This agent is a CLI tool with an **agentic loop** that calls an LLM and uses tools (`read_file`, `list_files`, `query_api`) to gather information from the project wiki, source code, and deployed backend API before answering questions.

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Command-line    │ ──> │ Agentic Loop │ ──> │ LLM API     │ ──> │ JSON Response│
│ Argument        │     │ + Tools      │     │ (Qwen)      │     │ to stdout    │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │ File System │ │ Wiki Docs   │ │ Backend API │
       │ (src code)  │ │ (wiki/)     │ │ (LMS)       │
       └─────────────┘ └─────────────┘ └─────────────┘
```

### Agentic Loop

```
1. Send user question + tool definitions to LLM
2. Parse response:
   - If tool_calls present:
     a. Execute each tool (read_file, list_files, query_api)
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
| Settings Loader | `agent.py:AgentSettings`, `BackendSettings` | Load `.env.agent.secret` and `.env.docker.secret` |
| Tool Executor | `agent.py:execute_tool()` | Run `read_file`, `list_files`, or `query_api` |
| Path Validator | `agent.py:validate_path()` | Prevent path traversal attacks |
| LLM Client | `agent.py:call_llm()` | HTTP POST to LLM API using `httpx` |
| Agentic Loop | `agent.py:run_agentic_loop()` | Coordinate LLM calls and tool execution |
| Response Formatter | `agent.py:main()` | Build JSON with `answer`, `source`, and `tool_calls` |
| Output Handler | `agent.py:main()` | JSON to stdout, logs to stderr |

## Tools

### read_file

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git.md`, `backend/app/main.py`)

**Returns:** File contents as string, or error message.

**Security:**
- Rejects absolute paths
- Rejects path traversal (`..`)
- Verifies resolved path is within project root

### list_files

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`, `backend/app/routers`)

**Returns:** Newline-separated list of entries, or error message.

**Security:**
- Same path validation as `read_file`

### query_api

**Purpose:** Query the backend LMS API with optional authentication.

**Parameters:**
- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate?lab=lab-01`)
- `body` (string, optional): JSON request body for POST/PUT requests
- `auth` (boolean, optional): Whether to include authentication header (default: true)

**Returns:** JSON string with `status_code` and `body`, or error message.

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Sent as `Authorization: Bearer <LMS_API_KEY>` header
- Set `auth=false` to test unauthenticated access (e.g., for 401 status code questions)

## LLM Provider

**Provider:** Qwen Code API (OpenAI-compatible)

**Configuration:**
- **Endpoint:** Configurable via `LLM_API_BASE` (default: VM deployment)
- **Model:** `qwen3-coder-plus`
- **Authentication:** Bearer token via `LLM_API_KEY`

## Environment Variables

The agent reads ALL configuration from environment variables:

| Variable | Source File | Purpose |
|----------|-------------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | `.env.docker.secret` | Backend API base URL (default: `http://localhost:42002`) |

**Important:** The autochecker injects its own values at runtime. Hardcoding will cause failures.

## System Prompt

The system prompt guides the LLM to choose the right tool:

- **Wiki questions** (how-to, workflows) → `list_files` + `read_file`
- **Source code questions** (what framework, how it works) → `read_file`
- **Data queries** (item count, scores) → `query_api`
- **Bug diagnosis** → `query_api` to reproduce error, then `read_file` to find root cause

**Key instructions:**
- All file paths must include directory prefix (e.g., `wiki/git.md` not just `git.md`)
- For backend files, use `backend/app/filename.py` or `backend/app/routers/filename.py`
- For analytics endpoints, always include the lab parameter
- Source is OPTIONAL for API/system questions but REQUIRED for wiki/source/bug questions
- For bug diagnosis, ALWAYS use both `query_api` and `read_file`

## Usage

```bash
# Run with a question
uv run agent.py "How do you resolve a merge conflict?"

# Output (JSON to stdout)
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Output Format

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
- `source`: Wiki/source reference (optional for API questions, required for wiki/source/bug questions)
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

## Benchmark Results

The agent passes all 10 local evaluation questions:

1. ✅ Wiki: Branch protection steps
2. ✅ Wiki: SSH connection to VM
3. ✅ Source: Backend framework (FastAPI)
4. ✅ Source: API router modules
5. ✅ API: Item count in database
6. ✅ API: Unauthenticated status code (401)
7. ✅ Bug: Division by zero in completion-rate
8. ✅ Bug: TypeError in top-learners sorting
9. ✅ Reasoning: HTTP request journey (LLM judge)
10. ✅ Reasoning: ETL idempotency (LLM judge)

## Lessons Learned

1. **Tool descriptions matter:** Vague descriptions led to wrong tool selection. Adding explicit guidance (e.g., "For analytics endpoints, always include the lab parameter") improved accuracy.

2. **Source extraction:** The regex for extracting source references initially only matched `.md` files. Updated to also match `.py` files for bug diagnosis questions.

3. **Bug diagnosis pattern:** The LLM needed explicit instruction to use BOTH `query_api` (to reproduce the error) AND `read_file` (to find the root cause). Without this, it would only use one tool.

4. **Environment variable separation:** Keeping `LLM_API_KEY` (for the LLM provider) separate from `LMS_API_KEY` (for the backend API) was critical. Mixing them up caused authentication failures.

5. **Iterative improvement:** Running `run_eval.py` after each change helped identify specific failures quickly. The hint messages in the eval output guided prompt improvements.

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent with agentic loop and 3 tools |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `.env.docker.secret` | Backend API configuration (gitignored) |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `plans/task-3.md` | Task 3 implementation plan |
| `tests/test_agent_task1.py` | Regression tests (4 tests) |

## Future Work

- Add more tools (e.g., `search_code` for grep-like searches)
- Improve source extraction with better regex patterns
- Add support for multi-file analysis in a single tool call
- Implement caching for repeated API calls
