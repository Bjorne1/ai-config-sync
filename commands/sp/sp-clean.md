---
name: sp-clean
description: "Clean up completed or abandoned workflow state files"
---

# Clean Workflows

Archive or delete completed/abandoned workflow state files.

## What This Does

**Pre-check:** If `.superpowers/workflows/` doesn't exist, inform user no workflows to clean.

Then:
1. Scan all workflow state files in `.superpowers/workflows/`
2. Categorize workflows:
   - **Completed**: current_phase = "completed"
   - **Active**: current_phase != "completed", recently updated
   - **Abandoned**: current_phase != "completed", >30 days old
3. Allow selection for cleanup
4. Provide options: Archive, Delete, Keep

## Cleanup Actions

**Archive:**
- Move to `.superpowers/archive/<workflow-id>.json`
- Preserves state for future reference
- Recommended for completed workflows

**Delete:**
- Permanently remove state file
- Cannot be undone
- Use for abandoned/test workflows

**Keep:**
- No action, workflow remains active

## Safety

**Completed workflows:**
- Can safely archive (preserves record)
- Delete only if truly no longer needed

**Active workflows:**
- Requires confirmation before any action
- Risk of losing progress

**Abandoned workflows (>30 days):**
- Suggested for cleanup
- Check if worktree still exists before deleting

## Usage

Interactive cleanup:
```bash
/sp-clean
```

Auto-archive completed:
```bash
/sp-clean --archive-completed
```

## Example Output

```
Workflow Cleanup:
═══════════════════════════════════════════════════════════════

Completed Workflows (suggest: Archive):
  1. user-authentication (completed 2026-02-01)
  2. bug-fix-login (completed 2026-01-28)

Active Workflows (suggest: Keep):
  3. payment-integration (in progress, updated 2026-02-03)

Abandoned Workflows (suggest: Delete):
  4. experimental-feature (pending, last update 2025-12-10)
  5. test-workflow (in progress, last update 2025-11-15)

───────────────────────────────────────────────────────────────
Select workflows to clean [comma-separated, e.g. 1,2,4]: 1,4

Workflow 1 (user-authentication): [A]rchive / [D]elete / [K]eep? a
Workflow 4 (experimental-feature): [A]rchive / [D]elete / [K]eep? d

Confirm actions:
  - Archive: user-authentication
  - Delete: experimental-feature
Proceed? [y/n]: y

✓ Archived: user-authentication → .superpowers/archive/
✓ Deleted: experimental-feature

Cleanup complete.
```

## When to Use

- After completing workflows (archive for history)
- Periodically to clean up abandoned experiments
- Before project handoff (clean state)
- When .superpowers/ directory gets cluttered
