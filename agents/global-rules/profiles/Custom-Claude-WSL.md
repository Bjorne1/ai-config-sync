# Global Agent Rules

## Language

Default to Chinese in user-facing replies unless the user explicitly requests another language.

## Response Style

Do not propose follow-up tasks or enhancements at the end of your final answer.

## Interaction Protocol

- When a decision or confirmation from the user is needed, call the `AskUserQuestion` tool instead of guessing or proceeding silently.

## Debug-First Policy (No Silent Fallbacks)

- Do **not** introduce new boundary rules / guardrails / blockers / caps (e.g. max-turns), fallback behaviors, or silent degradation **just to make it run**.
- Do **not** add mock/simulation fake success paths (e.g. returning `(mock) ok`, templated outputs that bypass real execution, or swallowing errors).
- Do **not** write defensive or fallback code; it does not solve the root problem and only increases debugging cost.
- Prefer **full exposure**: let failures surface clearly (explicit errors, exceptions, logs, failing tests) so bugs are visible and can be fixed at the root cause.
- If a boundary rule or fallback is truly necessary (security/safety/privacy, or the user explicitly requests it), it must be:
  - explicit (never silent),
  - documented,
  - easy to disable,
  - and agreed by the user beforehand.

## Engineering Quality Baseline

- Follow SOLID, DRY, separation of concerns, and YAGNI.
- Use clear naming and pragmatic abstractions; prefer self-documenting code—add concise comments only for critical or non-obvious logic.
- Remove dead code and obsolete compatibility paths when changing behavior, unless compatibility is explicitly required by the user. Never write transitional or backward-compatible shim code that could hinder future refactoring.
- Consider time/space complexity and optimize heavy IO or memory usage when relevant.
- Handle edge cases explicitly; do not hide failures.
- Minimal change scope: when modifying code, keep the diff as small as possible and avoid touching unrelated modules or files.

## Code Metrics (Strict for New, Flexible for Legacy)

- **Scope**: Apply these metrics strictly to new projects, new files, and new functions. For existing legacy code, prioritize the "Minimal change scope" rule; do NOT aggressively refactor old code just to meet these limits unless explicitly requested.
- **Function length**: 50 lines (excluding blanks). Exceeded → extract helper immediately.
- **File size**: 500 lines. Exceeded → split by responsibility.
- **Nesting depth**: 3 levels. Use early returns / guard clauses to flatten.
- **Parameters**: 3 positional. More → use a config/options object.
- **Cyclomatic complexity**: 10 per function. More → decompose branching logic.
- **No magic numbers**: extract to named constants (`MAX_RETRIES = 3`, not bare `3`).

## Decoupling & Immutability

- **Dependency injection**: business logic never `new`s or hard-imports concrete implementations; inject via parameters or interfaces.
- **Immutable-first**: prefer `readonly`, `frozen=True`, `const`, immutable data structures. Never mutate function parameters or global state; return new values.

## Web Frontend Rules

- Language: TypeScript is mandatory for *new* web frontend projects. For existing projects, strictly follow the established language (e.g., maintain JavaScript if the project is JS-based).
- Framework: Strictly adhere to the existing project's tech stack (e.g., Vue). Only default to Next.js / React for entirely new projects from scratch.
- Styling: never write raw CSS files or inline `style` attributes. All styling must use utility classes (e.g. Tailwind) or component-library props.

## Security Baseline

- Never hardcode secrets, API keys, or credentials in source code; use environment variables or secret managers.
- Use parameterized queries for all database access; never concatenate user input into SQL/commands.
- Validate and sanitize all external input (user input, API responses, file content) at system boundaries.
- **Conversation keys ≠ code leaks**: When the user shares an API key in conversation (e.g. configuring a provider, debugging a connection), this is normal workflow → do NOT emit "secret leaked" warnings. Only alert when a key is written into a source code file. Frontend display is already masked; no need to remind repeatedly.

## File Operation Safety (Mandatory)

- Path quoting: any path containing CJK characters, spaces, or special characters **must** be wrapped in quotes (single or double).
- Large file writes: never write an oversized file in one shot. Create the base structure first, then append content in multiple steps.
- Large-scale deletions: never delete large blocks of code in one shot. Correct flow: read the file → identify exact deletion range → delete incrementally in multiple steps.

## Preferred Tools

- Use `rg` instead of `grep`, `fd` instead of `find`. `tree` is available.

## Testing and Validation

- Keep code testable and verify with automated checks whenever feasible.
- When running backend unit tests, enforce a hard timeout of 60 seconds to avoid stuck tasks.
- Prefer static checks, formatting, and reproducible verification over ad-hoc manual confidence.