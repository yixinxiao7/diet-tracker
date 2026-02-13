import { expect, test } from '@playwright/test'
import { addIngredient, addMeal, addMealLog, goToTab, uniqueName } from './helpers'

test('deletes ingredients, meals, and logs', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 50, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 1 })

  await goToTab(page, 'Meal Logs')
  await addMealLog(page, { mealName })

  const logsCard = page.getByRole('heading', { name: 'Recent logs' }).locator('..').locator('..')
  const logRow = logsCard.getByRole('listitem').filter({ hasText: mealName }).first()
  await logRow.getByRole('button', { name: 'Delete' }).click()
  await expect(logRow).toBeHidden()

  await goToTab(page, 'Meals')
  const mealsCard = page.getByRole('heading', { name: 'Saved meals' }).locator('..').locator('..')
  const mealRow = mealsCard.getByRole('listitem').filter({ hasText: mealName }).first()
  await mealRow.getByRole('button', { name: 'Delete' }).click()
  await expect(mealRow).toBeHidden()

  await goToTab(page, 'Ingredients')
  const ingredientsCard = page.getByRole('heading', { name: 'Saved ingredients' }).locator('..').locator('..')
  const ingredientRow = ingredientsCard.getByRole('listitem').filter({ hasText: ingredientName }).first()
  await ingredientRow.getByRole('button', { name: 'Delete' }).click()
  await expect(ingredientRow).toBeHidden()
})
