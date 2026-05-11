# Technical Spec: Frontend Architecture

## Overview

Design the React SPA structure, component tree, routing, state management,
and data flow patterns.

---

## Routing Structure

**[DECISION: Route hierarchy]**

Choices:
- A) **Flat routes with layout wrapper** — `/upload`, `/results/:id`,
  `/dashboard`, `/database`, `/feedback`, `/training`, `/settings`
  **(Recommended)**
- B) Nested routes: `/app/dashboard`, `/app/database/species`, etc.

**Recommended route table:**

| Path | Page | Role |
|------|------|------|
| `/` | Landing / redirect to upload | All |
| `/login` | Login form | Public |
| `/register` | Registration form | Public |
| `/upload` | Image upload (single + batch) | All |
| `/results/:jobId` | Retrieval results | All |
| `/dashboard` | Overview dashboard (charts, counts) | All (filtered by role) |
| `/database` | Database browser (strain/species/media) | All (read), Owner (write) |
| `/database/species/:id` | Species detail | All |
| `/database/strains/:id` | Strain detail | All |
| `/feedback` | My submitted feedback | All |
| `/feedback/inbox` | Feedback review (data owner) | Owner |
| `/training` | Training status + trigger | Owner |
| `/settings` | User settings | All |
| `/admin/users` | User management | Owner |

---

## Component Tree (Key Pages)

### Upload Page

    <UploadPage>
      <UploadModeToggle />           # Single vs Batch tab
      <SingleUpload>
        <ImageDropzone />
        <StrainInput />
        <MediaSelector />
        <MaxColoniesSlider />
        <ProcessButton />
      </SingleUpload>
      <BatchUpload>
        <FolderDropzone />
        <TemplateJsonEditor />
        <BatchPreview>
          <StrainCard>               # Per strain in batch
            <ImageGrid>
              <ImageCard>            # Per image
                <RemoveButton />
              </ImageCard>
            </ImageGrid>
          </StrainCard>
        </BatchPreview>
        <ProcessBatchButton />
      </BatchUpload>
    </UploadPage>

### Results Page

    <ResultsPage>
      <ResultsSummary />              # Strain, top species, confidence
      <ResultsTable>
        <SpeciesRow>                  # Per species
          <RankBadge />
          <SpeciesName />
          <ConfidenceBar />
          <NeighborDetail>            # Expandable
            <MediaGroup>              # Per medium
              <MediaLabel />
              <NeighborCarousel>
                <NeighborThumbnail /> # Clickable
              </NeighborCarousel>
            </MediaGroup>
          </NeighborDetail>
          <FeedbackButton />
        </SpeciesRow>
      </ResultsTable>
      <KnnGraphView />                # Phase 2
    </ResultsPage>

### Database Browser

    <DatabasePage>
      <FilterBar>
        <SpeciesFilter />
        <StrainSearch />
        <MediaFilter />
        <DateRangeFilter />
        <SourceFilter />
      </FilterBar>
      <DataTable>
        <DataRow>
          <ImagePreview />
          <StrainInfo />
          <SpeciesBadge />
          <MediaBadge />
          <ActionMenu>               # Edit, Archive (owner)
            <EditButton />
            <ArchiveButton />
            <ReportIssueButton />
          </ActionMenu>
        </DataRow>
      </DataTable>
      <Pagination />
    </DatabasePage>

---

## State Management Strategy

**[DECISION: State management approach]**

Choices:
- A) **TanStack Query (server state) + React Context (auth/theme) +
  local useState (UI)** — no global state library needed
  **(Recommended)**
- B) Zustand — lightweight global store
- C) Redux Toolkit — heavier, devtools

**State categories:**

| Category | Solution | Examples |
|----------|----------|----------|
| Server data | TanStack Query | Species list, search results, dashboard stats |
| Auth state | React Context | Current user, JWT token, role |
| UI state | useState / useReducer | Modal open, tab selected, form values |
| Theme | React Context + localStorage | Dark/light mode |
| Cache invalidation | TanStack Query | Auto-refetch after mutation |

---

## Data Flow

### Image Upload -> Retrieval Flow

    1. User selects image(s) + metadata
    2. Client POST /api/images/upload (FormData)
    3. Server returns { job_id }
    4. Client polls GET /api/jobs/{job_id} via TanStack Query
       (refetchInterval: 2000, enabled: status !== 'completed')
    5. On completion: redirect to /results/{job_id}
    6. Client GET /api/retrieval/results/{job_id}
    7. Render ResultsPage

### Feedback Flow

    1. User clicks "Report incorrect" on a result
    2. Client POST /api/feedback { query_strain, predicted, suggested,
       description }
    3. TanStack Query invalidates feedback list
    4. Data owner views /feedback/inbox
    5. Owner clicks Accept -> PATCH /api/feedback/{id} { status: accepted }
    6. Backend updates database + triggers re-index task

---

## UI Component Library Strategy

**[DECISION: Component library approach]**

Already have shadcn/ui with Button. Need to add:

- [ ] **Layout**: Sidebar, Header, Shell
- [ ] **Navigation**: Breadcrumb, Tabs, Menu
- [ ] **Forms**: Input, Select, Textarea, Checkbox, Slider, File Upload
- [ ] **Data Display**: Table, Card, Badge, Avatar
- [ ] **Feedback**: Toast (Sonner), Dialog, Alert, Progress, Skeleton
- [ ] **Overlay**: Sheet, Dropdown Menu, Popover, Tooltip

**[DECISION: How to add shadcn/ui components]**

Choices:
- A) `pnpm dlx shadcn@latest add <component>` — recommended by shadcn
  **(Recommended)**
- B) Manually copy from shadcn/ui source
- C) Use Radix primitives directly + custom styling

**[DECISION: Icon library]**

Choices:
- A) **lucide-react** (already installed) **(Recommended)**
- B) react-icons (larger collection, heavier bundle)
- C) Heroicons (Tailwind ecosystem)

---

## Responsive Design

**[DECISION: Responsive approach]**

Choices:
- A) **Desktop-first — 1280px+ primary target** — fungal researchers work
  on desktop/laptop with large screens **(Recommended)**
- B) Mobile-first — progressive enhancement upward
- C) Tablet-first — middle ground

**[DECISION: Layout pattern]**

Choices:
- A) **Sidebar + content area** — persistent left sidebar (collapsible),
  main content scrolls. Dashboard-style layout. **(Recommended)**
- B) Top nav + full-width content — simpler, less space-efficient
- C) Full-page dedicated layouts — no shared shell

---

## Performance Considerations

- Code-split routes with `React.lazy` + `Suspense`
- Virtualize long lists (species table, database browser)
  with `@tanstack/react-virtual`
- Image lazy loading for neighbor thumbnails
- Debounce filter/search inputs (300ms)
- Prefetch on hover for common navigation targets
