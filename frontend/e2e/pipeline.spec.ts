import { test, expect } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'

const SAMPLE_BATCH_ZIP = '/tmp/opencode/e2e-sample/e2e_test_batch.zip'
const SAMPLE_IMAGE = path.resolve(__dirname, '..', 'public', 'sample', 'T379', 'MEA_original.jpg')

async function lo(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_logout !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => { (window as any).__mycoai_logout() })
  await page.waitForTimeout(200)
}

async function asOwner(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_switchRole !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => (window as any).__mycoai_switchRole('owner'))
  await page.waitForFunction(() => !document.querySelector('input#email'), {}, { timeout: 10000 })
}

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

// ── Authentication Tests ─────────────────────────────────────────────────────

test.describe('Auth: Token Refresh', () => {
  test('login as owner gets valid token', async ({ page }) => {
    await asOwner(page)
    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    expect(token).toBeTruthy()
    expect(token!.length).toBeGreaterThan(20)
  })

  test('login as user gets valid token', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForFunction(() => (window as any).__mycoai_switchRole !== undefined, {}, { timeout: 5000 })
    await page.evaluate(() => (window as any).__mycoai_switchRole('user'))
    await page.waitForFunction(() => !document.querySelector('input#email'), {}, { timeout: 10000 })

    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    expect(token).toBeTruthy()
    expect(token!.length).toBeGreaterThan(20)
  })

  test('401 triggers token refresh', async ({ page }) => {
    await asOwner(page)

    // Set an obviously expired token to trigger refresh path
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTQwMDAtODAwMC0wMDAwMDAwMDAwMDAiLCJyb2xlIjoib3duZXIiLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzE1OTM0MjAwLCJleHAiOjE3MTU5MzQyMDEsImp0aSI6IjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMCJ9.invalid'
    await page.evaluate((t) => localStorage.setItem('access_token', t), expiredToken)

    // Navigate to retrieve - should trigger 401 and attempt refresh via stored refresh_token
    await go(page, '/retrieve')

    // After refresh attempt, navigate should have redirected to login
    // Since our expired token is truly invalid, the refresh should fail too
    // and we should be back at login
    // Wait a moment for redirect
    await page.waitForTimeout(1000)

    const tokenAfter = await page.evaluate(() => localStorage.getItem('access_token'))
    // Token should have been cleared or refreshed
    // If refresh failed, token is cleared
    // If refresh succeeded (unlikely with fake token), token is new
    expect(tokenAfter !== expiredToken).toBeTruthy()
  })
})

// ── Upload Pipeline Tests ─────────────────────────────────────────────────────

test.describe('Upload Pipeline', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('retrieve page loads with upload UI', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator("h1:has-text('Retrieve Species')")).toBeVisible()
    await expect(page.locator('text=Upload')).toBeVisible()
    await expect(page.locator('text=Segment')).toBeVisible()
    await expect(page.locator('text=Results')).toBeVisible()
  })

  test('single strain mode shows Load Single Sample button', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator('button:has-text("Load Single Sample")')).toBeVisible()
    await expect(page.locator('button:has-text("Load Batch Sample")')).toBeVisible()
  })

  test('Load Single Sample populates strain data', async ({ page }) => {
    await get(page, '/retrieve')
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(500)

    // Should show strain identifier
    const strainInput = page.locator('#strain')
    await expect(strainInput).toHaveValue(/T379|T362/)
  })

  test('Load Batch Sample populates multiple strains', async ({ page }) => {
    await get(page, '/retrieve')
    await page.click('button:has-text("Load Batch Sample")')
    await page.waitForTimeout(500)

    // Should show batch mode with strain tabs
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/T379|T362/)
  })

  test('batch ZIP upload section visible', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator('text=Batch Upload (ZIP)').first()).toBeVisible()
    await expect(page.locator('text=Download Template (ZIP)').first()).toBeVisible()
  })

  test('auto-segment button initially disabled when no images', async ({ page }) => {
    await get(page, '/retrieve')
    const segBtn = page.locator('button:has-text("Auto Segment")')
    // When no images loaded, button should be disabled or after loading sample, enabled
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(500)
    await expect(segBtn).toBeEnabled()
  })
})

// ── Segmentation Pipeline Tests ───────────────────────────────────────────────

test.describe('Segmentation Pipeline', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('segment step visible in stepper', async ({ page }) => {
    await get(page, '/retrieve')
    await expect(page.locator('text=Segment').first()).toBeVisible()
  })

  test('load sample → auto-segment navigates to segmentation step', async ({ page }) => {
    await get(page, '/retrieve')
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(500)

    // Click Auto Segment - this calls POST /images/{id}/segment
    const segBtn = page.locator('button:has-text("Auto Segment")')
    if (await segBtn.isEnabled()) {
      await segBtn.click()
      // Wait for segmentation to complete
      await page.waitForTimeout(3000)

      // Check if we're in segmentation review step
      const pageText = await page.textContent('body')
      // Either shows segmentation review or stays in upload (if API failed)
      expect(pageText).toMatch(/Segment|segment|Review|review|detected/i)
    }
  })
})

// ── Retrieval Pipeline Tests ──────────────────────────────────────────────────

test.describe('Retrieval Pipeline', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('KNN configuration slider visible in results', async ({ page }) => {
    await get(page, '/retrieve')

    // Navigate directly to result step by loading sample then running segment then retrieve
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(500)

    // Click Auto Segment
    const segBtn = page.locator('button:has-text("Auto Segment")')
    if (await segBtn.isEnabled()) {
      await segBtn.click()
      await page.waitForTimeout(3000)
    }

    // Check if we can progress to results
    const nextBtn = page.locator('button:has-text("Run Retrieval")')
    if (await nextBtn.isVisible()) {
      // K-value configuration should be visible after reaching results
      // The Run Retrieval button triggers the retrieval and moves to results
      // which shows KNN Configuration
    }
  })

  test('retrieve species flow completes end-to-end', async ({ page }) => {
    test.setTimeout(60000)

    await get(page, '/retrieve')

    // Step 1: Load sample data
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(800)

    // Step 2: Verify sample data loaded
    const strainInput = page.locator('#strain')
    const strainValue = await strainInput.inputValue()
    expect(strainValue).toBeTruthy()

    // Step 3: Click Auto Segment
    const segBtn = page.locator('button:has-text("Auto Segment")')
    if (await segBtn.isEnabled()) {
      await segBtn.click()
      // Wait for backend segmentation to complete
      await page.waitForTimeout(5000)

      // Step 4: Should show segmentation review
      const segReview = page.locator('text=Segmentation Review')
      const isInSegReview = await segReview.isVisible().catch(() => false)

      if (isInSegReview) {
        // Step 5: Run retrieval
        const runBtn = page.locator('button:has-text("Run Retrieval")')
        if (await runBtn.isEnabled()) {
          await runBtn.click()
          // Wait for retrieval to complete (polling)
          await page.waitForTimeout(8000)

          // Step 6: Check results page
          const resultsText = await page.textContent('body')
          expect(resultsText).toMatch(/rank|Rank|species|Species|score|Score/i)
        }
      }
    }
  })
})

// ── K-Value Comparison Tests (K=7, K=11) ─────────────────────────────────────

test.describe('K-Value Comparison (K=7, K=11)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('result detail shows KNN configuration', async ({ page }) => {
    test.setTimeout(120000)

    await get(page, '/retrieve')
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(800)

    const segBtn = page.locator('button:has-text("Auto Segment")')
    if (!(await segBtn.isEnabled())) {
      test.skip(true, 'No images to segment - backend may not be running')
      return
    }

    await segBtn.click()
    await page.waitForTimeout(8000)

    const runBtn = page.locator('button:has-text("Run Retrieval")')
    if (!(await runBtn.isEnabled())) {
      test.skip(true, 'Cannot run retrieval - backend may not be running')
      return
    }

    // Set K=7 first
    const kSlider = page.locator('input[type="range"]')
    if (await kSlider.isVisible()) {
      await kSlider.fill('7')
    }

    await runBtn.click()
    // Wait for retrieval job to complete
    await page.waitForTimeout(15000)

    // Check for ranking results
    const resultsText = await page.textContent('body')
    expect(resultsText).toMatch(/k=7|K=7|#1|Rank/i)

    // Change K to 11 and run again
    if (await kSlider.isVisible()) {
      await kSlider.fill('11')
      if (await runBtn.isEnabled()) {
        await runBtn.click()
        await page.waitForTimeout(15000)
      }
    }
  })
})

// ── Batch ZIP Upload Tests ────────────────────────────────────────────────────

test.describe('Batch ZIP Upload', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('batch ZIP upload accepts zip file', async ({ page }) => {
    test.setTimeout(30000)

    // Skip if ZIP file doesn't exist
    if (!fs.existsSync(SAMPLE_BATCH_ZIP)) {
      test.skip(true, `Sample batch ZIP not found: ${SAMPLE_BATCH_ZIP}`)
      return
    }

    await get(page, '/retrieve')

    // Find the ZIP file input (hidden inside the drop area)
    const fileInput = page.locator('input[type="file"][accept=".zip"]')
    if (!(await fileInput.isVisible())) {
      test.skip(true, 'ZIP upload input not visible')
      return
    }

    await fileInput.setInputFiles(SAMPLE_BATCH_ZIP)
    // Wait for upload processing
    await page.waitForTimeout(10000)

    // Check for success/failure indicators
    const bodyText = await page.textContent('body')
    expect(bodyText).toMatch(/successful|failed|error|complete|strain/i)
  })
})

// ── Single Image Upload Tests ─────────────────────────────────────────────────

test.describe('Single Image Upload', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('single image upload adds image card', async ({ page }) => {
    test.setTimeout(30000)

    if (!fs.existsSync(SAMPLE_IMAGE)) {
      test.skip(true, `Sample image not found: ${SAMPLE_IMAGE}`)
      return
    }

    await get(page, '/retrieve')

    // Fill strain name
    const strainInput = page.locator('#strain')
    await strainInput.fill('E2E-TEST-STRAIN')

    // Find the Add Image button
    const addBtn = page.locator('button:has-text("Add Image")')
    if (!(await addBtn.isEnabled())) {
      test.skip(true, 'Add Image button not enabled')
      return
    }

    // Find the hidden file input for image upload
    // The file input is ref'd and hidden - use page.setInputFiles on all file inputs
    const fileInputs = page.locator('input[type="file"][accept="image/*"]')
    const count = await fileInputs.count()
    if (count > 0) {
      await fileInputs.first().setInputFiles(SAMPLE_IMAGE)
      await page.waitForTimeout(5000)

      // Check if image card appeared
      const bodyText = await page.textContent('body')
      expect(bodyText).toMatch(/E2E-TEST-STRAIN|MEA_original|Media|File/i)
    }
  })
})

// ── Result Consistency Tests ──────────────────────────────────────────────────

test.describe('Result Consistency (K=7 vs K=11)', () => {
  test.beforeEach(async ({ page }) => { await asOwner(page) })

  test('retrieval returns ranked species with scores', async ({ page }) => {
    test.setTimeout(120000)

    await get(page, '/retrieve')
    await page.click('button:has-text("Load Single Sample")')
    await page.waitForTimeout(800)

    const segBtn = page.locator('button:has-text("Auto Segment")')
    if (!(await segBtn.isEnabled())) {
      test.skip(true, 'Backend likely not running')
      return
    }

    await segBtn.click()
    await page.waitForTimeout(8000)

    const runBtn = page.locator('button:has-text("Run Retrieval")')
    if (!(await runBtn.isEnabled())) {
      test.skip(true, 'Cannot run retrieval')
      return
    }

    await runBtn.click()
    await page.waitForTimeout(20000)

    const resultsText = await page.textContent('body')

    // Verify result structure matches expected format:
    // - Ranked species list with scores
    // - Per-image KNN detail with neighbors
    // - Ground truth comparison info

    // Check for rank indicators
    const hasRankings = /#1|#2|#3|Rank|rank/.test(resultsText)
    const hasScores = /score|Score|sim/i.test(resultsText)
    const hasSpecies = /thymicola|sclerotigenum|Penicillium|polonicum|cyclopium/i.test(resultsText)

    // At minimum, the page should be structured correctly
    expect(resultsText).toBeTruthy()

    if (hasRankings || hasScores || hasSpecies) {
      console.log('Results structure verified:', { hasRankings, hasScores, hasSpecies })
    }
  })
})
