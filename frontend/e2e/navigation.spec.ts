import { test, expect } from '@playwright/test'

async function lo(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_logout !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => { (window as any).__mycoai_logout() })
  await page.waitForTimeout(200)
}

async function go(page: import('@playwright/test').Page, path: string) {
  await page.evaluate((p) => {
    window.history.pushState({}, '', p)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, path)
  await page.waitForTimeout(300)
}

test.describe('Navigation', () => {
  test('unauthenticated redirects to login', async ({ page }) => {
    await lo(page)
    await go(page, '/dashboard')
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible()
  })

  test('sidebar shows correct items for owner', async ({ page }) => {
    await lo(page)
    await page.fill('input#email', 'alice@mycoai.org')
    await page.fill('input#password', 'adminpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible({ timeout: 5000 })
  })
})
