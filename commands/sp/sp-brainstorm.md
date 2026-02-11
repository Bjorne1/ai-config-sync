---
name: sp-brainstorm
description: "Start the complete superpowers workflow from brainstorming to completion"
---

# Superpowers Brainstorm Workflow

This command initiates the full workflow for creating a new feature or component.

## What This Does

1. Brainstorm and design validation
2. Create isolated git worktree
3. Write detailed implementation plan
4. Execute tasks (choose between subagent-driven or parallel session)
5. Test and code review
6. Merge, PR, or keep branch

## Workflow

Use the Skill tool to invoke: `sp-brainstorm`

This will:
- Guide you through brainstorming with questions
- Present design in sections for validation
- Save design document to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Create workflow state file in `.superpowers/workflows/`
- Automatically proceed through setup, planning, and execution phases

## State Management

A workflow state file will be created for cross-session resumption.
Use `/sp-continue` to resume if interrupted.

## Example

```bash
# Start new workflow
/sp-brainstorm

# Claude will guide you through:
# 1. Understanding your requirements
# 2. Exploring design options
# 3. Creating worktree
# 4. Writing implementation plan
# 5. Executing tasks
```

## Cross-Platform Support

Works on both:
- **ClaudeCode** (uses CLAUDE.md for configuration)
- **Codex** (uses AGENT.md for configuration)
