# Claude Skill Style Guide

Conventions for Claude Code skill files in Sun Lab projects.

---

## Skill File Conventions

Claude Code skill files (`.md` files in `.claude/skills/`) follow specific formatting conventions.

### Line Length

All skill and asset markdown files must adhere to the **120 character line limit**. This matches the Python code
formatting standard.

- Wrap prose text at 120 characters
- Break long sentences at natural boundaries (after punctuation, between clauses)
- Code blocks may exceed 120 characters only when necessary for readability
- Tables may exceed 120 characters when proper column alignment aids clarity

### YAML Frontmatter

Every SKILL.md requires YAML frontmatter with `name` and `description`:

```yaml
---
name: exploring-codebase
description: >-
  Performs in-depth codebase exploration at the start of a coding session. Builds comprehensive
  understanding of project structure, architecture, key components, and patterns. Use at session
  start or when the user asks to understand the codebase.
---
```

**Name**: Use gerund form (verb + -ing), lowercase with hyphens. Examples: `exploring-codebase`,
`applying-sun-lab-style`, `designing-experiments`.

**Description**: Write in third person. Include both what the skill does and when to use it.

### Table Formatting

Use **pretty table formatting** with proper column alignment:

**Good:**

```markdown
| Field              | Type        | Required | Description                              |
|--------------------|-------------|----------|------------------------------------------|
| `name`             | str         | Yes      | Visual identifier (e.g., 'A', 'Gray')    |
| `code`             | int         | Yes      | Unique uint8 code for MQTT communication |
```

**Avoid:**

```markdown
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | Yes | Visual identifier |
```

### Table Formatting Rules

1. Align all `|` characters vertically
2. Use dashes (`-`) that span the full column width
3. Pad cells to consistent widths within each column
4. Use backticks for field names, types, and values

### Section Organization

```markdown
# Skill Name

Brief description of the skill's purpose.

---

## When to Use

- Bullet points describing use cases

---

## Main Content Section

### Subsection

Content with tables, code blocks, and explanations.
```

### Code Blocks

Use fenced code blocks with language identifiers:

````markdown
```yaml
cues:
  - name: "A"
    code: 1
```

```python
def process_data() -> None:
    pass
```
````

### Voice and Directional Language

Skill files use two voice styles:

- **Descriptive content**: Third person imperative. Example: "Extracts zone positions from configuration files."
- **Agent directives**: Second person with "You MUST", "You should". Example: "You MUST use the Task tool."

### Progressive Disclosure

Keep SKILL.md under 500 lines. Split content into separate files when needed:

```
skill-name/
├── SKILL.md              # Main instructions (loaded when triggered)
├── REFERENCE.md          # Detailed reference (loaded as needed)
└── EXAMPLES.md           # Usage examples (loaded as needed)
```

Reference files using standard markdown links: `[REFERENCE.md](REFERENCE.md)`

---

## Verification Checklist

**You MUST verify your edits against this checklist before submitting any changes to skill files.**

```
Skill File Compliance:
- [ ] YAML frontmatter with `name` and `description`
- [ ] Name uses gerund form (verb + -ing), lowercase with hyphens
- [ ] Description in third person, includes what AND when to use
- [ ] All lines ≤ 120 characters (tables/code blocks may exceed for clarity)
- [ ] Tables use pretty formatting with aligned columns
- [ ] Major sections separated with horizontal rules (`---`)
- [ ] Code blocks include language identifiers
- [ ] Third person imperative for descriptions
- [ ] Second person for agent directives ("You MUST...")
- [ ] Sentence case for section headers
- [ ] SKILL.md under 500 lines (split to reference files if needed)
- [ ] References one level deep from SKILL.md
```
