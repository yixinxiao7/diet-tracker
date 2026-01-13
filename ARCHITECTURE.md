# Diet Tracker — Architecture

This document describes the architecture, data flow, security controls, and operational considerations for the Diet Tracker serverless application.

## 1. High-level overview

User (browser React SPA) ↔ Cognito (Hosted UI & User Pool) → API Gateway (JWT authorizer) → Lambda (Python) → RDS PostgreSQL  
Secrets (DB credentials) are stored in AWS Secrets Manager and retrieved by Lambda at runtime.

## 2. Components

- Frontend
  - React SPA served from S3 (static hosting)
  - Uses OAuth2 Authorization Code + PKCE with Cognito Hosted UI
  - Sends Authorization: Bearer <JWT> to backend APIs

- Authentication
  - AWS Cognito User Pool (Hosted UI)
  - JWTs validated at API Gateway via Cognito authorizer

- API & Compute
  - API Gateway (REST) with JWT authorizer
  - AWS Lambda functions (Python 3.12) grouped by domain:
    - meals
    - meal_logs
    - daily_summary
    - users (bootstrap / me)

- Data & Secrets
  - Amazon RDS (PostgreSQL) in private subnet (recommended)
  - AWS Secrets Manager stores DB credentials
  - Lambda retrieves secrets at cold start, caches DB connections per invocation container

- Infra & CI/CD
  - Infrastructure defined with SAM (infra/sam/template.yaml)
  - GitHub Actions for build & Lambda deployment (.github/workflows)

## 3. Data flow (typical request)

1. User logs in via Cognito Hosted UI → browser receives id/access tokens.
2. Browser calls API Gateway with Authorization: Bearer <access_token>.
3. API Gateway validates token using Cognito authorizer.
4. Gateway forwards request to appropriate Lambda.
5. Lambda reads DB credentials from Secrets Manager (cached securely), connects to RDS, performs queries.
6. Lambda returns JSON response → API Gateway → browser.

## 4. Security & best practices

- No AWS credentials in the browser. Only JWTs.
- Least-privilege IAM roles:
  - Lambda role: minimal permissions to Secrets Manager (Decrypt/GetSecretValue) and RDS network access.
  - CI/CD role: permission to package & deploy Lambda functions only.
- Secrets Management:
  - Use Secrets Manager for DB credentials; rotate periodically.
- Network:
  - Place RDS in private subnets.
  - Put Lambdas that access RDS in same VPC (with minimal subnets & security groups).
- Token validation:
  - Validate JWT signature and claims (aud, iss, exp) via API Gateway authorizer; also validate in-service when needed.
- Protect sensitive logs: avoid printing secrets or PII.

## 5. Database schema (summary)
- users (id PK uuid, cognito_user_id unique, email unique, created_at)
- ingredients (id, user_id FK, name, calories_per_unit, unit)
- meals (id, user_id FK, name, created_at)
- meal_ingredients (id, meal_id FK, ingredient_id FK, quantity)
- meal_logs (id, user_id FK, meal_id FK, consumed_at date)

## 6. API contract (summary)
All endpoints require a valid Cognito JWT in Authorization header.

- /ingredients [GET, POST, PUT, DELETE]
- /meals [GET, POST, GET/{id}, PUT/{id}, DELETE/{id}]
- /meal-logs [GET, POST, DELETE/{id}]
- /daily-summary [GET?date=YYYY-MM-DD | ?from=&to=]
- /users/bootstrap [POST] (optional), /users/me [GET]

Refer to README.md for full endpoint table.

## 7. Operational concerns

- Monitoring / Observability
  - Enable CloudWatch Logs for Lambdas.
  - Emit custom metrics for errors and daily-calorie aggregations.
  - Set alarms on high error rates, elevated latency, or SecretsManager access failures.

- Scaling & Cost
  - Lambdas autoscale; RDS must be sized for concurrent connections (use connection pooling like pg-bouncer if traffic grows).
  - Keep RDS small for free-tier; consider Aurora Serverless or RDS Proxy for scaling/cost tradeoffs.

- Backups & Migrations
  - Enable automated RDS backups and snapshots.
  - Use SQL migration tools (e.g., Flyway/psql scripts under infra/sql).

## 8. Example minimal IAM policy snippets

- Lambda (SecretsManager read):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:secretsmanager:<region>:<acct>:secret:<secret-name>*"
    }
  ]
}
```

- Lambda VPC/network: allow access to RDS security group only.

## 9. Recommendations / Next steps

- Add RDS Proxy or connection pooling to avoid connection storms.
- Add automated tests for API contract and integration tests against a test DB.
- Configure CloudWatch dashboards and alerts for production readiness.
- Consider infra as code (Terraform or enhanced SAM) for maintainability.
