---
name: sp-executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute tasks with TDD and review after each task.

**Core principle:** TDD is mandatory, Review after each task.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Batch
**Default: First 3 tasks**

For each task:
1. **Update workflow state:** Mark task as `"in_progress"`, record current_step: 1

2. **Step 4.1: TDD Implementation (Mandatory)**
   - Follow RED-GREEN-REFACTOR cycle:
     * RED: Write failing test first
     * GREEN: Write minimal implementation to pass
     * REFACTOR: Clean up while keeping tests green
   - If you write code before tests: Delete the code and start over
   - Use `sp-test-driven-dev` skill

3. **Run verifications as specified**

4. **Step 4.2: Code Review (After each task)**
   - Announce: "Task complete. Requesting code review."
   - Use `sp-requesting-review` skill
   - Address any feedback before proceeding

5. **Update workflow state:** Mark task as `"completed"`, record commit_sha, completed_at timestamp

6. **Increment counter:** Update `completed_tasks` in workflow state

### Step 3: Report
When batch complete:
- Show what was implemented
- Show verification output
- Show review results
- Say: "Ready for feedback."

### Step 4: Continue
Based on feedback:
- Apply changes if needed
- Execute next batch
- Repeat until complete

### Step 5: Complete Development

After all tasks complete and verified:

**Proceed to finish branch**:
- Announce: "All tasks completed with TDD and reviewed. Ready to finish the branch."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

**Note:** Since every task has been reviewed, no final review is needed.

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker mid-batch (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- TDD is mandatory for all tasks (RED-GREEN-REFACTOR)
- Code Review after each task (not at the end)
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Between batches: just report and wait
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## State Management

**Before each task:**
1. Update task status: `"in_progress"`
2. Record current_step: 1
3. Update workflow state file at `.superpowers/workflows/<workflow-id>.json`

**After each task completion:**
1. Update task status: `"completed"`
2. Record commit_sha from git log
3. Record completed_at timestamp
4. Increment completed_tasks counter
5. Update workflow state file

**During batch execution:**
- Update current_step as progress through task steps
- Add notes for context if interrupted
- Save after each task completion

**After all tasks:**
1. Update current_phase: `"completed"`
2. Ready for sp-finishing-branch

**State file location:** `.superpowers/workflows/<workflow-id>.json`

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:test-driven-dev** - REQUIRED: TDD for each task implementation
- **superpowers:requesting-review** - REQUIRED: Review after each task
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
