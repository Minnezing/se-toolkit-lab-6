# Task 2 Plan: The Documentation Agent

## Overview

Extend the agent from Task 1 with tools (`read_file`, `list_files`) and an agentic loop that allows the LLM to iteratively gather information before answering.

## Tool Design

### read_file

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git.md`)

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:**
- Validate path does not contain `..` (path traversal)
- Ensure resolved path is within project root using `Path.resolve()`
- Reject absolute paths

### list_files

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated list of entries (files and directories).

**Security:**
- Same path validation as `read_file`
- Only list directories, not files

## Tool Schema (OpenAI Function Calling)

Tools will be defined as JSON schemas in the LLM request:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

## Agentic Loop

```
1. Build messages list with system prompt + user question
2. Send to LLM with tool definitions
3. Parse response:
   - If tool_calls present:
     a. Execute each tool
     b. Append tool results to messages
     c. Loop back to step 2 (max 10 iterations)
   - If no tool_calls:
     a. Extract final answer
     b. Determine source from tool_calls history
     c. Output JSON and exit
```

**Max iterations:** 10 tool calls per question

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover relevant wiki files
2. Use `read_file` to read specific files
3. Find the answer in the file contents
4. Include the source reference (file path + section anchor if applicable)
5. Only respond with final answer when confident

Example:
```
You are a documentation assistant. You have access to two tools:
- list_files: List files in a directory
- read_file: Read contents of a file

When answering questions:
1. First use list_files to find relevant documentation
2. Use read_file to read specific files
3. Find the exact section that answers the question
4. Include the source as "path/to/file.md#section-anchor"
5. Only give final answer after gathering enough information
```

## Output Format

```json
{
  "answer": "<final answer from LLM>",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Path Security Implementation

```python
def validate_path(path: str, project_root: Path) -> Path:
    """Validate and resolve path, preventing traversal attacks."""
    # Reject absolute paths
    if Path(path).is_absolute():
        raise ValueError("Absolute paths not allowed")
    
    # Reject path traversal
    if ".." in path:
        raise ValueError("Path traversal not allowed")
    
    # Resolve and verify within project root
    full_path = (project_root / path).resolve()
    if not str(full_path).startswith(str(project_root.resolve())):
        raise ValueError("Path outside project root")
    
    return full_path
```

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `plans/task-2.md` | Create | This plan |
| `agent.py` | Update | Add tools, agentic loop, new output format |
| `AGENT.md` | Update | Document tools and loop |
| `tests/test_agent_task1.py` | Update | Add 2 new tests for Task 2 |

## Testing Strategy

**Test 1:** Question requiring `read_file`
- Question: "How do you resolve a merge conflict?"
- Verify: `read_file` in tool_calls, `wiki/git-workflow.md` in source

**Test 2:** Question requiring `list_files`
- Question: "What files are in the wiki?"
- Verify: `list_files` in tool_calls

## Dependencies

Already available from Task 1:
- `httpx` - for API calls
- `pydantic-settings` - for config
- `pytest` - for testing
