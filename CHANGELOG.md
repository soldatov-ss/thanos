# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] – 2025-11-XX

### Added

- **Weighted Selection System**: Ability to influence elimination probability via `.thanosrc.json`.
    - Support for weighting by file extension (e.g., `.log`, `.tmp`).
    - Support for weighting by file age in days (e.g., `30+`).
    - Support for weighting by file size in MB (e.g., `100+`).
- **Configuration Commands**:
    - `thanos init`: Creates default `.thanosignore` and `.thanosrc.json` files.
- **Smart Protections**: Built-in protection for `.git`, `node_modules`, `venv`, `__pycache__`, and configuration files.
- **Custom Ignore**: Support for `.thanosignore` files using standard gitignore syntax.
- **Safety Flags**: Added `--no-protect` option to bypass all safety checks.
- **Debug Tools**: Added `debug` functionality to analyze file protections and pattern matching.

### Changed

- **CLI Structure**: Main functionality moved to `thanos snap` subcommand **(Breaking Change!)**.
- **Output**: Enhanced CLI output with "Balance Assessment" statistics and ASCII art.
---

## [0.1.1] – 2025-11-XX

### Added

- **`--seed` / `-s` option** for deterministic, reproducible file selection
    - Running `--dry-run --seed <N>` and then `--seed <N>` deletes the exact same files
    - Useful for debugging, auditing, testing, and scripting

### Fixed

- Random selection now remains consistent when a seed is provided

---

## [0.1.0] – 2025-XX-XX

### Added

- Initial release
- Random file elimination (exactly 50% of files)
- Dry run mode
- Recursive directory support
- Interactive confirmation
- CLI powered by Typer
- Basic project documentation

---
[0.2.0]: https://github.com/soldatov-ss/thanos/releases/tag/v0.2.0

[0.1.1]: https://github.com/soldatov-ss/thanos/releases/tag/v0.1.1

[0.1.0]: https://github.com/soldatov-ss/thanos/releases/tag/v0.1.0
