#!/usr/bin/env python3
"""Agent CLI - Calls an LLM and returns a structured JSON answer.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    Logs to stderr.
"""

import json
import sys
from pathlib import Path

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


def call_lllm(question: str, settings: AgentSettings) -> str:
    """Call the LLM API and return the answer.

    Args:
        question: The user's question.
        settings: LLM configuration.

    Returns:
        The LLM's answer as a string.
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]
    print(f"LLM response received.", file=sys.stderr)
    return answer


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
    print(f"Question: {question}", file=sys.stderr)

    # Load settings
    try:
        settings = AgentSettings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    # Call LLM and format response
    try:
        answer = call_lllm(question, settings)
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        answer = f"Error: {e}"

    # Build output structure
    result = {
        "answer": answer,
        "tool_calls": [],
    }

    # Output JSON to stdout
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
