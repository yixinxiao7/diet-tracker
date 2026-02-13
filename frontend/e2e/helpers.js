export function uniqueName(prefix) {
  return `${prefix}-${Date.now()}`
}

export async function goToTab(page, name) {
  await page.getByRole('button', { name }).click()
}

export async function addIngredient(page, { name, caloriesPerUnit, unit = 'g' }) {
  await page.getByLabel('Name').fill(name)
  await page.getByLabel('Calories per unit').fill(String(caloriesPerUnit))
  await page.getByLabel('Unit', { exact: true }).fill(unit)
  await page.getByRole('button', { name: 'Add ingredient' }).click()
}

export async function addMeal(page, { name, ingredientName, quantity = 1 }) {
  await page.getByLabel('Meal name').fill(name)
  await page.getByLabel('Ingredient').selectOption({ label: ingredientName })
  await page.getByLabel('Quantity').fill(String(quantity))
  await page.getByRole('button', { name: 'Add' }).click()
  await page.getByRole('button', { name: 'Save meal' }).click()
}

export async function addMealLog(page, { mealName, date }) {
  await page.getByLabel('Meal').selectOption({ label: mealName })
  if (date) {
    await page.getByLabel('Date').fill(date)
  }
  await page.getByRole('button', { name: 'Log meal' }).click()
}
