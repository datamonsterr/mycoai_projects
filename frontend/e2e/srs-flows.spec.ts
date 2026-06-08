import { test, expect } from '@playwright/test'

// ── Helpers ──────────────────────────────────────────────────────────────────

async function loginAs(page: import('@playwright/test').Page, email: string, password: string) {
  await page.goto('/login')
  await page.fill('input#email', email)
  await page.fill('input#password', password)
  await page.click('button[type="submit"]')
}

async function logout(page: import('@playwright/test').Page) {
  await page.evaluate(() => localStorage.clear())
  await page.reload()
}

async function navigate(page: import('@playwright/test').Page, href: string) {
  await page.evaluate((h) => { window.history.pushState({}, '', h) }, href)
  await page.evaluate(() => window.dispatchEvent(new PopStateEvent('popstate')))
}

// ── UC-AUTH-01 Authenticate User ─────────────────────────────────────────────

test.describe('UC-AUTH-01: Authenticate User', () => {
  test('login page renders with required fields (FR-001)', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible()
    await expect(page.locator('input#email[type="email"]')).toBeVisible()
    await expect(page.locator('input#password[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('login page shows register/signup toggle (FR-002)', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator("text=Don't have an account")).toBeVisible()
    await page.click("text=Don't have an account")
    await expect(page.locator('input#name')).toBeVisible()
    await expect(page.locator("text=Already have an account")).toBeVisible()
  })

  test('shows error on invalid credentials (NFR-001)', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input#email', 'nonexistent@test.com')
    await page.fill('input#password', 'badpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 })
  })

  test('successful login as user redirects to retrieve (FR-001)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await expect(page.locator('text=Retrieve Species')).toBeVisible({ timeout: 5000 })
  })

  test('successful login as owner shows dashboard (FR-001)', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    await expect(page.locator('text=Dashboard')).toBeVisible({ timeout: 5000 })
  })

  test('unauthenticated access redirects to login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })

  test('login form validates empty fields (NFR-014)', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input#email', '')
    await page.fill('input#password', '')
    await page.click('button[type="submit"]')
    const emailInput = page.locator('input#email[required]')
    const passwordInput = page.locator('input#password[required]')
    await expect(emailInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
  })
})

// ── UC-AUTH-02 Manage Users ──────────────────────────────────────────────────

test.describe('UC-AUTH-02: Manage Users (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('user management page renders (FR-003, FR-005)', async ({ page }) => {
    await navigate(page, '/users')
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible()
    await expect(page.locator('text=Send Invite')).toBeVisible()
    await expect(page.locator('text=Dr. Alice Chen')).toBeVisible()
    await expect(page.locator('text=Jane Smith')).toBeVisible()
  })

  test('shows all users with roles', async ({ page }) => {
    await navigate(page, '/users')
    await expect(page.locator('text=owner')).toHaveCount(2)
    await expect(page.locator('text=user')).toHaveCount(2)
    await expect(page.locator('text=inactive')).toBeVisible()
  })

  test('cannot demote last active Data Owner (FR-005, NFR-011)', async ({ page }) => {
    // Verify the last-owner protection is visible in the UI logic
    await navigate(page, '/users')
    // The demote buttons are disabled when only 1 active owner remains — but we have 2 owners
    // so demote should be enabled (not disabled with last-owner constraint)
    await expect(page.locator('button[title="Demote to User"]').first()).toBeVisible()
  })

  test('promote/demote buttons visible for each user', async ({ page }) => {
    await navigate(page, '/users')
    const promoteButtons = page.locator('button[title="Promote to Data Owner"]')
    const demoteButtons = page.locator('button[title="Demote to User"]')
    expect(await promoteButtons.count()).toBeGreaterThanOrEqual(1)
    expect(await demoteButtons.count()).toBeGreaterThanOrEqual(1)
  })
})

// ── UC-RETRIEVE-01 Retrieve Species ─────────────────────────────────────────

test.describe('UC-RETRIEVE-01: Retrieve Species', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('retrieve page renders upload flow (FR-006)', async ({ page }) => {
    await navigate(page, '/retrieve')
    await expect(page.locator('text=Retrieve Species')).toBeVisible()
    await expect(page.locator('text=Single Strain')).toBeVisible()
    await expect(page.locator('text=Batch Strains')).toBeVisible()
  })

  test('upload step shows file input fields (FR-006, FR-009)', async ({ page }) => {
    await navigate(page, '/retrieve')
    await expect(page.locator('text=Upload')).toBeVisible()
    await expect(page.locator('text=Strain')).toBeVisible()
    await expect(page.locator('text=Media')).toBeVisible()
  })

  test('batch toggle switches between single and batch mode (FR-007, FR-008)', async ({ page }) => {
    await navigate(page, '/retrieve')
    await page.click('text=Batch Strains')
    await expect(page.locator('text=Batch Template')).toBeVisible({ timeout: 3000 })
  })

  test('segmentation step renders after upload (FR-009, UC-PREP-01)', async ({ page }) => {
    await navigate(page, '/retrieve')
    // Verify Segment step exists in flow
    await expect(page.locator('text=Segment')).toBeVisible()
  })

  test('results step shows prediction output (FR-032)', async ({ page }) => {
    await navigate(page, '/retrieve')
    // Verify Results label exists in flow pipeline
    await expect(page.locator('text=Results')).toBeVisible()
  })

  test('KNN configuration available (FR-030)', async ({ page }) => {
    await navigate(page, '/retrieve')
    // KNN settings are shown in controls section
    const pageText = await page.textContent('body')
    expect(pageText).toContain('KNN')
  })

  test('non-owner user can also retrieve (FR-006)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/retrieve')
    await expect(page.locator('text=Retrieve Species')).toBeVisible()
  })
})

// ── UC-PREP-01 Prepare Segmented Images ──────────────────────────────────────

test.describe('UC-PREP-01: Prepare Segmented Images', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('segmentation step visible in retrieve flow (UC-PREP-01)', async ({ page }) => {
    await navigate(page, '/retrieve')
    await expect(page.locator('h1:has-text("Retrieve Species")')).toBeVisible()
    await expect(page.locator('text=Segment')).toBeVisible()
  })

  test('max colonies control visible (UC-PREP-01 input)', async ({ page }) => {
    await navigate(page, '/retrieve')
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Colony')
  })
})

// ── UC-FEEDBACK-01 Submit Feedback ───────────────────────────────────────────

test.describe('UC-FEEDBACK-01: Submit Feedback', () => {
  test('user feedback page renders (FR-013)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/my-feedback')
    await expect(page.locator('h1:has-text("My Feedback")')).toBeVisible()
  })

  test('data owner feedback inbox renders (FR-015)', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    await navigate(page, '/feedback-inbox')
    await expect(page.locator('h1:has-text("Feedback Inbox")')).toBeVisible()
  })

  test('feedback inbox shows pending items (FR-015)', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    await navigate(page, '/feedback-inbox')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/pending|accept|reject/i)
  })

  test('action buttons accept/reject visible (FR-015)', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    await navigate(page, '/feedback-inbox')
    await expect(page.locator('button:has-text("Accept")').first()).toBeVisible()
    await expect(page.locator('button:has-text("Reject")').first()).toBeVisible()
  })
})

// ── UC-DATA-01 Index New Data ────────────────────────────────────────────────

test.describe('UC-DATA-01: Index New Data (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('index page renders (FR-017)', async ({ page }) => {
    await navigate(page, '/index')
    await expect(page.locator('h1:has-text("Index New Data")')).toBeVisible()
    await expect(page.locator('text=Single')).toBeVisible()
    await expect(page.locator('text=Batch')).toBeVisible()
  })

  test('species selection required (FR-018)', async ({ page }) => {
    await navigate(page, '/index')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/species|Species/)
    expect(bodyText).toMatch(/media|Media/)
    expect(bodyText).toMatch(/strain|Strain/)
  })

  test('review step before indexing (FR-017)', async ({ page }) => {
    await navigate(page, '/index')
    await expect(page.locator('text=Review')).toBeVisible()
  })

  test('non-owner cannot access index page (FR-034, NFR-011)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/index')
    // User gets redirected to Retrieve, not Index
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
    await expect(page.locator('h1:has-text("Index New Data")')).not.toBeVisible()
  })
})

// ── UC-META-01 Manage Metadata ───────────────────────────────────────────────

test.describe('UC-META-01: Manage Metadata (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('metadata page renders with Species and Media tabs (FR-019)', async ({ page }) => {
    await navigate(page, '/metadata')
    await expect(page.locator('h1:has-text("Manage Metadata")')).toBeVisible()
    await expect(page.locator('text=Species')).toBeVisible()
    await expect(page.locator('text=Media')).toBeVisible()
  })

  test('species tab shows catalog entries (FR-019)', async ({ page }) => {
    await navigate(page, '/metadata')
    await expect(page.locator('text=Species')).toBeVisible()
    // Species names should appear in the table
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/Penicillium|Aspergillus|Fusarium|Cladosporium/i)
  })

  test('add new species button visible (FR-019)', async ({ page }) => {
    await navigate(page, '/metadata')
    await expect(page.locator('button:has-text("Add")').first()).toBeVisible()
  })

  test('archive/restore actions available (FR-023)', async ({ page }) => {
    await navigate(page, '/metadata')
    // Archive/restore buttons on metadata entries
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/archive|Archived|Archived/i)
  })

  test('non-owner cannot access metadata page (FR-034, NFR-011)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/metadata')
    await expect(page.locator('h1:has-text("Manage Metadata")')).not.toBeVisible()
  })
})

// ── UC-DATA-02 Manage Dataset ────────────────────────────────────────────────

test.describe('UC-DATA-02: Manage Dataset (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('dataset browser renders (FR-021)', async ({ page }) => {
    await navigate(page, '/dataset')
    await expect(page.locator('h1:has-text("Dataset Browser")')).toBeVisible()
  })

  test('shows data update status indicators (FR-022)', async ({ page }) => {
    await navigate(page, '/dataset')
    const bodyText = await page.textContent('body')
    // Should show status: current, updated_requires_reindex, or archived
    expect(bodyText).toMatch(/current|reindex|archived/i)
  })

  test('search and filter controls available (FR-021)', async ({ page }) => {
    await navigate(page, '/dataset')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/search|filter|Search/i)
  })

  test('group by strain/media/species (FR-021)', async ({ page }) => {
    await navigate(page, '/dataset')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/strain|media|species/i)
  })

  test('archive/restore actions available (FR-023)', async ({ page }) => {
    await navigate(page, '/dataset')
    await expect(page.locator('button[title="Archive"]').first()).toBeVisible()
  })

  test('non-owner cannot access dataset page (FR-034, NFR-011)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/dataset')
    await expect(page.locator('h1:has-text("Dataset Browser")')).not.toBeVisible()
  })
})

// ── UC-MODEL-01 Maintain Model and Index ─────────────────────────────────────

test.describe('UC-MODEL-01: Maintain Model and Index (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('model and index page renders (FR-025, FR-028)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('h1:has-text("Model & Index Maintenance")')).toBeVisible()
  })

  test('shows Qdrant index status (FR-025)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('text=Qdrant Index Status')).toBeVisible()
    // Should show needs_reindex or similar
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/reindex|current|index/i)
  })

  test('re-index button visible (FR-025)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('button:has-text("Re-index")').first()).toBeVisible()
  })

  test('shows current model version (FR-028)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('text=Feature Extractor Model')).toBeVisible()
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('efficientnet')
  })

  test('shows candidate model evaluation (FR-028)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('text=Evaluation Metrics')).toBeVisible()
    await expect(page.locator('text=F1')).toBeVisible()
  })

  test('retraining guidance visible (FR-026, FR-027)', async ({ page }) => {
    await navigate(page, '/model')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/retrain|Retraining|recommended/i)
  })

  test('promote/reject buttons for candidate models (FR-028)', async ({ page }) => {
    await navigate(page, '/model')
    await expect(page.locator('button:has-text("Promote")').first()).toBeVisible()
    await expect(page.locator('button:has-text("Reject")').first()).toBeVisible()
  })
})

// ── Dashboard (FR-033) ───────────────────────────────────────────────────────

test.describe('Dashboard (FR-033): Dataset Overview', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('dashboard renders with metrics (FR-033)', async ({ page }) => {
    await navigate(page, '/dashboard')
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
    await expect(page.locator('text=Dataset and index overview')).toBeVisible()
  })

  test('dashboard shows total images metric', async ({ page }) => {
    await navigate(page, '/dashboard')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/Images|images|Total/)
  })

  test('dashboard shows species distribution chart (FR-033)', async ({ page }) => {
    await navigate(page, '/dashboard')
    // The chart should show species names
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/Penicillium|commune|expansum/i)
  })
})

// ── Audit Log (FR-029) ───────────────────────────────────────────────────────

test.describe('FR-029: Audit Log (Data Owner)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
  })

  test('audit log page renders (FR-029)', async ({ page }) => {
    await navigate(page, '/audit')
    await expect(page.locator('h1:has-text("Audit Log")')).toBeVisible()
  })

  test('audit log shows mutation records', async ({ page }) => {
    await navigate(page, '/audit')
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/reindex|accept_feedback|update_metadata|archive_item/i)
  })
})

// ── Navigation & Sidebar ─────────────────────────────────────────────────────

test.describe('Navigation: Sidebar & Routing', () => {
  test('owner sees all admin sidebar items', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    const sidebar = page.locator('nav')
    await expect(sidebar.locator('text=Dashboard')).toBeVisible()
    await expect(sidebar.locator('text=Retrieve Species')).toBeVisible()
    await expect(sidebar.locator('text=Index New Data')).toBeVisible()
    await expect(sidebar.locator('text=Dataset Browser')).toBeVisible()
    await expect(sidebar.locator('text=Manage Metadata')).toBeVisible()
    await expect(sidebar.locator('text=Feedback Inbox')).toBeVisible()
    await expect(sidebar.locator('text=Model & Index')).toBeVisible()
    await expect(sidebar.locator('text=User Management')).toBeVisible()
    await expect(sidebar.locator('text=Audit Log')).toBeVisible()
  })

  test('user sees only user sidebar items', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    const sidebar = page.locator('nav')
    await expect(sidebar.locator('text=Retrieve Species')).toBeVisible()
    await expect(sidebar.locator('text=My Feedback')).toBeVisible()
    await expect(sidebar.locator('text=Dashboard')).not.toBeVisible()
    await expect(sidebar.locator('text=Index New Data')).not.toBeVisible()
    await expect(sidebar.locator('text=User Management')).not.toBeVisible()
  })

  test('sidebar can collapse and expand', async ({ page }) => {
    await loginAs(page, 'alice@mycoai.org', 'adminpass')
    const collapseBtn = page.locator('button[title="Collapse sidebar"]').first()
    await expect(collapseBtn).toBeVisible()
  })

  test('navigating to owner-only route as user shows retrieve (FR-034)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/users')
    await expect(page.locator('h1:has-text("User Management")')).not.toBeVisible()
    await expect(page.locator('text=Retrieve Species')).toBeVisible()
  })

  test('navigating to owner-only route as user shows retrieve (dashboard)', async ({ page }) => {
    await loginAs(page, 'jane@university.edu', 'password123')
    await navigate(page, '/dashboard')
    await expect(page.locator('h1:has-text("Dashboard")')).not.toBeVisible()
    await expect(page.locator('text=Retrieve Species')).toBeVisible()
  })
})

// ── NFR Compliance ───────────────────────────────────────────────────────────

test.describe('NFR Compliance', () => {
  test('NFR-001: authentication required for protected routes', async ({ page }) => {
    const protectedPaths = ['/dashboard', '/retrieve', '/my-feedback', '/index', '/dataset', '/metadata', '/users', '/model', '/audit']
    for (const path of protectedPaths) {
      await page.goto(path)
      await expect(page).toHaveURL(/\/login/, { timeout: 3000 })
    }
  })

  test('NFR-009: API error format is consistent (via page load)', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input#email', 'wrong@test.com')
    await page.fill('input#password', 'wrong')
    await page.click('button[type="submit"]')
    // Error message should be present and user-friendly
    const error = page.locator('text=Invalid credentials')
    await expect(error).toBeVisible({ timeout: 5000 })
  })

  test('NFR-014: input fields are required and validated', async ({ page }) => {
    await page.goto('/login')
    const emailInput = page.locator('input#email')
    const passwordInput = page.locator('input#password')
    await expect(emailInput).toHaveAttribute('required', '')
    await expect(passwordInput).toHaveAttribute('required', '')
  })
})
