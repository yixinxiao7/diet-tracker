import { useEffect, useMemo, useState } from 'react'
import {
  getAuthConfigErrors,
  getIdToken,
  getStoredTokens,
  getUserEmail,
  handleAuthCallback,
  login,
  logout,
} from './auth/auth'
import { apiDelete, apiGet, apiPost, apiPut } from './api/client'
import './App.css'

const TABS = [
  { id: 'ingredients', label: 'Ingredients' },
  { id: 'meals', label: 'Meals' },
  { id: 'logs', label: 'Meal Logs' },
  { id: 'summary', label: 'Summary' },
]

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function normalizeIngredientName(name) {
  return String(name || '').trim().toLowerCase()
}

function isDuplicateIngredientName(name, ingredients) {
  const target = normalizeIngredientName(name)
  if (!target) return false
  return ingredients.some((item) => normalizeIngredientName(item.name) === target)
}

function normalizeMealName(name) {
  return String(name || '').trim().toLowerCase()
}

function isDuplicateMealName(name, meals, ignoreId) {
  const target = normalizeMealName(name)
  if (!target) return false
  return meals.some((meal) => {
    if (ignoreId && meal.id === ignoreId) return false
    return normalizeMealName(meal.name) === target
  })
}

function App() {
  const [authStatus, setAuthStatus] = useState('checking')
  const [authError, setAuthError] = useState('')
  const [activeTab, setActiveTab] = useState('ingredients')
  const [userEmail, setUserEmail] = useState('')

  const [ingredients, setIngredients] = useState([])
  const [ingredientsLoading, setIngredientsLoading] = useState(false)
  const [ingredientsError, setIngredientsError] = useState('')
  const [ingredientForm, setIngredientForm] = useState({
    name: '',
    calories: '',
    unit: '',
  })

  const [meals, setMeals] = useState([])
  const [mealsLoading, setMealsLoading] = useState(false)
  const [mealsError, setMealsError] = useState('')
  const [mealDraft, setMealDraft] = useState({ name: '', items: [] })
  const [mealItemDraft, setMealItemDraft] = useState({ ingredientId: '', quantity: '' })
  const [selectedMealId, setSelectedMealId] = useState('')
  const [selectedMeal, setSelectedMeal] = useState(null)
  const [mealDetailLoading, setMealDetailLoading] = useState(false)
  const [mealDetailError, setMealDetailError] = useState('')

  const [mealLogs, setMealLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState('')
  const [logForm, setLogForm] = useState({
    mealId: '',
    date: formatDateInput(new Date()),
    quantity: '1',
  })

  const [dailyDate, setDailyDate] = useState(formatDateInput(new Date()))
  const [dailySummary, setDailySummary] = useState(null)
  const [dailyLoading, setDailyLoading] = useState(false)
  const [dailyError, setDailyError] = useState('')

  const [rangeFrom, setRangeFrom] = useState(formatDateInput(new Date()))
  const [rangeTo, setRangeTo] = useState(formatDateInput(new Date()))
  const [rangeSummary, setRangeSummary] = useState([])
  const [rangeLoading, setRangeLoading] = useState(false)
  const [rangeError, setRangeError] = useState('')

  const [submitting, setSubmitting] = useState('')

  const configErrors = useMemo(() => getAuthConfigErrors(), [])
  const ingredientMap = useMemo(
    () => new Map(ingredients.map((i) => [i.id, i])),
    [ingredients],
  )

  useEffect(() => {
    let cancelled = false

    const initAuth = async () => {
      const applyAuthenticated = () => {
        if (cancelled) return
        setAuthStatus('authenticated')
        setUserEmail(getUserEmail() || '')
      }

      const existingTokens = getStoredTokens()
      if (existingTokens?.id_token) {
        applyAuthenticated()
      }

      try {
        const callback = await handleAuthCallback()
        if (callback?.error && !cancelled) {
          setAuthError(callback.error)
        }
        if (callback?.tokens && !cancelled) {
          applyAuthenticated()
          return
        }
      } catch (err) {
        if (!cancelled) {
          setAuthError(err.message || 'Authentication failed')
        }
      }

      const token = await getIdToken()
      if (cancelled) return

      if (token) {
        applyAuthenticated()
      } else {
        // Check if there's a pending auth flow (another effect processing the code)
        const pendingCode = new URLSearchParams(window.location.search).get('code')
        if (pendingCode) {
          // Wait for the other effect to complete the token exchange
          for (let i = 0; i < 20; i++) {
            await new Promise(resolve => setTimeout(resolve, 100))
            if (cancelled) return
            const tokens = getStoredTokens()
            if (tokens?.id_token) {
              applyAuthenticated()
              return
            }
          }
        }
        setAuthStatus('unauthenticated')
      }
    }

    initAuth()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (authStatus !== 'authenticated') return

    const initUserData = async () => {
      // Bootstrap user in database (idempotent - creates if not exists)
      try {
        await apiPost('/users/bootstrap', {})
      } catch {
        // Ignore - user may already exist (409) or other non-critical error
      }

      // Load user data
      loadIngredients()
      loadMeals()
      loadMealLogs()
    }

    initUserData()
  }, [authStatus])

  const loadIngredients = async () => {
    setIngredientsLoading(true)
    setIngredientsError('')
    try {
      const data = await apiGet('/ingredients?limit=100&offset=0')
      setIngredients(data.ingredients || [])
    } catch (err) {
      setIngredientsError(err.message || 'Failed to load ingredients')
    } finally {
      setIngredientsLoading(false)
    }
  }

  const loadMeals = async () => {
    setMealsLoading(true)
    setMealsError('')
    try {
      const data = await apiGet('/meals?limit=100&offset=0')
      setMeals(data.meals || [])
    } catch (err) {
      setMealsError(err.message || 'Failed to load meals')
    } finally {
      setMealsLoading(false)
    }
  }

  const loadMealLogs = async () => {
    setLogsLoading(true)
    setLogsError('')
    try {
      const data = await apiGet('/meal-logs?limit=100&offset=0')
      setMealLogs(data.meal_logs || [])
    } catch (err) {
      setLogsError(err.message || 'Failed to load meal logs')
    } finally {
      setLogsLoading(false)
    }
  }

  const handleCreateIngredient = async (event) => {
    event.preventDefault()
    if (submitting) return
    setIngredientsError('')
    if (isDuplicateIngredientName(ingredientForm.name, ingredients)) {
      setIngredientsError('Ingredient name already exists')
      return
    }
    setSubmitting('create-ingredient')
    try {
      await apiPost('/ingredients', {
        name: ingredientForm.name.trim(),
        calories_per_unit: Number(ingredientForm.calories),
        unit: ingredientForm.unit.trim(),
      })
      setIngredientForm({ name: '', calories: '', unit: '' })
      loadIngredients()
    } catch (err) {
      setIngredientsError(err.message || 'Failed to create ingredient')
    } finally {
      setSubmitting('')
    }
  }

  const handleDeleteIngredient = async (id) => {
    setIngredientsError('')
    const prev = ingredients
    setIngredients((current) => current.filter((item) => item.id !== id))
    setMealDraft((current) => ({
      ...current,
      items: current.items.filter((item) => item.ingredient_id !== id),
    }))
    try {
      await apiDelete(`/ingredients/${id}`)
    } catch (err) {
      setIngredients(prev)
      setIngredientsError(err.message || 'Failed to delete ingredient')
    }
  }

  const addMealItem = () => {
    if (!mealItemDraft.ingredientId || !mealItemDraft.quantity) return
    setMealDraft((current) => ({
      ...current,
      items: [
        ...current.items,
        {
          ingredient_id: mealItemDraft.ingredientId,
          quantity: Number(mealItemDraft.quantity),
        },
      ],
    }))
    setMealItemDraft({ ingredientId: '', quantity: '' })
  }

  const removeMealItem = (index) => {
    setMealDraft((current) => ({
      ...current,
      items: current.items.filter((_, idx) => idx !== index),
    }))
  }

  const handleCreateMeal = async (event) => {
    event.preventDefault()
    if (submitting) return
    setMealsError('')
    if (isDuplicateMealName(mealDraft.name, meals)) {
      setMealsError('Meal name already exists')
      return
    }
    setSubmitting('create-meal')
    try {
      await apiPost('/meals', {
        name: mealDraft.name.trim(),
        ingredients: mealDraft.items,
      })
      setMealDraft({ name: '', items: [] })
      loadMeals()
    } catch (err) {
      setMealsError(err.message || 'Failed to create meal')
    } finally {
      setSubmitting('')
    }
  }

  const loadMealDetail = async (mealId) => {
    if (!mealId) return
    setMealDetailLoading(true)
    setMealDetailError('')
    try {
      const data = await apiGet(`/meals/${mealId}`)
      setSelectedMeal(data)
      setMealDraft({
        name: data.name,
        items: data.ingredients.map((item) => ({
          ingredient_id: item.ingredient_id,
          quantity: item.quantity,
        })),
      })
    } catch (err) {
      setMealDetailError(err.message || 'Failed to load meal')
    } finally {
      setMealDetailLoading(false)
    }
  }

  const handleUpdateMeal = async () => {
    if (!selectedMealId) return
    setMealsError('')
    if (isDuplicateMealName(mealDraft.name, meals, selectedMealId)) {
      setMealsError('Meal name already exists')
      return
    }
    try {
      await apiPut(`/meals/${selectedMealId}`, {
        name: mealDraft.name.trim(),
        ingredients: mealDraft.items,
      })
      loadMeals()
      loadMealDetail(selectedMealId)
    } catch (err) {
      setMealsError(err.message || 'Failed to update meal')
    }
  }

  const handleDeleteMeal = async (mealId) => {
    setMealsError('')
    const prevMeals = meals
    const prevSelectedId = selectedMealId
    const prevSelectedMeal = selectedMeal
    setMeals((current) => current.filter((m) => m.id !== mealId))
    if (selectedMealId === mealId) {
      setSelectedMealId('')
      setSelectedMeal(null)
    }
    try {
      await apiDelete(`/meals/${mealId}`)
      loadMealLogs()
    } catch (err) {
      setMeals(prevMeals)
      setSelectedMealId(prevSelectedId)
      setSelectedMeal(prevSelectedMeal)
      setMealsError(err.message || 'Failed to delete meal')
    }
  }

  const handleCreateLog = async (event) => {
    event.preventDefault()
    if (submitting) return
    setLogsError('')
    setSubmitting('create-log')
    try {
      await apiPost('/meal-logs', {
        meal_id: logForm.mealId,
        date: logForm.date,
        quantity: Number(logForm.quantity),
      })
      loadMealLogs()
    } catch (err) {
      setLogsError(err.message || 'Failed to log meal')
    } finally {
      setSubmitting('')
    }
  }

  const handleDeleteLog = async (logId) => {
    setLogsError('')
    const prev = mealLogs
    setMealLogs((current) => current.filter((log) => log.id !== logId))
    try {
      await apiDelete(`/meal-logs/${logId}`)
    } catch (err) {
      setMealLogs(prev)
      setLogsError(err.message || 'Failed to delete log')
    }
  }

  const handleDailySummary = async (event) => {
    event.preventDefault()
    setDailyError('')
    setDailyLoading(true)
    try {
      const data = await apiGet(`/daily-summary?date=${dailyDate}`)
      setDailySummary(data)
    } catch (err) {
      setDailyError(err.message || 'Failed to load summary')
    } finally {
      setDailyLoading(false)
    }
  }

  const handleRangeSummary = async (event) => {
    event.preventDefault()
    setRangeError('')
    setRangeLoading(true)
    try {
      const data = await apiGet(`/daily-summary?from=${rangeFrom}&to=${rangeTo}`)
      setRangeSummary(data.days || [])
    } catch (err) {
      setRangeError(err.message || 'Failed to load range summary')
    } finally {
      setRangeLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="hero">
          <p className="eyebrow">Diet Tracker</p>
          <h1>Plan with intention.</h1>
          <p className="subtitle">
            Ingredients, meals, logs, and daily totals in one place.
          </p>
        </div>
        <div className="auth-card">
          <div>
            {authStatus === 'authenticated' ? (
              <p className="meta-value">{userEmail || 'Signed in'}</p>
            ) : (
              <p className="meta-value muted">Not signed in</p>
            )}
          </div>
          {authStatus === 'checking' && (
            <button className="button ghost" disabled>
              Checking...
            </button>
          )}
          {authStatus === 'unauthenticated' && (
            <button className="button primary" onClick={login}>
              Sign in
            </button>
          )}
          {authStatus === 'authenticated' && (
            <button className="button ghost" onClick={logout}>
              Log out
            </button>
          )}
        </div>
      </header>

      {configErrors.length > 0 && (
        <div className="alert warning" role="alert">
          Missing environment variables: {configErrors.join(', ')}
        </div>
      )}
      {authError && <div className="alert error" role="alert">{authError}</div>}

      <nav className="tabs" role="tablist" aria-label="Main sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="panel">
        {authStatus !== 'authenticated' && (
          <div className="empty-state">
            <h2>Track what you eat, effortlessly</h2>
            <p className="muted">
              Add ingredients with calorie info, combine them into meals, then log what you eat each day to see your totals.
            </p>
            <button className="button primary" onClick={login}>
              Sign in to get started
            </button>
          </div>
        )}

        {authStatus === 'authenticated' && activeTab === 'ingredients' && (
          <section className="section" role="tabpanel" id="panel-ingredients" aria-labelledby="tab-ingredients">
            <div className="section-header">
              <h2>Ingredients</h2>
              <p>Build your pantry with calorie data per unit.</p>
            </div>

            <form className="form" onSubmit={handleCreateIngredient}>
              <div className="field">
                <label htmlFor="ingredient-name">Name</label>
                <input
                  id="ingredient-name"
                  value={ingredientForm.name}
                  onChange={(event) =>
                    setIngredientForm((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Brown rice"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="ingredient-calories">Calories per unit</label>
                <input
                  id="ingredient-calories"
                  type="number"
                  min="0"
                  value={ingredientForm.calories}
                  onChange={(event) =>
                    setIngredientForm((current) => ({ ...current, calories: event.target.value }))
                  }
                  placeholder="120"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="ingredient-unit">Unit</label>
                <input
                  id="ingredient-unit"
                  value={ingredientForm.unit}
                  onChange={(event) =>
                    setIngredientForm((current) => ({ ...current, unit: event.target.value }))
                  }
                  placeholder="g, ml, tbsp"
                  required
                />
              </div>
              <button className="button primary" type="submit" disabled={submitting === 'create-ingredient'}>
                {submitting === 'create-ingredient' ? 'Adding...' : 'Add ingredient'}
              </button>
              {ingredientsError && <p className="form-error" role="alert">{ingredientsError}</p>}
            </form>

            <div className="card list">
              <div className="list-header">
                <h3>Saved ingredients</h3>
                {ingredientsLoading && <span className="pill" aria-live="polite">Loading</span>}
              </div>
              {ingredients.length === 0 && !ingredientsLoading && (
                <p className="muted">Add your first ingredient above — it will appear here so you can use it in meals.</p>
              )}
              <ul role="list">
                {ingredients.map((item) => (
                  <li key={item.id} className="list-row">
                    <div>
                      <strong>{item.name}</strong>
                      <span className="cal-value">{item.calories_per_unit} cal / {item.unit}</span>
                    </div>
                    <button
                      className="button ghost"
                      type="button"
                      onClick={() => handleDeleteIngredient(item.id)}
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {authStatus === 'authenticated' && activeTab === 'meals' && (
          <section className="section" role="tabpanel" id="panel-meals" aria-labelledby="tab-meals">
            <div className="section-header">
              <h2>Meals</h2>
              <p>Combine ingredients into reusable meals.</p>
            </div>

            <form className="form" onSubmit={handleCreateMeal}>
              <div className="field">
                <label htmlFor="meal-name">Meal name</label>
                <input
                  id="meal-name"
                  value={mealDraft.name}
                  onChange={(event) =>
                    setMealDraft((current) => ({ ...current, name: event.target.value }))
                  }
                  placeholder="Weekday lunch"
                  required
                />
              </div>
              <div className="inline-group">
                <div className="field">
                  <label htmlFor="meal-ingredient">Ingredient</label>
                  <select
                    id="meal-ingredient"
                    value={mealItemDraft.ingredientId}
                    onChange={(event) =>
                      setMealItemDraft((current) => ({
                        ...current,
                        ingredientId: event.target.value,
                      }))
                    }
                  >
                    <option value="">Select ingredient</option>
                    {ingredients.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="meal-ingredient-quantity">Quantity</label>
                  <input
                    id="meal-ingredient-quantity"
                    type="number"
                    min="0"
                    step="0.1"
                    value={mealItemDraft.quantity}
                    onChange={(event) =>
                      setMealItemDraft((current) => ({ ...current, quantity: event.target.value }))
                    }
                  />
                </div>
                <button className="button ghost" type="button" onClick={addMealItem}>
                  Add
                </button>
              </div>

              <ul className="mini-list">
                {mealDraft.items.map((item, index) => {
                  const ingredient = ingredientMap.get(item.ingredient_id)
                  return (
                    <li key={`${item.ingredient_id}-${index}`}>
                      <span>{ingredient?.name || 'Ingredient'}</span>
                      <span>{item.quantity}</span>
                      <button
                        className="button ghost"
                        type="button"
                        onClick={() => removeMealItem(index)}
                      >
                        Remove
                      </button>
                    </li>
                  )
                })}
              </ul>

              <button className="button primary" type="submit" disabled={submitting === 'create-meal'}>
                {submitting === 'create-meal' ? 'Saving...' : 'Save meal'}
              </button>
              {mealsError && <p className="form-error" role="alert">{mealsError}</p>}
            </form>

            <div className="grid">
              <div className="card list">
                <div className="list-header">
                  <h3>Saved meals</h3>
                  {mealsLoading && <span className="pill">Loading</span>}
                </div>
                {meals.length === 0 && !mealsLoading && (
                  <p className="muted">Create a meal by combining ingredients above. Saved meals appear here for easy logging.</p>
                )}
                <ul role="list">
                  {meals.map((meal) => (
                    <li key={meal.id} className="list-row">
                      <div>
                        <strong>{meal.name}</strong>
                        <span className="cal-value">{meal.total_calories} cal</span>
                      </div>
                      <div className="row-actions">
                        <button
                          className="button ghost"
                          type="button"
                          onClick={() => {
                            setSelectedMealId(meal.id)
                            loadMealDetail(meal.id)
                          }}
                        >
                          View
                        </button>
                        <button
                          className="button ghost"
                          type="button"
                          onClick={() => handleDeleteMeal(meal.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="card detail">
                <div className="list-header">
                  <h3>Meal details</h3>
                  {mealDetailLoading && <span className="pill">Loading</span>}
                </div>
                {mealDetailError && <p className="form-error" role="alert">{mealDetailError}</p>}
                {!selectedMeal && !mealDetailLoading && (
                  <p className="muted">Click "View" on a meal to see its ingredients and edit it.</p>
                )}
                {selectedMeal && (
                  <>
                    <h4>{selectedMeal.name}</h4>
                    <p className="muted">Total {selectedMeal.total_calories} cal</p>
                    <ul className="mini-list">
                      {selectedMeal.ingredients.map((item) => (
                        <li key={item.ingredient_id}>
                          <span>{item.name}</span>
                          <span>{item.quantity} {item.unit}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="detail-actions">
                      <button className="button primary" type="button" onClick={handleUpdateMeal}>
                        Save changes
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        )}

        {authStatus === 'authenticated' && activeTab === 'logs' && (
          <section className="section" role="tabpanel" id="panel-logs" aria-labelledby="tab-logs">
            <div className="section-header">
              <h2>Meal Logs</h2>
              <p>Track what you eat and when.</p>
            </div>

            <form className="form" onSubmit={handleCreateLog}>
              <div className="field">
                <label htmlFor="log-meal">Meal</label>
                <select
                  id="log-meal"
                  value={logForm.mealId}
                  onChange={(event) =>
                    setLogForm((current) => ({ ...current, mealId: event.target.value }))
                  }
                  required
                >
                  <option value="">Select meal</option>
                  {meals.map((meal) => (
                    <option key={meal.id} value={meal.id}>
                      {meal.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="log-date">Date</label>
                <input
                  id="log-date"
                  type="date"
                  value={logForm.date}
                  onChange={(event) =>
                    setLogForm((current) => ({ ...current, date: event.target.value }))
                  }
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="log-quantity">Quantity</label>
                <input
                  id="log-quantity"
                  type="number"
                  min="1"
                  step="1"
                  value={logForm.quantity}
                  onChange={(event) =>
                    setLogForm((current) => ({ ...current, quantity: event.target.value }))
                  }
                  required
                />
              </div>
              <button className="button primary" type="submit" disabled={submitting === 'create-log'}>
                {submitting === 'create-log' ? 'Logging...' : 'Log meal'}
              </button>
              {logsError && <p className="form-error" role="alert">{logsError}</p>}
            </form>

            <div className="card list">
              <div className="list-header">
                <h3>Recent logs</h3>
                {logsLoading && <span className="pill" aria-live="polite">Loading</span>}
              </div>
              {mealLogs.length === 0 && !logsLoading && (
                <p className="muted">Log a meal above to start tracking your daily intake. Check the Summary tab to see your totals.</p>
              )}
              <ul role="list">
                {mealLogs.map((log) => (
                  <li key={log.id} className="list-row">
                    <div>
                      <strong>{log.meal_name}</strong>
                      <span className="meta-text">{log.date} • {log.quantity}x</span>
                    </div>
                    <button
                      className="button ghost"
                      type="button"
                      onClick={() => handleDeleteLog(log.id)}
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {authStatus === 'authenticated' && activeTab === 'summary' && (
          <section className="section" role="tabpanel" id="panel-summary" aria-labelledby="tab-summary">
            <div className="section-header">
              <h2>Summary</h2>
              <p>See your totals for a day or date range.</p>
            </div>

            <div className="grid">
              <form className="card form" onSubmit={handleDailySummary}>
                <h3>Daily total</h3>
                <div className="field">
                  <label htmlFor="summary-date">Date</label>
                  <input
                    id="summary-date"
                    type="date"
                    value={dailyDate}
                    onChange={(event) => setDailyDate(event.target.value)}
                    required
                  />
                </div>
                <button className="button primary" type="submit">
                  Get summary
                </button>
                {dailyLoading && <p className="muted">Loading...</p>}
                {dailyError && <p className="form-error" role="alert">{dailyError}</p>}
                {dailySummary && !dailyLoading && (
                  <div className="summary-card">
                    <p>Total</p>
                    <strong>{dailySummary.total_calories} cal</strong>
                  </div>
                )}
              </form>

              <form className="card form" onSubmit={handleRangeSummary}>
                <h3>Date range</h3>
                <div className="field">
                  <label htmlFor="range-from">From</label>
                  <input
                    id="range-from"
                    type="date"
                    value={rangeFrom}
                    onChange={(event) => setRangeFrom(event.target.value)}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="range-to">To</label>
                  <input
                    id="range-to"
                    type="date"
                    value={rangeTo}
                    onChange={(event) => setRangeTo(event.target.value)}
                    required
                  />
                </div>
                <button className="button primary" type="submit">
                  Get range
                </button>
                {rangeLoading && <p className="muted">Loading...</p>}
                {rangeError && <p className="form-error" role="alert">{rangeError}</p>}
                {rangeSummary.length > 0 && !rangeLoading && (
                  <ul className="mini-list">
                    {rangeSummary.map((day) => (
                      <li key={day.date}>
                        <span>{day.date}</span>
                        <span>{day.total_calories} cal</span>
                      </li>
                    ))}
                  </ul>
                )}
              </form>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
