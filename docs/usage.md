# Usage Guide

Complete guide for using Thanos CLI tool.

## Table of Contents

- [Quick Start](#quick-start)
- [Commands](#commands)
- [Common Scenarios](#common-scenarios)
- [Safety Guidelines](#safety-guidelines)
- [Understanding Output](#understanding-output)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Initialize Configuration

Create `.thanosignore` and `.thanosrc.json` configuration files:

```bash
thanos init
```

### Preview Before Snapping

Always start with a dry run:

```bash
# Preview in current directory
thanos snap -d

# Preview specific directory recursively
thanos snap test_env/ -r -d

# Preview with seed for reproducibility
thanos snap -d --seed 42
```

### Execute the Snap

After reviewing the preview:

```bash
# Snap current directory
thanos snap

# Safe snap: move eliminated files to trash
thanos snap --trash

# Snap with same seed to delete exact files from preview
thanos snap --seed 42

# Snap specific directory recursively
thanos snap test_env/ -r
```

## Commands

### `thanos snap` - Eliminate Files

The main command that eliminates half of all files.

```bash
thanos snap [DIRECTORY] [OPTIONS]
```

**Arguments:**

- `DIRECTORY` - Target directory (default: current directory)

**Options:**

- `-t, --trash` - Move files to system trash instead of permanent deletion.
- `-r, --recursive` - Include files in subdirectories
- `-d, --dry-run` - Preview without deleting
- `-s, --seed INTEGER` - Random seed for reproducibility
- `--no-protect` - Disable all file protections (DANGEROUS!)

**Examples:**

```bash
# Preview current directory
thanos snap -d

# Snap specific directory
thanos snap /path/to/dir

# Recursive snap with seed
thanos snap -r --seed 42

# Preview without protections (chaos mode)
thanos snap -d --no-protect
```

### `thanos init` - Initialize Configuration

Creates example `.thanosignore` and `.thanosrc.json` files.

```bash
thanos init [DIRECTORY]
```

**Arguments:**

- `DIRECTORY` - Directory to initialize (default: current)

**Creates:**

- `.thanosignore` - Gitignore-style protection patterns
- `.thanosrc.json` - Weighted selection configuration

**Example:**

```bash
# Initialize in current directory
thanos init

# Initialize in specific directory
thanos init /path/to/project
```

## File Protection

### Default Protections

Thanos automatically protects critical files and directories:

**Version Control:**

- `.git/`, `.svn/`, `.hg/`
- `.gitignore`, `.gitattributes`

**Python:**

- `venv/`, `.venv/`, `env/`
- `__pycache__/`, `*.pyc`, `*.pyo`

**Node.js:**

- `node_modules/`

**Configuration:**

- `.env`, `.env.*`
- `*.config`, `config.yml`, `config.yaml`
- Lock files (`package-lock.json`, `Cargo.lock`, etc.)

**System:**

- `.DS_Store`, `Thumbs.db`, `desktop.ini`

**Thanos:**

- `.thanosignore`, `.thanosrc.json`

### Custom Protection with `.thanosignore`

Create a `.thanosignore` file to protect additional files using gitignore-style patterns:

```gitignore
# Protect important directories
important/
backup/
docs/

# Protect database files
*.db
*.sqlite

# Protect specific files
secrets.json
credentials.yaml

# Pattern examples
*-important.*    # Files ending with -important
**/*.bak         # All .bak files recursively
logs/*.log       # .log files in logs directory
!debug.log       # Negation (don't protect debug.log)
```

The `.thanosignore` file is searched up to 5 parent directories, so you can place it at your project root.

## Weighted Selection

### Overview

Control which files are more likely to be eliminated using weights in `.thanosrc.json`.

**Weight Values:**

- `0.0` - Never eliminate (full protection)
- `0.1-0.4` - Low probability (keep important files)
- `0.5` - Neutral (default)
- `0.6-0.9` - High probability (eliminate temp files)
- `1.0` - Always eliminate (if selected)

When multiple weight types apply to a file, they are averaged.

### Weight Types

#### 1. Extension-Based Weights (`by_extension`)

Weight files by their extension:

```yaml
{
    "weights": {
        "by_extension": {
            ".log": 0.9,
            // Logs - likely eliminate
            ".tmp": 0.95,
            // Temp files - very likely eliminate
            ".cache": 0.95,
            // Cache files - very likely eliminate
            ".bak": 0.8,
            // Backups - likely eliminate
            ".py": 0.3,
            // Python code - likely keep
            ".js": 0.3,
            // JavaScript code - likely keep
            ".db": 0.1,
            // Databases - likely keep
            ".json": 0.2
            // JSON files - likely keep
        }
    }
}
```

#### 2. Age-Based Weights (`by_age_days`)

Weight files by how old they are:

```yaml
{
    "weights": {
        "by_age_days": {
            "0-7": 0.3,
            // Last week - keep recent
            "7-30": 0.5,
            // Last month - neutral
            "30-90": 0.7,
            // 1-3 months - likely eliminate
            "90+": 0.9
            // 3+ months - very likely eliminate
        }
    }
}
```

**Supported formats:**

- `"0-7"` - Range: 0 to 7 days
- `"30+"` - Open range: 30 days or older
- `"30-"` - Alternative syntax for 30+

#### 3. Size-Based Weights (`by_size_mb`)

Weight files by their size in megabytes:

```json
{
    "weights": {
        "by_size_mb": {
            "0-1": 0.4,
            // Small files < 1 MB - keep
            "1-10": 0.5,
            // Medium 1-10 MB - neutral
            "10-100": 0.6,
            // Large 10-100 MB - likely eliminate
            "100+": 0.8
            // Very large 100+ MB - eliminate
        }
    }
}
```

**Supported formats:**

- `"0-1"` - Range: 0 to 1 MB
- `"10+"` - Open range: 10 MB or larger
- `"10-"` - Alternative syntax for 10+

### Combined Weights Example

```json
{
    "weights": {
        "by_extension": {
            ".log": 0.9,
            ".tmp": 0.95,
            ".py": 0.2
        },
        "by_age_days": {
            "0-7": 0.2,
            "7-30": 0.5,
            "30+": 0.9
        },
        "by_size_mb": {
            "0-1": 0.3,
            "1-10": 0.5,
            "10+": 0.8
        }
    }
}
```

**Example calculation:**

```
File: old.log (90 days old, 5 MB)
- by_extension[".log"] = 0.9
- by_age_days["90+"] = 0.9
- by_size_mb["1-10"] = 0.5
Average weight = (0.9 + 0.9 + 0.5) / 3 = 0.77
```

## Common Scenarios

### Scenario 1: Python Project Cleanup

```bash
# Initialize config
cd my-python-project
thanos init

# Edit .thanosignore to protect important files
cat >> .thanosignore << EOF
src/
tests/
README.md
requirements.txt
EOF

# Preview what would be deleted
thanos snap -r -d

# Execute if satisfied
thanos snap -r
```

### Scenario 2: Clean Old Log Files

```bash
# Create weighted config
cat > .thanosrc.json << EOF
{
  "weights": {
    "by_extension": {
      ".log": 0.95,
      ".txt": 0.95
    },
    "by_age_days": {
      "0-7": 0.3,
      "7-30": 0.7,
      "30+": 0.95
    }
  }
}
EOF

# Preview
thanos snap logs/ -r -d

# Execute
thanos snap logs/ -r
```

### Scenario 3: Chaos Engineering Testing

```bash
# Disable protections and use seed for reproducibility
thanos snap test_env/ -r -d --no-protect --seed 12345

# Run the same elimination in CI/CD
thanos snap test_env/ -r --no-protect --seed 12345
```

### Scenario 4: Reduce Large Media Collections

```bash
# Target large files
cat > .thanosrc.json << EOF
{
  "weights": {
    "by_extension": {
      ".mp4": 0.6,
      ".mov": 0.6,
      ".avi": 0.6
    },
    "by_size_mb": {
      "0-100": 0.3,
      "100-500": 0.6,
      "500+": 0.9
    }
  }
}
EOF

# Preview
thanos snap ~/Videos/old -r -d

# Execute
thanos snap ~/Videos/old -r
```

## Safety Guidelines

### ⚠️ Always Use Dry Run First

```bash
# GOOD: Check first
thanos snap -d
thanos snap

# RISKY: Direct snap without preview
thanos snap  # Don't do this without -d first!

# Safer alternative: move files to trash instead of permanent deletion
thanos snap --trash
```

### 🔒 Confirmation Required

Thanos requires you to type `snap` to confirm:

```
⚠️  WARNING: This will permanently delete files!
Type 'snap' to proceed: snap
```

### 🎯 Use Seeds for Reproducibility

```bash
# Preview with seed
thanos snap -d --seed 42

# Execute same selection
thanos snap --seed 42
```

## Understanding Output

### Dry Run Output

```
╭─────────────────────────────────────────────╮
│ 🫰 THE SNAP                                 │
│ Perfectly balanced, as all things should be │
╰─────────────────────────────────────────────╯

🛡️  Default protections enabled
📋 Loaded 15 patterns from /home/user/project/.thanosignore
⚖️  Weighted selection enabled from /home/user/project/.thanosrc.json
Base path: /home/user/project/test_env

   📊 Balance Assessment
╭────────────────────┬─────╮
│ Total files found  │ 100 │
│ Protected files    │  45 │
│ Eligible files     │  55 │
│ Files to eliminate │  27 │
│ Survivors          │  28 │
╰────────────────────┴─────╯

╭─────────────────────────────────────╮
│ 🔍 DRY RUN MODE                     │
│ These files would be eliminated:    │
╰─────────────────────────────────────╯

   💀 test_env/old.log
   💀 test_env/cache.tmp
   ...

╭────────────────────────────────────────────╮
│ ⚠️  This was a dry run.                    │
│     No files were harmed.                  │
│                                            │
│ 💡 Run with --seed 42 to delete these     │
│    exact files                             │
╰────────────────────────────────────────────╯
```

### Debug Output

```
╭─────────────────────╮
│ 🔍 DEBUG MODE       │
│ Analyzing file...   │
╰─────────────────────╯

Default patterns: 25
Patterns from /home/user/.thanosignore: 10

Active patterns:
  • .git/
  • .venv/
  • node_modules/
  • *.pyc
  • important/
  ...

Protected: 45 files
Unprotected: 55 files

╭─────────────────────────────────────────────╮
│ Unprotected Files (eligible for snap)      │
╰─────────────────────────────────────────────╯
  ○ test.log
  ○ cache.tmp
  ...
```

## Troubleshooting

### "No eligible files found"

All files are protected by default protections or `.thanosignore`.

**Solution:**

```bash
# Check what's protected
thanos debug -p

# Use --no-protect if intentional
thanos snap --no-protect -d
```

### Files still being deleted despite `.thanosignore`

Check pattern syntax and file location:

```bash
# Debug to see if patterns match
thanos debug -r

# Verify .thanosignore location (should be in project root)
find . -name ".thanosignore"

# Check pattern syntax (must be gitignore-style)
cat .thanosignore
```


### Permission denied errors

Some files may be protected by the system:

```bash
# Files will be skipped with error message
# Check file permissions
ls -la

# Run with appropriate permissions if needed
sudo thanos snap /protected/path  # Use with extreme caution!
```

## Best Practices

1. **Always initialize first**: `thanos init`
2. **Always dry run first**: `thanos snap -d`
3. **Use debug to verify protections**: `thanos debug`
4. **Use seeds for reproducibility**: `--seed 42`
5. **Start with small, safe directories**: Test on `/tmp` first
6. **Backup important data**: Better safe than sorry
7. **Use `.thanosignore` liberally**: Protect anything important
8. **Test weight configurations**: Use dry run to verify behavior
9. **Place `.thanosignore` at project root**: It's searched up 5 levels
10. **Combine multiple weight types**: Extension + age + size for best control
