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

    file_stats = _safe_file_stats(file)
    matched = [
        w
        for w in [
            _extension_weight(file, weights_config.get("by_extension", {})),
            _age_weight(file_stats, weights_config.get("by_age_days", {})),
            _size_weight(file_stats, weights_config.get("by_size_mb", {})),
        ]
        if w is not None
    ]
    return sum(matched) / len(matched) if matched else 0.5


def _safe_file_stats(file: Path) -> tuple[float, int] | None:
    """Return (mtime, size) for a file when available."""
    try:
        stat_result = file.stat()
    except OSError:
        return None
    return stat_result.st_mtime, stat_result.st_size


def _extension_weight(file: Path, ext_weights: dict) -> float | None:
    """Return extension-based weight when configured, else None."""
    if ext_weights and file.suffix in ext_weights:
        return ext_weights[file.suffix]
    return None


def _age_weight(file_stats: tuple[float, int] | None, age_weights: dict) -> float | None:
    """Return age-based weight when the file matches a configured range, else None."""
    if not age_weights or file_stats is None:
        return None
    try:
        age_days = (time.time() - file_stats[0]) / 86400
        return _first_matching_weight(age_days, age_weights, _matches_age_range)
    except ValueError:
        return None


def _size_weight(file_stats: tuple[float, int] | None, size_weights: dict) -> float | None:
    """Return size-based weight when the file matches a configured range, else None."""
    if not size_weights or file_stats is None:
        return None
    try:
        size_mb = file_stats[1] / (1024 * 1024)
        return _first_matching_weight(size_mb, size_weights, _matches_size_range)
    except ValueError:
        return None


def _first_matching_weight(value: float, configured_weights: dict, matcher) -> float | None:
    """Return the first configured weight whose range matches value, else None."""
    for range_name, weight in configured_weights.items():
        if matcher(value, range_name):
            return weight
    return None


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
    if age_range.endswith(("+", "-")):
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
    if size_range.endswith(("+", "-")):
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


def weighted_random_sample(
    files: list[Path], weights: list[float], k: int, rng: random.Random | None = None
) -> list[Path]:
    """Select k files using weighted random sampling."""
    if rng is None:
        rng = random.Random()
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
            idx = rng.randint(0, len(remaining_files) - 1)
        else:
            r = rng.uniform(0, total)
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
