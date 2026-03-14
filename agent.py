#!/usr/bin/env python3
"""Agent CLI - Documentation agent with tools and agentic loop.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    Logs to stderr.
"""

import json
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Load LLM configuration from .env.agent.secret."""

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
    )

    llm_api_key: str
    llm_api_base: str
    llm_model: str = "qwen3-coder-plus"


# Project root for path security
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def validate_path(path: str) -> Path:
    """Validate and resolve path, preventing traversal attacks.

    Args:
        path: Relative path from project root.

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If path is invalid or outside project root.
    """
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


def read_file(path: str) -> str:
    """Read a file from the project repository.

    Args:
        path: Relative path from project root.

    Returns:
        File contents as string, or error message.
    """
    try:
        validated_path = validate_path(path)
        if not validated_path.exists():
            return f"Error: File not found: {path}"
        if not validated_path.is_file():
            return f"Error: Not a file: {path}"
        content = validated_path.read_text(encoding="utf-8")
        print(f"  [read_file] Read {path} ({len(content)} chars)", file=sys.stderr)
        return content
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path.

    Args:
        path: Relative directory path from project root.

    Returns:
        Newline-separated list of entries, or error message.
    """
    try:
        validated_path = validate_path(path)
        if not validated_path.exists():
            return f"Error: Directory not found: {path}"
        if not validated_path.is_dir():
            return f"Error: Not a directory: {path}"
        entries = sorted([e.name for e in validated_path.iterdir()])
        result = "\n".join(entries)
        print(f"  [list_files] Listed {path} ({len(entries)} entries)", file=sys.stderr)
        return result
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read specific files after discovering them with list_files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
}

SYSTEM_PROMPT = """You are a documentation assistant. You have access to two tools:
- list_files: List files in a directory
- read_file: Read contents of a file

When answering questions:
1. First use list_files to find relevant documentation files (e.g., path: "wiki")
2. Use read_file to read specific files (e.g., path: "wiki/git-workflow.md")
3. Find the exact section that answers the question
4. Include the source as "path/to/file.md#section-anchor" format
5. Only give final answer after gathering enough information

IMPORTANT: All paths must include the directory prefix. For wiki files, use "wiki/filename.md" not just "filename.md".

If you don't find the answer in the documentation, say so honestly.
Always include the source reference in your final answer."""


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """Execute a tool and return the result.

    Args:
        tool_name: Name of the tool to execute.
        args: Tool arguments.

    Returns:
        Tool result as string.
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {tool_name}"

    func = TOOL_FUNCTIONS[tool_name]
    try:
        return func(**args)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def call_llm(
    messages: list[dict[str, Any]],
    settings: AgentSettings,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the LLM API and return the response.

    Args:
        messages: List of message dicts.
        settings: LLM configuration.
        tools: Optional list of tool definitions.

    Returns:
        Parsed LLM response.
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.7,
    }
    if tools:
        payload["tools"] = tools

    print(f"Calling LLM at {url}...", file=sys.stderr)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    print(f"LLM response received.", file=sys.stderr)
    return data


def run_agentic_loop(question: str, settings: AgentSettings) -> dict[str, Any]:
    """Run the agentic loop: LLM → tool calls → execute → repeat.

    Args:
        question: User's question.
        settings: LLM configuration.

    Returns:
        Result dict with answer, source, and tool_calls.
    """
    # Initialize messages with system prompt and user question
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Track all tool calls
    all_tool_calls: list[dict[str, Any]] = []
    tool_call_count = 0

    print(f"Question: {question}", file=sys.stderr)

    # Agentic loop
    while tool_call_count < MAX_TOOL_CALLS:
        # Call LLM with tools
        response = call_llm(messages, settings, tools=TOOLS)

        # Get the assistant message
        assistant_message = response["choices"][0]["message"]

        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])

        if not tool_calls:
            # No tool calls - final answer
            print(f"Final answer received.", file=sys.stderr)
            answer = assistant_message.get("content", "")

            # Extract source from answer if possible (look for file.md#anchor pattern)
            source = ""
            import re
            source_match = re.search(r'(\w+/[\w-]+\.md(?:#[\w-]+)?)', answer)
            if source_match:
                source = source_match.group(1)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": all_tool_calls,
            }

        # Execute tool calls
        for tool_call in tool_calls:
            if tool_call_count >= MAX_TOOL_CALLS:
                break

            tool_call_id = tool_call.get("id", f"call_{tool_call_count}")
            function = tool_call.get("function", {})
            tool_name = function.get("name", "unknown")

            # Parse arguments
            try:
                args = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            print(f"Executing tool: {tool_name} with args: {args}", file=sys.stderr)

            # Execute tool
            result = execute_tool(tool_name, args)

            # Record tool call
            tool_call_record = {
                "tool": tool_name,
                "args": args,
                "result": result,
            }
            all_tool_calls.append(tool_call_record)
            tool_call_count += 1

            # Add tool result to messages as user message with tool response
            # Some APIs prefer this format over the "tool" role
            messages.append({
                "role": "user",
                "content": f"[Tool result from {tool_name}]: {result}",
            })

        # Add assistant message to history (without tool_calls to avoid confusion)
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content", ""),
        })

    # Max tool calls reached
    print(f"Max tool calls ({MAX_TOOL_CALLS}) reached.", file=sys.stderr)

    # Try to extract answer from last assistant message
    last_answer = assistant_message.get("content", "Maximum tool calls reached without a final answer.")

    # Extract source if possible
    source = ""
    import re
    source_match = re.search(r'(\w+/[\w-]+\.md(?:#[\w-]+)?)', last_answer)
    if source_match:
        source = source_match.group(1)

    return {
        "answer": last_answer,
        "source": source,
        "tool_calls": all_tool_calls,
    }


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    # Parse command-line arguments
    if len(sys.argv) < 2:
        print("Error: No question provided.", file=sys.stderr)
        print("Usage: uv run agent.py \"Your question\"", file=sys.stderr)
        return 1

    question = sys.argv[1]

    # Load settings
    try:
        settings = AgentSettings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    # Run agentic loop
    try:
        result = run_agentic_loop(question, settings)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        result = {
            "answer": f"Error: {e}",
            "source": "",
            "tool_calls": [],
        }

    # Output JSON to stdout
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
