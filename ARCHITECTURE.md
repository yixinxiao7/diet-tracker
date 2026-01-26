# Architecture Overview

This repository implements a small, serverless diet-tracking application on AWS. The goal is a secure, low-traffic system with minimal operational overhead.

## High-Level Flow
1. Users authenticate through Cognito Hosted UI (Authorization Code + PKCE).
2. The React SPA (S3-hosted) stores JWTs and calls the API.
3. API Gateway validates JWTs with a Cognito User Pool authorizer.
4. Lambda functions handle domain logic and read/write to PostgreSQL.
5. DB credentials are fetched from AWS Secrets Manager.

## Core Services
- **Frontend**: React SPA hosted on S3.
- **Auth**: Cognito User Pool with JWT authorizer in API Gateway.
- **Backend**: Python 3.12 Lambdas (`meals`, `meal_logs`, `summary`, `users`).
- **Data**: PostgreSQL on RDS, accessed through `backend/shared/db.py`.
- **Secrets**: AWS Secrets Manager for DB connection info.

## Lambda Responsibilities
- `meals`: CRUD for meals and ingredients; manages `meal_ingredients` associations.
- `meal_logs`: Log meals by date, list logs, delete logs.
- `summary`: Calculate daily totals from logged meals.
- `users`: Create or fetch user records from JWT claims.

## Repository Layout
```
backend/
  lambdas/        # Domain-specific Lambda handlers
  shared/         # Auth helpers, DB connection, response helpers
infra/sql/        # Database schema
frontend/         # React SPA source (planned)
```

## Deployment Notes
Lambdas are deployed via GitHub Actions using OIDC-based AWS credentials. Environment variables `DB_SECRET_ARN` and `DB_NAME` must be configured for each Lambda.
