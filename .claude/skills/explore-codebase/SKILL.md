---
name: exploring-codebase
description: >-
  Performs in-depth codebase exploration at the start of a coding session. Builds comprehensive
  understanding of project structure, architecture, key components, and patterns. Use when starting
  a new session, when asked to understand or explore the codebase, when asked "what does this project
  do", when exploring unfamiliar code, or when the user asks about project structure or architecture.
---

# Codebase Exploration

Performs thorough codebase exploration to build deep understanding before coding work begins.

---

## Exploration Approach

Use the Task tool with `subagent_type: Explore` to investigate the codebase. Focus on understanding:

1. **Project purpose and structure** - README, documentation, directory layout
2. **Architecture** - Main components, how they interact, communication patterns
3. **Core code** - Key classes, data models, utilities
4. **Configuration** - How the project is configured and customized
5. **Dependencies** - External libraries and integrations
6. **Patterns and conventions** - Coding style, naming conventions, design patterns

Adapt exploration depth based on project size and complexity. For small projects, a quick overview
suffices. For large projects, explore systematically.

---

## Guiding Questions

Answer these questions during exploration:

### Architecture
- What is the main entry point or controller?
- How do components communicate (IPC, APIs, events)?
- What external systems does this integrate with?

### Patterns
- What naming conventions are used?
- What design patterns appear (factories, dataclasses, protocols)?
- How is configuration managed?

### Structure
- Where is the core business logic?
- Where are tests located?
- What build/tooling configuration exists?

---

## Output Format

Provide a structured summary including:

- Project purpose (1-2 sentences)
- Key components table
- Important files list with paths
- Notable patterns or conventions
- Any areas of complexity or concern

### Example Output

```markdown
## Project Purpose

Provides shared data acquisition and processing assets for Sun Lab libraries. Decouples sl-experiment
and sl-forgery by providing common dataclasses and low-level tools.

## Key Components

| Component          | Location                                          | Purpose                               |
|--------------------|---------------------------------------------------|---------------------------------------|
| Data Classes       | src/sl_shared_assets/data_classes/                | Dataclasses for data and config       |
| Data Transfer      | src/sl_shared_assets/data_transfer/               | Data transfer and checksum utilities  |
| Interfaces         | src/sl_shared_assets/interfaces/                  | CLI and MCP server interfaces         |

## Important Files

- `src/sl_shared_assets/data_classes/configuration_data.py` - Experiment configuration dataclasses
- `src/sl_shared_assets/data_classes/session_data.py` - Session data structures
- `src/sl_shared_assets/data_classes/task_template_data.py` - Task template schema definitions
- `src/sl_shared_assets/interfaces/mcp_server.py` - MCP server for agentic configuration

## Notable Patterns

- Frozen dataclasses for immutable configuration objects
- MyPy strict mode with full type annotations
- MCP server for agentic configuration management

## Areas of Concern

- Cross-library dependencies require coordinated updates
- Configuration validation requires careful type checking
```

---

## Usage

Invoke at session start to ensure full context before making changes. Prevents blind modifications
and ensures understanding of existing patterns.
