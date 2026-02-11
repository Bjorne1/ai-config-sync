---
name: sp-continue
description: "Resume an incomplete workflow from a previous session"
---

# Continue Superpowers Workflow

Resume a workflow that was interrupted or left incomplete in a previous session.

## What This Does

1. Check if `.superpowers/workflows/` exists (create if needed)
2. Scan for active (incomplete) workflows
3. Present all active workflows with current status
4. Allow selection of which workflow to resume
5. Smart resume: detect exact resumption point (task, step)
6. Load context and continue execution

## Pre-check

Before scanning, ensure directory exists:
```bash
if [ ! -d .superpowers/workflows ]; then
  echo "No .superpowers/workflows/ directory found."
  echo "No active workflows. Start a new workflow with /sp-brainstorm"
  exit 0
fi
```

## Usage

Simply run:
```bash
/sp-continue
```

Or specify workflow ID directly:
```bash
/sp-continue <workflow-id>
```

## Resume Logic

The system will intelligently determine where to resume:

**If task is completed:**
- Skip to next pending task

**If task is in_progress:**
- Resume from last completed step
- Example: Task 3, Step 3 of 5 completed → Resume from Step 4

**If task is pending:**
- Start from beginning (Step 1)

**Context loaded:**
- Worktree path
- Implementation plan
- Previous task commits
- Current task details and notes

## Example Output

```
Found 2 active workflows:

1. user-authentication
   Phase: Implementation (subagent-driven)
   Progress: 2/5 tasks completed (40%)
   Current: Task 3 (API Endpoints) - Step 3/5 completed
   Last Update: 2026-02-04 15:30

2. payment-integration
   Phase: Planning
   Progress: Plan written, awaiting execution choice
   Last Update: 2026-02-03 18:00

Select workflow to continue [1-2]:
```

After selection:
```
Resuming: user-authentication

Context loaded:
- Worktree: .worktrees/feature-user-auth
- Implementation Plan: docs/plans/2026-02-04-user-authentication.md
- Completed: Task 1 (Auth Service), Task 2 (Token Handler)

Current Task: Task 3 (API Endpoints)
Progress: 3/5 steps completed
- ✓ Step 1: Write failing test
- ✓ Step 2: Verify test fails
- ✓ Step 3: Write implementation
- ⏸ Step 4: Verify test passes
- ⏸ Step 5: Commit

Resume from Step 4? [y/n]
```

## After Completing All Tasks

When all tasks in the workflow are completed:

**DO NOT automatically proceed to finishing-branch.**

Instead, present this message:

```
✓ All tasks completed successfully!

Workflow: {workflow_name}
Completed: {total_tasks}/{total_tasks} tasks
Worktree: {worktree_path}

All tasks have been implemented with TDD and reviewed.
Ready to finish the branch.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Complete and merge the branch:
  /sp-finishing-branch

[Optional] Verify task status accuracy:
  /sp-update-task

What would you like to do next?
```

**Important:**
- Every task has been reviewed (per-task review is mandatory)
- No final review is needed
- User can proceed directly to finishing-branch
- Always wait for user input - do not auto-proceed

## Cross-Session Support

Works seamlessly across:
- Multiple ClaudeCode sessions
- ClaudeCode to Codex (and vice versa)
- Long breaks between coding sessions
