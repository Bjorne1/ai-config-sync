---
name: sp-update-task
description: "Automatically analyze code changes and update task status in workflow state file"
---

# Auto Update Task Status

Automatically analyze the current code implementation and intelligently update task status in the workflow state file.

## Core Principle

**智能分析，自动更新** - 不需要手动输入，AI 自动判断任务完成情况。

## How It Works

1. **加载工作流上下文**：读取 `.superpowers/workflows/` 中的活跃工作流
2. **分析代码变更**：检查 git 提交记录、文件变更、测试状态
3. **智能判断状态**：根据实际实现情况判断每个任务的状态
4. **自动更新状态文件**：更新任务状态、时间戳、提交哈希等
5. **生成报告**：展示更新内容供用户确认

## Usage

```bash
/sp-update-task
```

或指定工作流 ID：

```bash
/sp-update-task <workflow-id>
```

## Automatic Analysis Process

### Step 1: 选择工作流

如果有多个活跃工作流，展示列表供选择：

```
Found 2 active workflows:

1. user-authentication (2026-02-04-user-auth)
   Phase: Implementation
   Progress: 2/5 tasks (outdated)
   Last Update: 10 minutes ago

2. payment-integration (2026-02-03-payment)
   Phase: Implementation
   Progress: 0/3 tasks (outdated)
   Last Update: 2 hours ago

Select workflow to analyze [1-2]:
```

### Step 2: 智能分析任务状态

对每个任务自动执行以下检查：

**1. 文件存在性检查**
- 任务要求创建的文件是否存在
- 新文件：任务可能已完成
- 文件不存在：任务未开始或未完成

**2. Git 提交历史分析**
- 搜索相关提交信息（包含任务关键词）
- 提取最新相关 commit SHA
- 判断任务是否有对应提交

**3. 测试状态检查**
- 运行相关测试（如果任务涉及测试）
- 检查测试是否通过
- 测试失败 → 任务未完成或有问题

**4. 代码实现完整性**
- 读取任务要求的关键文件
- 检查是否实现了核心功能
- 简单模式：检查关键函数/类是否存在
- 深度模式：分析实现是否符合任务要求

**5. 依赖任务状态**
- 检查前置任务是否完成
- 依赖未完成 → 当前任务不应标记为完成

### Step 3: 生成状态更新建议

```
Analyzing workflow: user-authentication
Implementation plan: docs/plans/2026-02-04-user-auth-plan.md
Worktree: .worktrees/feature-user-auth

Task Analysis:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Task 1: Auth Service
Current status: completed ✓
Analysis: No changes needed
Evidence:
  ✓ File exists: src/auth/AuthService.ts
  ✓ Commit found: abc123 "Add auth service with token validation"
  ✓ Tests passing: auth.service.test.ts (5/5)

Task 2: Token Handler
Current status: pending → completed ✓
Analysis: Should be marked as COMPLETED
Evidence:
  ✓ File exists: src/auth/TokenHandler.ts
  ✓ Commit found: def456 "Implement JWT token handler"
  ✓ Tests passing: token.handler.test.ts (8/8)
Suggested update:
  - status: "completed"
  - commit_sha: "def456789..."
  - completed_at: "2026-02-04T16:45:00Z"

Task 3: API Endpoints
Current status: pending → in_progress ⚠️
Analysis: Should be marked as IN_PROGRESS
Evidence:
  ✓ Files partially exist: src/api/auth/login.ts (exists)
  ✗ Files missing: src/api/auth/register.ts, logout.ts
  ✓ Recent work: 3 commits in last hour
  ⚠ Tests failing: api.auth.test.ts (2/5 passing)
Suggested update:
  - status: "in_progress"
  - started_at: "2026-02-04T16:30:00Z"
  - current_step: 2
  - notes: "Login endpoint implemented, register/logout pending"

Task 4: Middleware
Current status: pending ✓
Analysis: Not started yet
Evidence:
  ✗ No relevant files found
  ✗ No related commits
Suggested update: None

Task 5: Integration Tests
Current status: pending → blocked 🚫
Analysis: Should be marked as BLOCKED
Evidence:
  ✗ Depends on: Task 3, Task 4 (not completed)
  ⚠ Cannot start until dependencies complete
Suggested update:
  - status: "blocked"
  - blocked_reason: "Waiting for Task 3, Task 4 completion"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 2 tasks need status updates

Apply these updates? [Y/n]:
```

### Step 4: 应用更新

用户确认后，自动更新状态文件：

```
✓ Task 2 updated: pending → completed
✓ Task 3 updated: pending → in_progress
✓ Task 5 updated: pending → blocked
✓ Workflow completed_tasks: 1 → 2
✓ Workflow last_updated: 2026-02-04T17:00:00Z

Workflow state saved: .superpowers/workflows/2026-02-04-user-auth.json
```

## Analysis Algorithm

### Status Decision Logic

```
For each task:
  evidence = collect_evidence(task)

  IF task.status == "completed":
    # Already completed, verify it's still valid
    IF !verify_implementation(evidence):
      SUGGEST: "completed" → "in_progress" (regression detected)
    ELSE:
      KEEP: "completed"

  ELSE IF has_commit(evidence) AND tests_pass(evidence) AND files_complete(evidence):
    SUGGEST: current → "completed"

  ELSE IF has_recent_work(evidence) OR files_partial(evidence):
    SUGGEST: current → "in_progress"

  ELSE IF dependencies_incomplete(evidence):
    SUGGEST: current → "blocked"

  ELSE:
    KEEP: current (insufficient evidence to change)
```

### Evidence Collection

**File Analysis:**
```bash
# Check task-related files existence
task_files = extract_files_from_task_description(task)
for file in task_files:
  if exists(file):
    evidence.files_exist.append(file)
  else:
    evidence.files_missing.append(file)
```

**Git History:**
```bash
# Find related commits (last 7 days)
keywords = extract_keywords(task.title)
commits = git log --since="7 days ago" --grep="keyword1\|keyword2" --oneline

# Get most recent relevant commit
if commits:
  evidence.commit_sha = commits[0].sha
  evidence.commit_message = commits[0].message
  evidence.commit_time = commits[0].timestamp
```

**Test Execution:**
```bash
# Run tests mentioned in task or related to changed files
test_files = find_test_files(task_files)
for test in test_files:
  result = run_test(test)
  evidence.test_results[test] = {
    passed: result.passed_count,
    failed: result.failed_count,
    status: result.exit_code
  }
```

**Dependency Check:**
```bash
# Check if prerequisite tasks are completed
for dep in task.depends_on:
  dep_task = workflow.tasks[dep]
  if dep_task.status != "completed":
    evidence.blocked_by.append(dep)
```

## Advanced Features

### 1. 智能关键词提取

从任务标题和描述中提取关键词用于搜索：

```
Task: "Implement JWT token validation middleware"
Keywords extracted: ["JWT", "token", "validation", "middleware"]
Git search: git log --grep="JWT\|token\|validation\|middleware"
File search: rg -l "JWT|token|validation|middleware" src/
```

### 2. 模糊匹配文件路径

任务可能不包含精确文件路径，需要智能匹配：

```
Task mentions: "auth service"
Search patterns:
  - **/auth*Service.* (exact match)
  - **/auth/*.* (directory match)
  - **/AuthService.* (case insensitive)
  - src/**/auth*.* (common patterns)
```

### 3. 测试覆盖率检查

更深入的完成度判断：

```
IF task.type == "feature":
  check_test_coverage(task_files)
  IF coverage < 80%:
    warn("Tests may be incomplete")
    status_confidence = "medium"
```

### 4. 代码质量检查

检查实现质量（可选）：

```
IF files_exist AND !is_placeholder_code(files):
  status_confidence = "high"
ELSE:
  status_confidence = "low"
  notes += "Implementation may be placeholder/TODO"
```

## Configuration

可选：在工作流状态文件中添加分析配置

```json
{
  "analysis_config": {
    "git_history_days": 7,
    "require_tests": true,
    "min_test_coverage": 80,
    "check_placeholders": true,
    "auto_apply": false
  }
}
```

## What Gets Updated

**For completed tasks:**
- `status`: "completed"
- `completed_at`: 当前时间戳
- `commit_sha`: 最新相关提交哈希
- Workflow `completed_tasks` +1

**For in-progress tasks:**
- `status`: "in_progress"
- `started_at`: 首次相关提交时间
- `current_step`: 根据完成度估算（1-5）
- `notes`: 简要进度说明

**For blocked tasks:**
- `status`: "blocked"
- `blocked_at`: 当前时间戳
- `blocked_reason`: 依赖任务列表

**Always updated:**
- Task `last_updated`: 当前时间戳
- Workflow `last_updated`: 当前时间戳

## Error Handling

**No workflows found:**
```
No .superpowers/workflows/ directory found.
No active workflows exist.
Start a new workflow with /brainstorm
```

**Worktree not accessible:**
```
Warning: Worktree not found at .worktrees/feature-user-auth
Analysis will be limited to current workspace files.
Continue with limited analysis? [Y/n]:
```

**Git not available:**
```
Warning: Git history not accessible
Status update will be based on file analysis only
Continue? [Y/n]:
```

**Invalid workflow state:**
```
Error: Workflow state file is corrupted or invalid JSON.
File: .superpowers/workflows/2026-02-04-user-auth.json

Options:
1. View file for manual repair
2. Skip this workflow
3. Reinitialize workflow (loses progress tracking)

Select option [1-3]:
```

## Manual Override Mode

如果需要手动调整状态（不使用自动分析）：

```bash
/sp-update-task --manual
```

交互流程回退为手动选择模式：
1. 选择工作流
2. 选择任务
3. 手动选择状态
4. 输入可选的 commit SHA 和 notes

## Best Practices

1. **定期运行**：每完成一个任务后运行一次，保持状态同步
2. **工作流开始前**：运行一次确保干净状态
3. **恢复工作前**：运行一次了解当前进度
4. **提交前**：运行一次验证任务状态准确
5. **结合使用**：配合 `/sp-status` 查看全局状态

## Integration

与其他命令无缝配合：

- **`/brainstorm`** → 创建初始工作流状态
- **`/sp-continue`** → 读取更新后的状态继续工作
- **`/sp-status`** → 查看所有工作流状态
- **执行技能** → 自动或手动更新任务状态
- **`/sp-finishing-branch`** → 完成前最后验证状态

## Implementation Details

### File Structure Analysis

```bash
# Step 1: Load workflow state
workflow = read_json(".superpowers/workflows/${workflow_id}.json")
plan = read_file(workflow.artifacts.impl_plan)

# Step 2: Parse tasks from plan
tasks = extract_tasks_from_plan(plan)

# Step 3: Switch to worktree (if exists)
if workflow.artifacts.worktree_path:
  pushd(workflow.artifacts.worktree_path)

# Step 4: Analyze each task
for task in tasks:
  evidence = analyze_task(task)
  suggestion = decide_status(evidence)
  updates.append({task, suggestion, evidence})

# Step 5: Present suggestions
display_update_report(updates)

# Step 6: Apply updates (if confirmed)
if user_confirms():
  apply_updates(workflow, updates)
  save_workflow_state(workflow)
```

### Commit Search Strategy

```bash
# Search by task keywords in commit messages
keywords = extract_keywords(task.title)
pattern = join(keywords, "\\|")

# Search recent commits (last 7 days)
commits = git log \
  --since="7 days ago" \
  --grep="${pattern}" \
  --perl-regexp \
  --oneline \
  --all

# Filter commits in worktree branch (if applicable)
if worktree_branch:
  commits = filter_by_branch(commits, worktree_branch)

# Get most recent
latest_commit = commits[0]
```

### Test Execution Strategy

```bash
# Find test files related to task
task_files = extract_files(task)
test_files = []

for file in task_files:
  # Look for test files
  test_patterns = [
    "${file}.test.ts",
    "${file}.spec.ts",
    "**/__tests__/${basename(file)}.*",
    "**/tests/${basename(file)}.*"
  ]
  test_files += find_matching_files(test_patterns)

# Run tests
for test in test_files:
  result = run_test(test)
  collect_results(result)
```

## Cross-Platform Support

Works on both:
- **ClaudeCode** (uses CLAUDE.md for configuration)
- **Codex** (uses AGENT.md for configuration)

Supports multiple git environments:
- Standard git repositories
- Git worktrees
- Monorepo structures
