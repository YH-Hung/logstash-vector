"""Vector configuration validation utilities."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def validate_vector_config(config_path: Path, skip_if_missing: bool = False) -> tuple[bool, str]:
    """
    Validate Vector TOML config using Vector CLI.

    Args:
        config_path: Path to Vector .toml file
        skip_if_missing: If True, skip validation when Vector CLI not found (returns True)
                        If False, fail validation when Vector CLI not found (returns False)

    Returns:
        Tuple of (is_valid, error_message)

    Note:
        Vector CLI location can be customized with VECTOR_BIN environment variable
    """
    if not config_path.exists():
        return (False, f"Config file not found: {config_path}")

    # Check if vector command is available (support VECTOR_BIN env var)
    vector_bin = os.environ.get("VECTOR_BIN") or shutil.which("vector")
    if not vector_bin:
        warning_msg = "Vector CLI not found - validation skipped. Install Vector or set VECTOR_BIN environment variable."
        # Print warning to stderr so user sees it
        print(f"WARNING: {warning_msg}", file=sys.stderr)

        if skip_if_missing:
            # Skip validation mode (for --no-validate flag)
            return (True, warning_msg)
        else:
            # Fail validation mode (for --validate flag, which is default)
            return (False, f"Vector CLI not found. Cannot validate config. Install Vector from https://vector.dev/docs/setup/installation/ or use --no-validate to skip validation.")

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
