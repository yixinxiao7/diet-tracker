import { expect, test } from '@playwright/test'

test('auth bypass shows signed-in state without connect button', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible()
  await expect(page.getByText('Not connected')).toBeHidden()
  await expect(page.getByRole('button', { name: 'Connect Cognito' })).toBeHidden()
})
