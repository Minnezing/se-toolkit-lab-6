"""Regression tests for agent.py (Task 1).

Tests verify that agent.py:
- Runs successfully with a question argument
- Outputs valid JSON to stdout
- Has required fields: answer (string) and tool_calls (empty list)
"""

import json
import subprocess
import sys


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    # Run agent with a simple question
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

    # Check required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"

    # Check field types
    assert isinstance(output["answer"], str), f"'answer' should be string, got {type(output['answer'])}"
    assert isinstance(output["tool_calls"], list), f"'tool_calls' should be list, got {type(output['tool_calls'])}"
    assert len(output["tool_calls"]) == 0, f"'tool_calls' should be empty, got {output['tool_calls']}"

    # Check answer is non-empty
    assert len(output["answer"]) > 0, "'answer' field is empty"


def test_agent_missing_argument():
    """Test that agent.py fails gracefully when no argument is provided."""
    result = subprocess.run(
        ["uv", "run", "agent.py"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should fail with non-zero exit code
    assert result.returncode != 0, "Agent should fail without argument"

    # Should print error to stderr
    assert "Error" in result.stderr or "Usage" in result.stderr, "Should print error or usage to stderr"
