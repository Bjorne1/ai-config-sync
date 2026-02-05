# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Skill Manager 是一个 CLI 工具，用于统一管理多个 AI 工具的 Skills。通过软链接将 Skill 文件从统一源目录同步到 Claude、Codex、Gemini 等工具的技能目录。

## 常用命令

```bash
# 安装依赖
npm install

# 启动交互式菜单
npm start

# 命令行快捷操作
npm run status    # 查看状态
npm run sync      # 同步所有 Skill
npm run validate  # 验证链接

# 管理员权限启动（Windows）
start.bat
```

## 架构说明

### 核心模块

- `index.js` - 主入口，包含交互式菜单和所有用户操作（添加/禁用/移除/同步/验证）
- `lib/config.js` - 配置管理，定义默认目标目录（claude/codex/gemini/antigravity）
- `lib/scanner.js` - 扫描源目录中的 Skill 文件和目录
- `lib/linker.js` - 软链接操作（创建/删除/验证/权限检查）

### 数据流

1. 用户操作 → `index.js` 处理用户输入
2. 配置读写 → `config.js` 管理 `config.json`
3. 扫描源目录 → `scanner.js` 枚举可用 Skills
4. 链接操作 → `linker.js` 执行 symlink 创建/删除

### 配置结构 (config.json)

```json
{
  "sourceDir": "Skill 源文件目录",
  "targets": {},  // 自定义目标目录（覆盖默认值）
  "skills": {     // 已启用的 Skill 及其目标工具
    "skill-name": ["claude", "codex"]
  }
}
```

## Windows 特殊要求

创建软链接需要管理员权限或启用开发者模式。程序启动时会自动检测权限。
