import { expect, test } from '@playwright/test'
import { addIngredient, addMeal, addMealLog, goToTab, uniqueName } from './helpers'

test('shows daily summary totals', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 150, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 1 })

  await goToTab(page, 'Meal Logs')
  await addMealLog(page, { mealName, date: '2024-01-10' })

  await goToTab(page, 'Summary')
  await page.getByLabel('Date').fill('2024-01-10')
  await page.getByRole('button', { name: 'Get summary' }).click()

  const dailyForm = page.getByRole('heading', { name: 'Daily total' }).locator('..')
  await expect(dailyForm.locator('strong', { hasText: '150' })).toBeVisible()
})

test('shows range summary totals for multiple dates', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 120, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 1 })

  await goToTab(page, 'Meal Logs')
  await addMealLog(page, { mealName, date: '2024-01-01' })
  await addMealLog(page, { mealName, date: '2024-01-03' })

  await goToTab(page, 'Summary')
  await page.getByLabel('From').fill('2024-01-01')
  await page.getByLabel('To').fill('2024-01-03')
  await page.getByRole('button', { name: 'Get range' }).click()

  const rangeForm = page.getByRole('heading', { name: 'Date range' }).locator('..')
  await expect(rangeForm.getByRole('listitem').filter({ hasText: '2024-01-01' })).toContainText('120 cal')
  await expect(rangeForm.getByRole('listitem').filter({ hasText: '2024-01-02' })).toContainText('0 cal')
  await expect(rangeForm.getByRole('listitem').filter({ hasText: '2024-01-03' })).toContainText('120 cal')
})
