# Claude Code Instructions

## Session Start Behavior

At the beginning of each coding session, before making any code changes, you should build a comprehensive
understanding of the codebase by invoking the `/explore-codebase` skill.

This ensures you:
- Understand the project architecture before modifying code
- Follow existing patterns and conventions
- Don't introduce inconsistencies or break integrations

## Style Guide Compliance

Before writing, modifying, or reviewing any code or documentation, you MUST invoke the `/sun-lab-style` skill to load
the Sun Lab conventions. This applies to ALL file types including:
- Python source files (`.py`)
- Documentation files (`README.md`, docstrings)
- Configuration files when adding comments or descriptions

All contributions must strictly follow these conventions and all reviews must check for compliance. Key conventions
include:
- Google-style docstrings with proper sections
- Full type annotations with explicit array dtypes
- Keyword arguments for function calls
- Third person imperative mood for comments and documentation
- Proper error handling with `console.error()`
- README structure and formatting standards

## Cross-Referenced Library Verification

Sun Lab projects often depend on other `ataraxis-*` or `sl-*` libraries. These libraries may be stored
locally in the same parent directory as this project (`/home/cyberaxolotl/Desktop/GitHubRepos/`).

**Before writing code that interacts with a cross-referenced library, you MUST:**

1. **Check for local version**: Look for the library in the parent directory (e.g.,
   `../ataraxis-time/`, `../ataraxis-base-utilities/`).

2. **Compare versions**: If a local copy exists, compare its version against the latest release or
   main branch on GitHub:
   - Read the local `pyproject.toml` to get the current version
   - Use `gh api repos/Sun-Lab-NBB/{repo-name}/releases/latest` to check the latest release
   - Alternatively, check the main branch version on GitHub

3. **Handle version mismatches**: If the local version differs from the latest release or main branch,
   notify the user with the following options:
   - **Use online version**: Fetch documentation and API details from the GitHub repository
   - **Update local copy**: The user will pull the latest changes locally before proceeding

4. **Proceed with correct source**: Use whichever version the user selects as the authoritative
   reference for API usage, patterns, and documentation.

**Why this matters**: Skills and documentation may reference outdated APIs. Always verify against the
actual library state to prevent integration errors.

## Available Skills

- `/explore-codebase` - Perform in-depth codebase exploration
- `/sun-lab-style` - Apply Sun Lab coding and documentation conventions (REQUIRED for all code and documentation changes)

## Project Context

This is **sl-shared-assets**, a Python library that provides data acquisition and processing assets shared between
Sun (NeuroAI) lab libraries. It decouples sl-experiment (data acquisition) and sl-forgery (data processing) by
providing common dataclasses and low-level tools.

### Key Areas

| Directory                             | Purpose                                               |
|---------------------------------------|-------------------------------------------------------|
| `src/sl_shared_assets/`               | Main library source code                              |
| `src/sl_shared_assets/cli.py`         | CLI entry point for configuration management          |
| `src/sl_shared_assets/configuration/` | Configuration dataclasses and management              |
| `src/sl_shared_assets/data/`          | Data handling and storage utilities                   |
| `tests/`                              | Test suite                                            |

### Architecture

- **Configuration System**: Dataclasses for configuring data acquisition and processing runtimes
- **Data Management**: Low-level tools for managing data throughout acquisition, processing, and analysis
- **CLI Interface**: Configuration management via command-line interface
- **Shared Types**: Common type definitions used across sl-experiment and sl-forgery

### Key Patterns

- **Dataclasses**: Heavy use of frozen dataclasses for configuration and data structures
- **Type Safety**: MyPy strict mode with full type annotations
- **Cross-Library Compatibility**: Designed as a dependency for other Sun lab libraries

### Code Standards

- MyPy strict mode with full type annotations
- Google-style docstrings
- 120 character line limit
- See `/sun-lab-style` for complete conventions
