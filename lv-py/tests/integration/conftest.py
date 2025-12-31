"""
Pytest fixtures for integration tests with Docker Compose.

Provides Docker services lifecycle management and test utilities.
"""

import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def logstash_samples_dir(test_data_dir: Path) -> Path:
    """Return path to Logstash sample configurations."""
    return test_data_dir / "logstash"


@pytest.fixture(scope="session")
def vector_samples_dir(test_data_dir: Path) -> Path:
    """Return path to Vector sample configurations."""
    return test_data_dir / "vector"


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Return temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def integration_test_dir() -> Path:
    """Return the integration test directory path."""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def docker_compose_file(integration_test_dir: Path) -> Path:
    """Return the docker-compose.yml file path."""
    return integration_test_dir / "docker-compose.yml"


@pytest.fixture(scope="session")
def docker_services(docker_compose_file: Path, integration_test_dir: Path) -> Generator:
    """
    Start Docker Compose services for integration testing.

    Yields when services are healthy, cleans up on teardown.
    """
    # Start services
    subprocess.run(
        ["docker-compose", "-f", str(docker_compose_file), "up", "-d"],
        cwd=integration_test_dir,
        check=True,
        capture_output=True,
    )

    # Wait for services to be healthy
    max_wait = 60  # seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        result = subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "ps"],
            cwd=integration_test_dir,
            capture_output=True,
            text=True,
        )

        # Check if all services are healthy
        if "Up (healthy)" in result.stdout:
            break

        time.sleep(2)
    else:
        # Timeout - dump logs and fail
        subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "logs"],
            cwd=integration_test_dir,
        )
        raise RuntimeError("Docker services failed to become healthy within timeout")

    # Additional wait for services to fully initialize
    time.sleep(5)

    yield

    # Cleanup: stop and remove containers
    subprocess.run(
        ["docker-compose", "-f", str(docker_compose_file), "down", "-v"],
        cwd=integration_test_dir,
        check=False,  # Don't fail if cleanup has issues
    )


@pytest.fixture(scope="function")
def clean_output_dirs(integration_test_dir: Path):
    """Clean output directories before each test."""
    logstash_output = integration_test_dir / "output" / "logstash"
    vector_output = integration_test_dir / "output" / "vector"

    # Create directories if they don't exist
    logstash_output.mkdir(parents=True, exist_ok=True)
    vector_output.mkdir(parents=True, exist_ok=True)

    # Clean existing files
    for output_file in logstash_output.glob("*"):
        if output_file.is_file():
            output_file.unlink()

    for output_file in vector_output.glob("*"):
        if output_file.is_file():
            output_file.unlink()

    yield


def wait_for_file_content(file_path: Path, min_size: int = 10, timeout: int = 30) -> bool:
    """
    Wait for a file to exist and have minimum content.

    Args:
        file_path: Path to the file to wait for
        min_size: Minimum file size in bytes
        timeout: Maximum time to wait in seconds

    Returns:
        True if file meets criteria, False on timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if file_path.exists() and file_path.stat().st_size >= min_size:
            return True
        time.sleep(0.5)

    return False


def get_container_logs(container_name: str, integration_test_dir: Path) -> str:
    """
    Get logs from a Docker container.

    Args:
        container_name: Name of the container
        integration_test_dir: Integration test directory

    Returns:
        Container logs as string
    """
    result = subprocess.run(
        ["docker", "logs", container_name],
        cwd=integration_test_dir,
        capture_output=True,
        text=True,
    )

    return result.stdout + result.stderr
