# Dataset Browser strain-group rows Design

Date: 2026-07-12

## Goal

Change the Dataset Browser from a flat image table into a strain-group browser. Each top-level row represents one Strain. Expanding a strain row reveals that strain's child images. The expanded child rows show image preview and operational metadata, but do not show image ID or segment count.

## Domain alignment

This design aligns the UI with the canonical glossary in `CONTEXT.md`:

- `Strain` is image metadata identifying one or more uploaded images.
- `Image Metadata` includes Species, Strain, Media, and related descriptive fields.
- `Data Update Status` remains an image-level state.
- `Plate` is not a canonical product term and should be removed from the browser UI.

Resulting browser semantics:

- Parent row = `Strain`
- Expanded child rows = `Image[]` belonging to that strain
- Image-scoped actions remain on child rows, not parent rows

## Current mismatch

Current implementation in `frontend/src/pages/Dataset.tsx` renders one row per image and labels the thumbnail column `Plate`. Expansion shows image details such as `Image ID` and `Segments`. That shape conflicts with the requested UX and with the domain model where a strain owns one or more images.

## Chosen approach

Use a backend strain-group API instead of frontend-only grouping.

Why:

- Keeps paging, totals, and filtering semantically correct at the strain-group level.
- Avoids misleading record counts from grouping a paginated flat image list in the browser.
- Makes future `group by strain` behavior explicit instead of incidental UI logic.

## Response shape

Replace the current flat `ImageListResponse` dataset-browser contract with a grouped response dedicated to this page.

### Parent group fields

Each parent group should include:

- `strain_id`
- `strain_name`
- `species_id`
- `species_name`
- `media`: distinct media labels represented in the child images, suitable for compact display
- `image_count`
- `images`: list of child image items

### Child image fields

Each child image should include only the fields required by the dataset browser child rows:

- `id`
- `source_url`
- `created_at`
- `data_update_status`
- `indexed_in_qdrant`
- `is_archived`
- `angle` only if the current UI still needs it elsewhere

Not included in child display:

- `segments_count`
- `image_id` as visible UI text
- `plate` terminology

Keeping `id` in the payload is still necessary for React keys, routing, and image-scoped actions.

## Filtering and search semantics

Existing filters remain, but apply to groups:

- Search by strain name
- Filter by Species
- Filter by Media
- Filter by Data Update Status
- Archive inclusion remains query-driven

Group inclusion rules:

- A strain group is returned if any child image matches the selected filters.
- Child image list inside a matching group includes only matching images, not all strain images.

This keeps filter results honest. A user selecting `Needs Reindex` should not expand a strain and see unrelated `current` images mixed in.

## Media display

A strain can have multiple child images and potentially multiple media values. The parent row should display a compact media summary:

- one media value: show that label
- multiple media values: show comma-separated labels or a compact `N media` summary depending on width

For the first implementation, comma-separated distinct media labels is acceptable.

## Table structure

### Parent table columns

Top-level strain table columns:

- expand chevron
- `Strain`
- `Species`
- `Media`
- `Images`

No top-level thumbnail column. No `Plate` column.

Parent rows do not need actions in this change because requested operations remain image-scoped.

### Expanded child section

Expanded content becomes a nested image list or nested table under the strain row.

Child columns:

- `Image` preview
- `Created`
- `Status`
- `Qdrant`
- `Actions` for Data Owner

No visible image ID. No segment count.

## Actions

Archive, restore, and edit actions remain image-scoped because the existing behavior edits image metadata and archive state per image. This avoids introducing new strain-level mutation semantics in the same change.

## Empty/loading states

Update labels to match strain-group semantics:

- browser subtitle should prefer `strains` or `results` instead of `records` if practical
- empty state should say `No strains found`
- loading skeleton should match parent strain columns, not image thumbnail columns

## Backward-compatibility boundary

This is a contract change between `frontend/src/pages/Dataset.tsx` and the backend list endpoint used by the dataset browser.

To keep blast radius low, the implementation should prefer one of these two patterns:

1. add a new grouped endpoint for dataset browser use only, or
2. keep the same endpoint path but change the response only if no other product screen depends on the flat shape

Recommended implementation choice during coding: inspect current consumers first, then choose the smaller safe option.

## Testing

### Frontend

Add regression tests for:

- parent rows render once per strain, not once per image
- `Plate` header removed
- no visible `Image ID`
- no visible segment count
- expanding a strain reveals matching child images
- child rows render preview, created date, status, qdrant badge, and actions

### Backend

Add tests for:

- list endpoint returns grouped strain rows
- search/filtering operate on grouped results
- child images are filtered to matching images only
- totals count strain groups, not child images
- qdrant/indexed and archive status fields remain correct for child images

## Risks

- Flat `ImageListResponse` may be reused elsewhere; changing it in place can break other screens.
- Grouping by strain requires clear rules when strain images span multiple media values.
- If the page later needs pagination, grouped totals and offset semantics must stay group-based.
