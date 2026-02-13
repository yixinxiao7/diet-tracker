import { expect, test } from '@playwright/test'
import { addIngredient, addMeal, goToTab, uniqueName } from './helpers'

test('creates meals with totals and blocks duplicate names', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 100, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 2 })

  const mealsCard = page.getByRole('heading', { name: 'Saved meals' }).locator('..').locator('..')
  const mealRow = mealsCard.getByRole('listitem').filter({ hasText: mealName }).first()
  await expect(mealRow).toContainText('200 cal')

  await page.getByLabel('Meal name').fill(mealName)
  await page.getByRole('button', { name: 'Save meal' }).click()
  await expect(page.getByText('Meal name already exists')).toBeVisible()
})

test('edits a meal and persists updated ingredients', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 80, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 1 })

  const mealRow = page.getByRole('listitem').filter({ hasText: mealName }).first()
  await mealRow.getByRole('button', { name: 'View' }).click()
  await expect(page.getByRole('heading', { name: mealName })).toBeVisible()

  await page.getByLabel('Meal name').fill(`${mealName} Updated`)
  await page.getByLabel('Ingredient').selectOption({ label: ingredientName })
  await page.getByLabel('Quantity').fill('2')
  await page.getByRole('button', { name: 'Add' }).click()
  await page.getByRole('button', { name: 'Save changes' }).click()

  await expect(page.getByRole('heading', { name: `${mealName} Updated` })).toBeVisible()
  const detailCard = page.getByRole('heading', { name: 'Meal details' }).locator('..').locator('..')
  const updatedItem = detailCard
    .locator('li', { hasText: ingredientName })
    .filter({ hasText: '2 g' })
    .first()
  await expect(updatedItem).toBeVisible()
})
