import { test, expect } from '@playwright/test'

test('debug login flow', async ({ page }) => {
  await page.goto('http://localhost:5173')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(500)

  // Log console messages
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[BROWSER ${msg.type()}]`, msg.text())
    }
  })

  // Take screenshot of login page
  await page.screenshot({ path: '/tmp/opencode/debug-login.png' })
  console.log('Screenshot saved to /tmp/opencode/debug-login.png')

  // Try bad login
  await page.fill('input#email', 'bad@test.com')
  await page.fill('input#password', 'badpass')
  await page.click('button[type="submit"]')

  // Wait for either error message or navigation
  await page.waitForTimeout(3000)
  await page.screenshot({ path: '/tmp/opencode/debug-login-after.png' })

  // Check page state
  const pageText = await page.textContent('body')
  console.log('Page text after login:', pageText?.substring(0, 500))
  console.log('Current URL:', page.url())

  // Check for error element
  const errorEl = page.locator('.text-destructive')
  const errorCount = await errorEl.count()
  console.log('Error elements:', errorCount)
  if (errorCount > 0) {
    console.log('Error text:', await errorEl.first().textContent())
  }
})
