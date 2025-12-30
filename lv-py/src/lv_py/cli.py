"""CLI interface for lv-py migration tool."""

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Logstash to Vector configuration migration tool."""
    pass


@main.command()
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", "-n", is_flag=True, help="Preview migration without writing files")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.option("--report", "-r", type=click.Path(path_type=Path), help="Migration report path")
@click.option("--validate/--no-validate", default=True, help="Validate with vector")
@click.option("--verbose", is_flag=True, help="Verbose output")
def migrate(
    directory: Path,
    dry_run: bool,
    output_dir: Path | None,
    report: Path | None,
    validate: bool,
    verbose: bool,
) -> None:
    """Migrate Logstash configs to Vector format."""
    console.print(f"[bold]Migrating Logstash configs from:[/bold] {directory}")
    console.print(f"Dry run: {dry_run}")

    # TODO: Implement migration logic
    # 1. Find all .conf files in directory
    # 2. Parse each file
    # 3. Transform to Vector config
    # 4. Generate TOML
    # 5. Write files (unless dry-run)
    # 6. Validate with Vector (if enabled)
    # 7. Generate migration report

    console.print("[yellow]TODO: Migration logic not yet implemented[/yellow]")


@main.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def validate(files: tuple[Path, ...]) -> None:
    """Validate Vector TOML files."""
    console.print(f"[bold]Validating {len(files)} file(s)[/bold]")

    # TODO: Implement validation logic
    console.print("[yellow]TODO: Validation logic not yet implemented[/yellow]")


@main.command()
@click.argument("logstash_conf", type=click.Path(exists=True, path_type=Path))
@click.argument("vector_toml", type=click.Path(exists=True, path_type=Path))
def diff(logstash_conf: Path, vector_toml: Path) -> None:
    """Compare Logstash and Vector configurations."""
    console.print(f"[bold]Comparing:[/bold] {logstash_conf} ↔ {vector_toml}")

    # TODO: Implement diff logic
    console.print("[yellow]TODO: Diff logic not yet implemented[/yellow]")


if __name__ == "__main__":
    main()
