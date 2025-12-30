"""File discovery and operations utilities."""

from pathlib import Path


def find_conf_files(directory: Path) -> list[Path]:
    """
    Find all .conf files in a directory.

    Args:
        directory: Directory to search

    Returns:
        List of .conf file paths

    TODO: Implement proper file discovery
    - Recursively search directory
    - Filter for .conf extension
    - Handle permissions errors gracefully
    - Sort by filename
    """
    if not directory.exists():
        raise ValueError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # Placeholder
    return list(directory.glob("*.conf"))
