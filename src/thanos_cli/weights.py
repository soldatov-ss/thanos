import random
import time
from pathlib import Path


def calculate_file_weight(file: Path, weights_config: dict) -> float:
    """
    Calculate elimination probability for a file based on weights.
    Returns a value between 0.0 (protect) and 1.0 (highly likely to eliminate).
    Default is 0.5 (neutral).

    Supports three types of weights:
    1. by_extension: Weight based on file extension
    2. by_age_days: Weight based on file age in days
    3. by_size_mb: Weight based on file size in megabytes

    When multiple weight types are specified, they are averaged.
    """
    if not weights_config:
        return 0.5

    weights = []

    # Extension-based weights
    ext_weights = weights_config.get("by_extension", {})
    if ext_weights and file.suffix in ext_weights:
        weights.append(ext_weights[file.suffix])

    # Age-based weights
    age_weights = weights_config.get("by_age_days", {})
    if age_weights:
        try:
            # Get file modification time
            mtime = file.stat().st_mtime
            age_days = (time.time() - mtime) / 86400  # Convert seconds to days

            # Find matching age range
            for age_range, weight in age_weights.items():
                if _matches_age_range(age_days, age_range):
                    weights.append(weight)
                    break
        except (OSError, ValueError):
            # If we can't get file stats, skip age-based weighting
            pass

    # Size-based weights
    size_weights = weights_config.get("by_size_mb", {})
    if size_weights:
        try:
            # Get file size in MB
            size_bytes = file.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            # Find matching size range
            for size_range, weight in size_weights.items():
                if _matches_size_range(size_mb, size_range):
                    weights.append(weight)
                    break
        except (OSError, ValueError):
            # If we can't get file stats, skip size-based weighting
            pass

    # Return average of all applicable weights, or default if none match
    print(f"{file=} {sum(weights) / len(weights) if weights else 0.5}")
    return sum(weights) / len(weights) if weights else 0.5


def _matches_age_range(age_days: float, age_range: str) -> bool:
    """
    Check if age_days matches the given age range string.

    Supported formats:
    - "0-7": 0 to 7 days old
    - "7-30": 7 to 30 days old
    - "30+": 30 days or older
    - "30-": 30 days or older (alternative syntax)
    """
    age_range = age_range.strip()

    # Handle "30+" or "30-" format (30 or more days)
    if age_range.endswith("+") or age_range.endswith("-"):
        min_age = float(age_range[:-1])
        return age_days >= min_age

    # Handle range format "min-max"
    if "-" in age_range:
        parts = age_range.split("-")
        if len(parts) == 2:
            try:
                min_age = float(parts[0])
                max_age = float(parts[1])
                return min_age <= age_days < max_age
            except ValueError:
                return False

    return False


def _matches_size_range(size_mb: float, size_range: str) -> bool:
    """
    Check if size_mb matches the given size range string.

    Supported formats:
    - "0-1": 0 to 1 MB
    - "1-10": 1 to 10 MB
    - "10+": 10 MB or larger
    - "10-": 10 MB or larger (alternative syntax)
    """
    size_range = size_range.strip()

    # Handle "10+" or "10-" format (10 MB or larger)
    if size_range.endswith("+") or size_range.endswith("-"):
        min_size = float(size_range[:-1])
        return size_mb >= min_size

    # Handle range format "min-max"
    if "-" in size_range:
        parts = size_range.split("-")
        if len(parts) == 2:
            try:
                min_size = float(parts[0])
                max_size = float(parts[1])
                return min_size <= size_mb < max_size
            except ValueError:
                return False

    return False


def weighted_random_sample(files: list[Path], weights: list[float], k: int) -> list[Path]:
    """Select k files using weighted random sampling."""
    selected = []
    remaining_files = list(files)
    remaining_weights = list(weights)

    for _ in range(k):
        if not remaining_files:
            break

        # Weighted random choice
        total = sum(remaining_weights)
        if total == 0:
            # Fallback to uniform if all weights are 0
            idx = random.randint(0, len(remaining_files) - 1)
        else:
            r = random.uniform(0, total)
            cumulative = 0
            idx = 0
            for i, w in enumerate(remaining_weights):
                cumulative += w
                if r <= cumulative:
                    idx = i
                    break

        selected.append(remaining_files[idx])
        remaining_files.pop(idx)
        remaining_weights.pop(idx)

    return selected
