# MycoAI Documentation

## Folder Structure

```
docs/
├── README.md                   # You are here — how to use this folder
├── SRS.md                      # Software Requirements Specification
├── feature_spec/               # Ground-truth feature specifications
│   ├── 01-image-input.md       # Image upload, batch processing, template system
│   ├── 02-segmentation.md      # Auto-segment, editable bboxes, image removal
│   ├── 03-retrieval.md         # KNN species retrieval pipeline
│   ├── 04-visualization.md     # Ranked results, graph visualization (Phase 1 & 2)
│   ├── 05-feedback-pipeline.md # User feedback → data owner review workflow
│   ├── 06-data-management.md   # CRUD for species, strains, images, media
│   ├── 07-training-observation.md # Async training job status
│   └── 08-roles-and-permissions.md # Data Owner vs User
├── technical_spec/             # Technical decisions with decision points
│   ├── ...md                   # Each spec asks multiple-choice questions
└── living_spec/                # Synced working copy (auto-maintained)
```

## How to Use

### Reading
- **Feature specs** (`feature_spec/`): Ground truth for what the product does.
  Start here to understand any feature. These are the source of truth.
- **Technical specs** (`technical_spec/`): How we build it. Each doc contains
  open decision points marked with `[DECISION]`. Fill these in before
  implementation starts.
- **Living specs** (`living_spec/`): Working copies synced from `feature_spec/`.
  These are consumed by agents during implementation. Never edit these directly.

### Workflow

1. **New feature**: Add to `feature_spec/` → run spec-syncer → implement
2. **Feature change**: Update `feature_spec/` → run spec-syncer → review diffs
3. **Technical decision**: Read `technical_spec/` → fill `[DECISION]` blocks →
   implement
4. **Agent implementation**: Agents pull `living_spec/` for current context

### Commands

```bash
# Sync feature_spec → living_spec
# (invoke the spec-syncer subagent)

# Pull living spec for current work
# (invoke the spec-puller subagent)
```

## Rules

- `feature_spec/` is the ground truth. All changes originate here.
- `technical_spec/` captures decisions. Archive decisions once implemented.
- `living_spec/` is auto-generated. Do not edit directly.
- Each feature spec must be self-contained — read one file to understand one feature.
- Cross-references between specs use relative links.
