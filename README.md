# Skill Manager

统一管理多个 AI 工具的 Skills，通过软链接将 Skill 文件同步到 Claude、Codex、Gemini 等工具的技能目录。

## 功能特性

- 将 Skill 统一存放在一个源目录
- 通过软链接同步到多个 AI 工具
- 支持批量添加、禁用、移除 Skill
- 自动验证和修复损坏的链接

## 支持的工具

| 工具 | 目标目录 |
|------|----------|
| Claude | `~/.claude/skills` |
| Codex | `~/.codex/skills` |
| Gemini | `~/.gemini/skills` |
| Antigravity | `~/.gemini/antigravity/skills` |

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd skill-manage

# 安装依赖
npm install
```

## 使用前提

**Windows 需要管理员权限或开发者模式才能创建软链接：**

方式一：以管理员身份运行命令行

方式二：启用开发者模式
- 设置 → 更新和安全 → 开发者选项 → 开发人员模式

## 使用方式

### 交互式菜单

```bash
npm start
# 或
node index.js
```

### 命令行快捷方式

```bash
# 查看状态
npm run status
node index.js status

# 同步所有 Skill
npm run sync
node index.js sync

# 验证链接
npm run validate
node index.js validate
```

## 菜单功能说明

### 1. 添加/启用 Skill

从源目录扫描可用的 Skill 文件，选择要启用的 Skill 和目标工具。

### 2. 禁用 Skill

从指定工具中移除 Skill 链接，保留源文件。

### 3. 移除 Skill

从所有已启用的工具中移除 Skill 链接。

### 4. 查看当前状态

显示所有已启用 Skill 的状态表格：
- ✓ 链接有效
- ✗ 链接损坏或无效
- - 未启用到该工具

### 5. 修改源目录

更改 Skill 文件的存放位置。

### 6. 同步所有 Skill

检查并修复所有损坏的链接，确保配置与实际状态一致。

## 目录结构

```
skill-manage/
├── index.js          # 主程序
├── config.json       # 配置文件（自动生成）
├── skills/           # 默认源目录（自动生成）
│   ├── my-skill.md   # Skill 文件示例
│   └── my-skill-dir/ # Skill 目录示例
├── lib/
│   ├── config.js     # 配置管理
│   ├── scanner.js    # 目录扫描
│   └── linker.js     # 软链接操作
└── package.json
```

## 配置文件

`config.json` 结构：

```json
{
  "sourceDir": "D:\\wcs_project\\skill-manage\\skills",
  "targets": {},
  "skills": {
    "my-skill.md": ["claude", "codex"],
    "another-skill": ["claude"]
  }
}
```

- `sourceDir`: Skill 源文件目录
- `targets`: 自定义工具目录（覆盖默认值）
- `skills`: 已启用的 Skill 及其目标工具

## 常见问题

### 创建软链接失败

确保以管理员身份运行或已启用开发者模式。

### 链接显示无效

运行 `npm run sync` 修复损坏的链接。

### 添加新的目标工具

在 `config.json` 的 `targets` 中添加：

```json
{
  "targets": {
    "my-tool": "C:\\path\\to\\my-tool\\skills"
  }
}
```

## License

MIT
