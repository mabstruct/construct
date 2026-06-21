# Phase 1: Contract Canon & Artifact Governance — Pattern Map

## Target Areas

| Target | Closest Analog | Pattern To Reuse |
|--------|----------------|------------------|
| Canonical Pydantic artifact models | `src/construct/schemas/card.py` | `ConfigDict(extra="forbid")`, enum-backed literals, kebab-case validators |
| Workspace/file classification | `src/construct/schemas/workspace.py` + `src/construct/storage/workspace.py` | `WorkspaceScaffold` tuples + `PurePosixPath.match()` category checks |
| Boundary error wrapping | `src/construct/storage/workspace.py` | Convert YAML/JSON/Pydantic failures into domain `*Error` types |
| Validation aggregation | `src/construct/services/validation.py` | `ValidationReport` + `ValidationFinding` with file-specific messages |
| Skill validation checklist structure | `CONSTRUCT-CLAUDE-impl/claude/skills/construct-workspace-validate/SKILL.md` | Layered validation sections with exact file/field checks |
| Contract-change sync | `CONSTRUCT-CLAUDE-spec/process.md` | Spec + templates + skills + tests updated together |

## Concrete Code Excerpts To Follow

### Pydantic strict-model pattern

From `src/construct/schemas/card.py`:

```python
class KnowledgeCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

### Loader boundary conversion pattern

From `src/construct/storage/workspace.py`:

```python
try:
    return json.loads(path.read_text())
except json.JSONDecodeError as exc:
    raise WorkspaceLoadError(f"invalid JSON in {relative_path}: {exc}") from exc
```

### Validation accumulator pattern

From `src/construct/services/validation.py`:

```python
@dataclass
class ValidationReport:
    errors: list[ValidationFinding] = field(default_factory=list)
    warnings: list[ValidationFinding] = field(default_factory=list)
```

## Planning Guidance

- Prefer adding missing artifact schema models beside existing schema modules over embedding ad hoc dict checks in services.
- Keep file classification and write-gate helpers deterministic and filesystem-backed; tests should use `tmp_path`, not mocks.
- When skill docs change, preserve the current `## Procedure` + `### Validation` structure rather than inventing a new format.
