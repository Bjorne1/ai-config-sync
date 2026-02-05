# Skill Manager 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers-executing-plans` or `superpowers-subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现统一管理多个 AI 工具 skills 的命令行工具，通过软链接同步

**Architecture:** Node.js CLI 工具，使用 inquirer 提供交互式界面，通过 fs 模块管理软链接，配置文件驱动的 skill 同步机制

**Tech Stack:** Node.js, inquirer, chalk, cli-table3

---

## Task 1: 项目初始化

**Files:**
- Create: `package.json`
- Create: `skills\.gitkeep`

**Step 1: 初始化 package.json**

创建项目配置文件：

```json
{
  "name": "skill-manager",
  "version": "1.0.0",
  "description": "统一管理多个 AI 工具的 skills",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \"No tests yet\""
  },
  "keywords": ["cli", "skill", "symlink"],
  "author": "",
  "license": "MIT",
  "dependencies": {
    "inquirer": "^8.2.5",
    "chalk": "^4.1.2",
    "cli-table3": "^0.6.3"
  }
}
```

**Step 2: 安装依赖**

```bash
npm install
```

Expected: 成功安装 inquirer、chalk、cli-table3

**Step 3: 创建源目录占位文件**

```bash
mkdir skills
echo. > skills\.gitkeep
```

**Step 4: 提交**

```bash
git add package.json package-lock.json skills\.gitkeep
git commit -m "chore: initialize project with dependencies"
```

---

## Task 2: 配置模块 (config.js)

**Files:**
- Create: `lib\config.js`

**Step 1: 创建配置模块骨架**

```javascript
const fs = require('fs');
const path = require('path');
const os = require('os');

const CONFIG_FILE = path.join(__dirname, '..', 'config.json');
const homeDir = os.homedir();

const DEFAULT_TARGETS = {
  claude: path.join(homeDir, '.claude', 'skills'),
  codex: path.join(homeDir, '.codex', 'skills'),
  gemini: path.join(homeDir, '.gemini', 'skills'),
  antigravity: path.join(homeDir, '.gemini', 'antigravity', 'skills')
};

function getDefaultSourceDir() {
  return path.join(process.cwd(), 'skills');
}

function loadConfig() {
  // TODO: implement
}

function saveConfig(config) {
  // TODO: implement
}

function initConfig() {
  // TODO: implement
}

function getTargets(config) {
  // TODO: implement
}

module.exports = {
  loadConfig,
  saveConfig,
  initConfig,
  getTargets,
  DEFAULT_TARGETS,
  CONFIG_FILE
};
```

**Step 2: 实现 loadConfig 函数**

```javascript
function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    return null;
  }

  try {
    const content = fs.readFileSync(CONFIG_FILE, 'utf8');
    const config = JSON.parse(content);
    return config;
  } catch (error) {
    console.error('配置文件格式错误，将使用默认配置');
    // 备份损坏的配置
    const backupFile = `${CONFIG_FILE}.backup.${Date.now()}`;
    fs.copyFileSync(CONFIG_FILE, backupFile);
    return null;
  }
}
```

**Step 3: 实现 saveConfig 函数**

```javascript
function saveConfig(config) {
  const content = JSON.stringify(config, null, 2);
  fs.writeFileSync(CONFIG_FILE, content, 'utf8');
}
```

**Step 4: 实现 initConfig 函数**

```javascript
function initConfig() {
  const defaultConfig = {
    sourceDir: getDefaultSourceDir(),
    targets: {},
    skills: {}
  };

  // 创建源目录
  if (!fs.existsSync(defaultConfig.sourceDir)) {
    fs.mkdirSync(defaultConfig.sourceDir, { recursive: true });
  }

  saveConfig(defaultConfig);
  return defaultConfig;
}
```

**Step 5: 实现 getTargets 函数**

```javascript
function getTargets(config) {
  // 合并默认目标和自定义目标
  const targets = { ...DEFAULT_TARGETS };

  if (config.targets) {
    Object.keys(config.targets).forEach(tool => {
      if (config.targets[tool]) {
        targets[tool] = config.targets[tool];
      }
    });
  }

  return targets;
}
```

**Step 6: 提交**

```bash
git add lib\config.js
git commit -m "feat: add config module for managing configuration"
```

---

## Task 3: 扫描模块 (scanner.js)

**Files:**
- Create: `lib\scanner.js`

**Step 1: 创建扫描模块**

```javascript
const fs = require('fs');
const path = require('path');

function scanSkills(sourceDir) {
  if (!fs.existsSync(sourceDir)) {
    return [];
  }

  const items = fs.readdirSync(sourceDir);
  const skills = [];

  items.forEach(item => {
    // 跳过隐藏文件和 .gitkeep
    if (item.startsWith('.') || item === '.gitkeep') {
      return;
    }

    const fullPath = path.join(sourceDir, item);
    const stat = fs.statSync(fullPath);

    // 添加文件或目录
    if (stat.isFile() || stat.isDirectory()) {
      skills.push({
        name: item,
        path: fullPath,
        isDirectory: stat.isDirectory()
      });
    }
  });

  return skills;
}

function getSkillType(skillName) {
  return skillName.endsWith('/') ? 'dir' : 'file';
}

module.exports = {
  scanSkills,
  getSkillType
};
```

**Step 2: 提交**

```bash
git add lib\scanner.js
git commit -m "feat: add scanner module for discovering skills"
```

---

## Task 4: 软链接模块 (linker.js)

**Files:**
- Create: `lib\linker.js`

**Step 1: 创建软链接模块骨架**

```javascript
const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

function checkSymlinkPermission() {
  // TODO: implement
}

function isValidSymlink(targetPath, expectedSource) {
  // TODO: implement
}

function createSymlink(sourcePath, targetPath, isDirectory) {
  // TODO: implement
}

function removeSymlink(targetPath) {
  // TODO: implement
}

function ensureTargetDir(targetDir) {
  // TODO: implement
}

module.exports = {
  checkSymlinkPermission,
  isValidSymlink,
  createSymlink,
  removeSymlink,
  ensureTargetDir
};
```

**Step 2: 实现 ensureTargetDir 函数**

```javascript
function ensureTargetDir(targetDir) {
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }
}
```

**Step 3: 实现 isValidSymlink 函数**

```javascript
function isValidSymlink(targetPath, expectedSource) {
  try {
    if (!fs.existsSync(targetPath)) {
      return false;
    }

    const stats = fs.lstatSync(targetPath);
    if (!stats.isSymbolicLink()) {
      return false;
    }

    const linkTarget = fs.readlinkSync(targetPath);
    const resolvedTarget = path.resolve(path.dirname(targetPath), linkTarget);
    const resolvedExpected = path.resolve(expectedSource);

    return resolvedTarget === resolvedExpected;
  } catch (error) {
    return false;
  }
}
```

**Step 4: 实现 createSymlink 函数**

```javascript
function createSymlink(sourcePath, targetPath, isDirectory) {
  try {
    // 检查源是否存在
    if (!fs.existsSync(sourcePath)) {
      return {
        success: false,
        message: '源文件不存在'
      };
    }

    // 如果目标已存在
    if (fs.existsSync(targetPath)) {
      // 检查是否是有效的软链接
      if (isValidSymlink(targetPath, sourcePath)) {
        return {
          success: true,
          skipped: true,
          message: '已存在有效链接'
        };
      }

      // 存在冲突，需要用户确认
      return {
        success: false,
        conflict: true,
        message: '目标位置已存在文件或目录'
      };
    }

    // 创建软链接
    const type = isDirectory ? 'dir' : 'file';
    fs.symlinkSync(sourcePath, targetPath, type);

    return {
      success: true,
      message: '创建成功'
    };
  } catch (error) {
    // 权限错误
    if (error.code === 'EPERM') {
      return {
        success: false,
        permission: true,
        message: '权限不足'
      };
    }

    return {
      success: false,
      message: error.message
    };
  }
}
```

**Step 5: 实现 removeSymlink 函数**

```javascript
function removeSymlink(targetPath) {
  try {
    if (!fs.existsSync(targetPath)) {
      return {
        success: true,
        skipped: true,
        message: '链接不存在'
      };
    }

    const stats = fs.lstatSync(targetPath);
    if (!stats.isSymbolicLink()) {
      return {
        success: false,
        message: '目标不是软链接，拒绝删除'
      };
    }

    fs.unlinkSync(targetPath);

    return {
      success: true,
      message: '删除成功'
    };
  } catch (error) {
    return {
      success: false,
      message: error.message
    };
  }
}
```

**Step 6: 实现 checkSymlinkPermission 函数**

```javascript
function checkSymlinkPermission() {
  const testDir = path.join(process.cwd(), '.test-symlink');
  const testSource = path.join(testDir, 'source');
  const testTarget = path.join(testDir, 'target');

  try {
    // 创建测试目录
    fs.mkdirSync(testDir, { recursive: true });
    fs.writeFileSync(testSource, 'test');

    // 尝试创建软链接
    fs.symlinkSync(testSource, testTarget, 'file');

    // 清理
    fs.unlinkSync(testTarget);
    fs.unlinkSync(testSource);
    fs.rmdirSync(testDir);

    return { hasPermission: true };
  } catch (error) {
    // 清理
    try {
      if (fs.existsSync(testTarget)) fs.unlinkSync(testTarget);
      if (fs.existsSync(testSource)) fs.unlinkSync(testSource);
      if (fs.existsSync(testDir)) fs.rmdirSync(testDir);
    } catch (e) {}

    if (error.code === 'EPERM') {
      return {
        hasPermission: false,
        error: error.message
      };
    }

    return { hasPermission: false, error: error.message };
  }
}
```

**Step 7: 提交**

```bash
git add lib\linker.js
git commit -m "feat: add linker module for symlink operations"
```

---

## Task 5: 主入口和菜单 (index.js - Part 1)

**Files:**
- Create: `index.js`

**Step 1: 创建主入口骨架**

```javascript
const inquirer = require('inquirer');
const chalk = require('chalk');
const Table = require('cli-table3');
const config = require('./lib/config');
const scanner = require('./lib/scanner');
const linker = require('./lib/linker');

async function main() {
  console.log(chalk.cyan.bold('\n欢迎使用 Skill Manager!\n'));

  // 检查权限
  const permCheck = linker.checkSymlinkPermission();
  if (!permCheck.hasPermission) {
    console.log(chalk.red('❌ 创建软链接失败：权限不足\n'));
    console.log(chalk.yellow('解决方案：'));
    console.log('1. 以管理员身份运行');
    console.log('2. 或在 Windows 设置中启用开发者模式');
    console.log('   设置 → 更新和安全 → 开发者选项 → 开发人员模式\n');
    process.exit(1);
  }

  // 加载或初始化配置
  let cfg = config.loadConfig();
  if (!cfg) {
    console.log(chalk.yellow('检测到这是首次运行，正在初始化...\n'));
    cfg = config.initConfig();
    console.log(chalk.green('✓ 创建配置文件：config.json'));
    console.log(chalk.green(`✓ 创建源目录：${cfg.sourceDir}`));
    console.log(chalk.green('✓ 检测到 4 个工具目录\n'));
  }

  // 显示菜单
  await showMenu(cfg);
}

async function showMenu(cfg) {
  const choices = [
    { name: '添加/启用 Skill', value: 'add' },
    { name: '禁用 Skill', value: 'disable' },
    { name: '移除 Skill', value: 'remove' },
    { name: '查看当前状态', value: 'status' },
    { name: '修改源目录', value: 'change-source' },
    { name: '同步所有 Skill', value: 'sync' },
    { name: '退出', value: 'exit' }
  ];

  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: '请选择操作:',
      choices
    }
  ]);

  switch (action) {
    case 'add':
      await addSkill(cfg);
      break;
    case 'disable':
      await disableSkill(cfg);
      break;
    case 'remove':
      await removeSkill(cfg);
      break;
    case 'status':
      await showStatus(cfg);
      break;
    case 'change-source':
      await changeSourceDir(cfg);
      break;
    case 'sync':
      await syncAll(cfg);
      break;
    case 'exit':
      console.log(chalk.cyan('\n再见！\n'));
      process.exit(0);
  }

  // 继续显示菜单
  await showMenu(cfg);
}

// TODO: implement menu actions
async function addSkill(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

async function disableSkill(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

async function removeSkill(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

async function showStatus(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

async function changeSourceDir(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

async function syncAll(cfg) {
  console.log(chalk.yellow('功能开发中...'));
}

// 启动
main().catch(error => {
  console.error(chalk.red('发生错误：'), error.message);
  process.exit(1);
});
```

**Step 2: 测试基本菜单**

```bash
node index.js
```

Expected: 显示欢迎信息和菜单选项

**Step 3: 提交**

```bash
git add index.js
git commit -m "feat: add main entry and menu skeleton"
```

---

## Task 6: 实现"查看当前状态"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 showStatus 函数**

替换 `showStatus` 函数：

```javascript
async function showStatus(cfg) {
  console.log(chalk.cyan('\n📊 当前状态：\n'));

  const targets = config.getTargets(cfg);
  const toolNames = Object.keys(targets);

  // 检查源目录
  console.log(chalk.gray(`源目录: ${cfg.sourceDir}`));

  // 如果没有配置任何 skill
  if (Object.keys(cfg.skills).length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Skill\n'));
    return;
  }

  // 创建表格
  const table = new Table({
    head: ['Skill', ...toolNames],
    style: { head: ['cyan'] }
  });

  // 填充表格数据
  Object.keys(cfg.skills).forEach(skillName => {
    const enabledTools = cfg.skills[skillName];
    const row = [skillName];

    toolNames.forEach(tool => {
      if (enabledTools.includes(tool)) {
        // 检查链接是否有效
        const targetPath = path.join(targets[tool], skillName);
        const sourcePath = path.join(cfg.sourceDir, skillName);

        if (linker.isValidSymlink(targetPath, sourcePath)) {
          row.push(chalk.green('✓'));
        } else {
          row.push(chalk.red('✗'));
        }
      } else {
        row.push(chalk.gray('-'));
      }
    });

    table.push(row);
  });

  console.log(table.toString());
  console.log();
}
```

**Step 2: 添加必要的 require**

在文件顶部确保有：

```javascript
const path = require('path');
```

**Step 3: 测试状态显示**

```bash
node index.js
```

选择"查看当前状态"，应该显示"暂无已启用的 Skill"

**Step 4: 提交**

```bash
git add index.js
git commit -m "feat: implement status display with table"
```

---

## Task 7: 实现"添加/启用 Skill"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 addSkill 函数**

替换 `addSkill` 函数：

```javascript
async function addSkill(cfg) {
  // 扫描源目录
  const skills = scanner.scanSkills(cfg.sourceDir);

  if (skills.length === 0) {
    console.log(chalk.yellow('\n源目录为空，请先添加 skill 文件\n'));
    return;
  }

  // 选择要启用的 skills
  const { selectedSkills } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedSkills',
      message: '选择要启用的 Skills:',
      choices: skills.map(s => ({
        name: `${s.name}${s.isDirectory ? ' (目录)' : ''}`,
        value: s
      }))
    }
  ]);

  if (selectedSkills.length === 0) {
    console.log(chalk.yellow('\n未选择任何 Skill\n'));
    return;
  }

  // 选择要启用到哪些工具
  const targets = config.getTargets(cfg);
  const toolNames = Object.keys(targets);

  const { selectedTools } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedTools',
      message: '选择要启用到的工具:',
      choices: toolNames.map(tool => ({
        name: tool,
        value: tool,
        checked: true // 默认全选
      }))
    }
  ]);

  if (selectedTools.length === 0) {
    console.log(chalk.yellow('\n未选择任何工具\n'));
    return;
  }

  // 创建软链接
  console.log();
  for (const skill of selectedSkills) {
    for (const tool of selectedTools) {
      const targetDir = targets[tool];

      // 检查目标目录是否存在
      if (!fs.existsSync(targetDir)) {
        console.log(chalk.yellow(`⚠ 跳过 ${tool}：目录不存在 (${targetDir})`));
        continue;
      }

      linker.ensureTargetDir(targetDir);

      const sourcePath = skill.path;
      const targetPath = path.join(targetDir, skill.name);

      const result = linker.createSymlink(sourcePath, targetPath, skill.isDirectory);

      if (result.success) {
        if (result.skipped) {
          console.log(chalk.gray(`⊙ ${skill.name} → ${tool}: ${result.message}`));
        } else {
          console.log(chalk.green(`✓ ${skill.name} → ${tool}: ${result.message}`));

          // 更新配置
          if (!cfg.skills[skill.name]) {
            cfg.skills[skill.name] = [];
          }
          if (!cfg.skills[skill.name].includes(tool)) {
            cfg.skills[skill.name].push(tool);
          }
        }
      } else if (result.permission) {
        console.log(chalk.red(`❌ ${skill.name} → ${tool}: ${result.message}`));
        console.log(chalk.yellow('   提示：请以管理员身份运行或启用开发者模式'));
      } else if (result.conflict) {
        // 询问是否覆盖
        const { overwrite } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'overwrite',
            message: `${skill.name} → ${tool}: ${result.message}，是否覆盖？`,
            default: false
          }
        ]);

        if (overwrite) {
          // 删除旧文件/目录
          if (fs.lstatSync(targetPath).isSymbolicLink()) {
            fs.unlinkSync(targetPath);
          } else if (fs.statSync(targetPath).isDirectory()) {
            fs.rmSync(targetPath, { recursive: true });
          } else {
            fs.unlinkSync(targetPath);
          }

          // 重新创建
          const retryResult = linker.createSymlink(sourcePath, targetPath, skill.isDirectory);
          if (retryResult.success) {
            console.log(chalk.green(`✓ ${skill.name} → ${tool}: 创建成功`));

            // 更新配置
            if (!cfg.skills[skill.name]) {
              cfg.skills[skill.name] = [];
            }
            if (!cfg.skills[skill.name].includes(tool)) {
              cfg.skills[skill.name].push(tool);
            }
          } else {
            console.log(chalk.red(`❌ ${skill.name} → ${tool}: ${retryResult.message}`));
          }
        } else {
          console.log(chalk.gray(`⊙ ${skill.name} → ${tool}: 跳过`));
        }
      } else {
        console.log(chalk.red(`❌ ${skill.name} → ${tool}: ${result.message}`));
      }
    }
  }

  // 保存配置
  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}
```

**Step 2: 添加 fs require**

在文件顶部确保有：

```javascript
const fs = require('fs');
```

**Step 3: 创建测试 skill**

```bash
echo # Test Skill > skills\test-skill.md
```

**Step 4: 测试添加功能**

```bash
node index.js
```

选择"添加/启用 Skill"，测试完整流程

**Step 5: 提交**

```bash
git add index.js
git commit -m "feat: implement add/enable skill functionality"
```

---

## Task 8: 实现"禁用 Skill"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 disableSkill 函数**

替换 `disableSkill` 函数：

```javascript
async function disableSkill(cfg) {
  // 检查是否有已启用的 skills
  const enabledSkills = Object.keys(cfg.skills);

  if (enabledSkills.length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Skill\n'));
    return;
  }

  // 选择要禁用的 skill
  const { skillName } = await inquirer.prompt([
    {
      type: 'list',
      name: 'skillName',
      message: '选择要禁用的 Skill:',
      choices: enabledSkills
    }
  ]);

  const enabledTools = cfg.skills[skillName];

  if (enabledTools.length === 0) {
    console.log(chalk.yellow('\n该 Skill 未启用到任何工具\n'));
    return;
  }

  // 选择要从哪些工具禁用
  const { selectedTools } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedTools',
      message: '选择要禁用的工具:',
      choices: enabledTools.map(tool => ({
        name: tool,
        value: tool,
        checked: true
      }))
    }
  ]);

  if (selectedTools.length === 0) {
    console.log(chalk.yellow('\n未选择任何工具\n'));
    return;
  }

  // 删除软链接
  const targets = config.getTargets(cfg);
  console.log();

  for (const tool of selectedTools) {
    const targetPath = path.join(targets[tool], skillName);

    const result = linker.removeSymlink(targetPath);

    if (result.success) {
      if (result.skipped) {
        console.log(chalk.gray(`⊙ ${skillName} → ${tool}: ${result.message}`));
      } else {
        console.log(chalk.green(`✓ ${skillName} → ${tool}: ${result.message}`));
      }

      // 更新配置
      cfg.skills[skillName] = cfg.skills[skillName].filter(t => t !== tool);
    } else {
      console.log(chalk.red(`❌ ${skillName} → ${tool}: ${result.message}`));
    }
  }

  // 如果该 skill 不再启用到任何工具，从配置中删除
  if (cfg.skills[skillName].length === 0) {
    delete cfg.skills[skillName];
  }

  // 保存配置
  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}
```

**Step 2: 测试禁用功能**

```bash
node index.js
```

选择"禁用 Skill"，测试完整流程

**Step 3: 提交**

```bash
git add index.js
git commit -m "feat: implement disable skill functionality"
```

---

## Task 9: 实现"移除 Skill"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 removeSkill 函数**

替换 `removeSkill` 函数：

```javascript
async function removeSkill(cfg) {
  // 检查是否有已启用的 skills
  const enabledSkills = Object.keys(cfg.skills);

  if (enabledSkills.length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Skill\n'));
    return;
  }

  // 选择要移除的 skills
  const { selectedSkills } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedSkills',
      message: '选择要移除的 Skills (仅删除链接，不删除源文件):',
      choices: enabledSkills
    }
  ]);

  if (selectedSkills.length === 0) {
    console.log(chalk.yellow('\n未选择任何 Skill\n'));
    return;
  }

  // 二次确认
  const { confirmed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirmed',
      message: `确认从所有工具移除 ${selectedSkills.length} 个 Skill？`,
      default: false
    }
  ]);

  if (!confirmed) {
    console.log(chalk.yellow('\n操作已取消\n'));
    return;
  }

  // 删除软链接
  const targets = config.getTargets(cfg);
  console.log();

  for (const skillName of selectedSkills) {
    const enabledTools = cfg.skills[skillName] || [];

    for (const tool of enabledTools) {
      const targetPath = path.join(targets[tool], skillName);

      const result = linker.removeSymlink(targetPath);

      if (result.success) {
        console.log(chalk.green(`✓ ${skillName} → ${tool}: ${result.message}`));
      } else {
        console.log(chalk.red(`❌ ${skillName} → ${tool}: ${result.message}`));
      }
    }

    // 从配置中删除
    delete cfg.skills[skillName];
  }

  // 保存配置
  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}
```

**Step 2: 测试移除功能**

```bash
node index.js
```

选择"移除 Skill"，测试完整流程

**Step 3: 提交**

```bash
git add index.js
git commit -m "feat: implement remove skill functionality"
```

---

## Task 10: 实现"修改源目录"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 changeSourceDir 函数**

替换 `changeSourceDir` 函数：

```javascript
async function changeSourceDir(cfg) {
  console.log(chalk.gray(`\n当前源目录: ${cfg.sourceDir}\n`));

  const { newSourceDir } = await inquirer.prompt([
    {
      type: 'input',
      name: 'newSourceDir',
      message: '输入新的源目录路径:',
      default: cfg.sourceDir,
      validate: (input) => {
        if (!input || input.trim() === '') {
          return '路径不能为空';
        }
        return true;
      }
    }
  ]);

  const normalizedPath = path.resolve(newSourceDir);

  // 检查目录是否存在
  if (!fs.existsSync(normalizedPath)) {
    const { createDir } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'createDir',
        message: '目录不存在，是否创建？',
        default: true
      }
    ]);

    if (createDir) {
      fs.mkdirSync(normalizedPath, { recursive: true });
      console.log(chalk.green(`\n✓ 已创建目录: ${normalizedPath}\n`));
    } else {
      console.log(chalk.yellow('\n操作已取消\n'));
      return;
    }
  }

  // 更新配置
  cfg.sourceDir = normalizedPath;
  config.saveConfig(cfg);

  console.log(chalk.green('\n✓ 源目录已更新\n'));
}
```

**Step 2: 测试修改源目录功能**

```bash
node index.js
```

选择"修改源目录"，测试完整流程

**Step 3: 提交**

```bash
git add index.js
git commit -m "feat: implement change source directory functionality"
```

---

## Task 11: 实现"同步所有 Skill"功能

**Files:**
- Modify: `index.js`

**Step 1: 实现 syncAll 函数**

替换 `syncAll` 函数：

```javascript
async function syncAll(cfg) {
  console.log(chalk.cyan('\n🔄 开始同步所有 Skill...\n'));

  // 检查是否有已启用的 skills
  const enabledSkills = Object.keys(cfg.skills);

  if (enabledSkills.length === 0) {
    console.log(chalk.yellow('暂无已启用的 Skill\n'));
    return;
  }

  const targets = config.getTargets(cfg);
  let successCount = 0;
  let failCount = 0;
  let skipCount = 0;

  for (const skillName of enabledSkills) {
    const enabledTools = cfg.skills[skillName];
    const sourcePath = path.join(cfg.sourceDir, skillName);

    // 检查源是否存在
    if (!fs.existsSync(sourcePath)) {
      console.log(chalk.red(`✗ ${skillName}: 源文件不存在，已跳过`));
      skipCount++;
      continue;
    }

    const isDirectory = fs.statSync(sourcePath).isDirectory();

    for (const tool of enabledTools) {
      const targetDir = targets[tool];

      // 检查目标目录是否存在
      if (!fs.existsSync(targetDir)) {
        console.log(chalk.yellow(`⚠ ${skillName} → ${tool}: 目标目录不存在，已跳过`));
        skipCount++;
        continue;
      }

      linker.ensureTargetDir(targetDir);

      const targetPath = path.join(targetDir, skillName);

      // 如果已存在有效链接，跳过
      if (linker.isValidSymlink(targetPath, sourcePath)) {
        console.log(chalk.gray(`⊙ ${skillName} → ${tool}: 链接有效`));
        successCount++;
        continue;
      }

      // 如果存在损坏的链接或文件，删除
      if (fs.existsSync(targetPath)) {
        try {
          const stats = fs.lstatSync(targetPath);
          if (stats.isSymbolicLink()) {
            fs.unlinkSync(targetPath);
          } else if (stats.isDirectory()) {
            fs.rmSync(targetPath, { recursive: true });
          } else {
            fs.unlinkSync(targetPath);
          }
        } catch (error) {
          console.log(chalk.red(`✗ ${skillName} → ${tool}: 清理失败 - ${error.message}`));
          failCount++;
          continue;
        }
      }

      // 创建软链接
      const result = linker.createSymlink(sourcePath, targetPath, isDirectory);

      if (result.success) {
        console.log(chalk.green(`✓ ${skillName} → ${tool}: 修复成功`));
        successCount++;
      } else {
        console.log(chalk.red(`✗ ${skillName} → ${tool}: ${result.message}`));
        failCount++;
      }
    }
  }

  // 统计
  console.log(chalk.cyan('\n同步完成：'));
  console.log(chalk.green(`  成功: ${successCount}`));
  if (failCount > 0) {
    console.log(chalk.red(`  失败: ${failCount}`));
  }
  if (skipCount > 0) {
    console.log(chalk.yellow(`  跳过: ${skipCount}`));
  }
  console.log();
}
```

**Step 2: 测试同步功能**

```bash
node index.js
```

选择"同步所有 Skill"，测试完整流程

**Step 3: 提交**

```bash
git add index.js
git commit -m "feat: implement sync all skills functionality"
```

---

## Task 12: 支持快捷命令

**Files:**
- Modify: `index.js`

**Step 1: 添加命令行参数处理**

在 `main` 函数开头添加：

```javascript
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  console.log(chalk.cyan.bold('\n欢迎使用 Skill Manager!\n'));

  // 检查权限
  const permCheck = linker.checkSymlinkPermission();
  if (!permCheck.hasPermission) {
    console.log(chalk.red('❌ 创建软链接失败：权限不足\n'));
    console.log(chalk.yellow('解决方案：'));
    console.log('1. 以管理员身份运行');
    console.log('2. 或在 Windows 设置中启用开发者模式');
    console.log('   设置 → 更新和安全 → 开发者选项 → 开发人员模式\n');
    process.exit(1);
  }

  // 加载或初始化配置
  let cfg = config.loadConfig();
  if (!cfg) {
    console.log(chalk.yellow('检测到这是首次运行，正在初始化...\n'));
    cfg = config.initConfig();
    console.log(chalk.green('✓ 创建配置文件：config.json'));
    console.log(chalk.green(`✓ 创建源目录：${cfg.sourceDir}`));
    console.log(chalk.green('✓ 检测到 4 个工具目录\n'));
  }

  // 处理快捷命令
  if (command) {
    switch (command) {
      case 'status':
        await showStatus(cfg);
        process.exit(0);
        break;
      case 'sync':
        await syncAll(cfg);
        process.exit(0);
        break;
      case 'validate':
        await validateLinks(cfg);
        process.exit(0);
        break;
      default:
        console.log(chalk.red(`未知命令: ${command}\n`));
        console.log('可用命令:');
        console.log('  node index.js          - 启动交互式菜单');
        console.log('  node index.js status   - 查看状态');
        console.log('  node index.js sync     - 同步所有');
        console.log('  node index.js validate - 验证链接\n');
        process.exit(1);
    }
  }

  // 显示菜单
  await showMenu(cfg);
}
```

**Step 2: 添加 validateLinks 函数**

在 `syncAll` 函数后添加：

```javascript
async function validateLinks(cfg) {
  console.log(chalk.cyan('\n🔍 验证所有软链接...\n'));

  const enabledSkills = Object.keys(cfg.skills);

  if (enabledSkills.length === 0) {
    console.log(chalk.yellow('暂无已启用的 Skill\n'));
    return;
  }

  const targets = config.getTargets(cfg);
  let validCount = 0;
  let invalidCount = 0;
  const invalidLinks = [];

  for (const skillName of enabledSkills) {
    const enabledTools = cfg.skills[skillName];
    const sourcePath = path.join(cfg.sourceDir, skillName);

    for (const tool of enabledTools) {
      const targetPath = path.join(targets[tool], skillName);

      if (linker.isValidSymlink(targetPath, sourcePath)) {
        validCount++;
      } else {
        invalidCount++;
        invalidLinks.push({ skill: skillName, tool });
        console.log(chalk.red(`✗ ${skillName} → ${tool}: 链接无效或已损坏`));
      }
    }
  }

  console.log(chalk.cyan('\n验证完成：'));
  console.log(chalk.green(`  有效: ${validCount}`));
  if (invalidCount > 0) {
    console.log(chalk.red(`  无效: ${invalidCount}`));
    console.log(chalk.yellow('\n提示: 运行 "node index.js sync" 修复损坏的链接'));
  }
  console.log();
}
```

**Step 3: 测试快捷命令**

```bash
node index.js status
node index.js sync
node index.js validate
```

**Step 4: 提交**

```bash
git add index.js
git commit -m "feat: add command line shortcuts for status, sync, and validate"
```

---

## Task 13: 更新 package.json scripts

**Files:**
- Modify: `package.json`

**Step 1: 添加便捷脚本**

更新 `scripts` 部分：

```json
{
  "scripts": {
    "start": "node index.js",
    "status": "node index.js status",
    "sync": "node index.js sync",
    "validate": "node index.js validate",
    "test": "echo \"No tests yet\""
  }
}
```

**Step 2: 测试 npm scripts**

```bash
npm run status
npm run sync
npm run validate
```

**Step 3: 提交**

```bash
git add package.json
git commit -m "chore: add npm scripts for convenience"
```

---

## Task 14: 创建 .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: 创建 .gitignore 文件**

```
node_modules/
config.json
.test-symlink/
*.log
```

**Step 2: 提交**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Task 15: 最终测试和完善

**Step 1: 完整功能测试**

测试所有功能：
1. 启动程序 → 检查首次运行流程
2. 添加/启用 Skill → 测试多选和冲突处理
3. 查看状态 → 验证表格显示
4. 禁用 Skill → 验证部分禁用
5. 移除 Skill → 验证二次确认
6. 修改源目录 → 验证目录创建
7. 同步所有 → 验证修复功能
8. 快捷命令 → 验证 status/sync/validate

**Step 2: 边界情况测试**

- 源目录为空
- 目标工具目录不存在
- 权限不足
- 配置文件损坏
- 软链接损坏

**Step 3: 用户体验优化**

检查所有输出信息：
- 颜色使用是否合理
- 提示信息是否清晰
- 错误处理是否友好

**Step 4: 最终提交**

```bash
git add -A
git commit -m "test: complete full functionality testing and refinement"
```

---

## 完成标准

- ✅ 所有功能模块实现完成
- ✅ 交互式菜单正常工作
- ✅ 软链接创建/删除功能正常
- ✅ 配置文件读写正常
- ✅ 错误处理完善
- ✅ 权限检查有效
- ✅ 快捷命令可用
- ✅ 代码已提交到 git

## 测试验证清单

1. [ ] 首次运行初始化
2. [ ] 添加单个文件 skill
3. [ ] 添加目录 skill
4. [ ] 多工具同时启用
5. [ ] 冲突处理和覆盖
6. [ ] 查看状态表格
7. [ ] 禁用部分工具
8. [ ] 完全移除 skill
9. [ ] 修改源目录
10. [ ] 同步修复损坏链接
11. [ ] 验证链接有效性
12. [ ] 快捷命令执行
13. [ ] 权限不足提示
14. [ ] 目录不存在警告
