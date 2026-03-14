"""Regression tests for agent.py (Task 1 and Task 2).

Tests verify that agent.py:
- Runs successfully with a question argument
- Outputs valid JSON to stdout
- Has required fields: answer, source, and tool_calls
- Uses tools correctly (read_file, list_files)
"""

import json
import subprocess
import sys


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields (Task 1)."""
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


def test_agent_uses_read_file_for_git_question():
    """Test that agent.py uses read_file tool for git merge conflict question (Task 2)."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict in git?"],
        capture_output=True,
        text=True,
        timeout=90,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")

    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # Check that read_file was used
    tool_names = [call.get("tool") for call in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected 'read_file' in tool_calls, got: {tool_names}"

    # Check that source references wiki/git.md or similar
    assert "wiki/" in output["source"] or "git" in output["source"].lower(), \
        f"Expected wiki/git reference in source, got: {output['source']}"


def test_agent_uses_list_files_for_directory_question():
    """Test that agent.py uses list_files tool for directory listing question (Task 2)."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki directory?"],
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

    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # Check that list_files was used
    tool_names = [call.get("tool") for call in output["tool_calls"]]
    assert "list_files" in tool_names, f"Expected 'list_files' in tool_calls, got: {tool_names}"

    # Check that answer contains file listings
    assert len(output["answer"]) > 50, "Answer should contain file listing"
