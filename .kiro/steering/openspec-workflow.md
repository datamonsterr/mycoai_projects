# OpenSpec Workflow Integration

This project uses [OpenSpec](https://openspec.dev) for structured change management. Specs live in `openspec/` at the repo root.

## Directory Structure

```
openspec/
├── changes/             # Active and in-progress changes
│   └── <change-name>/
│       ├── .openspec.yaml   # Schema + metadata
│       ├── proposal.md      # What & why
│       ├── design.md        # How (decisions, trade-offs, migration)
│       ├── tasks.md         # Implementation checklist (- [ ] / - [x])
│       └── specs/           # Delta specs (capability requirements)
│           └── <capability>/
│               └── spec.md  # ADDED/MODIFIED/REMOVED requirements
└── specs/               # Main specs (accumulated truth)
    └── <capability>/
        └── spec.md      # Requirements with Scenarios (WHEN/THEN)
```

## Active Changes

Use `openspec list --json` to see active changes and their progress.

## Workflows (via openspec CLI)

### Propose a new change
```bash
openspec new change "<name>"
openspec instructions <artifact-id> --change "<name>" --json
```
Creates proposal.md → design.md → tasks.md in sequence.

### Implement a change
```bash
openspec instructions apply --change "<name>" --json
```
Returns context files to read and task list. Implement tasks, mark `- [ ]` → `- [x]`.

### Sync delta specs to main specs
After implementation, sync capability delta specs from `changes/<name>/specs/` to `openspec/specs/<capability>/spec.md` using intelligent merging (ADDED/MODIFIED/REMOVED/RENAMED).

### Archive a completed change
```bash
mkdir -p openspec/changes/archive
mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
```

## Spec Format

### Main Spec (`openspec/specs/<capability>/spec.md`)
```markdown
## Purpose
Brief description of this capability.

## Requirements

### Requirement: Feature Name
The system SHALL do something.

#### Scenario: Specific behavior
- **WHEN** condition
- **THEN** expected outcome
```

### Delta Spec (in changes)
```markdown
## ADDED Requirements
### Requirement: New Feature
...

## MODIFIED Requirements
### Requirement: Existing Feature
#### Scenario: New scenario to add
...

## REMOVED Requirements
### Requirement: Deprecated Feature
```

## Integration with Kiro

- Use **Spec sessions** in Kiro for new changes (they follow the same propose → design → tasks → implement pattern)
- For existing OpenSpec changes, read the change artifacts and implement tasks directly
- Reference `openspec/specs/` as the source of truth for existing requirements
- When implementing, always read proposal.md + design.md + tasks.md first for full context
- Mark tasks complete in tasks.md as you go: `- [ ]` → `- [x]`

## Key Commands

```bash
# List active changes
openspec list --json

# Get change status
openspec status --change "<name>" --json

# Get implementation instructions
openspec instructions apply --change "<name>" --json

# Get artifact creation instructions
openspec instructions <artifact-id> --change "<name>" --json
```
