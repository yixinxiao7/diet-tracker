import { expect, test } from '@playwright/test'

test('shows error banner when ingredients load fails', async ({ page }) => {
  await page.route('**/ingredients?*', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Failed to load ingredients (test)' }),
    })
  })

  await page.goto('/')

  await expect(page.getByText('Failed to load ingredients (test)')).toBeVisible()
})
