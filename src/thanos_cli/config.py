import json
from pathlib import Path
from typing import Optional


def get_default_protected_patterns() -> set[str]:
    """Return default patterns that should be protected."""
    return {
        # Version control (The history of the universe must be preserved)
        ".git",
        ".git/",
        ".gitignore",
        ".gitattributes",
        ".svn",
        ".hg",
        # --- THE HEAVYWEIGHTS (Prevent Statistical Skew) ---
        # Python virtual environments
        "venv/",
        ".venv/",
        "env/",
        ".env.local/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        # Node.js
        "node_modules/",
        # --- CRITICAL CONFIGURATION ---
        # Environment and config files
        ".env",
        ".env.*",
        "*.config",
        "config.yml",
        "config.yaml",
        # Lock files (Keep these safe to ensure reproducibility after the snap)
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "Pipfile.lock",
        "poetry.lock",
        "Gemfile.lock",
        "uv.lock",
        # --- TOOL CONFIGURATION ---
        # Thanos shouldn't snap himself
        ".thanosignore",
        ".thanosrc.json",
        # IDEs (Debatable, but usually annoying to lose)
        ".vscode/",
        ".idea/",
        # Database files
        "*.db",
        "*.sqlite",
    }


def find_config_file(directory: str, filename: str) -> Optional[Path]:
    """
    Search for a config file in the directory and parent directories.
    This allows .thanosignore to work from parent directories.
    """
    current = Path(directory).resolve()

    # Search up to 5 levels of parent directories
    for _ in range(5):
        config_file = current / filename
        if config_file.exists():
            return config_file

        # Move to parent directory
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def load_thanosignore(directory: str) -> tuple[set[str], Optional[Path]]:
    """
    Load patterns from .thanosignore file.
    Returns (patterns, config_file_path).
    """
    ignore_file = find_config_file(directory, ".thanosignore")
    patterns = set()

    if ignore_file:
        with open(ignore_file) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.add(line)

    return patterns, ignore_file


def load_thanosrc(directory: str) -> tuple[dict, Optional[Path]]:
    """
    Load configuration from .thanosrc.json file.
    Returns (config_dict, config_file_path).
    """
    config_file = find_config_file(directory, ".thanosrc.json")

    if config_file:
        with open(config_file) as f:
            return json.load(f), config_file

    return {}, None
