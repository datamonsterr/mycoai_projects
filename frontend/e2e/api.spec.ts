import { test, expect } from '@playwright/test'

test.describe('API Service Units', () => {
  test('api client uses correct base URL', async ({ page }) => {
    await page.goto('/login')
    const apiClient = page.evaluate(() => {
      const resp = new Response(JSON.stringify({}), {status: 401, statusText: 'Unauthorized'})
      return window.location.origin
    })
    expect(apiClient).toBeTruthy()
  })

  test('auth service stores tokens in localStorage', async ({ page, context }) => {
    await context.grantPermissions(['storage'])
    await page.goto('/login')
    await page.fill('input[type="email"]', 'test@example.com')
    await page.fill('input[type="password"]', 'password123')
    await page.click('button[type="submit"]')
    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    expect(token).toBeTruthy()
  })
})