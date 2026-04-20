# Architecture Decisions

This document captures the major technical decisions behind the diet-tracker application, the context that informed each choice, and the trade-offs accepted. It serves as a reference for anyone onboarding to the project or evaluating the system's design.

---

## ADR-001: Serverless Compute with AWS Lambda

**Status:** Accepted

**Context:** The application serves a small number of health-conscious users tracking daily dietary intake. Traffic is low and bursty — a few requests during meal times, near-zero overnight. Running a persistent server (EC2, ECS, EKS) would mean paying for idle capacity most of the day.

**Decision:** Use AWS Lambda (Python 3.12) for all backend compute, including API handlers and scheduled batch processing.

**Consequences:**
- Pay-per-invocation pricing keeps costs under the free tier for expected traffic levels.
- No server patching, OS updates, or capacity planning.
- Cold starts add ~200-500ms latency on the first request after idle periods. Acceptable for a personal health tool, not for a latency-sensitive trading system.
- 30-second timeout per function. Sufficient for CRUD operations and batch summaries, but rules out long-running analytics or data migration jobs.
- Each Lambda is a self-contained deployment unit, enabling independent scaling and isolated failure domains.
- Vendor lock-in: the handler signature, event format, and deployment model are AWS-specific. Migrating to another cloud would require rewriting the entry points (but not the business logic).

**Alternatives considered:**
- *ECS Fargate* — better for sustained throughput but overkill for <100 requests/day. Higher baseline cost.
- *EC2* — cheapest at sustained load, but operational burden (patching, scaling, monitoring) is disproportionate for a personal project.

---

## ADR-002: PostgreSQL on RDS (Not DynamoDB)

**Status:** Accepted

**Context:** The data model is inherently relational — users have ingredients, ingredients compose meals, meals are logged by date, and summaries aggregate across these relationships. Queries like "total calories for user X on date Y" require joining meal_logs → meals → meal_ingredients → ingredients.

**Decision:** Use Amazon RDS PostgreSQL as the primary data store.

**Consequences:**
- Relational joins and aggregations are first-class operations, making summary calculations straightforward SQL.
- Schema enforcement (NOT NULL, CHECK constraints, foreign keys with CASCADE) catches data integrity issues at the database level.
- Indexes on (user_id, date) enable efficient range queries for daily and weekly summaries.
- RDS has a monthly baseline cost (~$15/month for db.t3.micro after free tier), unlike DynamoDB's pure pay-per-request model.
- Connection management in Lambda requires care — each invocation opens a connection, and concurrent invocations can exhaust the connection limit. Mitigated by caching a single connection per Lambda container (warm starts reuse it).
- Backups rely on RDS automated snapshots (default 7-day retention).

**Alternatives considered:**
- *DynamoDB* — zero connection management, truly serverless pricing. But the relational data model would require denormalization, composite keys, and GSIs that add complexity. Aggregation queries (daily totals across multiple meals) are awkward without Streams + Lambda pipelines.
- *Aurora Serverless v2* — auto-scales to zero, avoids connection pooling issues. But minimum cost is higher than db.t3.micro for low-traffic workloads.

---

## ADR-003: Lambdas Run Outside the VPC

**Status:** Accepted

**Context:** Lambda functions inside a VPC require ENI (Elastic Network Interface) attachment, adding 1-10 seconds of cold start latency. RDS is inside a VPC but can be made publicly accessible with security group restrictions.

**Decision:** Run Lambdas outside the VPC. RDS is publicly accessible, protected by security groups that restrict inbound connections.

**Consequences:**
- Cold starts are fast (~200-500ms) since there's no ENI provisioning.
- Lambdas reach RDS over the public internet, which is a wider attack surface than VPC-internal communication.
- Security groups act as the network-level firewall. The RDS instance accepts connections only from authorized sources.
- Secrets Manager is accessed over the public AWS endpoints (no VPC endpoint needed).
- If the security posture needs tightening (e.g., for compliance), Lambdas can be moved into the VPC at the cost of cold start latency. RDS Proxy would mitigate connection pooling issues in that scenario.

**Alternatives considered:**
- *Lambda in VPC + RDS Proxy* — strongest security posture, connection pooling handled by the proxy. But adds ~$15/month for RDS Proxy and 1-10s cold start penalty. Disproportionate for a personal tool.
- *Lambda in VPC + NAT Gateway* — needed if Lambdas require internet access from within the VPC. NAT Gateway costs ~$32/month minimum. Not justified here.

---

## ADR-004: Cognito with PKCE for Authentication

**Status:** Accepted

**Context:** The frontend is a public SPA (no server-side rendering), so it cannot securely store a client secret. The application needs user identity for data isolation — every query is scoped to the authenticated user's `cognito_user_id`.

**Decision:** Use Amazon Cognito User Pool with OAuth 2.0 Authorization Code flow + PKCE (Proof Key for Code Exchange). API Gateway validates JWTs using a Cognito authorizer.

**Consequences:**
- Cognito handles user registration, login, password reset, and token issuance. No custom auth code to maintain.
- PKCE prevents authorization code interception attacks without requiring a client secret.
- Tokens (id_token, access_token, refresh_token) are stored in localStorage on the client. This is vulnerable to XSS but standard practice for SPAs without a backend-for-frontend.
- API Gateway validates the JWT signature and expiration before the request reaches Lambda. Invalid tokens are rejected at the edge.
- Cognito's free tier covers 50,000 MAU. Well within the expected user count.
- The `VITE_AUTH_BYPASS=1` flag enables local development and E2E testing without a real Cognito instance.

**Alternatives considered:**
- *Auth0* — more flexible UI customization, but adds an external dependency and potential cost at scale.
- *Custom JWT implementation* — full control, but requires implementing token issuance, validation, refresh, and key rotation. High effort, high risk for a personal project.
- *Supabase Auth* — good developer experience, but ties auth to Supabase's ecosystem rather than AWS-native services.

---

## ADR-005: React SPA with Vanilla CSS (No Component Library)

**Status:** Accepted

**Context:** The frontend is a single-page application with a small number of views — ingredient management, meal composition, meal logging, and daily summaries. The design calls for a warm, organic aesthetic with specific typography (Fraunces + Space Grotesk) and a cream/teal color palette.

**Decision:** Use React 19 with Vite as the build tool. All styling is vanilla CSS with custom properties — no Tailwind, no MUI, no component library.

**Consequences:**
- Total control over the visual design. The warm, friendly aesthetic described in CLAUDE.md is implemented without fighting a component library's opinionated defaults.
- CSS custom properties (defined in `index.css :root`) create a lightweight design system: `--surface`, `--accent`, `--ink`, `--muted`, `--radius-*`, `--space-*`.
- Bundle size stays small — no UI library dependencies. The entire frontend is React + ReactDOM + custom CSS.
- Every component's styles must be hand-written. No pre-built form controls, modals, or data tables. This is acceptable for a small app but wouldn't scale to a large team.
- No TypeScript — reduces setup complexity but loses compile-time type checking. Acceptable for a solo developer who owns the full stack.

**Alternatives considered:**
- *Tailwind CSS* — faster iteration with utility classes, but the warm organic aesthetic requires enough custom values that Tailwind's defaults don't help much.
- *shadcn/ui* — accessible, composable components. But adds Tailwind as a dependency and imposes a visual style that conflicts with the brand personality.
- *Next.js* — SSR benefits are unnecessary for this app (no SEO requirements, no server-side data fetching). Vite is simpler and faster for a pure SPA.

---

## ADR-006: S3 + CloudFront for Frontend Hosting

**Status:** Accepted

**Context:** The frontend is a static SPA — a single `index.html` entry point plus bundled JS/CSS assets. It needs HTTPS, a custom domain (`diet-tracker.yixinx.com`), and reasonable global latency.

**Decision:** Host the built frontend in an S3 bucket (private, OAC-protected) and serve it through CloudFront with an ACM certificate for HTTPS.

**Consequences:**
- S3 storage costs are negligible (a few MB of static assets).
- CloudFront provides edge caching, HTTPS termination, and custom domain support.
- Deployments are a simple `aws s3 sync` followed by a CloudFront cache invalidation.
- Separate S3 buckets and CloudFront distributions for staging and production enable environment isolation.
- No server-side rendering capability. All routing is client-side (CloudFront is configured to return `index.html` for all paths).

---

## ADR-007: GitHub Actions CI/CD with OIDC Authentication

**Status:** Accepted

**Context:** The project is hosted on GitHub. Deployments need to authenticate with AWS to update Lambda code, sync S3 buckets, and invalidate CloudFront caches. Storing long-lived AWS access keys as GitHub secrets is a security risk.

**Decision:** Use GitHub Actions for CI/CD. Authenticate to AWS using OpenID Connect (OIDC) federation — GitHub's identity provider issues short-lived tokens that AWS STS exchanges for temporary credentials.

**Consequences:**
- No long-lived AWS credentials stored in GitHub. OIDC tokens are valid for the duration of the workflow run only.
- The IAM trust policy restricts which repositories, branches, and environments can assume the role. The `sub` claim format changes based on whether the workflow uses `environment:` (e.g., `repo:yixinxiao7/diet-tracker:environment:staging`).
- Separate GitHub environments (`staging`, `production`) with distinct secrets enable environment-specific configurations.
- Production deployments require manual approval (GitHub environment protection rules with required reviewers).
- The `dorny/paths-filter` action in the staging workflow skips unnecessary jobs (e.g., don't rebuild backend if only frontend changed).

**Pipeline structure:**
1. **Test Backend** — pytest unit + integration tests (triggered on PR/push with backend changes)
2. **Test Frontend** — ESLint + Playwright E2E tests (triggered on PR/push with frontend changes)
3. **Deploy to Staging** — automatic on push to main (tests must pass first)
4. **Deploy to Production** — manual trigger with required reviewer approval

**Alternatives considered:**
- *AWS CodePipeline + CodeBuild* — native AWS integration, but more complex setup and harder to version control alongside the application code.
- *Static IAM keys in GitHub secrets* — simpler setup, but keys don't expire and must be manually rotated. A compromised key grants indefinite access.

---

## ADR-008: Structured Logging and Custom CloudWatch Metrics

**Status:** Accepted

**Context:** Lambda functions log to CloudWatch Logs by default, but unstructured text logs are difficult to query and aggregate. The application needs visibility into request rates, latency distributions, error rates, and database performance.

**Decision:** Implement structured JSON logging (via a custom `StructuredLogger`) and emit custom CloudWatch metrics under the `DietTracker` namespace. Define CloudWatch alarms for error rates, latency, slow queries, batch failures, and RDS CPU.

**Consequences:**
- JSON-formatted logs enable CloudWatch Logs Insights queries (e.g., filter by user_id, operation, or error type).
- Custom metrics provide application-level visibility beyond what AWS default metrics offer (e.g., per-endpoint latency percentiles).
- Five CloudWatch alarms notify via SNS when thresholds are breached: high error rate, high p99 latency, slow database queries, batch job failures, and RDS CPU saturation.
- Metrics emission is wrapped in try/except to ensure monitoring never crashes the application. A silent monitoring failure is preferable to a user-facing error.
- CloudWatch costs are minimal at low volume but could grow with high-cardinality custom metrics.

---

## ADR-009: Batch Pre-computation for Daily Summaries

**Status:** Accepted

**Context:** The daily summary endpoint needs to calculate total calories, meal counts, and weekly aggregates. Computing these on every request requires joining multiple tables and aggregating across all meals for a given day/week.

**Decision:** Run a scheduled batch job (`daily_summaries_batch` Lambda, triggered by EventBridge) that pre-computes daily summaries, weekly reports, and detects nutritional anomalies. The summary API endpoint reads from the pre-computed tables first, falling back to live calculation for same-day data.

**Consequences:**
- Summary reads are fast — a single row lookup from `daily_summaries` instead of a multi-table join.
- The batch job runs once daily (after midnight), keeping compute costs minimal.
- Same-day data is always fresh because the API falls back to live calculation when the batch hasn't run yet.
- UPSERT logic (ON CONFLICT ... DO UPDATE) makes the batch job idempotent — safe to re-run without duplicating data.
- Anomaly detection (calories deviating >50% from 7-day rolling average) runs as part of the batch, writing to `nutrition_anomalies`.
- If the batch job fails, the API still works (live fallback), but weekly reports and anomaly data become stale.

---

## ADR-010: No Infrastructure-as-Code (Manual AWS Setup)

**Status:** Accepted (with caveats)

**Context:** The application uses ~10 AWS services. Setting up IaC (CloudFormation, CDK, Terraform) for a personal project adds significant upfront effort and ongoing maintenance.

**Decision:** AWS resources are provisioned manually through the console. Deployment automation (Lambda code updates, S3 sync, CloudFront invalidation) is handled by GitHub Actions. Infrastructure definitions are documented but not codified.

**Consequences:**
- Fast initial setup — no learning curve for CDK/Terraform, no debugging template drift.
- Environment replication (staging/production) requires manual duplication of resources, increasing the risk of configuration drift between environments.
- Disaster recovery is slower — rebuilding the infrastructure from scratch requires following documentation rather than running a template.
- The `infra/` directory contains SQL schemas and CloudWatch alarm/dashboard JSON definitions, but these must be applied manually.
- This is the most significant technical debt in the project. For a team environment or production system, IaC would be essential.

**Future direction:** If the project grows beyond a personal tool, adopt AWS CDK (Python) to codify the infrastructure. CDK's imperative style aligns well with the existing Python backend.

---

## ADR-011: User Isolation via Application-Layer Filtering

**Status:** Accepted

**Context:** Multiple users share the same database. Each user should only see their own ingredients, meals, and logs.

**Decision:** All database queries include a `WHERE user_id = %s` clause. The `user_id` is derived from the authenticated JWT claims (Cognito `sub` → internal user ID lookup). There is no database-level row security (PostgreSQL RLS).

**Consequences:**
- Simple and transparent — every query explicitly scopes to the current user.
- A bug in any query that omits the `user_id` filter could leak data across users. Mitigated by consistent patterns in all handlers and code review.
- No need for PostgreSQL RLS configuration, which adds complexity to migrations and schema management.
- If the application scales to many tenants, RLS or separate schemas per tenant would provide stronger isolation guarantees.

---

## ADR-012: E2E Testing Strategy with Mock API

**Status:** Accepted

**Context:** The frontend communicates with a REST API backed by Lambda + RDS. Running E2E tests against real AWS infrastructure is slow, expensive, and flaky (network latency, cold starts, shared state).

**Decision:** Frontend E2E tests (Playwright) run against a local mock API server (`frontend/mock-api/server.js`) that simulates the backend's HTTP interface. Auth is bypassed via `VITE_AUTH_BYPASS=1`.

**Consequences:**
- E2E tests are fast (no network calls to AWS), deterministic (no shared state), and free (no Lambda invocations).
- The mock server must be kept in sync with the real API contract. A divergence means tests pass but production breaks.
- Backend correctness is covered separately by pytest unit and integration tests.
- No true end-to-end coverage of the full stack (frontend → API Gateway → Lambda → RDS). Smoke tests (`backend/tests/smoke/`) partially fill this gap but are not run in CI.
- Playwright tests run in CI with Chromium, uploading test reports as GitHub Actions artifacts (30-day retention).

---

## ADR-013: Shared Backend Infrastructure Across Environments

**Status:** Accepted

**Context:** A fully isolated staging environment would require duplicating the RDS instance (~$15/month), API Gateway stage, Lambda function aliases, and Cognito user pool. The CI/CD pipeline already separates environments at the GitHub Actions level (distinct environments, secrets, and approval gates), and the frontend has separate S3 buckets for staging and production.

**Decision:** Staging and production share the same API Gateway, Lambda functions, RDS database, and Cognito user pool. Environment separation is enforced at the CI/CD layer (GitHub environments with required reviewers for production) and the frontend hosting layer (separate S3 buckets), not at the AWS infrastructure layer.

**Consequences:**
- Monthly AWS costs stay minimal — a single RDS instance, single API Gateway, and single Cognito pool instead of doubling each.
- The CI pipeline validates code correctness through unit tests (pytest), mock-API E2E tests (Playwright), and linting before any deployment reaches production.
- No pre-production environment to catch deployment-specific issues (e.g., IAM permission changes, environment variable misconfigurations, or API contract mismatches between frontend and backend).
- Load tests and smoke tests run against production data. Test data cleanup must be reliable to avoid contamination.
- For a team environment, isolated staging infrastructure would be essential. The current approach is a deliberate cost optimization for a single-developer project with low traffic.

**Future direction:** If the project onboards additional users or contributors, introduce a separate API Gateway stage (`staging`) backed by Lambda aliases and a dedicated RDS schema or instance. AWS CDK (see ADR-010) would make this duplication manageable.

---

## Summary of Key Trade-offs

| Decision | Optimized For | Accepted Risk |
|----------|---------------|---------------|
| Lambda | Cost, simplicity | Cold starts, vendor lock-in |
| RDS PostgreSQL | Data integrity, query flexibility | Connection management, baseline cost |
| Lambdas outside VPC | Fast cold starts | Wider network attack surface |
| Cognito PKCE | Managed auth, SPA-compatible | localStorage token storage (XSS risk) |
| Vanilla CSS | Design control, small bundle | Manual styling effort |
| OIDC for CI/CD | No long-lived credentials | AWS-GitHub coupling |
| No IaC | Fast setup | Config drift, manual disaster recovery |
| Mock API for E2E | Fast, reliable tests | API contract drift risk |
| Shared backend infra | Low AWS costs | No pre-production validation of deployments |
