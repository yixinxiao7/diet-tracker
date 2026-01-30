# Code Audit Recommendations

## High Priority

- [x] **Refactor SQL interpolation in meal_logs.py** - Replace the dynamic `where_clause` string building with fully parameterized queries
- [x] **Add exception handling in users.py** - Wrap database operations in try/except blocks to handle duplicate email errors and log failures properly
- [x] **Implement connection cleanup with context managers** - Ensure all database connections are properly closed on error paths using `with` statements or consistent finally blocks

## Medium Priority

- [x] **Add integer type validation for quantity field** - Validate that `quantity` in meal_logs is explicitly an integer before database insertion to prevent type casting issues
- [x] **Add Secrets Manager error handling in db.py** - Wrap `get_secret_value()` call in try/except with retry logic for transient failures
- [x] **Handle JSON parsing errors explicitly** - Catch `JSONDecodeError` in Lambda handlers and return 400 Bad Request instead of generic 500 errors

## Low Priority

- [x] **Document pagination limits** - Add comments explaining the 100-item cap on list endpoints
- [ ] **Consider request validation schema** - Evaluate Pydantic or similar for structured request validation in future refactoring

## Frontend Implementation (Required for Production)

- [x] **Implement Cognito authentication flow** - Add OAuth 2.0 + PKCE integration with Cognito Hosted UI
- [x] **Create API client module** - Build HTTP client with automatic JWT header attachment
- [x] **Implement core UI pages** - Build components for ingredients, meals, meal logging, and daily summary views
- [x] **Add loading and error states** - Implement proper UX for async operations

## Testing Improvements

- [ ] **Add integration tests** - Create tests that run against a real PostgreSQL instance
- [ ] **Add API Gateway integration tests** - Test full request/response cycle through API Gateway
- [ ] **Add end-to-end tests** - Test frontend to backend flows once frontend is implemented

## Post-Deployment Monitoring

- [ ] **Set up CloudWatch alarms** - Monitor Lambda error rates and duration
- [ ] **Track API Gateway metrics** - Monitor 4xx/5xx error rates
- [ ] **Establish database backup procedures** - Configure RDS automated backups and test restore process
