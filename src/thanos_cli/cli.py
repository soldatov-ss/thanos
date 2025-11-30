"""Console script for thanos_cli."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .snap import snap

app = typer.Typer(
    name="thanos",
    help="🫰 Thanos - Eliminate half of all files with a snap.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.command(name="snap")
def snap_command(
    directory: Annotated[
        str,
        typer.Argument(
            help="Target directory (default: current directory)",
        ),
    ] = ".",
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Include subdirectories",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Preview without deleting",
        ),
    ] = False,
    seed: Annotated[
        Optional[int],
        typer.Option(
            "--seed",
            "-s",
            help="Random seed for reproducibility",
        ),
    ] = None,
    no_protect: Annotated[
        bool,
        typer.Option(
            "--no-protect",
            help="Disable all protections (DANGEROUS!)",
        ),
    ] = False,
):
    """
    🫰 Eliminate half of all files with a snap.

    Examples:

      # Preview in current directory
      thanos snap -d

      # Snap specific directory
      thanos snap test_env/ -d

      # Recursive with seed
      thanos snap -r --seed 42
    """
    try:
        snap(directory, recursive, dry_run, seed, no_protect)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def init(
    directory: Annotated[
        str,
        typer.Argument(
            help="Directory to initialize (default: current)",
        ),
    ] = ".",
):
    """
    📝 Create example .thanosignore and .thanosrc.json files.
    """
    base_path = Path(directory)

    # Create .thanosignore
    thanosignore_path = base_path / ".thanosignore"
    if not thanosignore_path.exists():
        thanosignore_content = """# Thanos Ignore File
# Patterns listed here will be protected from elimination

# The Black Hole Prevention
# (Large folders that usually absorb all damage if not ignored)
node_modules/**
venv/**
.venv/**
__pycache__/**

# Important directories
important/**
backup/**
docs/**

# Database files
*.db
*.sqlite

# System & Config
.env
.git/**
.vscode/**
.idea/**

# Important data files
*-important.*
*-backup.*
"""
        thanosignore_path.write_text(thanosignore_content)
        console.print(f"[green]✓[/green] Created [bold]{thanosignore_path}[/bold]")
    else:
        console.print(f"[yellow]⚠️[/yellow]  {thanosignore_path} already exists")

    # Create .thanosrc.json
    thanosrc_path = base_path / ".thanosrc.json"
    if not thanosrc_path.exists():
        thanosrc_content = {
            "weights": {
                "by_extension": {
                    ".log": 0.9,
                    ".tmp": 0.95,
                    ".cache": 0.95,
                    ".bak": 0.8,
                    ".old": 0.8,
                    ".py": 0.3,
                    ".js": 0.3,
                    ".db": 0.1,
                    ".json": 0.2,
                }
            }
        }
        thanosrc_path.write_text(json.dumps(thanosrc_content, indent=2))
        console.print(f"[green]✓[/green] Created [bold]{thanosrc_path}[/bold]")
    else:
        console.print(f"[yellow]⚠️[/yellow]  {thanosrc_path} already exists")

    console.print()
    console.print(
        Panel(
            "[bold green]✨ Initialization complete![/bold green]\n\n"
            "Edit these files to customize:\n"
            f"  • [cyan]{thanosignore_path}[/cyan]\n"
            f"  • [cyan]{thanosrc_path}[/cyan]\n\n"
            "[dim]Run 'thanos snap -d' to test your configuration.[/dim]",
            border_style="green",
        )
    )


@app.callback(invoke_without_command=True)
def default_callback(ctx: typer.Context):
    """
    Default behavior when no command is specified.
    """
    if ctx.invoked_subcommand is None:
        # Show help by default
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
