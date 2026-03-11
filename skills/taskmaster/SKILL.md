---
name: taskmaster
description: >
  Unified task tracking protocol with CSV checkpointing, verification gates,
  and context-recovery. Two modes: LITE (3-8 steps, lightweight CSV at project
  root) and FULL (5-15 steps, four-file system in .codex-tasks/<task-name>/
  with spec freeze + validation gates + decision audit log + compaction recovery).

  WHEN TO USE: user asks to "track tasks", "create todo list", "make a plan",
  "track progress", "long task", "big project", "build from scratch",
  "autonomous session", "跟踪任务", "自主执行", "长时任务", "从零开始",
  "任务管理", "做个计划", "大工程", or when a task clearly requires 3+ ordered
  steps that produce file changes.

  DO NOT USE: single-step fixes, pure Q&A, code review, explaining code,
  search/research tasks, tasks with fewer than 3 steps, or tasks that don't
  produce file changes. For research use deep-research skill instead.
version: 4.0.0
---

# Taskmaster — Unified Task Protocol

## Purpose

Single skill for **all** multi-step task tracking, with two operating modes:

| | LITE Mode | FULL Mode |
|---|---|---|
| **When** | Quick tasks, 3-8 steps, <1 hour | Long autonomous sessions, 5-15 steps, 1+ hours |
| **Trigger** | Default for simple multi-step tasks | User says "long task", "big project", "autonomous", or task clearly needs hours of work |
| **Files** | `TODO.csv` only | `SPEC.md` + `TODO.csv` + `PROGRESS.md` |
| **Location** | Project root | `<project-root>/.codex-tasks/<task-name>/` |
| **Verification** | Optional (notes column) | Mandatory (validation_command + acceptance_criteria) |
| **Decision log** | None | PROGRESS.md |
| **Spec freeze** | None | SPEC.md (user-approved, immutable) |
| **Context recovery** | Re-read CSV | Re-read all 3 files from `.codex-tasks/<task-name>/` |

If unsure which mode, start LITE. Upgrade to FULL mid-task if complexity grows.

---

## LITE Mode

Lightweight CSV tracking synchronized with `update_plan`.

### Core Rule

**One row in CSV = One step in `update_plan`** (same order, same text, synced at every update).

### Workflow

1. **Determine project root** — Git root when in repo, else CWD.
2. **Choose task name** — 10-40 chars, derive from user request. Filename: `"<Task Name> TO DO list.csv"`
3. **Create plan** — Split into 3-8 steps. Call `update_plan` with exactly one `in_progress`. Verb-first texts (e.g., "Locate root cause", "Implement fix").
4. **Create CSV** at project root:

```csv
id,task,status,completed_at,notes
1,<step text>,TODO,,
2,<step text>,TODO,,
```

Rules:
- `status`: only `TODO` or `DONE`
- `completed_at`: empty until DONE; then local time like `2026-02-05 11:38`

5. **Update during execution** — When finishing a step: mark `completed` in `update_plan`, mark next `in_progress`, update CSV row to `DONE` + fill `completed_at`.
6. **Handle plan changes** — Update `update_plan` first, then apply same change to CSV.
7. **Close-out** — Delete CSV when all rows are DONE. Keep if user explicitly wants record.

### Performance Mode (optional)

For stress/load/latency tasks, add metric columns:
- `metric_name`, `target`, `actual`, `evidence_path`
- Same `TODO` → `DONE` lifecycle
- Template: `assets/perf_todo_template.csv`

### LITE Output Contract

Every status update must include:
1. `任务:` one-line goal
2. `进度:` X/Y steps DONE
3. `当前:` the in-progress step
4. `文件:` CSV path (or "deleted" if done)

---

## FULL Mode

Complete long-horizon protocol with verification gates, decision audit trail,
context protection, and compaction recovery. Based on the four-file system
proven in production autonomous coding sessions (25+ hours, 30k+ lines):

- **SPEC.md** — Frozen goal (what to build, what NOT to build)
- **TODO.csv** — Milestone tracker with verification gates (what to do next)
- **PROGRESS.md** — Decision log + audit trail (what happened and why)
- **Implement rules** — Embedded in this skill (how to behave)

All task artifacts live in `<project-root>/.codex-tasks/<task-name>/` to prevent
polluting the project source tree. Each task gets its own subdirectory, enabling
multiple long tasks to coexist without conflict.

### Core Rules

1. **CSV is single source of truth** — Re-read TODO.csv from disk before starting
   each new step. Never rely on in-context memory of the CSV.
2. **No step is DONE without verification** — Every step must pass its
   `validation_command` before being marked DONE.
3. **Stop-and-fix on failure** — If validation fails, mark status as FAILED,
   increment `retry_count`, append error to notes, fix, then re-validate.
   Never skip a failed step.
4. **Retry limit = 5** — If `retry_count` reaches 5, try an alternative approach
   (different implementation strategy, skip and revisit later, or decompose into
   smaller sub-steps). Log the decision in PROGRESS.md. Only request human
   intervention if ALL alternative approaches also fail.
5. **Scope discipline** — Only work on the current IN_PROGRESS step. Do not
   "helpfully" fix unrelated code or refactor things outside the plan.
6. **External logging** — Write verbose reasoning to PROGRESS.md, not into the
   conversation. Keep the conversation lean.
7. **Cache before process** — When fetching external data (APIs, web pages, docs),
   write raw results to `.codex-tasks/<task-name>/raw/` first. Subsequent
   processing reads from local cache to avoid redundant requests.
8. **Idempotent runs** — Each task creates a unique `<task-name>` directory.
   Never overwrite another task's artifacts.

### Task Naming

Generate a semantic, unique task name:
- Format: `<YYYYMMDD>-<short-topic>` (e.g., `20260224-rest-api`, `20260224-auth-refactor`)
- All lowercase, hyphen-separated, no spaces
- If the same topic already exists, append a numeric suffix: `-2`, `-3`

### Directory Structure

```
<project-root>/
├── .codex-tasks/                         # ← All task artifacts (NOT in ~/.codex/)
│   ├── 20260224-rest-api/                # Task 1
│   │   ├── SPEC.md                       # Frozen specification
│   │   ├── TODO.csv                      # Progress tracker
│   │   ├── PROGRESS.md                   # Decision log
│   │   └── raw/                          # Cached external data (optional)
│   ├── 20260224-auth-refactor/           # Task 2 (parallel, independent)
│   │   ├── SPEC.md
│   │   ├── TODO.csv
│   │   └── PROGRESS.md
│   └── .gitignore                        # Auto-created: ignores all task dirs
├── src/                                  # Project source — never polluted
├── ...
```

- `.codex-tasks/` lives at the **project root**, not the global `~/.codex/`.
- On first use, auto-create `.codex-tasks/.gitignore` with content: `*`
  (ignores all task artifacts by default).
- If the user explicitly wants task artifacts committed, remove the gitignore.
- When the task completes, ask the user whether to keep or delete the task dir.

### Workflow

#### Phase 0: Initialize

1. **Determine project root** — Git root if in repo, else CWD.
2. **Choose task name** — Semantic, unique (see Task Naming above).
3. **Create task directory**: `.codex-tasks/<task-name>/`
4. **Auto-create `.codex-tasks/.gitignore`** with content `*` if it doesn't exist.
5. **Create SPEC.md** from `assets/SPEC_TEMPLATE.md`:
   - Goals (what to build)
   - Non-goals (what NOT to do)
   - Constraints (tech stack, style, limits)
   - Environment (auto-detect: language, runtime, package manager, test framework)
   - Risk assessment (external deps, breaking changes, disk space, timeouts)
   - Deliverables (concrete outputs)
   - Done-when (final acceptance criteria + validation command)
   - Demo flow (how to verify the finished product)
6. **Log SPEC.md to conversation** for visibility, then **continue immediately**.
   Do NOT wait for user approval — autonomous execution is the default.
   SPEC.md is the reference anchor; if scope needs adjustment mid-task,
   update SPEC.md directly and log the change reason in PROGRESS.md.

#### Phase 1: Plan

1. **Break down into milestones** — 5-15 steps, verb-first text.
2. **Define verification for each step**:
   - `acceptance_criteria`: human-readable definition of done
   - `validation_command`: shell command that exits 0 on success
3. **Create TODO.csv**:

```csv
id,task,status,acceptance_criteria,validation_command,completed_at,retry_count,notes
1,<step text>,TODO,<what success looks like>,<command that exits 0>,,0,
2,<step text>,TODO,<what success looks like>,<command that exits 0>,,0,
```

Column rules:
- `status`: `TODO` | `IN_PROGRESS` | `DONE` | `FAILED`
- `completed_at`: empty until DONE, then local time `2026-02-05 11:38`
- `validation_command`: exits 0 = pass. Use `echo SKIP` for non-automatable steps.
- `retry_count`: starts 0, +1 on each validation failure

4. **Call `update_plan`** with matching steps (one `in_progress`).
5. **Initialize PROGRESS.md** from `assets/PROGRESS_TEMPLATE.md`.

#### Phase 2: Execute (the agent loop)

For each step, repeat:

```
1. RE-READ   → Load .codex-tasks/<task-name>/TODO.csv from disk (NOT memory)
2. MARK      → Set current step IN_PROGRESS in CSV + update_plan
3. IMPLEMENT → Do the actual work (scope: ONLY this step)
4. VALIDATE  → Run validation_command
   ├─ PASS   → Mark DONE, fill completed_at
   └─ FAIL   → Mark FAILED, retry_count += 1, append error to notes
              → Fix and re-validate
              → If retry_count >= 5 → Try alternative approach, log in PROGRESS.md
              → Only request human help if all alternatives exhausted
5. LOG       → Append entry to PROGRESS.md:
              - What was done
              - Key decisions + reasoning (alternatives considered)
              - Problems encountered + resolution
              - Next step preview
6. NEXT      → Go to step 1 for next TODO row
```

**Compaction recovery**: If you lose context mid-task, follow the
Context Recovery Protocol (see below) to restore state and resume.

#### Phase 3: Handle plan changes

- If scope changes mid-execution:
  1. Update `update_plan` first
  2. Apply same change to CSV (re-number `id` if needed)
  3. Update SPEC.md if the change affects goals/constraints
  4. Log the change reason in PROGRESS.md

#### Phase 4: Close-out

1. Verify ALL rows are DONE.
2. Run a final integration validation if defined in SPEC.md's done-when.
3. Write final summary in PROGRESS.md (total milestones, failures, recoveries,
   human interventions, key learnings).
4. Auto-delete `.codex-tasks/<task-name>/` by default. If the task was complex
   or produced valuable learnings, keep it and log the reason in PROGRESS.md.
5. If all tasks in `.codex-tasks/` are completed and deleted, remove the
   `.codex-tasks/` directory itself to leave the project clean.

### Context Protection

These rules prevent context degradation during long sessions:

- **Re-read before each step**: The CSV file is truth, not your memory of it.
  Always load `.codex-tasks/<task-name>/TODO.csv` from disk.
- **Keep conversation lean**: Reasoning and verbose output go to PROGRESS.md.
  The conversation should only contain status updates (Output Contract format).
- **Cache external data**: When fetching docs, APIs, or web pages, save raw
  results to `.codex-tasks/<task-name>/raw/` first. Process from local cache.
  Never fetch the same URL twice — check raw/ first.
- **No task drift**: Only work on the current IN_PROGRESS row. Ignore temptations
  to "improve" other parts of the codebase. If you spot an unrelated issue,
  note it in PROGRESS.md under "Recommendations" but do NOT fix it now.
- **Session handoff**: If stopping mid-task, ensure PROGRESS.md's Context
  Recovery Block is up-to-date so the next session can resume instantly.

### Context Recovery Protocol

When you lose context (compaction, session restart, manual resume, or `/continue`):

1. **Detect** — If you don't have clear knowledge of the current task state,
   you have lost context. Do NOT guess or hallucinate previous progress.
2. **Locate** — Find the task directory: `ls .codex-tasks/`
3. **Recover** — Read all three files in order:
   - `SPEC.md` → restore goal understanding and constraints
   - `TODO.csv` → find current progress (first non-DONE row = resume point)
   - `PROGRESS.md` → read the **Context Recovery Block** first (top of file),
     then skim recent milestone entries for decision context
4. **Verify** — Cross-check: does the CSV state match PROGRESS.md's last entry?
   If not, CSV wins (it's the source of truth).
5. **Resume** — Continue from the first non-DONE row in TODO.csv.
   Announce recovery in Output Contract format:
   ```
   🔄 上下文恢复完成
   任务: <from SPEC.md>
   进度: X/Y steps DONE
   恢复点: Step #N — <title>
   上次状态: <from PROGRESS.md Context Recovery Block>
   ```

> **Critical**: Update PROGRESS.md's Context Recovery Block EVERY time a
> milestone changes status. This block is the fast-path for recovery —
> without it, the agent must re-read every milestone entry to reconstruct state.

### Project Hygiene

- On first FULL mode use in a project, auto-create `.codex-tasks/.gitignore`
  with content `*` to prevent task artifacts from being committed.
- Task artifacts are gitignored by default. Only remove the gitignore if the
  user explicitly asks to commit task artifacts.
- When all tasks complete, auto-delete `.codex-tasks/` to leave the project clean.

### Output Contract

Every status update must include:
1. `任务:` one-line goal (from SPEC.md)
2. `进度:` X/Y steps DONE
3. `当前:` the IN_PROGRESS step (or FAILED step with retry count)
4. `验证:` last validation result (pass/fail + command used)
5. `文件:` `.codex-tasks/<task-name>/` path

### Example

```
.codex-tasks/
├── .gitignore                    # Content: *
└── 20260224-rest-api/
    ├── SPEC.md
    ├── TODO.csv
    ├── PROGRESS.md
    └── raw/                      # Cached external data
        └── openapi-spec.json
```

```csv
id,task,status,acceptance_criteria,validation_command,completed_at,retry_count,notes
1,Scaffold project structure,DONE,package.json + src/ exist,test -f package.json && test -d src,2026-02-24 11:36,0,
2,Implement core editor,IN_PROGRESS,Canvas renders shapes,npm test -- --grep editor,,1,First attempt: missing canvas dep
3,Add real-time collaboration,TODO,Cursors sync across tabs,npm test -- --grep collab,,0,
4,Write integration tests,TODO,All tests pass + coverage >80%,npm test && npm run coverage,,0,
5,Update documentation,TODO,README reflects all features,test -f README.md,,0,
```
