# TO_FIX.md — Test Suite Improvements

**Status: All items resolved**

---

## P1 — Fix Existing Test Issues

### 1. ✅ Remove Duplicate FakeCursor/FakeConnection in test_users.py

**File:** `backend/tests/test_users.py`

**Resolution:** Removed duplicate classes, now imports from `conftest.py`. Tests verify `conn.committed` and `conn.closed`.

---

### 2. ✅ Fix test_response.py Module Reload Side Effect

**File:** `backend/tests/test_response.py`

**Resolution:** Added `try/finally` to reset module state. Added `test_response_default_origin` test.

---

## P2 — Expand Validation Tests

### 3. ✅ Add Parameterized Tests for Validation Functions

**File:** `backend/tests/test_validation.py`

**Resolution:** Added parameterized tests with 14 UUID cases and 17 date cases covering edge cases (uppercase, leap years, invalid formats, None, empty strings).

---

## P3 — Add Missing Lambda Tests

### 4. ✅ Create test_meals.py

**File:** `backend/tests/test_meals.py`

**Resolution:** Created with 12 tests covering:
- Input validation (missing fields, invalid pagination, invalid UUID)
- CRUD operations (create, list, get, update, delete)
- Transaction handling (commit on success, rollback on failure)
- Helper function tests (`_load_ingredient_calories`, `_get_user_id_or_404`)

---

### 5. ✅ Create test_ingredients.py

**File:** `backend/tests/test_ingredients.py`

**Resolution:** Created with 10 tests covering:
- Input validation (missing fields, invalid pagination, invalid UUID)
- CRUD operations
- Cascade delete warning (409 response)
- Force delete with `?force=true`

---

### 6. ✅ Create test_meal_logs.py

**File:** `backend/tests/test_meal_logs.py`

**Resolution:** Created with 7 tests covering:
- Date validation (invalid format returns 400)
- UUID validation
- CRUD operations with date filtering

---

### 7. ✅ Create test_summary.py

**File:** `backend/tests/test_summary.py`

**Resolution:** Created with 6 tests covering:
- Missing/invalid date parameters
- Daily summary endpoint
- Range summary endpoint

---

## P4 — Add Test for Logging Module

### 8. ✅ Create test_logging.py

**File:** `backend/tests/test_logging.py`

**Resolution:** Created with 4 tests covering:
- Logger instance creation
- Default log level (INFO)
- Handler attachment
- Singleton behavior (same logger returned for same name)

---

## Bonus — Additional Tests Created

### ✅ test_handlers.py

**File:** `backend/tests/test_handlers.py`

Tests route dispatching for all 4 Lambda handlers (meals, meal_logs, summary, users).

---

### ✅ test_db.py

**File:** `backend/tests/test_db.py`

Tests for `db.py` module:
- `get_internal_user_id` (found and not found cases)
- Secret caching (only fetched once)
- Connection pooling (same connection returned)

---

## Verification Checklist

- [x] All tests pass
- [x] No import errors
- [x] Coverage improved

### Test Files Summary

| File | Tests |
|------|-------|
| test_auth.py | 2 |
| test_response.py | 2 |
| test_validation.py | 31 (parameterized) |
| test_users.py | 3 |
| test_meals.py | 12 |
| test_ingredients.py | 10 |
| test_meal_logs.py | 7 |
| test_summary.py | 6 |
| test_logging.py | 4 |
| test_handlers.py | 6 |
| test_db.py | 3 |

**Total: 86 test cases**
