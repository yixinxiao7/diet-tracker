# Repository Guidelines

## Project Structure & Module Organization
- `api/index.py` is the Vercel Python Function: a FastAPI adapter that routes `/api/*` requests to the handlers.
- `backend/lambdas/` contains handlers grouped by domain (`meals`, `meal_logs`, `summary`, `users`, `daily_summaries_batch`). Each has a `handler.py` entry point plus supporting modules (for example `meals.py`, `ingredients.py`). The directory name predates the move off AWS Lambda.
- `backend/shared/` holds cross-cutting utilities like auth helpers (`auth.py`), DB access (`db.py`), and response formatting (`response.py`).
- Root files include `Pipfile`/`Pipfile.lock` for Python dependencies and `README.md` for architecture and API notes.

## Build, Test, and Development Commands
- `pipenv install --dev` installs runtime and dev dependencies from `Pipfile`.
- `pipenv run pytest` runs the test suite (add tests under `backend/tests/`).
- Vercel deploys from Git (previews on PRs, production on `main`); `vercel dev` runs the app locally. Most validation is via unit tests, including `backend/tests/test_api_adapter.py` for the adapter.

## Coding Style & Naming Conventions
- Python 3.12, 4-space indentation, PEP 8 style.
- Use `snake_case` for functions/variables, `PascalCase` for classes.
- Keep Lambda entry points in `handler.py` and domain logic in sibling modules (for example `meals.py`).
- No formatter/linter is configured yet; keep diffs clean and consistent with existing files.

## Testing Guidelines
- Framework: `pytest` (with `pytest-mock` available).
- Place tests in `backend/tests/` and name files `test_*.py`.
- Prefer unit tests for shared utilities and handler modules; use fixtures for the API Gateway-style event payloads the adapter builds.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits (examples: `feat: ...`, `chore: ...`).
- PRs should include a short description, linked issue (if any), and a note on how changes were validated (for example `pipenv run pytest`).

## Security & Configuration Notes
- Do not commit secrets or credentials. Configure them as Vercel environment variables (`DATABASE_URL`, `CRON_SECRET`, etc.) and `frontend/.env.local` for local dev.
- Keep authentication logic centralized in `backend/shared/auth.py` and avoid duplicating JWT parsing in handlers.