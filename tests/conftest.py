"""Pytest fixtures for Vector configuration testing."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_log_path(project_root) -> Path:
    """Path to sample log file."""
    return project_root / "sample" / "web_hmib_1.log"


@pytest.fixture
def fixtures_dir(project_root) -> Path:
    """Path to test fixtures directory."""
    fixtures = project_root / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    return fixtures


@pytest.fixture
def sample_logs_dir(fixtures_dir) -> Path:
    """Path to sample logs directory."""
    logs_dir = fixtures_dir / "sample_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


@pytest.fixture
def expected_outputs_dir(fixtures_dir) -> Path:
    """Path to expected outputs directory."""
    outputs_dir = fixtures_dir / "expected_outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir


@pytest.fixture
def vector_binary() -> str:
    """Check if Vector is installed and return path."""
    # Check if vector is in PATH
    result = subprocess.run(
        ["which", "vector"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return "vector"
    
    # Check common installation paths
    common_paths = [
        "/usr/local/bin/vector",
        "/usr/bin/vector",
        os.path.expanduser("~/.cargo/bin/vector"),
    ]
    
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    pytest.skip("Vector binary not found. Please install Vector.")


@pytest.fixture
def temp_config_file(tmp_path) -> Path:
    """Create a temporary Vector config file path."""
    return tmp_path / "vector.toml"


@pytest.fixture
def temp_log_file(tmp_path) -> Path:
    """Create a temporary log file path."""
    return tmp_path / "test.log"


def run_vector(
    config_path: Path,
    input_file: Path = None,
    stdin_data: str = None,
    timeout: int = 10
) -> tuple[str, str, int]:
    """
    Run Vector with the given config and return stdout, stderr, and return code.
    
    Args:
        config_path: Path to Vector config file
        input_file: Optional path to input log file
        stdin_data: Optional stdin data to pipe to Vector
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    cmd = ["vector", "--config", str(config_path)]
    
    if input_file:
        # Use file source - Vector will read from the file
        # We'll configure the source in the config file itself
        pass
    
    try:
        if stdin_data:
            result = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        pytest.fail(f"Vector command timed out after {timeout} seconds")
    except FileNotFoundError:
        pytest.skip("Vector binary not found")


@pytest.fixture
def vector_output(vector_binary, temp_config_file, temp_log_file):
    """
    Run Vector and return output.
    
    This fixture creates a function that can be called with config content
    and optional input data.
    """
    def _run_vector(config_content: str, input_data: str = None) -> tuple[str, str, int]:
        # Write config to temp file
        temp_config_file.write_text(config_content)
        
        # If input_data is provided, write to temp log file
        if input_data:
            temp_log_file.write_text(input_data)
        
        # Run vector
        return run_vector(temp_config_file, temp_log_file if input_data else None)
    
    return _run_vector


def parse_vector_jsonl_output(output: str) -> List[Dict[str, Any]]:
    """
    Parse Vector's JSONL output into a list of dictionaries.
    
    Args:
        output: Vector stdout containing JSON lines
        
    Returns:
        List of parsed event dictionaries
    """
    events = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            events.append(event)
        except json.JSONDecodeError:
            # Skip non-JSON lines (e.g., Vector log messages)
            continue
    return events


@pytest.fixture
def parsed_output(vector_output):
    """
    Parse Vector JSON output.
    
    Returns a function that runs Vector and parses the output.
    """
    def _parse(config_content: str, input_data: str = None) -> List[Dict[str, Any]]:
        stdout, stderr, return_code = vector_output(config_content, input_data)
        if return_code != 0:
            pytest.fail(f"Vector failed with return code {return_code}. stderr: {stderr}")
        return parse_vector_jsonl_output(stdout)
    
    return _parse


@pytest.fixture
def vector_config_path(project_root) -> Path:
    """Path to main Vector configuration file."""
    config_path = project_root / "vector" / "vector.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    return config_path
