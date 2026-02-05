# Skill Manager 设计文档

## 概述

统一管理多个 AI 工具（ClaudeCode、Codex、Gemini、Antigravity）的 skills，通过软链接方式实现一处更新、多处同步。

## 问题背景

- 4个工具的 skills 目录各不相同
- 每次添加/更新/删除 skill 需要手动到多个目录操作
- 维护成本高，容易遗漏或不一致

## 目标

- 统一源目录存放所有 skills
- 通过配置文件控制每个 skill 启用到哪些工具
- 提供交互式界面进行管理操作
- 自动创建/删除软链接

## 技术方案

### 技术栈

- **Node.js**: 主要开发语言
- **inquirer**: 交互式命令行界面
- **chalk**: 彩色输出
- **fs/path**: 文件和软链接操作
- **os**: 自动获取用户主目录

### 项目结构

```
skill-manager/
├── package.json          # 项目配置和依赖
├── index.js              # 主入口，启动交互式菜单
├── lib/
│   ├── config.js         # 配置文件读写和默认值
│   ├── linker.js         # 软链接创建/删除逻辑
│   └── scanner.js        # 扫描源目录的 skills
├── config.json           # 用户配置文件
└── docs/
    └── plans/
        └── 2026-02-04-skill-manager-design.md
```

### 配置文件设计

**config.json**:
```json
{
  "sourceDir": "D:\\wcs_project\\skill-manage\\skills",
  "targets": {},
  "skills": {
    "my-skill.md": ["claude", "codex"],
    "complex-skill/": ["claude", "gemini", "antigravity"]
  }
}
```

**字段说明**:
- `sourceDir`: 源 skills 目录（默认当前项目下的 `skills/`）
- `targets`: 工具目标目录映射（留空使用默认路径）
- `skills`: 每个 skill 启用到哪些工具

**默认目标路径** (代码中定义):
```javascript
const homeDir = os.homedir();
const DEFAULT_TARGETS = {
  claude: path.join(homeDir, '.claude', 'skills'),
  codex: path.join(homeDir, '.codex', 'skills'),
  gemini: path.join(homeDir, '.gemini', 'skills'),
  antigravity: path.join(homeDir, '.gemini', 'antigravity', 'skills')
};
```

## 功能设计

### 主菜单

```
? 请选择操作:
  ❯ 添加/启用 Skill
    禁用 Skill
    移除 Skill
    查看当前状态
    修改源目录
    同步所有 Skill
    退出
```

### 功能详细说明

#### 1. 添加/启用 Skill
- 扫描源目录，列出所有 skills（文件和目录）
- 多选框选择要操作的 skills
- 多选框选择要启用到哪些工具
- 创建软链接 + 更新配置文件

#### 2. 禁用 Skill
- 列出已启用的 skills
- 选择要禁用的 skill
- 选择要从哪些工具禁用
- 删除对应软链接 + 更新配置

#### 3. 移除 Skill
- 从所有工具移除该 skill 的软链接
- 从配置文件删除记录
- **不删除源文件**

#### 4. 查看当前状态
- 表格展示每个 skill 启用在哪些工具
- 显示软链接是否有效

#### 5. 修改源目录
- 输入新的源目录路径
- 更新配置并重新扫描

#### 6. 同步所有 Skill
- 根据配置文件重建所有软链接
- 修复损坏的链接

## 软链接实现逻辑

### 创建软链接流程

1. **检查源是否存在**
   - 验证源目录中的 skill 文件/目录是否存在
   - 不存在则跳过并警告

2. **检查目标目录**
   - 自动创建目标工具的 skills 目录（如果不存在）
   - 使用 `fs.mkdirSync(targetDir, { recursive: true })`

3. **处理冲突**
   - 如果目标位置已存在同名文件/目录/链接：
     - 如果是有效的软链接且指向源目录 → 跳过
     - 如果是文件/目录/损坏的链接 → 询问是否覆盖

4. **创建链接**
   ```javascript
   fs.symlinkSync(
     sourcePath,
     targetPath,
     isDirectory ? 'dir' : 'file'
   );
   ```

### 删除软链接流程

- 验证目标路径是软链接
- 只删除软链接，不删除源文件
- 删除后从配置中移除对应记录

### 权限处理 (Windows)

- 检测是否有创建软链接权限
- 失败时提示用户以管理员身份运行或开启开发者模式

## 错误处理

### 权限不足
```
❌ 创建软链接失败：权限不足

解决方案：
1. 以管理员身份运行
2. 或在 Windows 设置中启用开发者模式
   设置 → 更新和安全 → 开发者选项 → 开发人员模式
```

### 源目录不存在
- 首次运行时自动创建
- 提示用户：`源目录为空，请先添加 skill 文件`

### 目标工具目录不存在
```
⚠️  Codex 目录不存在：C:\Users\xxx\.codex\skills
是否继续为其他工具创建链接？
```

### 软链接损坏
- "查看状态"时标记为 `❌ 已损坏`
- "同步"操作时自动修复

### 配置文件损坏/不存在
- 自动创建默认配置
- 备份旧配置（如果格式错误）

## 用户体验设计

### 视觉反馈

```
✓ 成功创建软链接：my-skill.md → claude
✓ 成功创建软链接：my-skill.md → codex
⚠ 跳过 gemini：目录不存在
❌ 创建失败：权限不足

📊 当前状态：
┌─────────────────┬────────┬────────┬────────┬──────────────┐
│ Skill           │ Claude │ Codex  │ Gemini │ Antigravity  │
├─────────────────┼────────┼────────┼────────┼──────────────┤
│ my-skill.md     │   ✓    │   ✓    │   -    │      -       │
│ complex-skill/  │   ✓    │   -    │   ✓    │      ✓       │
└─────────────────┴────────┴────────┴────────┴──────────────┘
```

### 快捷命令支持

```bash
node index.js                    # 启动交互式菜单
node index.js status             # 快速查看状态
node index.js sync               # 快速同步所有
node index.js validate           # 验证所有链接有效性
```

### 首次运行流程

```
欢迎使用 Skill Manager！

检测到这是首次运行，正在初始化...
✓ 创建配置文件：config.json
✓ 创建源目录：D:\wcs_project\skill-manage\skills
✓ 检测到 4 个工具目录

请选择操作...
```

## 安全性考虑

- 删除操作前二次确认
- 覆盖文件前显示详情并确认
- 只删除软链接，永不删除源文件
- 配置文件验证和自动修复

## 性能优化

- 批量操作时显示进度条
- 大量 skills（>50个）时支持搜索过滤
- 缓存扫描结果避免重复读取

## 未来扩展

- 支持其他 AI 工具（Cursor、Windsurf 等）
- 支持 skill 模板快速创建
- 支持 skill 版本管理
- 远程 skill 仓库同步
