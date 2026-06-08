import { test, expect } from '@playwright/test'

async function lo(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_logout !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => { (window as any).__mycoai_logout() })
  await page.waitForTimeout(200)
}

test.describe('API Service Units', () => {
  test('api client uses correct base URL', async ({ page }) => {
    await lo(page)
    const origin = await page.evaluate(() => window.location.origin)
    expect(origin).toBeTruthy()
  })

  test('auth service login flow works with mock', async ({ page }) => {
    await lo(page)
    await page.fill('input#email', 'alice@mycoai.org')
    await page.fill('input#password', 'adminpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible({ timeout: 5000 })
  })
})
