import random
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_default_protected_patterns, load_thanosignore, load_thanosrc
from .protection import should_protect_file
from .utils import get_files
from .weights import calculate_file_weight, weighted_random_sample

console = Console()


def snap(
    directory: str = ".",
    recursive: bool = False,
    dry_run: bool = False,
    seed: Optional[int] = None,
    no_protect: bool = False,
):
    """Execute the snap operation."""

    # Header
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]🫰 THE SNAP[/bold yellow]\n[dim]Perfectly balanced, as all things should be[/dim]",
            border_style="yellow",
        )
    )
    console.print()

    if seed is not None:
        random.seed(seed)
        console.print(f"🎲 [cyan]Using random seed:[/cyan] [bold]{seed}[/bold]")

    # Load protection patterns
    protected_patterns = set()

    if not no_protect:
        ignore_patterns, ignore_file_path = load_thanosignore(directory)
        if ignore_patterns:
            protected_patterns.update(ignore_patterns)
            console.print(
                f"📋 [green]Loaded {len(ignore_patterns)} patterns from [bold]{ignore_file_path}[/bold][/green]"
            )
        else:
            protected_patterns.update(get_default_protected_patterns())
            console.print("🛡️  [green]Default protections enabled[/green]")
    else:
        console.print("⚠️  [bold red]WARNING: All file protections disabled![/bold red]")

    # Load configuration
    config, config_file_path = load_thanosrc(directory)
    weights_config = config.get("weights", {})
    use_weights = bool(weights_config)

    if use_weights:
        console.print(f"⚖️  [green]Weighted selection enabled from [bold]{config_file_path}[/bold][/green]")

    # Get all files
    all_files = get_files(directory, recursive)
    base_path = Path(directory).resolve()

    # Filter out protected files
    files = []
    protected_files = []

    for file in all_files:
        if not no_protect and should_protect_file(file, base_path, protected_patterns):
            protected_files.append(file)
        else:
            files.append(file)

    total_files = len(files)

    if total_files <= 1:
        console.print()
        console.print(
            Panel(
                "[yellow]No eligible files found.[/yellow]\nThe universe is empty (or fully protected).",
                border_style="yellow",
            )
        )
        return

    # Calculate elimination count
    files_to_eliminate = total_files // 2

    # Select files for elimination
    if use_weights:
        weights = [calculate_file_weight(f, weights_config) for f in files]
        eliminated = weighted_random_sample(files, weights, files_to_eliminate)
    else:
        eliminated = random.sample(files, files_to_eliminate)

    # Display balance assessment
    console.print()
    table = Table(title="📊 Balance Assessment", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", style="bold", justify="right")

    table.add_row("Total files found", str(len(all_files)))
    table.add_row("Protected files", f"[green]{len(protected_files)}[/green]")
    table.add_row("Eligible files", str(total_files))
    table.add_row("Files to eliminate", f"[red]{files_to_eliminate}[/red]")
    table.add_row("Survivors", f"[green]{total_files - files_to_eliminate}[/green]")

    console.print(table)
    console.print()

    # Dry run mode
    if dry_run:
        console.print(
            Panel("[bold yellow]🔍 DRY RUN MODE[/bold yellow]\nThese files would be eliminated:", border_style="yellow")
        )
        console.print()

        for file in eliminated[:20]:
            console.print(f"   [red]💀[/red] {file}")

        if len(eliminated) > 20:
            console.print(f"   [dim]... and {len(eliminated) - 20} more files[/dim]")

        if protected_files and len(protected_files) <= 10:
            console.print()
            console.print("[green]🛡️  Protected files:[/green]")
            for file in protected_files:
                console.print(f"   [green]✓[/green] {file}")

        console.print()
        console.print(
            Panel(
                "⚠️  [bold]This was a dry run. No files were harmed.[/bold]\n\n"
                f"💡 [dim]{'Use --seed <number> to get reproducible results' if seed is None else f'Run with --seed {seed} to delete these exact files'}[/dim]",  # noqa: E501
                border_style="green",
            )
        )
        return

    # Show files to be eliminated
    console.print(Panel("[bold red]📋 Files selected for elimination:[/bold red]", border_style="red"))
    console.print()

    for file in eliminated[:20]:
        console.print(f"   [red]💀[/red] {file}")

    if len(eliminated) > 20:
        console.print(f"   [dim]... and {len(eliminated) - 20} more files[/dim]")

    console.print()
    console.print(
        Panel(
            "⚠️  [bold red]WARNING: This will permanently delete the files listed above![/bold red]\n"
            "[yellow]There is no undo. Files will be gone forever.[/yellow]",
            border_style="red",
        )
    )
    console.print()

    # Confirmation
    confirm = console.input("[bold]Type 'snap' to proceed:[/bold] ")

    if confirm.lower() != "snap":
        console.print()
        console.print(Panel("[yellow]Snap cancelled.[/yellow]\nThe universe remains unchanged.", border_style="yellow"))
        return

    # Execute the snap
    console.print()
    console.print("[bold yellow]💥 Snapping...[/bold yellow]")
    console.print()

    eliminated_count = 0
    failed_count = 0

    with console.status("[bold yellow]Eliminating files...[/bold yellow]"):
        for file in eliminated:
            try:
                file.unlink()
                eliminated_count += 1
                console.print(f"   [green]✓[/green] Eliminated: [dim]{file}[/dim]")
            except Exception as e:
                failed_count += 1
                console.print(f"   [red]❌[/red] Failed: [dim]{file}[/dim] - {e}")

    # Final summary
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✨ The snap is complete.[/bold green]\n\n"
            f"[green]Eliminated:[/green] {eliminated_count} files\n"
            f"[red]Failed:[/red] {failed_count} files\n\n"
            f"[dim]Perfectly balanced, as all things should be.[/dim]",
            border_style="green",
        )
    )
