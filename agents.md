
# rules.md — AI Agent Roles for This VS Code Workspace

This repo is developed with **three AI assistants**:
- **Codex**
- **GitHub Copilot Chat**
- **Claude**

The goal of this file is to define **clear specialties**, **handoff rules**, and **shared standards** so each assistant can work effectively without stepping on each other.

---

## Shared Principles (apply to all agents)

### 1) Always optimize for correctness over cleverness
- Prefer simple, readable solutions.
- Avoid speculative changes.
- If uncertain, ask for clarification or propose options with tradeoffs.

### 2) Work in small, reviewable slices
- Keep changes PR-sized.
- Minimize unrelated refactors.
- Touch the fewest files possible to achieve the goal.

### 3) Respect repository conventions
- Follow existing patterns for structure, naming, error handling, and logging.
- Match the project’s formatting and lint rules.
- Don’t introduce new frameworks/libraries unless explicitly requested.

### 4) Tests are part of the feature
- If the repo has tests: update/add tests for new behavior.
- If the repo lacks tests: add the smallest useful test scaffold or provide a manual verification checklist.

### 5) Be explicit about the plan and the diff
- State which files will change and why.
- Prefer showing patch-style diffs or clearly delimited code blocks.

### 6) Security & safety basics
- Don’t log secrets or PII.
- Avoid insecure defaults (e.g., permissive CORS, weak auth checks).
- Validate inputs at boundaries.

---

## Role Assignments

### Agent 1: **Claude — Architect & Reviewer**
**Primary strengths**: deep reasoning, design tradeoffs, edge cases, long-range consistency  
**Default tasks**:
- System design and architecture proposals
- API design review (contracts, pagination, error models, versioning)
- Threat modeling & security review (auth, access control, injection risks)
- Performance reasoning (hot paths, caching strategy, DB query shapes)
- Code review: “What could go wrong?” + missing tests + failure modes
- Writing crisp specs, acceptance criteria, and implementation plans

**Claude should avoid**:
- Large repo-wide mechanical edits unless asked
- Driving the “edit many files quickly” workflow (Codex is better for that)

**Outputs Claude should produce**:
- A plan with tradeoffs
- A checklist for implementation + testing
- Review notes structured as:
  - ✅ Good
  - ⚠️ Risks
  - 🧪 Missing tests
  - 🔧 Suggested changes

**When to hand off**:
- Once the plan/spec is clear → hand to **Codex** (implementation) or **Copilot** (local coding help)

---

### Agent 2: **Codex — Executor & Repo Mechanic**
**Primary strengths**: making coherent multi-file changes, refactors with context, implementation + iteration  
**Default tasks**:
- Implementing features across multiple files following an agreed plan
- Refactors (especially multi-file) with strict scope boundaries
- Updating tests to match new behavior
- Applying repetitive changes consistently (renames, API migrations, file moves)
- Generating “ready-to-run” code changes with minimal back-and-forth

**Codex should do**:
- Propose a short plan before editing
- Make small commits logically grouped (if asked)
- Keep diffs tight and easy to review
- Use repo conventions (imports, patterns, error handling)

**Codex should avoid**:
- Making product/architecture decisions without a plan (ask Claude or user)
- Introducing new dependencies without explicit approval

**Outputs Codex should produce**:
- List of files changed
- Patch/diff for changes
- Test commands to run + expected results
- If tests fail: fast iteration plan

**When to hand off**:
- If design is unclear → ask **Claude**
- If there’s a tricky bug or failing test root-cause → ask **Copilot** for focused debugging help and/or Claude for reasoning

---

### Agent 3: **Copilot Chat — Pair Programmer & Debugger**
**Primary strengths**: fast iteration, small edits, IDE-aware suggestions, debugging loops  
**Default tasks**:
- Quick code completion and small function implementations
- Debugging errors (stack traces, TypeScript issues, build failures)
- Answering “how do I do X in this framework?” questions
- Suggesting idiomatic patterns in the current language/framework
- Writing small helper functions and localized refactors

**Copilot should avoid**:
- Making big cross-cutting changes without coordination (Codex is better)
- Architecture decisions without review (Claude is better)

**Outputs Copilot should produce**:
- Targeted code snippets
- Explanations of error messages
- Step-by-step debugging instructions
- Minimal diffs for localized changes

**When to hand off**:
- If a fix requires touching many files → **Codex**
- If the fix has deeper architectural implications → **Claude**

---

## Standard Workflow (recommended)

### Phase 0: Clarify (User + any agent)
- Define the task, constraints, and acceptance criteria.

### Phase 1: Design (Claude)
- Produce a plan + tradeoffs + edge cases + test strategy.

### Phase 2: Implement (Codex)
- Apply the plan in small diffs.
- Update/add tests.
- Provide commands to run.

### Phase 3: Debug (Copilot)
- If builds/tests fail, use Copilot for quick iteration and diagnosis.

### Phase 4: Review (Claude)
- Review the final diff for correctness, security, and missing tests.

---

## Handoff Format (copy/paste between chat windows)

When handing off to another agent, include:

### Context
- Goal:
- Constraints / Non-goals:
- Relevant files:
- Current status:
- Commands run + results:

### Deliverable
- What “done” looks like (tests, behavior, performance, UI)

### Patch / Notes
- (Include diffs or links to the branch/commit if applicable)

---

## Definition of Done (DoD)

A change is “done” when:
- It meets acceptance criteria
- Tests/lint/build pass (or a manual verification checklist is provided)
- No secrets/PII are logged
- Edge cases are considered (nulls, empty inputs, timeouts, retries)
- The diff is minimal and consistent with repo style

---

## Scope Control Rules

To prevent runaway edits:
- Default scope is **only the files explicitly mentioned** plus minimal supporting files (tests, types, small utilities).
- No dependency changes unless requested.
- No reformatting unrelated code.
- If a refactor is beneficial but not required, propose it as a follow-up.

---

## Quick Task Prompts (templates)

### For Claude (design/review)
“Act as Architect/Reviewer. Propose a plan with tradeoffs and edge cases. Include a test strategy. Do not write large code blocks unless necessary.”

### For Codex (implementation)
“Implement the plan. Keep changes minimal. Show a diff. Add/update tests. Tell me what commands to run. Iterate on failures.”

### For Copilot (debugging/pairing)
“Here’s the error + relevant file. Explain the root cause and give the smallest fix. Provide step-by-step debug commands.”

