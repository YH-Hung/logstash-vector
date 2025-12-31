"""File discovery and operations utilities."""

from pathlib import Path


def find_conf_files(directory: Path) -> list[Path]:
    """
    Find all .conf files in a directory.

    Args:
        directory: Directory to search

    Returns:
        List of .conf file paths sorted by name

    Raises:
        ValueError: If directory doesn't exist or is not a directory
    """
    if not directory.exists():
        raise ValueError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    # Find all .conf files recursively
    conf_files = list(directory.rglob("*.conf"))

    # Sort by filename for consistent ordering
    return sorted(conf_files, key=lambda p: p.name)
