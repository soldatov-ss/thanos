# 🫰 Thanos

> *"Perfectly balanced, as all things should be."*

A Python CLI tool that randomly eliminates half of the files in a directory with a snap. Inspired by Marvel's Thanos and his infamous snap.

[![Test Python application](https://github.com/soldatov-ss/thanos/actions/workflows/test.yml/badge.svg)](https://github.com/soldatov-ss/thanos/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚠️ Warning

**This tool permanently deletes files!** Use `--dry-run` first to preview what would be deleted. Deleted files cannot be recovered. Use at your own risk!

## ✨ Features

- 🎲 **Random Selection**: Eliminates exactly half of all files randomly
- 🔒 **Safety First**: Requires confirmation before deletion
- 👁️ **Dry Run Mode**: Preview what would be deleted without actually deleting
- 📁 **Recursive Support**: Optionally include files in subdirectories
- 🎨 **Beautiful CLI**: Colorful output with emojis and clear status messages
- 🧪 **Well Tested**: Comprehensive test suite with pytest

## 📦 Installation

### Using uv (recommended)

```bash
uv add thanos
```

### Using pip

```bash
pip install thanos
```


## 🚀 Quick Start

```bash
# Always start with a dry run to see what would be deleted
thanos --dry-run

# Snap the current directory (requires confirmation)
thanos

# Snap a specific directory
thanos /path/to/directory

# Include subdirectories recursively
thanos --recursive

# Dry run on a specific directory with subdirectories
thanos /path/to/directory --recursive --dry-run
```

## 📖 Usage

```bash
thanos [OPTIONS] [DIRECTORY]
```

### Arguments

- `DIRECTORY` - Target directory to snap (default: current directory)

### Options

- `-r, --recursive` - Include files in subdirectories recursively
- `-d, --dry-run` - Preview what would be deleted without actually deleting
- `--help` - Show help message and exit

### Examples

```bash
# See what would happen in current directory
thanos --dry-run

# Snap current directory
thanos

# Snap specific directory
thanos /tmp/test-files

# Snap with subdirectories
thanos ~/old-projects --recursive
```

For detailed usage instructions, see [USAGE.md](docs/usage.md).


## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤔 FAQ

**Q: Can I recover deleted files?**
A: No, files are permanently deleted. Always use `--dry-run` first!

**Q: How are files selected?**
A: Files are selected completely randomly using Python's `random.sample()`.

**Q: Does it delete directories?**
A: No, only files are affected. Empty directories may remain.

**Q: What if I have an odd number of files?**
A: If you have 11 files, 5 will be deleted (11 // 2 = 5) and 6 will remain.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the beautiful CLI
- Tested with [pytest](https://pytest.org/)
- Inspired by the Marvel Cinematic Universe

---

**Remember**: With great power comes great responsibility. Use Thanos wisely! 🫰
