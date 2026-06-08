import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('unauthenticated redirects to login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })

  test('sidebar shows correct items for owner', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@example.com')
    await page.fill('input[type="password"]', 'adminpassword')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Retrieve Species')).toBeVisible()
  })
})