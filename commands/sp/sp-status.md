---
name: sp-status
description: "View the status of all active superpowers workflows"
---

# Workflow Status

View the current state of all active superpowers workflows.

## What This Shows

**Pre-check:** If `.superpowers/workflows/` doesn't exist, inform user no workflows found.

For each active workflow:
- Workflow ID and type
- Current phase (planning, implementation, completed)
- Execution mode (subagent-driven, executing-plans)
- Task progress (completed/total)
- Current task and step
- Last update timestamp
- Worktree path
- Related documents

## Usage

View all workflows:
```bash
/sp-status
```

View specific workflow:
```bash
/sp-status <workflow-id>
```

## Output Example

```
Active Superpowers Workflows:
═══════════════════════════════════════════════════════════════

📋 Workflow: user-authentication
   Type: feature
   Phase: Implementation (subagent-driven)
   Progress: 2/5 tasks (40%)

   ✓ Task 1: Auth Service (abc123de)
   ✓ Task 2: Token Handler (def456gh)
   ⚙ Task 3: API Endpoints (Step 3/5 - in progress)
   ⏸ Task 4: Integration Tests
   ⏸ Task 5: Documentation

   Worktree: .worktrees/feature-user-auth
   Design: docs/plans/2026-02-04-user-authentication-design.md
   Plan: docs/plans/2026-02-04-user-authentication.md
   Last Update: 2026-02-04 15:30:00

───────────────────────────────────────────────────────────────

📋 Workflow: payment-integration
   Type: feature
   Phase: Planning
   Progress: Plan written, awaiting execution choice

   Worktree: .worktrees/feature-payment
   Design: docs/plans/2026-02-03-payment-integration-design.md
   Plan: docs/plans/2026-02-03-payment-integration.md
   Last Update: 2026-02-03 18:00:00

═══════════════════════════════════════════════════════════════
Total: 2 active workflows
```

## When to Use

- Check progress of current work
- Before starting a new workflow (see what's already in progress)
- After resuming a session (remind yourself of active work)
- Before cleanup (see what can be archived)
