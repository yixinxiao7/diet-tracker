import { expect, test } from '@playwright/test'
import { addIngredient, addMeal, addMealLog, goToTab, uniqueName } from './helpers'

test('logs a meal and shows it in recent logs', async ({ page }) => {
  await page.goto('/')

  const ingredientName = uniqueName('Ingredient')
  await addIngredient(page, { name: ingredientName, caloriesPerUnit: 150, unit: 'g' })

  await goToTab(page, 'Meals')
  const mealName = uniqueName('Meal')
  await addMeal(page, { name: mealName, ingredientName, quantity: 1 })

  await goToTab(page, 'Meal Logs')
  await addMealLog(page, { mealName })
  const logsCard = page.getByRole('heading', { name: 'Recent logs' }).locator('..').locator('..')
  await expect(logsCard.locator('strong', { hasText: mealName })).toBeVisible()
})
