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
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

    from lv_py.migration import migrate_config
    from lv_py.utils.file_utils import find_conf_files

    console.print(f"[bold cyan]Logstash to Vector Migration Tool[/bold cyan]")
    console.print(f"Source directory: [yellow]{directory}[/yellow]")
    console.print(f"Mode: [yellow]{'DRY RUN' if dry_run else 'LIVE'}[/yellow]")
    console.print()

    # Find all .conf files
    try:
        conf_files = find_conf_files(directory)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    if not conf_files:
        console.print("[yellow]No .conf files found in directory[/yellow]")
        return

    console.print(f"Found [green]{len(conf_files)}[/green] configuration file(s)")
    console.print()

    # Track overall results
    total_files = len(conf_files)
    successful_migrations = 0
    failed_migrations = 0
    all_reports = []

    # Process each file
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Migrating...", total=total_files)

        for conf_file in conf_files:
            progress.update(task, description=f"Processing {conf_file.name}...")

            # Determine output path
            if output_dir:
                output_path = output_dir / conf_file.with_suffix(".toml").name
            else:
                output_path = conf_file.with_suffix(".toml")

            # Migrate
            vector_config, migration_report = migrate_config(conf_file, output_path)
            all_reports.append(migration_report)

            if vector_config and not migration_report.errors:
                # Success
                if not dry_run:
                    # Write TOML file
                    toml_content = vector_config.to_toml()
                    output_path.write_text(toml_content)

                    # Validate if requested
                    if validate:
                        is_valid, error_msg = vector_config.validate_syntax()
                        if not is_valid and verbose:
                            console.print(f"[yellow]Validation warning for {conf_file.name}:[/yellow] {error_msg}")

                successful_migrations += 1
                if verbose:
                    console.print(f"[green]✓[/green] {conf_file.name} → {output_path.name}")
            else:
                # Failed
                failed_migrations += 1
                if verbose:
                    console.print(f"[red]✗[/red] {conf_file.name} - {len(migration_report.errors)} error(s)")

            progress.advance(task)

    # Display summary
    console.print()
    console.print("[bold]Migration Summary[/bold]")

    summary_table = Table(show_header=False)
    summary_table.add_row("Total files", str(total_files))
    summary_table.add_row("[green]Successful[/green]", str(successful_migrations))
    summary_table.add_row("[red]Failed[/red]", str(failed_migrations))
    console.print(summary_table)

    # Write combined migration report
    if report or not dry_run:
        report_path = report or directory / "migration-report.md"

        combined_report_lines = ["# Combined Migration Report\n"]
        for migration_report in all_reports:
            combined_report_lines.append(migration_report.to_markdown())
            combined_report_lines.append("\n---\n")

        if not dry_run:
            report_path.write_text("\n".join(combined_report_lines))
            console.print(f"\n[cyan]Migration report:[/cyan] {report_path}")

    # Exit with appropriate code
    if failed_migrations > 0:
        raise SystemExit(1)


@main.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def validate(files: tuple[Path, ...]) -> None:
    """Validate Vector TOML files."""
    from lv_py.utils.validation import validate_vector_config

    console.print(f"[bold]Validating {len(files)} file(s)[/bold]")

    all_valid = True
    for file_path in files:
        is_valid, error_msg = validate_vector_config(file_path)

        if is_valid:
            console.print(f"[green]✓[/green] {file_path}")
        else:
            console.print(f"[red]✗[/red] {file_path}")
            console.print(f"  [red]{error_msg}[/red]")
            all_valid = False

    if not all_valid:
        raise SystemExit(1)


@main.command()
@click.argument("logstash_conf", type=click.Path(exists=True, path_type=Path))
@click.argument("vector_toml", type=click.Path(exists=True, path_type=Path))
def diff(logstash_conf: Path, vector_toml: Path) -> None:
    """Compare Logstash and Vector configurations."""
    console.print(f"[bold]Comparing:[/bold] {logstash_conf} ↔ {vector_toml}")

    # TODO: Implement diff logic (US3)
    console.print("[yellow]Diff command coming in User Story 3[/yellow]")


if __name__ == "__main__":
    main()
