# Claude Code Instructions

## Session Start Behavior

At the beginning of each coding session, before making any code changes, You should build a comprehensive
understanding of the codebase by invoking the `/explore-codebase` skill.

This ensures:
- Understanding of the project architecture before modifying code
- Following existing patterns and conventions
- Avoiding inconsistencies or broken integrations

## Style Guide Compliance

Before writing, modifying, or reviewing any code or documentation, You MUST invoke the `/sun-lab-style` skill to load
the Sun Lab conventions. Reference the appropriate style guide based on the task:

| Task                              | Style Guide        | Key Requirements                                    |
|-----------------------------------|--------------------|-----------------------------------------------------|
| Writing Python code               | PYTHON_STYLE.md    | Type annotations, keyword arguments, error handling |
| Writing docstrings and comments   | PYTHON_STYLE.md    | Google-style, third person imperative, no bullets   |
| Creating or updating README files | README_STYLE.md    | Third person voice, present tense, standard sections|
| Writing commit messages           | COMMIT_STYLE.md    | Past tense verbs, ≤72 char header, ends with period |
| Creating skills or CLAUDE.md      | SKILL_STYLE.md     | 120 char lines, aligned tables, proper voice        |

All contributions must strictly follow these conventions and all reviews must check for compliance.

## Cross-Referenced Library Verification

Sun Lab projects often depend on other `ataraxis-*` or `sl-*` libraries. These libraries may be stored
locally in the same parent directory as this project (`/home/cyberaxolotl/Desktop/GitHubRepos/`).

**Before writing code that interacts with a cross-referenced library, You MUST:**

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
- `/sun-lab-style` - Apply Sun Lab conventions (REQUIRED for all code and documentation changes)

**Skills in downstream libraries (use MCP tools from this library):**
- `/machine-setup` - Located in sl-forgery (configures working directory, server credentials)
- `/acquisition-system-setup` - Located in sl-experiment (configures acquisition system parameters)
- `/experiment-design` - Located in sl-experiment (interactive guidance for building experiment configurations)

## MCP Server

This library exposes two MCP servers for agentic configuration management:

- **Base server** (`sl-shared-assets`): Shared tools that work across all acquisition systems. Start with:
  `sl-configure mcp --server base`
- **Mesoscope server** (`sl-mesoscope-vr`): Mesoscope-VR specific tools. Start with: `sl-configure mcp`

The servers provide tools for:
- **Setup**: Set working directory, create projects, configure system and server
- **Experiment Design**: Create templates, add cues/segments/trials/states incrementally
- **Query**: Read configurations, list components, validate completeness

Mesoscope-specific tools are prefixed with `mesoscope_` (e.g., `mesoscope_create_project_tool`).

See the `/experiment-design` skill in sl-experiment for interactive configuration building guidance.

## Downstream Library Integration

This library provides shared assets consumed by multiple Sun lab libraries. Two libraries may require coordinated
changes to this codebase:

| Library           | Relationship     | Common Change Triggers                                             |
|-------------------|------------------|--------------------------------------------------------------------|
| **sl-experiment** | Data acquisition | New session types, acquisition system configs, raw data structures |
| **sl-forgery**    | Data processing  | New processing pipelines, trackers, processed data structures      |

**When working on sl-experiment or sl-forgery**, changes to the following often require modifications here first:
- `SessionTypes`, `AcquisitionSystems` enums
- `ProcessingPipelines`, `ProcessingTrackers`, `DatasetTrackers` enums
- `SessionData`, `RawData`, `ProcessedData`, `TrackingData` dataclasses
- Experiment configuration structures (`MesoscopeExperimentConfiguration`, etc.)
- System configuration structures (`MesoscopeSystemConfiguration`, etc.)

**Workflow**: Make changes to sl-shared-assets first, then update the dependent library.

## Adding New Acquisition Systems

The codebase uses registry patterns to support multiple acquisition systems. To add a new system:

1. **Add enum value** to `AcquisitionSystems` in `configuration_utilities.py`
2. **Create system configuration module** (e.g., `new_system_configuration.py`) with:
   - System configuration dataclass inheriting from `YamlConfig`
   - Experiment configuration dataclass
   - A `save()` method for custom serialization if needed
3. **Update type aliases** in `configuration_utilities.py`:
   - Extend `SystemConfiguration` union type
   - Extend `ExperimentConfiguration` union type
4. **Register in `_SYSTEM_CONFIG_CLASSES`** dictionary
5. **Add experiment factory function** and register in `_EXPERIMENT_CONFIG_FACTORIES`
6. **(Optional) Create MCP server** for system-specific tools:
   - Create `{system}_mcp_server.py` in interfaces
   - Add entry to `_MCP_SERVERS` in `configure.py`
7. **Update downstream libraries** (sl-experiment, sl-forgery) as needed

Key files:
- `configuration_utilities.py` - Registries and factory functions
- `configure.py` - CLI and MCP server dispatcher

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
