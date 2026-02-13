1. allow decimals for calories per unit
2. create prod API Gateway stage and switch frontend base URL
   a. API Gateway: select REST API for diet-tracker
   b. Actions -> Create Stage -> name: prod
   c. Deploy the API to the prod stage
   d. Note the prod invoke URL: https://<api-id>.execute-api.<region>.amazonaws.com/prod
   e. Update GitHub Actions secret VITE_API_BASE_URL to the prod invoke URL
   f. Re-run Deploy Frontend workflow to rebuild with the new base URL
   g. Verify calls from CloudFront use /prod and succeed
3. move off RDS (Postgres) to DynamoDB to keep costs near free
   a. Define access patterns
      - List ingredients/meals/logs by user
      - Get meal details + ingredients
      - Log meals by date, list by date range
      - Daily summary totals
   b. DynamoDB single-table schema (recommended)
      - Table: diet-tracker
      - PK: USER#<user_id>
      - SK patterns:
        - PROFILE
        - INGREDIENT#<ingredient_id>
        - MEAL#<meal_id>
        - MEAL_INGREDIENT#<meal_id>#<ingredient_id>
        - MEAL_LOG#<date>#<log_id>
      - GSIs:
        - GSI1PK: MEAL#<meal_id> (lookup meal ingredients fast)
        - GSI1SK: INGREDIENT#<ingredient_id>
        - GSI2PK: DATE#<YYYY-MM-DD> (optional for cross-user daily stats)
        - GSI2SK: USER#<user_id>#MEAL_LOG#<log_id>
   c. Data model fields
      - Users: email, created_at
      - Ingredients: name, calories_per_unit, unit
      - Meals: name, total_calories, created_at
      - Meal ingredients: quantity
      - Meal logs: meal_id, date, quantity, meal_name, meal_calories snapshot
   d. Implement DynamoDB access layer (backend/shared/dynamo.py)
      - get_user, put_user, list_ingredients, list_meals
      - get_meal + batch load meal_ingredients
      - create/update/delete for ingredients, meals, logs
      - list logs with date range (SK begins_with / between)
   e. Update Lambdas to use DynamoDB
      - Replace psycopg2 calls with DynamoDB queries
      - Recalculate total_calories on meal create/update
   f. Migrate existing data (one-time)
      - Export from Postgres -> JSON
      - Import into DynamoDB with batch_writer
   g. Update deployments
      - Remove DB_SECRET_ARN/DB_NAME usage
      - Add DYNAMO_TABLE_NAME (and optional GSI names)
   h. Update tests
      - Use moto or local DynamoDB for unit tests
      - Update fixtures for new storage layer
