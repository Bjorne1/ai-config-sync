# <Feature Name> Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `sp-executing-plans`
> or `sp-subagent-driven-development` to implement this plan task-by-task.

**Goal:** [Single sentence description]

**Architecture:** [2-3 sentences from design]

**Tech Stack:** [Key technologies/libraries]

---

## Task Breakdown

### Task 1: [Component Name]

**Files:**
- Create: `exact/path/to/file.ext`
- Modify: `exact/path/to/existing.ext:123-145`
- Test: `tests/exact/path/to/test.ext`

**Step 1: Write the failing test**
```language
[Complete test code]
```

**Step 2: Run test to verify it fails**
Run: `<exact command>`
Expected: FAIL with "<expected failure message>"

**Step 3: Write minimal implementation**
```language
[Minimal implementation code]
```

**Step 4: Run test to verify it passes**
Run: `<exact command>`
Expected: PASS (all tests green)

**Step 5: Commit**
```bash
git add <files>
git commit -m "feat: implement <component>"
```

---

### Task 2: [Next Component]

[Same structure as Task 1...]

---

## Execution Options

After saving this plan, choose execution mode:

1. **Subagent-Driven** (当前session)
   - Use: `sp-subagent-driven-development`
   - Best for: Independent tasks, fast iteration

2. **Parallel Session** (新session)
   - Use: `sp-executing-plans`
   - Best for: Coupled tasks, need human checkpoints
