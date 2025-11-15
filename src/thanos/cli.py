"""Console script for thanos."""

import random
from typing import Annotated, Optional

import typer
from rich.console import Console

from thanos.utils import get_files

app = typer.Typer(
    name="thanos",
    help="🫰 Thanos - Eliminate half of all files with a snap. Perfectly balanced, as all things should be.",
    add_completion=False,
)
console = Console()


def snap(directory: str = ".", recursive: bool = False, dry_run: bool = False):
    """
    The Snap - Eliminates half of all files randomly.

    Args:
        directory: Target directory (default: current directory)
        recursive: Include subdirectories
        dry_run: Show what would be deleted without actually deleting
    """
    print("🫰 Initiating the Snap...")

    files = get_files(directory, recursive)
    total_files = len(files)

    if total_files == 0:
        print("No files found. The universe is empty.")
        return

    # Calculate how many files to eliminate
    files_to_eliminate = total_files // 2

    # Randomly select files for elimination
    eliminated = random.sample(files, files_to_eliminate)

    print("\n📊 Balance Assessment:")
    print(f"   Total files: {total_files}")
    print(f"   Files to eliminate: {files_to_eliminate}")
    print(f"   Survivors: {total_files - files_to_eliminate}")

    if dry_run:
        print("\n🔍 DRY RUN - These files would be eliminated:")
        for file in eliminated:
            print(f"   💀 {file}")
        print("\n⚠️  This was a dry run. No files were harmed.")
        return

    # Confirm before destruction
    print("\n⚠️  WARNING: This will permanently delete files!")
    confirm = input("Type 'snap' to proceed: ")

    if confirm.lower() != "snap":
        print("Snap cancelled. The universe remains unchanged.")
        return

    # Execute the snap
    print("\n💥 Snapping...")
    eliminated_count = 0

    for file in eliminated:
        try:
            file.unlink()
            eliminated_count += 1
            print(f"   💀 {file}")
        except Exception as e:
            print(f"   ❌ Failed to eliminate {file}: {e}")

    print("\n✨ The snap is complete.")
    print(f"   {eliminated_count} files eliminated.")
    print("   Perfectly balanced, as all things should be.")


@app.command()
def main(
    directory: Annotated[
        Optional[str],
        typer.Argument(
            help="Target directory to snap (default: current directory)",
            show_default=False,
        ),
    ] = ".",
    recursive: Annotated[
        bool, typer.Option("--recursive", "-r", help="Include files in subdirectories recursively")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Preview what would be deleted without actually deleting")
    ] = False,
):
    """
    🫰 Eliminate half of all files in a directory with a snap.

    Thanos randomly selects and deletes exactly half of the files in the specified
    directory. Use with caution - deleted files cannot be recovered!

    Examples:

        # Snap current directory (dry run first!)
        $ thanos --dry-run

        # Snap a specific directory
        $ thanos /path/to/directory

        # Include subdirectories recursively
        $ thanos --recursive

        # Snap a directory and its subdirectories
        $ thanos /path/to/directory --recursive
    """
    try:
        snap(directory, recursive, dry_run)
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    return 0


if __name__ == "__main__":
    app()
