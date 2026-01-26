# Repository Guidelines

## Project Structure & Module Organization
- `backend/lambdas/` contains Lambda handlers grouped by domain (`meals`, `meal_logs`, `summary`, `users`). Each Lambda has a `handler.py` entry point plus supporting modules (for example `meals.py`, `ingredients.py`).
- `backend/shared/` holds cross-cutting utilities like auth helpers (`auth.py`), DB access (`db.py`), and response formatting (`response.py`).
- Root files include `Pipfile`/`Pipfile.lock` for Python dependencies and `README.md` for architecture and API notes.

## Build, Test, and Development Commands
- `pipenv install --dev` installs runtime and dev dependencies from `Pipfile`.
- `pipenv run pytest` runs the test suite (add tests under `backend/tests/`).
- Lambdas are deployed via AWS tooling; there is no local server in this repo, so local validation is primarily via unit tests and module-level execution.

## Coding Style & Naming Conventions
- Python 3.12, 4-space indentation, PEP 8 style.
- Use `snake_case` for functions/variables, `PascalCase` for classes.
- Keep Lambda entry points in `handler.py` and domain logic in sibling modules (for example `meals.py`).
- No formatter/linter is configured yet; keep diffs clean and consistent with existing files.

## Testing Guidelines
- Framework: `pytest` (with `pytest-mock` available).
- Place tests in `backend/tests/` and name files `test_*.py`.
- Prefer unit tests for shared utilities and Lambda modules; use fixtures for mocked AWS event payloads.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits (examples: `feat: ...`, `chore: ...`).
- PRs should include a short description, linked issue (if any), and a note on how changes were validated (for example `pipenv run pytest`).

## Security & Configuration Notes
- Do not commit secrets or AWS credentials. Use environment variables or AWS Secrets Manager.
- Keep authentication logic centralized in `backend/shared/auth.py` and avoid duplicating JWT parsing in handlers.
