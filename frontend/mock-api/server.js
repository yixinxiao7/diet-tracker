import http from 'node:http'
import { randomUUID } from 'node:crypto'

const PORT = Number(process.env.MOCK_API_PORT || 8787)

const ingredients = new Map()
const meals = new Map()
const mealLogs = new Map()

function seedData() {
  const ingredientA = createIngredient({
    name: 'Brown rice',
    calories_per_unit: 1.2,
    unit: 'g',
  })
  const ingredientB = createIngredient({
    name: 'Chicken breast',
    calories_per_unit: 1.65,
    unit: 'g',
  })
  const ingredientC = createIngredient({
    name: 'Olive oil',
    calories_per_unit: 8.0,
    unit: 'tbsp',
  })

  createMeal({
    name: 'Weekday lunch',
    ingredients: [
      { ingredient_id: ingredientA.id, quantity: 180 },
      { ingredient_id: ingredientB.id, quantity: 140 },
      { ingredient_id: ingredientC.id, quantity: 1 },
    ],
  })
}

function jsonResponse(res, status, payload) {
  const body = payload ? JSON.stringify(payload) : ''
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
  })
  res.end(body)
}

function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    let raw = ''
    req.on('data', (chunk) => {
      raw += chunk
    })
    req.on('end', () => {
      if (!raw) {
        resolve(null)
        return
      }
      try {
        resolve(JSON.parse(raw))
      } catch (error) {
        reject(error)
      }
    })
  })
}

function createIngredient(payload) {
  const id = randomUUID()
  const item = {
    id,
    name: payload.name,
    calories_per_unit: Number(payload.calories_per_unit || 0),
    unit: payload.unit,
  }
  ingredients.set(id, item)
  return item
}

function createMeal(payload) {
  const id = randomUUID()
  const item = {
    id,
    name: payload.name,
    ingredients: payload.ingredients || [],
  }
  meals.set(id, item)
  return item
}

function normalizeName(name) {
  return String(name || '').trim().toLowerCase()
}

function hasDuplicateIngredientName(name, ignoreId) {
  const target = normalizeName(name)
  if (!target) return false
  for (const ingredient of ingredients.values()) {
    if (ignoreId && ingredient.id === ignoreId) continue
    if (normalizeName(ingredient.name) === target) {
      return true
    }
  }
  return false
}

function hasDuplicateMealName(name, ignoreId) {
  const target = normalizeName(name)
  if (!target) return false
  for (const meal of meals.values()) {
    if (ignoreId && meal.id === ignoreId) continue
    if (normalizeName(meal.name) === target) {
      return true
    }
  }
  return false
}

function createMealLog(payload) {
  const id = randomUUID()
  const item = {
    id,
    meal_id: payload.meal_id,
    date: payload.date,
    quantity: Number(payload.quantity || 0),
  }
  mealLogs.set(id, item)
  return item
}

function getMealCalories(meal) {
  return meal.ingredients.reduce((total, item) => {
    const ingredient = ingredients.get(item.ingredient_id)
    if (!ingredient) return total
    return total + ingredient.calories_per_unit * Number(item.quantity || 0)
  }, 0)
}

function mapMealListItem(meal) {
  return {
    id: meal.id,
    name: meal.name,
    total_calories: Math.round(getMealCalories(meal)),
  }
}

function mapMealDetail(meal) {
  const ingredientsDetail = meal.ingredients.map((item) => {
    const ingredient = ingredients.get(item.ingredient_id)
    const caloriesPerUnit = ingredient ? ingredient.calories_per_unit : 0
    const caloriesTotal = caloriesPerUnit * Number(item.quantity || 0)
    return {
      ingredient_id: item.ingredient_id,
      name: ingredient?.name || 'Unknown',
      unit: ingredient?.unit || '',
      quantity: item.quantity,
      calories_per_unit: caloriesPerUnit,
      calories_total: Math.round(caloriesTotal),
    }
  })

  return {
    id: meal.id,
    name: meal.name,
    total_calories: Math.round(getMealCalories(meal)),
    ingredients: ingredientsDetail,
  }
}

function mapMealLog(log) {
  const meal = meals.get(log.meal_id)
  return {
    id: log.id,
    meal_id: log.meal_id,
    meal_name: meal?.name || 'Unknown meal',
    date: log.date,
    quantity: log.quantity,
  }
}

function dateKey(input) {
  if (!input) return ''
  return input
}

function addDays(date, days) {
  const next = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))
  next.setUTCDate(next.getUTCDate() + days)
  return next
}

function eachDay(from, to) {
  const days = []
  let cursor = new Date(`${from}T00:00:00Z`)
  const end = new Date(`${to}T00:00:00Z`)
  while (cursor <= end) {
    days.push(cursor.toISOString().slice(0, 10))
    cursor = addDays(cursor, 1)
  }
  return days
}

function dailyTotalFor(date) {
  let total = 0
  for (const log of mealLogs.values()) {
    if (log.date !== date) continue
    const meal = meals.get(log.meal_id)
    if (!meal) continue
    total += getMealCalories(meal) * Number(log.quantity || 0)
  }
  return Math.round(total)
}

seedData()

const server = http.createServer(async (req, res) => {
  if (!req.url) {
    jsonResponse(res, 400, { error: 'Missing URL' })
    return
  }

  if (req.method === 'OPTIONS') {
    jsonResponse(res, 204, null)
    return
  }

  const url = new URL(req.url, `http://${req.headers.host}`)
  const path = url.pathname

  try {
    if (req.method === 'GET' && path === '/ingredients') {
      jsonResponse(res, 200, { ingredients: Array.from(ingredients.values()) })
      return
    }

    if (req.method === 'POST' && path === '/ingredients') {
      const body = await parseJsonBody(req)
      if (!body?.name || !body?.unit) {
        jsonResponse(res, 400, { error: 'Invalid ingredient payload' })
        return
      }
      if (hasDuplicateIngredientName(body.name)) {
        jsonResponse(res, 409, { error: 'Ingredient name already exists' })
        return
      }
      const created = createIngredient(body)
      jsonResponse(res, 201, created)
      return
    }

    if (req.method === 'DELETE' && path.startsWith('/ingredients/')) {
      const id = path.split('/')[2]
      ingredients.delete(id)
      for (const meal of meals.values()) {
        meal.ingredients = meal.ingredients.filter((item) => item.ingredient_id !== id)
      }
      jsonResponse(res, 204, null)
      return
    }

    if (req.method === 'GET' && path === '/meals') {
      const list = Array.from(meals.values()).map(mapMealListItem)
      jsonResponse(res, 200, { meals: list })
      return
    }

    if (req.method === 'POST' && path === '/meals') {
      const body = await parseJsonBody(req)
      if (!body?.name) {
        jsonResponse(res, 400, { error: 'Invalid meal payload' })
        return
      }
      if (hasDuplicateMealName(body.name)) {
        jsonResponse(res, 409, { error: 'Meal name already exists' })
        return
      }
      const created = createMeal(body)
      jsonResponse(res, 201, mapMealDetail(created))
      return
    }

    if (req.method === 'GET' && path.startsWith('/meals/')) {
      const id = path.split('/')[2]
      const meal = meals.get(id)
      if (!meal) {
        jsonResponse(res, 404, { error: 'Meal not found' })
        return
      }
      jsonResponse(res, 200, mapMealDetail(meal))
      return
    }

    if (req.method === 'PUT' && path.startsWith('/meals/')) {
      const id = path.split('/')[2]
      const meal = meals.get(id)
      if (!meal) {
        jsonResponse(res, 404, { error: 'Meal not found' })
        return
      }
      const body = await parseJsonBody(req)
      if (body?.name) {
        if (hasDuplicateMealName(body.name, id)) {
          jsonResponse(res, 409, { error: 'Meal name already exists' })
          return
        }
        meal.name = body.name
      }
      if (Array.isArray(body?.ingredients)) {
        meal.ingredients = body.ingredients
      }
      jsonResponse(res, 200, mapMealDetail(meal))
      return
    }

    if (req.method === 'DELETE' && path.startsWith('/meals/')) {
      const id = path.split('/')[2]
      meals.delete(id)
      for (const [logId, log] of mealLogs.entries()) {
        if (log.meal_id === id) {
          mealLogs.delete(logId)
        }
      }
      jsonResponse(res, 204, null)
      return
    }

    if (req.method === 'GET' && path === '/meal-logs') {
      const list = Array.from(mealLogs.values()).map(mapMealLog)
      jsonResponse(res, 200, { meal_logs: list })
      return
    }

    if (req.method === 'POST' && path === '/meal-logs') {
      const body = await parseJsonBody(req)
      if (!body?.meal_id || !body?.date) {
        jsonResponse(res, 400, { error: 'Invalid meal log payload' })
        return
      }
      const created = createMealLog(body)
      jsonResponse(res, 201, mapMealLog(created))
      return
    }

    if (req.method === 'DELETE' && path.startsWith('/meal-logs/')) {
      const id = path.split('/')[2]
      mealLogs.delete(id)
      jsonResponse(res, 204, null)
      return
    }

    if (req.method === 'GET' && path === '/daily-summary') {
      const date = url.searchParams.get('date')
      const from = url.searchParams.get('from')
      const to = url.searchParams.get('to')

      if (date) {
        jsonResponse(res, 200, {
          date: dateKey(date),
          total_calories: dailyTotalFor(dateKey(date)),
        })
        return
      }

      if (from && to) {
        const days = eachDay(from, to).map((day) => ({
          date: day,
          total_calories: dailyTotalFor(day),
        }))
        jsonResponse(res, 200, { days })
        return
      }
    }

    jsonResponse(res, 404, { error: 'Not found' })
  } catch (error) {
    jsonResponse(res, 500, { error: error?.message || 'Server error' })
  }
})

server.listen(PORT, () => {
  console.log(`Mock API listening on http://localhost:${PORT}`)
})
