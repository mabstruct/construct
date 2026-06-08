# Coding Conventions

**Analysis Date:** 2026-06-08

---

This project spans three distinct layers, each with its own conventions:
1. **Python runtime** (`src/construct/`) — Pydantic v2, Typer, dataclasses
2. **Claude-native agent system** (`CONSTRUCT-CLAUDE-impl/`) — markdown procedures, YAML frontmatter
3. **Views frontend** (`views/design-example/`) — React 19, Vite 8, Tailwind v4

---

## Python Layer

### Naming Patterns

**Files:**
- `snake_case.py` for all Python modules
- One module per concern: `card.py`, `validation.py`, `workspace.py`
- Schemas in `src/construct/schemas/`, services in `src/construct/services/`, storage in `src/construct/storage/`

**Functions:**
- `snake_case` for all functions and methods
- Private helper functions prefixed with `_`: `_split_frontmatter`, `_write_domains_registry`, `_to_kebab_case`
- Factory/builder helpers prefixed with `_write_`: `_write_domain_file`, `_write_connections`

**Variables:**
- `snake_case` throughout
- Compiled regex patterns are module-level constants in `UPPER_SNAKE_CASE`: `KEBAB_CASE_PATTERN`, `ENV_VAR_PATTERN`, `ROUTING_TASKS`

**Types:**
- Pydantic model names: `PascalCase` — `KnowledgeCard`, `DomainConfig`, `WorkspaceScaffold`
- Enum names: `PascalCase`, enum values: `lowercase` snake/kebab matching the data format — `EpistemicType.finding`, `Lifecycle.seed`
- Exception classes: `PascalCase` with `Error` suffix — `SchemaParseError`, `WorkspaceLoadError`, `WorkspaceInitError`
- Dataclass value objects: `PascalCase` — `ValidationFinding`, `ValidationReport`, `DomainInitInput`, `WorkspaceItem`

### Code Style

**Python version compatibility:**
- All modules begin with `from __future__ import annotations`
- Required Python ≥ 3.11 (`pyproject.toml`)
- Module docstrings on every source file (one-line summary, e.g., `"""Knowledge card schema and markdown parsing helpers."""`)

**Formatting:**
- No formatter config detected (no `.prettierrc`, no `ruff.toml`, no `.black`)
- Style follows PEP 8 conventions observed in source: 4-space indent, one blank line between top-level definitions, two blank lines between classes

**Linting:**
- No linting config detected in active codebase (archived Python path may have had it)
- Type annotations on all function signatures including `-> None` returns
- Return types declared explicitly: `-> tuple[str, str]`, `-> list[WorkspaceItem]`

### Import Organization

**Order (observed pattern):**
1. `from __future__ import annotations` (always first)
2. Standard library (`dataclasses`, `datetime`, `enum`, `json`, `pathlib`, `re`, `shutil`, `tomllib`)
3. Third-party (`pydantic`, `ruamel.yaml`, `typer`)
4. Internal project (`construct.schemas.*`, `construct.services.*`, `construct.storage.*`)

**Path Aliases:**
- None (direct package imports via `pythonpath = ["src"]` in pytest; package installed in `.venv`)

### Pydantic Conventions

**Model configuration:**
- Every Pydantic model sets `model_config = ConfigDict(extra="forbid")` — no extra fields allowed
- Use `Field()` for constraints: `Field(ge=1, le=5)`, `Field(min_length=1)`, `Field(default_factory=list)`

**Validators:**
- Use `@field_validator("field_name")` + `@classmethod` pattern (Pydantic v2)
- Use `@model_validator(mode="after")` for cross-field validation
- Validators raise `ValueError` with human-readable messages including examples: `"entries must be kebab-case, e.g. 'quantum-gravity' not 'quantum gravity'"`
- Validator return type explicitly declared: `def validate_id(cls, value: str) -> str:`

**Enums:**
- All domain enums inherit from `(str, Enum)` so they serialize to strings automatically
- Enum values match the literal strings used in data files (not uppercase Python convention)

### Error Handling

**Strategy:** Domain-specific exception hierarchy over generic exceptions.

**Patterns:**
- Define custom `ValueError` subclasses for each domain boundary: `SchemaParseError` (card parsing), `WorkspaceLoadError` (file loading), `WorkspaceInitError` (workspace setup)
- Always chain exceptions with `raise NewError("message") from original_exc`
- Convert third-party exceptions (YAMLError, JSONDecodeError, pydantic.ValidationError) to domain errors at the boundary
- Let `ValidationError` propagate unmodified when already correct type (the `except ValidationError: raise` pattern in `card.py`)

```python
# Boundary conversion pattern
try:
    return self._yaml.load(path.read_text())
except YAMLError as exc:
    raise WorkspaceLoadError(f"invalid YAML in {relative_path}: {exc}") from exc
```

**CLI error handling:**
- Catch domain exceptions in CLI commands, emit `typer.echo(f"ERROR {exc}")`, then `raise typer.Exit(code=1)`
- Never let raw exceptions reach the user in CLI context

### Dataclasses

**Pattern:** Use frozen dataclasses for immutable value objects, mutable dataclasses for accumulators.

```python
@dataclass(frozen=True)
class ValidationFinding:   # immutable value object
    severity: str
    path: str
    message: str

@dataclass
class ValidationReport:    # mutable accumulator with methods
    errors: list[ValidationFinding] = field(default_factory=list)
```

### Data Identifiers

**Kebab-case is the universal data identifier format.** Card IDs, domain IDs, taxonomy tags, connection targets — all must match `KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")`.

This pattern is defined independently in `schemas/card.py`, `schemas/config.py`, and `schemas/workspace.py` — not shared via import. If adding a new schema module, define it locally again.

---

## Claude-Native Agent Layer

### Skill File Conventions

**Location:** `CONSTRUCT-CLAUDE-impl/claude/skills/{skill-name}/SKILL.md`

**Skill names:** `construct-` prefix, kebab-case — `construct-card-create`, `construct-curation-cycle`, `construct-workspace-validate`

**Frontmatter fields (YAML at top of SKILL.md):**
```yaml
---
description: "One-sentence description for routing. Use when [trigger conditions]."
allowed-tools: Read, Write, Edit, Bash(git add *), Bash(git commit *)
---
```

**Document structure:**
1. `# Skill: {Name}` — heading
2. **Trigger, Agent, Produces** — one-liner context block
3. `## Procedure` with numbered `### Step N: Description` sections
4. Steps use decision tables (`| User provides | Action |`) for routing logic
5. `### Validation` section at end — checklist of what the skill must verify before completing

### Agent File Conventions

**Location:** `CONSTRUCT-CLAUDE-impl/claude/agents/{name}.md`

**Frontmatter:**
```yaml
---
name: curator
description: "Role summary — when to use this agent"
tools: Read, Write, Edit, Grep, Glob, Bash(git add *), Bash(git commit *)
skills:
  - construct-skill-name
memory: project
---
```

**Content:** Agent files define responsibilities, judgment criteria, escalation rules, and reference tables. They do NOT contain code — they configure Claude's behavior.

### Workflow Files

**Location:** `CONSTRUCT-CLAUDE-impl/construct/workflows/{name}.md`

**Format:** Markdown with ASCII flow diagrams, numbered steps, embedded trigger conditions, and clear skill invocation references (`**Skill:** construct-research-cycle`).

### Markdown Specification Files

**Location:** `CONSTRUCT-CLAUDE-spec/`

**Conventions:**
- Document title as `# H1`, sections as `## H2`, sub-sections as `### H3`
- Tables for structured enumerations (enum values, responsibility matrices, validation rules)
- All workspace file references in code fences: `` `cards/` ``, `` `connections.json` ``
- ADRs in `adrs/` with format `adr-NNNN-{slug}.md`
- Validation strategy embedded in specs — each SKILL.md ends with a validation checklist

---

## Views Frontend Layer

### Naming Patterns

**Files:**
- `PascalCase.jsx` for all React components — `Layout.jsx`, `KnowledgeGraph.jsx`
- Pages in `src/pages/`, shared components in `src/components/`
- Data files as JSON in `src/data/` — `articles.json`, `digests.json`

**Components:**
- Default export function with PascalCase name matching filename
- Internal helper components defined in the same file with PascalCase (e.g., `function CosmicBG()`)
- Constant data arrays and objects defined at module level before the component

**No TypeScript** — `.jsx` only (no `.tsx`), no type annotations in views layer.

### Code Style

**Formatting:**
- Single quotes for imports
- Inline JSX for small helper components, separate function for complex sub-components

**Linting:**
- ESLint v9 with `eslint-plugin-react-hooks` and `eslint-plugin-react-refresh` (`package.json`)
- No separate `.eslintrc` — config likely in `eslint.config.js` at project root

### Import Organization (React files)

**Order:**
1. React and React ecosystem (`react`, `react-router-dom`)
2. Third-party UI/chart libraries (`lucide-react`, `recharts`, `react-markdown`)
3. Local components (`../components/Layout`)
4. Local data (`../data/digests.json`)

### Component Design

**Patterns:**
- Default export arrow function or named function — both observed; prefer named function for pages
- Props destructured inline (when used)
- `useState` + `useMemo` for local filtering/sorting state (pattern in `Blog.jsx`, `Digests.jsx`, `Landscape.jsx`)
- Data loaded from static JSON imports (no API calls in current implementation)

**Routing:**
- `react-router-dom` v7 with `<Routes>` / `<Route>` in `App.jsx`
- Route tree defined in `App.jsx`, wrapped in `HashRouter` in `main.jsx`
- All routes nested under `<Layout />`

### Styling

**Framework:** Tailwind CSS v4 via `@tailwindcss/vite` plugin (no separate `tailwind.config.js` needed)

**Pattern:** Utility classes inline on JSX elements. Dark glassmorphism design system:
- `bg-black/40 backdrop-blur-2xl` for glass elements
- `border-white/[0.06]` for subtle borders
- `text-white/50` for muted text
- Custom `.glass` utility class defined in `index.css`

**No CSS modules, no styled-components.** All styling via Tailwind utility classes.

---

## Comments

**Python:**
- Module-level docstrings: one-line description on every module
- No inline comments in existing code — code is self-documenting via naming
- Exception messages serve as inline documentation for validation rules

**Claude-native:**
- Purpose comments in frontmatter `description` field
- Context blocks (Trigger/Agent/Produces) at top of each SKILL.md

**React:**
- JSDoc-style block comment when a component has a complex non-obvious purpose (seen in `KnowledgeGraph.jsx`)
- No `//` comments for obvious code

---

## Module Design

**Python:**
- `__init__.py` files are minimal (only `__version__` in root `__init__.py`)
- No barrel files — import from specific modules: `from construct.schemas.card import KnowledgeCard`
- Each module has one primary public concern; private helpers have `_` prefix

**Claude-native:**
- Skills are the unit of reuse — compose workflows from skill invocations
- No code sharing between skills; each SKILL.md is self-contained

---

*Convention analysis: 2026-06-08*
