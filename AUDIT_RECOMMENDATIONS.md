# Code Audit Recommendations

## Critical Priority (Fix Immediately)

- [x] **Cross-user ingredient deletion vulnerability** - `backend/lambdas/meals/ingredients.py:172` - Fixed: cascade check query now verifies ingredient ownership via JOIN
- [x] **Schema mismatch with RDS** - Fixed: migration applied to align RDS with `infra/sql/schema.sql`
- [x] **Unhandled KeyError on pathParameters** - Fixed: added `get_path_param()` helper in `validation.py` and updated all handlers
- [x] **Unhandled KeyError on event data** - Fixed: all handlers now use `.get()` with validation for `httpMethod` and `resource`

## High Priority (Before Production)

### Security
- [x] **Broken boolean type checking** - Fixed: reordered condition in `meal_logs.py:37` to check `isinstance(quantity, bool)` first
- [x] **No upper bounds on numeric inputs** - Fixed: added MAX_CALORIES (100k) and MAX_QUANTITY (10k) limits in `validation.py`
- [ ] **No request size limits** - All Lambda handlers accept unbounded request payloads (handled at API Gateway level)
- [x] **No statement timeout on database** - Fixed: added `statement_timeout=30000` (30s) option in `db.py`
- [x] **No string length validation** - Fixed: added MAX_NAME_LENGTH (255) and MAX_UNIT_LENGTH (50) validation

### Database Schema
- [ ] **Missing NOT NULL on user_id columns** - `ingredients.user_id` (line 12) and `meals.user_id` (line 20) in `schema.sql` allow NULL
- [ ] **Missing index on meal_ingredients.ingredient_id** - Cascade deletes will full-scan without this index
- [ ] **Missing index on meal_logs.meal_id** - Summary joins will scan without this index

### Infrastructure
- [ ] **RDS security group allows 0.0.0.0/0 on port 5432** - PostgreSQL is open to the entire internet; restrict to Lambda security group or VPC CIDR only
- [ ] **Document IAM role permissions** - `diet-tracker-execution-role` permissions are not documented; audit for least privilege
- [ ] **Restrict deployment to main branch only** - Currently deploys on `main` and `lambda-deployment` branches (deploy-lambdas.yml:4-7)

## Medium Priority

### Security
- [x] **Connection reuse without health check** - Fixed: added `_is_connection_healthy()` check in `db.py` before reusing connections
- [ ] **No rate limiting** - All API endpoints lack rate limiting protection (recommend API Gateway throttling)
- [x] **Information leakage in error messages** - Fixed: removed usage count from error message in `ingredients.py`
- [x] **No validation of calorie values** - Fixed: added `validate_calories()` in `validation.py` rejecting negatives and values > 100k
- [x] **No deduplication of ingredient IDs** - Fixed: added duplicate check in `meals.py` create_meal and update_meal

### Infrastructure
- [ ] **Hardcoded AWS account ID** - `deploy-lambdas.yml:75` exposes account ID in git history
- [ ] **Unpinned Python dependencies** - `Pipfile` uses `"*"` for versions; pin specific versions
- [ ] **DB_NAME in environment variables** - Should be in Secrets Manager with other DB credentials
- [ ] **Third-party deployment action** - Uses `aws-lambda-deploy` instead of official AWS CLI

### Code Quality
- [ ] **Repetitive pagination validation** - Same logic duplicated in `meals.py:106-113`, `ingredients.py:59-66`, `meal_logs.py:93-100`. Extract to shared utility
- [ ] **Repetitive user ID resolution** - Same pattern in 6+ locations. Extract to shared utility with proper error handling
- [ ] **Generic exception handling** - Catches all exceptions masking real errors (e.g., `meals.py:95-98`). Catch specific exceptions
- [ ] **Date validation lacks business logic** - Allows dates 100+ years in future/past for meal logs

## Low Priority

- [ ] **Consider request validation schema** - Evaluate Pydantic or similar for structured request validation
- [ ] **CORS credentials flag missing** - `response.py:11` doesn't include `Access-Control-Allow-Credentials` header
- [ ] **No secret rotation handling** - Secrets are cached forever in Lambda memory

## Completed Items

- [x] **Refactor SQL interpolation in meal_logs.py** - Replace the dynamic `where_clause` string building with fully parameterized queries
- [x] **Add exception handling in users.py** - Wrap database operations in try/except blocks to handle duplicate email errors and log failures properly
- [x] **Implement connection cleanup with context managers** - Ensure all database connections are properly closed on error paths using `with` statements or consistent finally blocks
- [x] **Add integer type validation for quantity field** - Validate that `quantity` in meal_logs is explicitly an integer before database insertion to prevent type casting issues
- [x] **Add Secrets Manager error handling in db.py** - Wrap `get_secret_value()` call in try/except with retry logic for transient failures
- [x] **Handle JSON parsing errors explicitly** - Catch `JSONDecodeError` in Lambda handlers and return 400 Bad Request instead of generic 500 errors
- [x] **Handle Decimal JSON serialization** - Convert psycopg2 Decimal values to JSON-safe types in `backend/shared/response.py`
- [x] **Document pagination limits** - Add comments explaining the 100-item cap on list endpoints
- [x] **Implement Cognito authentication flow** - Add OAuth 2.0 + PKCE integration with Cognito Hosted UI
- [x] **Create API client module** - Build HTTP client with automatic JWT header attachment
- [x] **Implement core UI pages** - Build components for ingredients, meals, meal logging, and daily summary views
- [x] **Add loading and error states** - Implement proper UX for async operations
- [x] **Add frontend E2E tests with mock API** - Playwright tests run against a local mock server

---

## Testing Gaps

### Critical Missing Tests
- [ ] **No integration tests** - All tests use mocked database; need tests against real PostgreSQL
- [ ] **No authorization tests** - No tests verify users cannot access other users' data
- [ ] **No API Gateway integration tests** - Test full request/response cycle through API Gateway
- [ ] **Frontend E2E tests are mocked** - Playwright tests use a mock API; add a full-stack E2E test

### Missing Edge Case Tests (~50+ tests needed)
- [ ] Null/missing `pathParameters` handling
- [ ] Null/missing `httpMethod` handling
- [ ] Very large pagination limits
- [ ] Negative pagination offsets
- [ ] Future/past dates beyond reasonable range
- [ ] Empty ingredients list edge cases
- [ ] Duplicate ingredient IDs in meal creation
- [ ] Negative calorie values
- [ ] Boolean values passed as integers
- [ ] Maximum string length inputs

### Missing Error Condition Tests (~30+ tests needed)
- [ ] Connection timeout scenarios
- [ ] Database constraint violations
- [ ] Transaction rollback conditions
- [ ] Query timeout scenarios
- [ ] Secrets Manager failures
- [ ] Invalid JSON request bodies

### Missing Security Tests (~15+ tests needed)
- [ ] SQL injection attempts in string fields
- [ ] Cross-user data access attempts
- [ ] Missing Cognito claims handling
- [ ] Invalid UUID format handling
- [ ] Path traversal attempts

### Current Test Coverage
| File | Tests | Status |
|------|-------|--------|
| test_validation.py | ~40 | Good |
| test_meals.py | 17 | Adequate |
| test_ingredients.py | 10 | Adequate |
| test_handlers.py | 8 | Basic |
| test_meal_logs.py | 7 | Basic |
| test_summary.py | 6 | Basic |
| test_logging.py | 4 | Basic |
| test_db.py | 3 | Minimal |
| test_users.py | 3 | Minimal |
| test_auth.py | 2 | Minimal |
| test_response.py | 2 | Minimal |

**Estimated additional tests needed:** 125-150 for adequate coverage

---

## Post-Deployment Monitoring

- [ ] **Set up CloudWatch alarms** - Monitor Lambda error rates and duration
- [ ] **Track API Gateway metrics** - Monitor 4xx/5xx error rates
- [ ] **Establish database backup procedures** - Configure RDS automated backups and test restore process
- [ ] **Add security event logging** - Log authentication failures, authorization denials

---

## Database Migration Required

Run this SQL to fix RDS schema:

```sql
-- 1. Add missing total_calories column to meals
ALTER TABLE meals
ADD COLUMN total_calories NUMERIC NOT NULL DEFAULT 0;

-- 2. Rename consumed_at to date in meal_logs
ALTER TABLE meal_logs
RENAME COLUMN consumed_at TO date;

-- 3. Add missing quantity column to meal_logs
ALTER TABLE meal_logs
ADD COLUMN quantity INT NOT NULL DEFAULT 1;

-- 4. Add missing indexes
CREATE INDEX meal_ingredients_ingredient_id_idx ON meal_ingredients(ingredient_id);
CREATE INDEX meal_logs_meal_id_idx ON meal_logs(meal_id);

-- 5. Recreate index with correct column name
DROP INDEX IF EXISTS meal_logs_user_id_date_idx;
CREATE INDEX meal_logs_user_id_date_idx ON meal_logs(user_id, date);

-- 6. Add NOT NULL constraints (requires no NULL values exist)
ALTER TABLE ingredients ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE meals ALTER COLUMN user_id SET NOT NULL;
```
