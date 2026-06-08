import { test, expect } from '@playwright/test'

test.describe('Auth', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('text=MycoAI Retrieval')).toBeVisible()
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('login form has register toggle', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator("text=Don't have an account")).toBeVisible()
    await page.click("text=Don't have an account")
    await expect(page.locator('input#name')).toBeVisible()
    await expect(page.locator("text=Already have an account")).toBeVisible()
  })

  test('shows error on failed login', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'wrong@test.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=Invalid credentials')).toBeVisible({ timeout: 5000 })
  })
})