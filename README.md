# 🫰 Thanos

> *"Perfectly balanced, as all things should be."*

<p align="center">
  <img src="docs/glove.png" width="120" alt="A glove"/>
</p>

A Python CLI tool that randomly eliminates half of the files in a directory with a snap. Inspired by Marvel's Thanos and
his infamous snap.

[![Test Python application](https://github.com/soldatov-ss/thanos/actions/workflows/test.yml/badge.svg)](https://github.com/soldatov-ss/thanos/actions/workflows/test.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Coverage Status](https://coveralls.io/repos/github/soldatov-ss/thanos/badge.svg?branch=master)](https://coveralls.io/github/soldatov-ss/thanos?branch=master)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ Warning

**This tool permanently deletes files!** Use `--dry-run` first to preview what would be deleted. Deleted files cannot be
recovered. Use at your own risk!

## ✨ Features

* 🗑️ **Trash Mode**: Optionally move files to the system trash/recycle bin instead of permanent deletion.
* ⚖️ **Weighted Selection**: Configure probabilities based on file age, size, or extension.
* 🛡️ **Smart Protections**: Automatically protects `.git`, `node_modules`, `venv`, and system files.
* 🚫 **Custom Ignore**: Support for `.thanosignore` using gitignore syntax.
* 🎲 **Reproducibility**: Use seeds to ensure the exact same files are selected every time.
* 📁 **Recursive Support**: Optionally include files in subdirectories.

## 📦 Installation

### Using uv (recommended)

```bash
uv add thanos-cli
uv pip install thanos-cli   # <- if you don't have pyproject.toml
```

### Using pip

```bash
pip install thanos-cli
```

## 🚀 Quick Start

### 1. Initialize Configuration

Create default `.thanosignore` and `.thanosrc.json` files in your project:

```bash
thanos init
```

### 2. Preview the Snap

Always start with a dry run to see the "dead" files without deleting them:

```bash
thanos snap --dry-run
```

### 3. Execute

When you are ready to restore balance:

```bash
# Permanent deletion (Standard Snap)
thanos snap

# Safer Snap (Move to Trash)
thanos snap --trash
```

## ⚙️ Configuration

Thanos supports advanced configuration to control the chaos.

### `.thanosignore`

Protect specific files or folders from being snapped (gitignore syntax):

```
# Protect specific folders
src/
important_docs/
!debug.log
```

### `.thanosrc.json`

Define weights (0.0 to 1.0) to make specific files more or less likely to be eliminated.

- **0.0**: Never eliminate
- **0.5**: Neutral (Default)
- **1.0**: Always eliminate

Supported weight types:

- **by_extension** — e.g., target `.tmp` or `.log` files
- **by_age_days** — e.g., target files older than `30+` days
- **by_size_mb** — e.g., target files larger than `100+` MB

See `docs/configuration.md` for the full schema.

## 📖 Commands

The CLI structure:

- `thanos init` — Generate configuration files.
- `thanos snap [DIRECTORY] [OPTIONS]` — Main command to eliminate files.

Options:

- `-t, --trash` — Move files to system trash instead of permanent deletion.
- `-r, --recursive` — Include subdirectories
- `-d, --dry-run` — Preview without deleting
- `--seed <INT>` — Set seed for reproducibility
- `--no-protect` — Disable protections (dangerous)

For detailed usage, see `docs/usage.md`.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤔 FAQ

**Q: Can I recover deleted files?**
A: If you use the --trash flag, **YES**, you can restore them from your system's Recycle Bin/Trash.
If you run the standard command without that flag, files are **permanently deleted**.

**Q: How are files selected?**
A: Randomly, but you can bias the selection using weights in `.thanosrc.json`.

**Q: What is protected by default?**
A: `.git`, `.svn`, `node_modules`, `venv`, `__pycache__`, `.env`, and more.

**Q: What if I have an odd number of files?**
A: If you have 11 files, 5 will be deleted (11 // 2 = 5) and 6 will remain.

## 🙏 Acknowledgments

- Inspired by the Marvel Cinematic Universe

---

**Remember: With great power comes great responsibility. Use Thanos wisely! 🫰**
