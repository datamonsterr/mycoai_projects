import { test, expect } from '@playwright/test'

async function lo(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  await page.waitForFunction(() => (window as any).__mycoai_logout !== undefined, {}, { timeout: 5000 })
  await page.evaluate(() => { (window as any).__mycoai_logout() })
  await page.waitForTimeout(200)
}

test.describe('Auth', () => {
  test('login page renders', async ({ page }) => {
    await lo(page)
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible()
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('login form has register toggle', async ({ page }) => {
    await lo(page)
    await expect(page.locator("text=Don't have an account")).toBeVisible()
    await page.click("text=Don't have an account")
    await expect(page.locator('input#name')).toBeVisible()
    await expect(page.locator("text=Already have an account")).toBeVisible()
  })

  test('shows error on failed login', async ({ page }) => {
    await lo(page)
    await page.fill('input#email', 'bad@test.com')
    await page.fill('input#password', 'badpassword')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 })
  })
})
