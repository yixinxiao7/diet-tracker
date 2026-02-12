import { expect, test } from '@playwright/test'
import { addIngredient, uniqueName } from './helpers'

test('creates ingredients and blocks duplicate names', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 100, unit: 'g' })
  await expect(page.getByText(ingredientName)).toBeVisible()

  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 120, unit: 'g' })
  await expect(page.getByText('Ingredient name already exists')).toBeVisible()
})
