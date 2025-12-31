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
    from rich.table import Table

    from lv_py.api import migrate_directory

    console.print(f"[bold cyan]Logstash to Vector Migration Tool[/bold cyan]")
    console.print(f"Source directory: [yellow]{directory}[/yellow]")
    console.print(f"Mode: [yellow]{'DRY RUN' if dry_run else 'LIVE'}[/yellow]")
    console.print()

    # Perform migration
    try:
        result = migrate_directory(directory=directory, output_dir=output_dir, dry_run=dry_run)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    if result.total_files == 0:
        console.print("[yellow]No .conf files found in directory[/yellow]")
        return

    console.print(f"Found [green]{result.total_files}[/green] configuration file(s)")
    console.print()

    # Display results based on mode
    if dry_run:
        # Dry-run mode: show preview
        console.print("[bold cyan]Migration Preview[/bold cyan]")
        console.print()

        for preview in result.previews:
            console.print(f"[bold]{preview.source_file.name}[/bold] → [bold]{preview.target_file.name}[/bold]")
            console.print(f"  Estimated size: {preview.estimated_size} bytes")

            if preview.transformations:
                console.print(f"  Transformations:")
                for transform in preview.transformations:
                    console.print(f"    • {transform.logstash_plugin} → {transform.vector_component}")
                    if transform.notes:
                        console.print(f"      {transform.notes}")

            if preview.unsupported_plugins:
                console.print(f"  [yellow]⚠  {len(preview.unsupported_plugins)} unsupported plugin(s)[/yellow]")

            if preview.notes:
                console.print(f"  [yellow]{preview.notes}[/yellow]")

            console.print()

        console.print("[bold]Summary[/bold]")
        summary_table = Table(show_header=False)
        summary_table.add_row("Total files", str(result.total_files))
        summary_table.add_row("[green]Would succeed[/green]", str(result.successful))
        summary_table.add_row("[red]Would fail[/red]", str(result.failed))
        console.print(summary_table)

        console.print()
        console.print("[cyan]Run without --dry-run to write files[/cyan]")

    else:
        # Live mode: show summary
        console.print("[bold]Migration Summary[/bold]")

        summary_table = Table(show_header=False)
        summary_table.add_row("Total files", str(result.total_files))
        summary_table.add_row("[green]Successful[/green]", str(result.successful))
        summary_table.add_row("[red]Failed[/red]", str(result.failed))
        console.print(summary_table)

        # Write combined migration report
        if report or result.reports:
            report_path = report or directory / "migration-report.md"

            combined_report_lines = ["# Combined Migration Report\n"]
            for migration_report in result.reports:
                combined_report_lines.append(migration_report.to_markdown())
                combined_report_lines.append("\n---\n")

            report_path.write_text("\n".join(combined_report_lines))
            console.print(f"\n[cyan]Migration report:[/cyan] {report_path}")

    # Exit with appropriate code
    if result.failed > 0:
        raise SystemExit(1)


@main.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def validate(files: tuple[Path, ...]) -> None:
    """Validate Vector TOML files."""
    from lv_py.api import validate_configs

    if not files:
        # Default to all .toml files in current directory
        files = tuple(Path.cwd().glob("*.toml"))

    console.print(f"[bold]Validating {len(files)} file(s)[/bold]")

    results = validate_configs(list(files))

    for validation_result in results.validation_results:
        if validation_result.is_valid:
            console.print(f"[green]✓[/green] {validation_result.file_path}")
        else:
            console.print(f"[red]✗[/red] {validation_result.file_path}")
            console.print(f"  [red]{validation_result.error_message}[/red]")

    if not results.all_valid:
        raise SystemExit(1)


@main.command()
@click.argument("logstash_conf", type=click.Path(exists=True, path_type=Path))
@click.argument("vector_toml", type=click.Path(exists=True, path_type=Path))
def diff(logstash_conf: Path, vector_toml: Path) -> None:
    """Compare Logstash and Vector configurations."""
    from lv_py.api import diff_configs

    console.print(f"[bold]Comparing:[/bold] {logstash_conf.name} ↔ {vector_toml.name}")
    console.print()

    try:
        result = diff_configs(logstash_conf, vector_toml)

        # Display formatted output
        formatted_output = result.to_formatted_output()
        console.print(formatted_output)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
