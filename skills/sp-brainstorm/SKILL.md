---
name: sp-brainstorm
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

# Brainstorming Ideas Into Designs

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in small sections (200-300 words), checking after each section whether it looks right so far.

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Break it into sections of 200-300 words
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

## After the Design

**Documentation:**
- Write the validated design to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- **Reference format:** Use `./design-plan.template.md` as a guide for structure
- Use elements-of-style:writing-clearly-and-concisely skill if available
- Commit the design document to git

**Implementation (if continuing):**
- Ask: "Ready to set up for implementation?"
- Use sp-using-git-worktrees to create isolated workspace
- Use sp-writing-plans to create detailed implementation plan

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design in sections, validate each
- **Be flexible** - Go back and clarify when something doesn't make sense

## State Management

After design document is saved:

**Step 1: Ensure directory structure exists**
```bash
# Create .superpowers directory structure if not exists
mkdir -p .superpowers/workflows

# Create .gitignore if not exists
if [ ! -f .superpowers/.gitignore ]; then
  cat > .superpowers/.gitignore << 'EOF'
# Ignore all workflow state files
workflows/*.json

# Keep directory structure
!workflows/.gitkeep

# Ignore archive
archive/
EOF
fi
```

**Step 2: Create workflow state file**
- Path: `.superpowers/workflows/<workflow-id>.json`
- **Reference format:** Use `./workflow-status.template.json` as a guide
- Initialize with planning phase
- Record design_doc path and basic metadata

**State file structure:**
```json
{
  "workflow_id": "YYYY-MM-DD-<topic>",
  "workflow_type": "feature",
  "created_at": "<ISO timestamp>",
  "last_updated": "<ISO timestamp>",

  "artifacts": {
    "design_doc": "docs/plans/YYYY-MM-DD-<topic>-design.md",
    "impl_plan": "",
    "worktree_path": "",
    "worktree_branch": "",
    "base_branch": "main"
  },

  "execution": {
    "mode": "",
    "current_phase": "planning",
    "total_tasks": 0,
    "completed_tasks": 0
  },

  "tasks": [],

  "reviews": {
    "spec_reviews": [],
    "code_reviews": [],
    "pending_reviews": []
  },

  "metadata": {
    "session_ids": ["<current-session-id>"],
    "tags": [],
    "priority": "normal"
  }
}
```
