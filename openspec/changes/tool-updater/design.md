## Context

当前项目是 Skill Manager，用于管理 AI 工具的 Skills 和 Commands 同步。用户在 WSL 侧安装了多个 AI 开发工具：
- Claude Code (`@anthropic-ai/claude-code`) - 有自带 `claude update` 命令
- Codex (`@openai/codex`) - npm 全局包
- OpenSpec (`@fission-ai/openspec`) - npm 全局包
- Auggie (`@augmentcode/auggie`) - npm 全局包
- ace-tool (`ace-tool`) - npm 全局包

这些工具更新频繁，用户需要逐个手动更新，效率低下。

## Goals / Non-Goals

**Goals:**
- 一键更新所有已配置的 WSL 侧工具
- 显示更新详情（当前版本、最新版本、更新结果）
- 支持添加/删除自定义工具
- 支持两种更新方式：npm 和自定义命令

**Non-Goals:**
- 不更新 Windows 侧工具（/mnt/c 路径下）
- 不自动检测未配置的工具
- 不支持版本回滚

## Decisions

### D1: 工具配置结构

**选择**: 在 config.json 中使用 `updateTools` 对象，key 为工具显示名，value 为配置对象。

```json
{
  "updateTools": {
    "Claude Code": {
      "type": "custom",
      "command": "claude update"
    },
    "Codex": {
      "type": "npm",
      "package": "@openai/codex"
    }
  }
}
```

**理由**:
- 与现有 `skills`、`commands` 配置风格一致
- 易于扩展新属性（如 versionCommand）
- key 为显示名便于用户理解

**备选**: 使用数组结构 → 查找效率低，去重复杂

### D2: Claude Code 更新方式

**选择**: 使用 `claude update` 自带命令

**理由**: Anthropic 官方推荐方式，可能包含额外的迁移逻辑

**备选**: `npm update -g` → 可能跳过官方迁移步骤

### D3: 版本检测方式

**选择**:
- npm 工具: `npm list -g <package> --json` 获取当前版本，`npm view <package> version` 获取最新版本
- custom 工具: 不预先检测版本，直接执行更新命令

**理由**: npm 有标准的版本查询机制；custom 命令的版本格式不统一，难以解析

### D4: 更新执行方式

**选择**: 串行执行，每个工具更新完成后再执行下一个

**理由**:
- 避免 npm 并发安装冲突
- 便于用户观察进度和错误

**备选**: 并行执行 → 可能导致 npm 锁冲突

## Risks / Trade-offs

- **[风险] npm 网络超时** → 使用默认超时，失败时显示错误并继续下一个工具
- **[风险] 自定义命令执行失败** → 捕获错误，显示失败信息，不中断整体流程
- **[权衡] 不检测 custom 工具版本** → 用户看到的信息较少，但实现更简单可靠
