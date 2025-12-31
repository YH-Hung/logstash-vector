"""Vector configuration validation utilities."""

import shutil
import subprocess
from pathlib import Path


def validate_vector_config(config_path: Path) -> tuple[bool, str]:
    """
    Validate Vector TOML config using Vector CLI.

    Args:
        config_path: Path to Vector .toml file

    Returns:
        Tuple of (is_valid, error_message)

    Note:
        If Vector CLI is not found, returns (True, "Vector CLI not found - skipping validation")
    """
    if not config_path.exists():
        return (False, f"Config file not found: {config_path}")

    # Check if vector command is available
    vector_bin = shutil.which("vector")
    if not vector_bin:
        # Vector not installed - skip validation but don't fail
        return (True, "Vector CLI not found - skipping validation")

    try:
        # Run vector validate command
        result = subprocess.run(
            [vector_bin, "validate", str(config_path)],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        if result.returncode == 0:
            return (True, "")
        else:
            # Validation failed - return error message
            error_msg = result.stderr or result.stdout or "Unknown validation error"
            return (False, error_msg.strip())

    except subprocess.TimeoutExpired:
        return (False, "Vector validation timed out after 30 seconds")
    except Exception as e:
        return (False, f"Validation error: {str(e)}")
