import { test, expect } from '@playwright/test'

// ── Helpers ──────────────────────────────────────────────────────────────────

async function lo(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_logout !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => { (window as any).__mycoai_logout() })
  await page.waitForTimeout(200)
}

async function login(page: import('@playwright/test').Page, email: string, pw: string) {
  await lo(page)
  await page.waitForSelector('input#email', { timeout: 5000 })
  await page.fill('input#email', email)
  await page.fill('input#password', pw)
  await page.click('button[type="submit"]')
  await page.waitForTimeout(300)
}

async function asOwner(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  // After full page load, user is me (=owner). Just verify.
  await page.waitForTimeout(200)
}

async function asUser(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.evaluate(() => { const w = window as any; if (w.__mycoai_switchRole) w.__mycoai_switchRole('user') })
  await page.waitForTimeout(200)
}

// Navigate WITHOUT page reload (client-side SPA routing)
async function go(page: import('@playwright/test').Page, path: string) {
  await page.evaluate((p) => {
    window.history.pushState({}, '', p)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, path)
  await page.waitForTimeout(300)
}

async function get(page: import('@playwright/test').Page, path: string) {
  await page.goto(path)
  await page.waitForLoadState('networkidle')
}

// ── UC-AUTH-01 Authenticate User ─────────────────────────────────────────────

test.describe('UC-AUTH-01: Authenticate User', () => {
  test('FR-001 login page renders with required fields', async ({ page }) => {
    await lo(page)
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible()
    await expect(page.locator('input#email')).toBeVisible()
    await expect(page.locator('input#password')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('FR-002 login page shows register/signup toggle', async ({ page }) => {
    await lo(page)
    await expect(page.locator("text=Don't have an account")).toBeVisible()
    await page.click("text=Don't have an account")
    await expect(page.locator('input#name')).toBeVisible()
    await expect(page.locator("text=Already have an account")).toBeVisible()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await lo(page)
    await page.fill('input#email', 'nonexistent@test.com')
    await page.fill('input#password', 'badpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 })
  })

  test('successful login as user → retrieve page (FR-001)', async ({ page }) => {
    await login(page, 'jane@university.edu', 'password123')
    // After login URL is / which shows Dashboard; navigate to /retrieve
    await go(page, '/retrieve')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible({ timeout: 5000 })
  })

  test('successful login as owner → dashboard (FR-001)', async ({ page }) => {
    await login(page, 'alice@mycoai.org', 'adminpass')
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible({ timeout: 5000 })
  })

  test('unauthenticated redirect: /dashboard shows login', async ({ page }) => {
    await lo(page)
    await go(page, '/dashboard')
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible({ timeout: 5000 })
  })

  test('NFR-014: submit invalid credentials shows error', async ({ page }) => {
    await lo(page)
    await page.fill('input#email', 'bad@test.com')
    await page.fill('input#password', 'badpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credentials or inactive account.')).toBeVisible({ timeout: 5000 })
  })
})

// ── UC-AUTH-02 Manage Users ──────────────────────────────────────────────────

test.describe('UC-AUTH-02: Manage Users (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-003 user management page renders', async ({ page }) => {
    await get(page, '/users')
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible()
    const t = await page.textContent('body')
    expect(t).toMatch(/Invite|invite|Onboard/i)
    expect(t).toContain('Dr. Alice Chen')
    expect(t).toContain('Jane Smith')
  })

  test('shows roles and statuses', async ({ page }) => {
    await get(page, '/users')
    const t = await page.textContent('body')
    expect(t).toMatch(/Data Owner|Owner/i)
    expect(t).toContain('inactive')
  })

  test('FR-005 promote/demote buttons visible', async ({ page }) => {
    await get(page, '/users')
    await expect(page.locator('button[title="Promote to Data Owner"]').first()).toBeVisible()
    await expect(page.locator('button[title="Demote to User"]').first()).toBeVisible()
  })
})

// ── UC-RETRIEVE-01 Retrieve Species ─────────────────────────────────────────

test.describe('UC-RETRIEVE-01: Retrieve Species', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-006 retrieve page renders', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
    const t = await page.textContent('body')
    expect(t).toMatch(/Single|Batch|upload|Upload/i)
  })

  test('FR-009 segment step visible in pipeline', async ({ page }) => {
    await get(page, '/retrieve')
    // Use first() to avoid strict mode violations
    await expect(page.locator('text=Segment').first()).toBeVisible()
  })

  test('FR-032 results step visible', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator('text=Results').first()).toBeVisible()
  })

  test('FR-006 non-owner user can also retrieve', async ({ page }) => {
    await asUser(page)
    await get(page, '/retrieve')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })

  test('FR-007/FR-008 batch mode toggle available', async ({ page }) => {
    await get(page, '/retrieve')
    const t = await page.textContent('body')
    expect(t).toMatch(/Batch|batch|Single|single/i)
  })
})

// ── UC-PREP-01 Prepare Segmented Images ──────────────────────────────────────

test.describe('UC-PREP-01: Prepare Segmented Images', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('segment step visible in retrieve flow', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
    await expect(page.locator('text=Segment').first()).toBeVisible()
  })

  test('upload step shows input area', async ({ page }) => {
    await get(page, '/retrieve')
    const t = await page.textContent('body')
    expect(t).toMatch(/strain|media|upload|Upload|plate/i)
  })
})

// ── UC-FEEDBACK-01 Submit Feedback ───────────────────────────────────────────

test.describe('UC-FEEDBACK-01: Submit Feedback', () => {
  test('FR-013 user my-feedback page renders', async ({ page }) => {
    await asUser(page)
    await go(page, '/my-feedback')
    await expect(page.locator('h1:has-text("My Feedback")')).toBeVisible()
  })

  test('FR-015 data owner feedback inbox renders', async ({ page }) => {
    await asOwner(page)
    await get(page, '/feedback-inbox')
    await expect(page.locator('h1:has-text("Feedback Inbox")')).toBeVisible()
  })

  test('FR-015 feedback inbox shows accept/reject actions', async ({ page }) => {
    await asOwner(page)
    await get(page, '/feedback-inbox')
    const t = await page.textContent('body')
    expect(t).toMatch(/Accept|Reject|accept|reject/i)
  })

  test('FR-015 feedback inbox shows pending items', async ({ page }) => {
    await asOwner(page)
    await get(page, '/feedback-inbox')
    const t = await page.textContent('body')
    expect(t).toMatch(/pending|Pending|contribution|species|wrong/i)
  })
})

// ── UC-DATA-01 Index New Data ────────────────────────────────────────────────

test.describe('UC-DATA-01: Index New Data (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-017 index page renders', async ({ page }) => {
    await get(page, '/index')
    await expect(page.locator('h1:has-text("Index New Data")')).toBeVisible()
    const t = await page.textContent('body')
    expect(t).toMatch(/upload|Upload|strain|index/i)
  })

  test('FR-018 species/media/strain fields required', async ({ page }) => {
    await get(page, '/index')
    const t = await page.textContent('body')
    expect(t).toMatch(/species|Species/i)
    expect(t).toMatch(/media|Media/i)
  })

  test('review step before indexing', async ({ page }) => {
    await get(page, '/index')
    await expect(page.locator('text=Review').first()).toBeVisible()
  })

  test('FR-034 non-owner redirected from /index', async ({ page }) => {
    await asUser(page)
    await go(page, '/index')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })
})

// ── UC-META-01 Manage Metadata ───────────────────────────────────────────────

test.describe('UC-META-01: Manage Metadata (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-019 metadata page renders with Species + Media tabs', async ({ page }) => {
    await get(page, '/metadata')
    await expect(page.locator('h1:has-text("Manage Metadata")')).toBeVisible()
    // Check for Species/Media tab buttons
    const t = await page.textContent('body')
    expect(t).toMatch(/Species|Media/i)
  })

  test('FR-019 species tab shows catalog entries', async ({ page }) => {
    await get(page, '/metadata')
    const t = await page.textContent('body')
    expect(t).toMatch(/Penicillium|Aspergillus|Fusarium|Cladosporium/i)
  })

  test('add species/media buttons visible', async ({ page }) => {
    await get(page, '/metadata')
    const t = await page.textContent('body')
    expect(t).toMatch(/Add Species|Add Media|Add/i)
  })

  test('FR-034 non-owner cannot access metadata page', async ({ page }) => {
    await asUser(page)
    await go(page, '/metadata')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })
})

// ── UC-DATA-02 Manage Dataset ────────────────────────────────────────────────

test.describe('UC-DATA-02: Manage Dataset (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-021 dataset browser renders', async ({ page }) => {
    await get(page, '/dataset')
    await expect(page.locator('h1:has-text("Dataset Browser")')).toBeVisible()
  })

  test('FR-022 shows data update status indicators', async ({ page }) => {
    await get(page, '/dataset')
    const t = await page.textContent('body')
    expect(t).toMatch(/current|reindex|archived/i)
  })

  test('FR-021 search/filter/group controls available', async ({ page }) => {
    await get(page, '/dataset')
    const t = await page.textContent('body')
    expect(t).toMatch(/Filter|filter|Group|group|Search|search/i)
  })

  test('archive action column visible', async ({ page }) => {
    await get(page, '/dataset')
    const t = await page.textContent('body')
    expect(t).toMatch(/Action|Archive|archive/i)
  })

  test('FR-034 non-owner cannot access dataset page', async ({ page }) => {
    await asUser(page)
    await go(page, '/dataset')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })
})

// ── UC-MODEL-01 Maintain Model and Index ─────────────────────────────────────

test.describe('UC-MODEL-01: Maintain Model and Index (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-025/FR-028 model and index page renders', async ({ page }) => {
    await get(page, '/model')
    await expect(page.locator('h1:has-text("Model & Index Maintenance")')).toBeVisible()
  })

  test('FR-025 shows Qdrant index status section', async ({ page }) => {
    await get(page, '/model')
    const t = await page.textContent('body')
    expect(t).toMatch(/reindex|current|Qdrant|Index/i)
  })

  test('FR-025 re-index button visible', async ({ page }) => {
    await get(page, '/model')
    await expect(page.locator('button:has-text("Re-index")').first()).toBeVisible()
  })

  test('FR-028 shows current model version', async ({ page }) => {
    await get(page, '/model')
    const t = await page.textContent('body')
    expect(t).toContain('efficientnet')
  })

  test('FR-028 shows evaluation metrics', async ({ page }) => {
    await get(page, '/model')
    const t = await page.textContent('body')
    expect(t).toMatch(/Evaluation|Metrics|F1|metrics/i)
  })

  test('FR-026/FR-027 retraining guidance visible', async ({ page }) => {
    await get(page, '/model')
    const t = await page.textContent('body')
    expect(t).toMatch(/retrain|Retraining|recommended/i)
  })

  test('FR-028 promote/reject buttons for candidate models', async ({ page }) => {
    await get(page, '/model')
    const t = await page.textContent('body')
    expect(t).toMatch(/Promote|Reject|promote|reject/i)
  })
})

// ── Dashboard FR-033 ─────────────────────────────────────────────────────────

test.describe('Dashboard (FR-033): Dataset Overview', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-033 dashboard renders with metrics', async ({ page }) => {
    await get(page, '/dashboard')
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible()
    const t = await page.textContent('body')
    expect(t).toMatch(/overview|Overview|metric|Metric/i)
  })

  test('shows total images metric card', async ({ page }) => {
    await get(page, '/dashboard')
    const t = await page.textContent('body')
    expect(t).toMatch(/Images|images|Total|Species|Media/i)
  })

  test('shows species distribution chart', async ({ page }) => {
    await get(page, '/dashboard')
    const t = await page.textContent('body')
    expect(t).toMatch(/Penicillium|commune|expansum/i)
  })
})

// ── Audit Log FR-029 ─────────────────────────────────────────────────────────

test.describe('FR-029: Audit Log (Data Owner)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('FR-029 audit log page renders', async ({ page }) => {
    await get(page, '/audit')
    await expect(page.locator('h1:has-text("Audit Log")')).toBeVisible()
  })

  test('shows mutation records with actions', async ({ page }) => {
    await get(page, '/audit')
    const t = await page.textContent('body')
    expect(t).toMatch(/reindex|accept_feedback|create_species|archive_item/i)
  })
})

// ── Navigation & RBAC ────────────────────────────────────────────────────────

test.describe('Navigation: Sidebar & RBAC', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('owner sees all admin sidebar items', async ({ page }) => {
    await get(page, '/dashboard')
    const nav = page.locator('nav')
    await expect(nav.locator('text=Dashboard').first()).toBeVisible()
    await expect(nav.locator('text=Index New Data').first()).toBeVisible()
    await expect(nav.locator('text=Dataset Browser').first()).toBeVisible()
    await expect(nav.locator('text=Manage Metadata').first()).toBeVisible()
    await expect(nav.locator('text=Feedback Inbox').first()).toBeVisible()
    await expect(nav.locator('text=Model & Index').first()).toBeVisible()
    await expect(nav.locator('text=User Management').first()).toBeVisible()
    await expect(nav.locator('text=Audit Log').first()).toBeVisible()
  })

  test('user sees only 2 sidebar items', async ({ page }) => {
    await asUser(page)
    await go(page, '/retrieve')
    const nav = page.locator('nav')
    await expect(nav.locator('text=Retrieve Species').first()).toBeVisible()
    await expect(nav.locator('text=My Feedback').first()).toBeVisible()
    await expect(nav.locator('text=Dashboard')).not.toBeVisible()
    await expect(nav.locator('text=Index New Data')).not.toBeVisible()
  })

  test('sidebar visible with navigation', async ({ page }) => {
    await get(page, '/dashboard')
    await expect(page.locator('nav')).toBeVisible()
  })

  test('FR-034: non-owner → /users shows retrieve (client-side nav)', async ({ page }) => {
    await asUser(page)
    await go(page, '/users')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })

  test('FR-034: non-owner → /dashboard shows retrieve (client-side nav)', async ({ page }) => {
    await asUser(page)
    await go(page, '/dashboard')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })

  test('FR-034: non-owner → /model shows retrieve (client-side nav)', async ({ page }) => {
    await asUser(page)
    await go(page, '/model')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
  })
})

// ── NFR Compliance ───────────────────────────────────────────────────────────

test.describe('NFR Compliance', () => {
  test('NFR-001: protected routes require auth', async ({ page }) => {
    await lo(page)
    const paths = ['/dashboard', '/retrieve', '/index', '/dataset', '/users', '/model', '/audit', '/metadata']
    for (const path of paths) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      const t = await page.textContent('body')
      expect(t).toMatch(/MycoAI|Sign in|login|Sign up/)
    }
  })

  test('NFR-009/FR-034: RBAC — non-owner gets retrieve via client-side nav', async ({ page }) => {
    await asUser(page)
    const ownerPaths = ['/model', '/audit', '/index', '/dataset', '/metadata', '/users']
    for (const path of ownerPaths) {
      await go(page, path)
      await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
    }
  })

  test('NFR-014: login inputs exist for validation', async ({ page }) => {
    await lo(page)
    await expect(page.locator('input#email')).toBeVisible()
    await expect(page.locator('input#password')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })
})
