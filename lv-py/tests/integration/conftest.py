"""Pytest fixtures for integration tests."""

from pathlib import Path

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


# TODO: Add Docker Compose fixtures when integration tests are implemented
# @pytest.fixture(scope="session")
# def logstash_container():
#     """Start Logstash container for integration testing."""
#     pass
#
# @pytest.fixture(scope="session")
# def vector_container():
#     """Start Vector container for integration testing."""
#     pass
