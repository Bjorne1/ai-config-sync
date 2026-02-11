---
name: sp-writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. Frequent commits.

**Note:** TDD is mandatory during execution, so plans don't need to explicitly specify TDD steps. However, you can include specific test case designs if helpful.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the sp-writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by sp-brainstorm skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

**Reference format:** Use `./implementation-plan.template.md` as a guide for structure

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `sp-executing-plans` or `sp-subagent-driven-development` to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

**Note:** TDD steps (write test → fail → implement → pass) are executed automatically during Phase 4. Plans can focus on *what* to test rather than *how* to follow TDD.

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Tests to write:**
- Test case 1: `test_specific_behavior` - verifies X returns Y
- Test case 2: `test_edge_case` - verifies handling of empty input

**Implementation:**
```python
def function(input):
    return expected
```

**Verification:**
Run: `pytest tests/path/test.py -v`
Expected: All tests pass

**Commit:**
```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, frequent commits
- TDD is enforced during execution - focus on *what* to test, not TDD mechanics

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use sp-subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Parallel Session chosen:**
- Guide them to open new session in worktree
- **REQUIRED SUB-SKILL:** New session uses sp-executing-plans

## State Management

After plan is saved:
1. Update workflow state file (`.superpowers/workflows/<workflow-id>.json`)
2. Record impl_plan path
3. Parse and add all tasks to state.tasks[] array
4. Set total_tasks count
5. Initialize each task with status: "pending"
6. Update current_phase to "execution_choice" or "implementation"
