import random
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from send2trash import send2trash

from .config import get_default_protected_patterns, load_thanosignore, load_thanosrc
from .protection import should_protect_file
from .utils import get_files
from .weights import calculate_file_weight, weighted_random_sample

console = Console()


def _print_header(percent: int, seed: Optional[int], use_trash: bool) -> None:
    """Render the command header and selected options."""
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]🫰 THE SNAP[/bold yellow]\n[dim]Perfectly balanced, as all things should be[/dim]",
            border_style="yellow",
        )
    )
    console.print()

    if percent != 50:
        console.print(f"🎯 [cyan]Custom elimination rate:[/cyan] [bold]{percent}%[/bold]")

    if seed is not None:
        console.print(f"🎲 [cyan]Using random seed:[/cyan] [bold]{seed}[/bold]")

    if use_trash:
        console.print("🗑️  [cyan]Trash mode enabled:[/cyan] Files will be moved to trash")


def _load_protected_patterns(directory: str, no_protect: bool) -> set[str]:
    """Load configured protection patterns."""
    protected_patterns: set[str] = set()

    if no_protect:
        console.print("⚠️  [bold red]WARNING: All file protections disabled![/bold red]")
        return protected_patterns

    ignore_patterns, ignore_file_path = load_thanosignore(directory)
    if ignore_patterns:
        protected_patterns.update(ignore_patterns)
        console.print(f"📋 [green]Loaded {len(ignore_patterns)} patterns from [bold]{ignore_file_path}[/bold][/green]")
        return protected_patterns

    protected_patterns.update(get_default_protected_patterns())
    console.print("🛡️  [green]Default protections enabled[/green]")
    return protected_patterns


def _split_files(
    all_files: list[Path], base_path: Path, no_protect: bool, protected_patterns: set[str]
) -> tuple[list[Path], list[Path]]:
    """Split files into eligible and protected groups."""
    files: list[Path] = []
    protected_files: list[Path] = []

    for file in all_files:
        if not no_protect and should_protect_file(file, base_path, protected_patterns):
            protected_files.append(file)
        else:
            files.append(file)

    return files, protected_files


def _get_elimination_count(total_files: int, percent: int) -> int:
    """Return the number of files to eliminate, or 0 if the snap would be a no-op."""
    if total_files < 1:
        return 0
    return int(total_files * percent / 100)


def _select_files(files: list[Path], weights_config: dict, files_to_eliminate: int, rng: random.Random) -> list[Path]:
    """Select files to eliminate, using configured weights when present."""
    if weights_config:
        weights = [calculate_file_weight(file, weights_config) for file in files]
        return weighted_random_sample(files, weights, files_to_eliminate, rng)
    return rng.sample(files, files_to_eliminate)


def _print_balance_assessment(
    all_files: list[Path], protected_files: list[Path], total_files: int, files_to_eliminate: int
) -> None:
    """Render the file counts table."""
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


def _print_dry_run(eliminated: list[Path], protected_files: list[Path], use_trash: bool, seed: Optional[int]) -> None:
    """Render dry-run results."""
    action = "moved to trash" if use_trash else "eliminated"
    console.print(
        Panel(f"[bold yellow]🔍 DRY RUN MODE[/bold yellow]\nThese files would be {action}:", border_style="yellow")
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

    seed_msg = "Use --seed <number> to get reproducible results"
    if seed is not None:
        seed_msg = f"Run with --seed {seed} to delete these exact files"

    console.print()
    console.print(
        Panel(
            f"⚠️  [bold]This was a dry run. No files were harmed.[/bold]\n\n💡 [dim]{seed_msg}[/dim]",
            border_style="green",
        )
    )


def _print_selected_files(eliminated: list[Path], use_trash: bool) -> None:
    """Render the selected files and the warning panel."""
    action = "moved to trash" if use_trash else "elimination"
    console.print(Panel(f"[bold red]📋 Files selected for {action}:[/bold red]", border_style="red"))
    console.print()

    for file in eliminated[:20]:
        console.print(f"   [red]💀[/red] {file}")

    if len(eliminated) > 20:
        console.print(f"   [dim]... and {len(eliminated) - 20} more files[/dim]")

    console.print()

    if use_trash:
        console.print(
            Panel(
                "⚠️  [bold yellow]WARNING: This will move files to trash/recycle bin![/bold yellow]\n"
                "[cyan]Files can be restored from trash if needed.[/cyan]",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                "⚠️  [bold red]WARNING: This will permanently delete the files listed above![/bold red]\n"
                "[yellow]There is no undo. Files will be gone forever.[/yellow]",
                border_style="red",
            )
        )
    console.print()


def _execute_snap(eliminated: list[Path], use_trash: bool) -> None:
    """Delete files or move them to trash, then render the summary."""
    action_label = "Moving files to trash" if use_trash else "Eliminating files"
    status_style = "yellow"
    progress_message = "🗑️  Moving to trash..." if use_trash else "💥 Snapping..."
    result_style = "cyan" if use_trash else "green"
    result_label = "Moved to trash" if use_trash else "Eliminated"
    console.print()
    console.print(f"[bold {status_style}]{progress_message}[/bold {status_style}]")
    console.print()

    eliminated_count = 0
    failed_count = 0

    with console.status(f"[bold {status_style}]{action_label}...[/bold {status_style}]"):
        for file in eliminated:
            try:
                if use_trash:
                    send2trash(str(file))
                    success_message = "Moved to trash"
                else:
                    file.unlink()
                    success_message = "Eliminated"
                eliminated_count += 1
                console.print(f"   [green]✓[/green] {success_message}: [dim]{file}[/dim]")
            except Exception as err:
                failed_count += 1
                console.print(f"   [red]❌[/red] Failed: [dim]{file}[/dim] - {err}")

    summary_lines = [
        "[bold green]✨ The snap is complete.[/bold green]",
        "",
        f"[{result_style}]{result_label}:[/{result_style}] {eliminated_count} files",
        f"[red]Failed:[/red] {failed_count} files",
        "",
    ]
    if use_trash:
        summary_lines.append("[dim]Files can be restored from your system's trash/recycle bin.[/dim]")
    summary_lines.append("[dim]Perfectly balanced, as all things should be.[/dim]")

    console.print()
    console.print(Panel.fit("\n".join(summary_lines), border_style="green"))


def snap(
    directory: str = ".",
    recursive: bool = False,
    dry_run: bool = False,
    seed: Optional[int] = None,
    no_protect: bool = False,
    use_trash: bool = False,
    percent: int = 50,
):
    """Execute the snap operation."""
    rng = random.Random(seed)
    _print_header(percent, seed, use_trash)
    protected_patterns = _load_protected_patterns(directory, no_protect)

    # Load configuration
    config, config_file_path = load_thanosrc(directory)
    weights_config = config.get("weights", {})
    if weights_config:
        console.print(f"⚖️  [green]Weighted selection enabled from [bold]{config_file_path}[/bold][/green]")

    # Get all files
    all_files = get_files(directory, recursive)
    base_path = Path(directory).resolve()
    files, protected_files = _split_files(all_files, base_path, no_protect, protected_patterns)

    total_files = len(files)
    files_to_eliminate = _get_elimination_count(total_files, percent)
    if files_to_eliminate == 0:
        console.print()
        if total_files < 1:
            console.print(
                Panel(
                    "[yellow]No eligible files found.[/yellow]\nThe universe is empty (or fully protected).",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    f"[yellow]0 files to eliminate at {percent}% of {total_files} eligible files.[/yellow]\n"
                    "Try a higher percentage or a directory with more files.",
                    border_style="yellow",
                )
            )
        return

    eliminated = _select_files(files, weights_config, files_to_eliminate, rng)
    _print_balance_assessment(all_files, protected_files, total_files, files_to_eliminate)

    if dry_run:
        _print_dry_run(eliminated, protected_files, use_trash, seed)
        return

    _print_selected_files(eliminated, use_trash)

    # Confirmation
    confirm = console.input("[bold]Type 'snap' to proceed:[/bold] ")

    if confirm.lower() != "snap":
        console.print()
        console.print(Panel("[yellow]Snap cancelled.[/yellow]\nThe universe remains unchanged.", border_style="yellow"))
        return

    _execute_snap(eliminated, use_trash)
