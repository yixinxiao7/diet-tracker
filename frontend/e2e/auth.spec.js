import { expect, test } from '@playwright/test'

test('auth bypass shows signed-in state', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible()
  await expect(page.getByText('test@example.com')).toBeVisible()
})

test('log out shows the sign-in form and signing in returns to the app', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Log out' }).click()

  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByLabel('Password')).toBeVisible()

  await page.getByRole('button', { name: 'Create an account' }).click()
  await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible()
  await page.getByRole('button', { name: 'Sign in' }).click()

  await page.getByLabel('Email').fill('test@example.com')
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible()
})

test('log out resets the signed-in view', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('tab', { name: 'Summary' }).click()
  await expect(page.getByRole('tab', { name: 'Summary' })).toHaveAttribute('aria-selected', 'true')

  await page.getByRole('button', { name: 'Log out' }).click()
  await page.getByLabel('Email').fill('test@example.com')
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('tab', { name: 'Ingredients' })).toHaveAttribute('aria-selected', 'true')
})
