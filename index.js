const inquirer = require('inquirer');
const chalk = require('chalk');
const Table = require('cli-table3');
const path = require('path');
const fs = require('fs');
const config = require('./lib/config');
const scanner = require('./lib/scanner');
const fileSync = require('./lib/file-sync');
const linker = require('./lib/linker');
const updater = require('./lib/updater');
const git = require('./lib/git');

function isWindows() {
  return process.platform === 'win32';
}

const PERMISSION_HINTS = {
  windows: [
    '1. 以管理员身份运行',
    '2. 或在 Windows 设置中启用开发者模式',
    '   设置 → 更新和安全 → 开发者选项 → 开发人员模式'
  ],
  linux: [
    '1. 检查目标目录的写入权限',
    '2. 或使用 sudo 运行程序'
  ]
};

function findLegacyFlattenedCommand(commands, cmdName) {
  for (const cmd of commands) {
    if (!cmd.isDirectory) {
      continue;
    }

    const child = cmd.children.find(item => {
      return scanner.flattenCommandName(cmd.name, item) === cmdName;
    });

    if (child) {
      return {
        parentName: cmd.name,
        sourcePath: path.join(cmd.path, child)
      };
    }
  }

  return null;
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  console.log(chalk.cyan.bold('\n欢迎使用 Skill Manager!\n'));

  // 检查权限
  const permCheck = linker.checkSymlinkPermission();
  if (!permCheck.hasPermission) {
    console.log(chalk.red('❌ 创建软链接失败：权限不足\n'));
    console.log(chalk.yellow('解决方案：'));
    const hints = isWindows() ? PERMISSION_HINTS.windows : PERMISSION_HINTS.linux;
    hints.forEach(hint => console.log(hint));
    console.log();
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
      case 'sync-commands':
        await syncCommands(cfg);
        process.exit(0);
        break;
      case 'validate':
        await validateLinks(cfg);
        process.exit(0);
        break;
      case 'git-pull':
        await gitPullAll(cfg);
        process.exit(0);
        break;
      case 'git-push':
        await gitPushAll(cfg);
        process.exit(0);
        break;
      case 'git-status':
        await gitStatusAll(cfg);
        process.exit(0);
        break;
      default:
        console.log(chalk.red(`未知命令: ${command}\n`));
        console.log('可用命令:');
        console.log('  node index.js              - 启动交互式菜单');
        console.log('  node index.js status       - 查看状态');
        console.log('  node index.js sync         - 同步所有 Skills');
        console.log('  node index.js sync-commands- 同步所有 Commands');
        console.log('  node index.js validate     - 验证链接');
        console.log('  node index.js git-pull     - 批量 Git Pull');
        console.log('  node index.js git-push     - 批量 Git Push');
        console.log('  node index.js git-status   - 查看仓库状态\n');
        process.exit(1);
    }
  }

  // 显示菜单
  await showMenu(cfg);
}

async function showMenu(cfg) {
  const choices = [
    new inquirer.Separator('── Skills ──'),
    { name: '添加/启用 Skill', value: 'add' },
    { name: '禁用 Skill', value: 'disable' },
    { name: '移除 Skill', value: 'remove' },
    { name: '同步所有 Skills', value: 'sync' },
    new inquirer.Separator('── Commands ──'),
    { name: '添加/启用 Command', value: 'add-command' },
    { name: '禁用 Command', value: 'disable-command' },
    { name: '移除 Command', value: 'remove-command' },
    { name: '同步所有 Commands', value: 'sync-commands' },
    new inquirer.Separator('── 工具更新 ──'),
    { name: '一键更新所有工具', value: 'update-tools' },
    { name: '管理更新工具列表', value: 'manage-update-tools' },
    new inquirer.Separator('── Git 操作 ──'),
    { name: '批量 Git Pull', value: 'git-pull' },
    { name: '批量 Git Push', value: 'git-push' },
    { name: '查看仓库状态', value: 'git-status' },
    { name: '配置 Projects 目录', value: 'git-config' },
    new inquirer.Separator('── 其他 ──'),
    { name: '查看当前状态', value: 'status' },
    { name: '清理无效配置', value: 'cleanup' },
    { name: '修改源目录', value: 'change-source' },
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
    case 'add-command':
      await addCommand(cfg);
      break;
    case 'disable-command':
      await disableCommand(cfg);
      break;
    case 'remove-command':
      await removeCommand(cfg);
      break;
    case 'sync-commands':
      await syncCommands(cfg);
      break;
    case 'update-tools':
      await updateAllToolsMenu(cfg);
      break;
    case 'manage-update-tools':
      await manageUpdateTools(cfg);
      break;
    case 'git-pull':
      await gitPullAll(cfg);
      break;
    case 'git-push':
      await gitPushAll(cfg);
      break;
    case 'git-status':
      await gitStatusAll(cfg);
      break;
    case 'git-config':
      await manageGitConfig(cfg);
      break;
    case 'status':
      await showStatus(cfg);
      break;
    case 'cleanup':
      await cleanupInvalidConfig(cfg);
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
      message: '选择要启用的 Skills (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 可用 Skills ──'),
        ...skills.map(s => ({
          name: `${s.name}${s.isDirectory ? ' (目录)' : ''}`,
          value: s
        }))
      ]
    }
  ]);

  if (selectedSkills.length === 0) {
    return;
  }

  // 选择要启用到哪些工具
  const targets = config.getTargets(cfg);
  const toolNames = Object.keys(targets);

  const { selectedTools } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedTools',
      message: '选择要启用到的工具 (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 可用工具 ──'),
        ...toolNames.map(tool => ({
          name: tool,
          value: tool,
          checked: true // 默认全选
        }))
      ]
    }
  ]);

  if (selectedTools.length === 0) {
    return;
  }

  // 创建软链接
  console.log();
  for (const skill of selectedSkills) {
    for (const tool of selectedTools) {
      const targetDir = targets[tool];

      // 检查工具是否已安装
      if (!config.isToolInstalled(tool)) {
        console.log(chalk.yellow(`⚠ 跳过 ${tool}：工具未安装`));
        continue;
      }

      linker.ensureTargetDir(targetDir, true);

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
      choices: [
        { name: '← 返回主菜单', value: '__back__' },
        new inquirer.Separator('── 已启用 Skills ──'),
        ...enabledSkills
      ]
    }
  ]);

  if (skillName === '__back__') {
    return;
  }

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
      message: '选择要禁用的工具 (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 已启用工具 ──'),
        ...enabledTools.map(tool => ({
          name: tool,
          value: tool,
          checked: true
        }))
      ]
    }
  ]);

  if (selectedTools.length === 0) {
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
      message: '选择要移除的 Skills (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 已启用 Skills ──'),
        ...enabledSkills
      ]
    }
  ]);

  if (selectedSkills.length === 0) {
    return;
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

  // 同时显示 Commands 状态
  await showCommandStatus(cfg);
}

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

      // 检查工具是否已安装
      if (!config.isToolInstalled(tool)) {
        console.log(chalk.yellow(`⚠ ${skillName} → ${tool}: 工具未安装，已跳过`));
        skipCount++;
        continue;
      }

      linker.ensureTargetDir(targetDir, true);

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

async function addCommand(cfg) {
  const sourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  const commands = scanner.scanCommands(sourceDir);

  if (commands.length === 0) {
    console.log(chalk.yellow('\nCommands 源目录为空，请先添加 .md 文件\n'));
    return;
  }

  const { selectedCommands } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedCommands',
      message: '选择要启用的 Commands (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 可用 Commands ──'),
        ...commands.map(c => ({
          name: c.isDirectory ? `${c.name}/ (${c.children.length} 个文件)` : c.name,
          value: c
        }))
      ]
    }
  ]);

  if (selectedCommands.length === 0) return;

  const targets = config.getCommandTargets(cfg);
  const toolNames = Object.keys(targets);

  const { selectedTools } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedTools',
      message: '选择要启用到的工具 (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 可用工具 ──'),
        ...toolNames.map(tool => ({ name: tool, value: tool, checked: true }))
      ]
    }
  ]);

  if (selectedTools.length === 0) return;

  console.log();
  for (const cmd of selectedCommands) {
    for (const tool of selectedTools) {
      if (!config.isToolInstalled(tool)) {
        console.log(chalk.yellow(`⚠ 跳过 ${tool}：工具未安装`));
        continue;
      }

      const targetDir = targets[tool];
      linker.ensureTargetDir(targetDir, true);

      const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);
      const expanded = scanner.expandCommandsForTool([cmd], tool, subfolderSupport);

      for (const item of expanded) {
        const targetPath = path.join(targetDir, item.name);
        const result = fileSync.createCopy(item.sourcePath, targetPath);

        if (result.success) {
          if (result.skipped) {
            console.log(chalk.gray(`⊙ ${item.name} → ${tool}: ${result.message}`));
          } else {
            console.log(chalk.green(`✓ ${item.name} → ${tool}: ${result.message}`));
          }
        } else if (result.conflict) {
          const { overwrite } = await inquirer.prompt([
            { type: 'confirm', name: 'overwrite', message: `${item.name} → ${tool}: ${result.message}，是否覆盖？`, default: false }
          ]);
          if (overwrite) {
            const removeResult = fileSync.removePath(targetPath);
            if (!removeResult.success) {
              console.log(chalk.red(`❌ ${item.name} → ${tool}: ${removeResult.message}`));
              continue;
            }

            const retryResult = fileSync.createCopy(item.sourcePath, targetPath);
            if (retryResult.success) {
              console.log(chalk.green(`✓ ${item.name} → ${tool}: 创建成功`));
            } else {
              console.log(chalk.red(`❌ ${item.name} → ${tool}: ${retryResult.message}`));
            }
          } else {
            console.log(chalk.gray(`⊙ ${item.name} → ${tool}: 跳过`));
          }
        } else {
          console.log(chalk.red(`❌ ${item.name} → ${tool}: ${result.message}`));
        }
      }

      if (!cfg.commands) cfg.commands = {};
      if (!cfg.commands[cmd.name]) cfg.commands[cmd.name] = [];
      if (!cfg.commands[cmd.name].includes(tool)) cfg.commands[cmd.name].push(tool);
    }
  }

  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}

async function disableCommand(cfg) {
  const enabledCommands = Object.keys(cfg.commands || {});

  if (enabledCommands.length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Command\n'));
    return;
  }

  const { cmdName } = await inquirer.prompt([
    {
      type: 'list',
      name: 'cmdName',
      message: '选择要禁用的 Command:',
      choices: [
        { name: '← 返回主菜单', value: '__back__' },
        new inquirer.Separator('── 已启用 Commands ──'),
        ...enabledCommands
      ]
    }
  ]);

  if (cmdName === '__back__') return;

  const enabledTools = cfg.commands[cmdName];
  if (!enabledTools || enabledTools.length === 0) {
    console.log(chalk.yellow('\n该 Command 未启用到任何工具\n'));
    return;
  }

  const { selectedTools } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedTools',
      message: '选择要禁用的工具 (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 已启用工具 ──'),
        ...enabledTools.map(tool => ({ name: tool, value: tool, checked: true }))
      ]
    }
  ]);

  if (selectedTools.length === 0) return;

  const targets = config.getCommandTargets(cfg);
  const sourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  const commands = scanner.scanCommands(sourceDir);
  const cmd = commands.find(c => c.name === cmdName);

  console.log();
  for (const tool of selectedTools) {
    const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);

    if (cmd && cmd.isDirectory && !subfolderSupport) {
      const expanded = scanner.expandCommandsForTool([cmd], tool, false);
      for (const item of expanded) {
        const targetPath = path.join(targets[tool], item.name);
        const result = fileSync.removePath(targetPath);
        if (result.success) {
          console.log(chalk.green(`✓ ${item.name} → ${tool}: ${result.message}`));
        } else {
          console.log(chalk.red(`❌ ${item.name} → ${tool}: ${result.message}`));
        }
      }
    } else {
      const targetPath = path.join(targets[tool], cmdName);
      const result = fileSync.removePath(targetPath);
      if (result.success) {
        if (result.skipped) {
          console.log(chalk.gray(`⊙ ${cmdName} → ${tool}: ${result.message}`));
        } else {
          console.log(chalk.green(`✓ ${cmdName} → ${tool}: ${result.message}`));
        }
      } else {
        console.log(chalk.red(`❌ ${cmdName} → ${tool}: ${result.message}`));
      }
    }

    cfg.commands[cmdName] = cfg.commands[cmdName].filter(t => t !== tool);
  }

  if (cfg.commands[cmdName].length === 0) delete cfg.commands[cmdName];

  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}

async function removeCommand(cfg) {
  const enabledCommands = Object.keys(cfg.commands || {});

  if (enabledCommands.length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Command\n'));
    return;
  }

  const { selectedCommands } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selectedCommands',
      message: '选择要移除的 Commands (直接回车返回主菜单):',
      choices: [
        new inquirer.Separator('── 已启用 Commands ──'),
        ...enabledCommands
      ]
    }
  ]);

  if (selectedCommands.length === 0) return;

  const { confirmed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirmed',
      message: `确认从所有工具移除 ${selectedCommands.length} 个 Command？`,
      default: false
    }
  ]);

  if (!confirmed) {
    console.log(chalk.yellow('\n操作已取消\n'));
    return;
  }

  const targets = config.getCommandTargets(cfg);
  const sourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  const commands = scanner.scanCommands(sourceDir);

  console.log();
  for (const cmdName of selectedCommands) {
    const enabledTools = cfg.commands[cmdName] || [];
    const cmd = commands.find(c => c.name === cmdName);

    for (const tool of enabledTools) {
      const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);

      if (cmd && cmd.isDirectory && !subfolderSupport) {
        const expanded = scanner.expandCommandsForTool([cmd], tool, false);
        for (const item of expanded) {
          const targetPath = path.join(targets[tool], item.name);
          const result = fileSync.removePath(targetPath);
          if (result.success) {
            console.log(chalk.green(`✓ ${item.name} → ${tool}: ${result.message}`));
          } else {
            console.log(chalk.red(`❌ ${item.name} → ${tool}: ${result.message}`));
          }
        }
      } else {
        const targetPath = path.join(targets[tool], cmdName);
        const result = fileSync.removePath(targetPath);
        if (result.success) {
          console.log(chalk.green(`✓ ${cmdName} → ${tool}: ${result.message}`));
        } else {
          console.log(chalk.red(`❌ ${cmdName} → ${tool}: ${result.message}`));
        }
      }
    }

    delete cfg.commands[cmdName];
  }

  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 配置已保存\n'));
}

async function syncCommands(cfg) {
  console.log(chalk.cyan('\n🔄 开始同步所有 Commands...\n'));

  const enabledCommands = Object.keys(cfg.commands || {});

  if (enabledCommands.length === 0) {
    console.log(chalk.yellow('暂无已启用的 Command\n'));
    return;
  }

  const targets = config.getCommandTargets(cfg);
  const sourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  const commands = scanner.scanCommands(sourceDir);

  let successCount = 0;
  let failCount = 0;
  let skipCount = 0;
  let configChanged = false;

  for (const cmdName of enabledCommands) {
    const enabledTools = cfg.commands[cmdName];
    const cmd = commands.find(c => c.name === cmdName);

    if (!cmd) {
      const legacyCommand = findLegacyFlattenedCommand(commands, cmdName);
      if (legacyCommand) {
        console.log(chalk.yellow(`⚠ ${cmdName}: 检测到旧版扁平化配置，正在清理残留目标`));

        for (const tool of enabledTools) {
          const targetPath = path.join(targets[tool], cmdName);
          const result = fileSync.removePath(targetPath);
          if (result.success) {
            const color = result.skipped ? chalk.gray : chalk.green;
            const symbol = result.skipped ? '⊙' : '✓';
            console.log(color(`${symbol} ${cmdName} → ${tool}: ${result.message}`));
            successCount++;
          } else {
            console.log(chalk.red(`✗ ${cmdName} → ${tool}: ${result.message}`));
            failCount++;
          }
        }

        delete cfg.commands[cmdName];
        configChanged = true;
        continue;
      }

      console.log(chalk.red(`✗ ${cmdName}: 源文件不存在，已跳过`));
      skipCount++;
      continue;
    }

    for (const tool of enabledTools) {
      if (!config.isToolInstalled(tool)) {
        console.log(chalk.yellow(`⚠ ${cmdName} → ${tool}: 工具未安装，已跳过`));
        skipCount++;
        continue;
      }

      const targetDir = targets[tool];
      linker.ensureTargetDir(targetDir, true);

      const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);
      const expanded = scanner.expandCommandsForTool([cmd], tool, subfolderSupport);

      for (const item of expanded) {
        const targetPath = path.join(targetDir, item.name);
        const result = fileSync.syncCopy(item.sourcePath, targetPath);
        if (result.success) {
          const color = result.skipped ? chalk.gray : chalk.green;
          const symbol = result.skipped ? '⊙' : '✓';
          console.log(color(`${symbol} ${item.name} → ${tool}: ${result.message}`));
          successCount++;
        } else {
          console.log(chalk.red(`✗ ${item.name} → ${tool}: ${result.message}`));
          failCount++;
        }
      }
    }
  }

  console.log(chalk.cyan('\n同步完成：'));
  console.log(`✓ ${successCount} 成功 | ✗ ${failCount} 失败 | ⚠ ${skipCount} 跳过`);
  if (configChanged) {
    config.saveConfig(cfg);
    console.log(chalk.green('✓ 已清理旧版 Command 配置'));
  }
  console.log();
}

async function showCommandStatus(cfg) {
  console.log(chalk.cyan('\n📊 Commands 状态：\n'));

  const sourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  console.log(chalk.gray(`Commands 源目录: ${sourceDir}`));

  if (!cfg.commands || Object.keys(cfg.commands).length === 0) {
    console.log(chalk.yellow('\n暂无已启用的 Command\n'));
    return;
  }

  const targets = config.getCommandTargets(cfg);
  const toolNames = Object.keys(targets);
  const commands = scanner.scanCommands(sourceDir);

  const table = new Table({
    head: ['Command', ...toolNames],
    style: { head: ['cyan'] }
  });

  Object.keys(cfg.commands).forEach(cmdName => {
    const enabledTools = cfg.commands[cmdName];
    const cmd = commands.find(c => c.name === cmdName);
    const row = [cmdName];

    toolNames.forEach(tool => {
      if (!enabledTools.includes(tool)) {
        row.push(chalk.gray('-'));
        return;
      }

      const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);
      let valid = true;

      if (cmd && cmd.isDirectory && !subfolderSupport) {
        const expanded = scanner.expandCommandsForTool([cmd], tool, false);
        valid = expanded.every(item => {
          const targetPath = path.join(targets[tool], item.name);
          return fileSync.isSyncedCopy(item.sourcePath, targetPath);
        });
      } else {
        const targetPath = path.join(targets[tool], cmdName);
        const sourcePath = cmd ? cmd.path : path.join(sourceDir, cmdName);
        valid = fileSync.isSyncedCopy(sourcePath, targetPath);
      }

      row.push(valid ? chalk.green('✓') : chalk.red('✗'));
    });

    table.push(row);
  });

  console.log(table.toString());
  console.log();
}

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

async function cleanupInvalidConfig(cfg) {
  console.log(chalk.cyan('\n🧹 检查无效配置...\n'));

  const sourceDir = cfg.sourceDir;
  const commandsSourceDir = cfg.commandsSourceDir || path.join(process.cwd(), 'commands');
  const targets = config.getTargets(cfg);
  const commandTargets = config.getCommandTargets(cfg);

  const invalidSkills = [];
  const invalidCommands = [];  // { name, tools: [tool], deadLinks: [linkName] }

  // 检查 Skills
  for (const skillName of Object.keys(cfg.skills || {})) {
    const sourcePath = path.join(sourceDir, skillName);
    if (!fs.existsSync(sourcePath)) {
      invalidSkills.push(skillName);
    }
  }

  // 检查 Commands - 需要检查实际链接是否有效
  const commands = scanner.scanCommands(commandsSourceDir);
  for (const cmdName of Object.keys(cfg.commands || {})) {
    const enabledTools = cfg.commands[cmdName] || [];
    const cmd = commands.find(c => c.name === cmdName);

    // 源不存在，整个配置无效
    if (!cmd) {
      const legacyCommand = findLegacyFlattenedCommand(commands, cmdName);
      if (legacyCommand) {
        invalidCommands.push({ name: cmdName, tools: enabledTools, deadLinks: [cmdName] });
        continue;
      }

      // 检查是否是扁平化命名
      const dashIndex = cmdName.indexOf('-');
      if (dashIndex > 0) {
        const folderName = cmdName.substring(0, dashIndex);
        const fileName = cmdName.substring(dashIndex + 1);
        const expandedPath = path.join(commandsSourceDir, folderName, fileName);
        if (!fs.existsSync(expandedPath)) {
          invalidCommands.push({ name: cmdName, tools: enabledTools, deadLinks: [cmdName] });
        }
      } else {
        invalidCommands.push({ name: cmdName, tools: enabledTools, deadLinks: [cmdName] });
      }
      continue;
    }

    // 对于目录，检查展开后的链接
    if (cmd.isDirectory) {
      const deadLinks = [];
      for (const tool of enabledTools) {
        const subfolderSupport = config.getCommandSubfolderSupport(cfg, tool);
        if (subfolderSupport) {
          // 支持子文件夹，检查目录链接
          const targetPath = path.join(commandTargets[tool], cmdName);
          if (!fileSync.isSyncedCopy(cmd.path, targetPath)) {
            deadLinks.push({ tool, linkName: cmdName });
          }
        } else {
          // 不支持子文件夹，检查每个展开的文件链接
          const expanded = scanner.expandCommandsForTool([cmd], tool, false);
          const expectedNames = new Set(expanded.map(item => item.name));
          for (const item of expanded) {
            const targetPath = path.join(commandTargets[tool], item.name);
            if (fileSync.hasPath(targetPath) && !fileSync.isSyncedCopy(item.sourcePath, targetPath)) {
              deadLinks.push({ tool, linkName: item.name });
            }
          }

          // 检查是否有旧的展开目标（源文件已改名或历史残留）
          const toolDir = commandTargets[tool];
          if (fs.existsSync(toolDir)) {
            const existingLinks = fs.readdirSync(toolDir);
            const prefix = cmdName + '-';
            for (const link of existingLinks) {
              if (link.startsWith(prefix) && link.endsWith('.md') && !expectedNames.has(link)) {
                deadLinks.push({ tool, linkName: link });
              }
            }
          }
        }
      }

      if (deadLinks.length > 0) {
        invalidCommands.push({ name: cmdName, tools: enabledTools, deadLinks });
      }
    }
  }

  if (invalidSkills.length === 0 && invalidCommands.length === 0) {
    console.log(chalk.green('✓ 所有配置均有效，无需清理\n'));
    return;
  }

  // 显示无效项
  if (invalidSkills.length > 0) {
    console.log(chalk.yellow(`发现 ${invalidSkills.length} 个无效 Skill（源文件不存在）：`));
    invalidSkills.forEach(name => console.log(chalk.gray(`  - ${name}`)));
  }
  if (invalidCommands.length > 0) {
    console.log(chalk.yellow(`发现 ${invalidCommands.length} 个无效 Command 配置：`));
    invalidCommands.forEach(item => {
      console.log(chalk.gray(`  - ${item.name}`));
      item.deadLinks.forEach(link => {
        const linkName = typeof link === 'string' ? link : link.linkName;
        const tool = typeof link === 'string' ? '' : ` → ${link.tool}`;
        console.log(chalk.gray(`      残留目标: ${linkName}${tool}`));
      });
    });
  }

  // 确认清理
  const { confirmed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirmed',
      message: '是否清理这些无效配置并删除对应的残留目标？',
      default: true
    }
  ]);

  if (!confirmed) {
    console.log(chalk.yellow('\n操作已取消\n'));
    return;
  }

  console.log();

  // 清理无效 Skills
  for (const skillName of invalidSkills) {
    const enabledTools = cfg.skills[skillName] || [];
    for (const tool of enabledTools) {
      const targetPath = path.join(targets[tool], skillName);
      const result = linker.removeSymlink(targetPath);
      if (result.success && !result.skipped) {
        console.log(chalk.green(`✓ 删除死链接: ${skillName} → ${tool}`));
      }
    }
    delete cfg.skills[skillName];
  }

  // 清理无效 Commands
  for (const item of invalidCommands) {
    for (const link of item.deadLinks) {
      const linkName = typeof link === 'string' ? link : link.linkName;
      const tools = typeof link === 'string' ? item.tools : [link.tool];

      for (const tool of tools) {
        const targetPath = path.join(commandTargets[tool], linkName);
        const result = fileSync.removePath(targetPath);
        if (result.success && !result.skipped) {
          console.log(chalk.green(`✓ 删除残留目标: ${linkName} → ${tool}`));
        }
      }
    }

    // 如果整个配置无效（源不存在），删除配置
    const cmd = commands.find(c => c.name === item.name);
    if (!cmd) {
      delete cfg.commands[item.name];
    }
  }

  config.saveConfig(cfg);
  console.log(chalk.green('\n✓ 清理完成，配置已保存\n'));
}

async function updateAllToolsMenu(cfg) {
  console.log(chalk.cyan('\n🔄 开始更新所有工具...\n'));

  const tools = config.getUpdateTools(cfg);
  const entries = Object.entries(tools);

  if (entries.length === 0) {
    console.log(chalk.yellow('未配置任何更新工具\n'));
    return;
  }

  const results = await updater.updateAllTools(tools, (name, current, total) => {
    console.log(chalk.cyan(`\n[${current}/${total}] 正在更新 ${name}...`));
  });

  console.log(chalk.cyan('\n\n📊 更新结果：\n'));

  const table = new Table({
    head: ['工具', '更新前', '更新后', '状态'],
    style: { head: ['cyan'] }
  });

  results.forEach(r => {
    const before = r.versionBefore || '-';
    const after = r.versionAfter || '-';
    const status = r.success ? chalk.green('✓ 成功') : chalk.red('✗ 失败');
    table.push([r.name, before, after, status]);
  });

  console.log(table.toString());
  console.log();
}

async function manageUpdateTools(cfg) {
  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: '管理更新工具:',
      choices: [
        { name: '查看当前配置', value: 'list' },
        { name: '添加工具', value: 'add' },
        { name: '删除工具', value: 'remove' },
        { name: '返回主菜单', value: 'back' }
      ]
    }
  ]);

  switch (action) {
    case 'list':
      await listUpdateTools(cfg);
      break;
    case 'add':
      await addUpdateTool(cfg);
      break;
    case 'remove':
      await removeUpdateTool(cfg);
      break;
  }
}

async function listUpdateTools(cfg) {
  const tools = config.getUpdateTools(cfg);
  const entries = Object.entries(tools);

  if (entries.length === 0) {
    console.log(chalk.yellow('\n未配置任何更新工具\n'));
    return;
  }

  console.log(chalk.cyan('\n📋 当前更新工具配置：\n'));

  const table = new Table({
    head: ['工具名称', '类型', '配置'],
    style: { head: ['cyan'] }
  });

  entries.forEach(([name, cfg]) => {
    const detail = cfg.type === 'npm' ? cfg.package : cfg.command;
    table.push([name, cfg.type, detail]);
  });

  console.log(table.toString());
  console.log();
}

async function addUpdateTool(cfg) {
  const { name } = await inquirer.prompt([
    {
      type: 'input',
      name: 'name',
      message: '工具显示名称:',
      validate: input => input.trim() ? true : '请输入名称'
    }
  ]);

  const { type } = await inquirer.prompt([
    {
      type: 'list',
      name: 'type',
      message: '更新类型:',
      choices: [
        { name: 'npm (npm update -g)', value: 'npm' },
        { name: '自定义命令', value: 'custom' }
      ]
    }
  ]);

  let toolConfig;
  if (type === 'npm') {
    const { pkg } = await inquirer.prompt([
      {
        type: 'input',
        name: 'pkg',
        message: 'npm 包名 (如 @openai/codex):',
        validate: input => input.trim() ? true : '请输入包名'
      }
    ]);
    toolConfig = { type: 'npm', package: pkg.trim() };
  } else {
    const { command } = await inquirer.prompt([
      {
        type: 'input',
        name: 'command',
        message: '更新命令 (如 claude update):',
        validate: input => input.trim() ? true : '请输入命令'
      }
    ]);
    toolConfig = { type: 'custom', command: command.trim() };
  }

  const tools = { ...config.getUpdateTools(cfg) };
  tools[name.trim()] = toolConfig;
  config.setUpdateTools(cfg, tools);

  console.log(chalk.green(`\n✓ 已添加工具: ${name}\n`));
}

async function removeUpdateTool(cfg) {
  const tools = config.getUpdateTools(cfg);
  const names = Object.keys(tools);

  if (names.length === 0) {
    console.log(chalk.yellow('\n未配置任何更新工具\n'));
    return;
  }

  const { selected } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'selected',
      message: '选择要删除的工具:',
      choices: names
    }
  ]);

  if (selected.length === 0) return;

  const newTools = { ...tools };
  selected.forEach(name => delete newTools[name]);
  config.setUpdateTools(cfg, newTools);

  console.log(chalk.green(`\n✓ 已删除 ${selected.length} 个工具\n`));
}

async function gitPullAll(cfg) {
  const gitConfig = config.getGitConfig(cfg);

  if (gitConfig.projectDirs.length === 0) {
    console.log(chalk.yellow('\n未配置 Projects 目录，请先通过菜单 "配置 Projects 目录" 添加\n'));
    return;
  }

  console.log(chalk.cyan('\n🔍 扫描 Git 仓库...\n'));

  const repos = git.scanGitRepos(gitConfig.projectDirs, gitConfig.exclude);

  if (repos.length === 0) {
    console.log(chalk.yellow('未找到 Git 仓库\n'));
    return;
  }

  // 预览列表
  const table = new Table({
    head: ['仓库', '分支', '状态', 'Behind'],
    style: { head: ['cyan'] }
  });

  const repoStatuses = repos.map(repo => {
    const status = git.getRepoStatus(repo.path);
    return { ...repo, status };
  });

  repoStatuses.forEach(({ name, status }) => {
    const dirty = status.isDirty ? chalk.yellow('dirty') : chalk.green('clean');
    const behind = status.behind > 0 ? chalk.yellow(String(status.behind)) : chalk.gray('0');
    table.push([name, status.branch, dirty, behind]);
  });

  console.log(table.toString());

  const pullable = repoStatuses.filter(r => r.status.hasRemote && !r.status.isDirty && r.status.behind > 0);

  if (pullable.length === 0) {
    console.log(chalk.green('\n✓ 所有仓库已是最新（或因 dirty/无远程 跳过）\n'));
    return;
  }

  const { confirmed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirmed',
      message: `确认对 ${repos.length} 个仓库执行 git pull --ff-only？`,
      default: true
    }
  ]);

  if (!confirmed) {
    console.log(chalk.yellow('\n操作已取消\n'));
    return;
  }

  const results = await git.pullAll(repos, (name, current, total) => {
    console.log(chalk.cyan(`[${current}/${total}] ${name}...`));
  });

  // 结果表格
  console.log(chalk.cyan('\n📊 Pull 结果：\n'));

  const resultTable = new Table({
    head: ['仓库', '状态', '信息'],
    style: { head: ['cyan'] }
  });

  results.forEach(r => {
    const status = r.success
      ? (r.skipped ? chalk.gray('⊙ 跳过') : chalk.green('✓ 成功'))
      : chalk.red('✗ 失败');
    resultTable.push([r.name, status, r.message]);
  });

  console.log(resultTable.toString());
  console.log();
}

async function gitPushAll(cfg) {
  const gitConfig = config.getGitConfig(cfg);

  if (gitConfig.projectDirs.length === 0) {
    console.log(chalk.yellow('\n未配置 Projects 目录，请先通过菜单 "配置 Projects 目录" 添加\n'));
    return;
  }

  console.log(chalk.cyan('\n🔍 扫描 Git 仓库...\n'));

  const repos = git.scanGitRepos(gitConfig.projectDirs, gitConfig.exclude);

  if (repos.length === 0) {
    console.log(chalk.yellow('未找到 Git 仓库\n'));
    return;
  }

  // 预览列表
  const table = new Table({
    head: ['仓库', '分支', '状态', 'Ahead'],
    style: { head: ['cyan'] }
  });

  const repoStatuses = repos.map(repo => {
    const status = git.getRepoStatus(repo.path);
    return { ...repo, status };
  });

  repoStatuses.forEach(({ name, status }) => {
    const dirty = status.isDirty ? chalk.yellow('dirty') : chalk.green('clean');
    const ahead = status.ahead > 0 ? chalk.yellow(String(status.ahead)) : chalk.gray('0');
    table.push([name, status.branch, dirty, ahead]);
  });

  console.log(table.toString());

  const pushable = repoStatuses.filter(r => r.status.hasRemote && r.status.ahead > 0);

  if (pushable.length === 0) {
    console.log(chalk.green('\n✓ 所有仓库无需推送\n'));
    return;
  }

  const { confirmed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirmed',
      message: `确认对 ${repos.length} 个仓库执行 git push？`,
      default: true
    }
  ]);

  if (!confirmed) {
    console.log(chalk.yellow('\n操作已取消\n'));
    return;
  }

  const results = await git.pushAll(repos, (name, current, total) => {
    console.log(chalk.cyan(`[${current}/${total}] ${name}...`));
  });

  // 结果表格
  console.log(chalk.cyan('\n📊 Push 结果：\n'));

  const resultTable = new Table({
    head: ['仓库', '状态', '信息'],
    style: { head: ['cyan'] }
  });

  results.forEach(r => {
    const status = r.success
      ? (r.skipped ? chalk.gray('⊙ 跳过') : chalk.green('✓ 成功'))
      : chalk.red('✗ 失败');
    resultTable.push([r.name, status, r.message]);
  });

  console.log(resultTable.toString());
  console.log();
}

async function gitStatusAll(cfg) {
  const gitConfig = config.getGitConfig(cfg);

  if (gitConfig.projectDirs.length === 0) {
    console.log(chalk.yellow('\n未配置 Projects 目录，请先通过菜单 "配置 Projects 目录" 添加\n'));
    return;
  }

  console.log(chalk.cyan('\n🔍 扫描 Git 仓库...\n'));

  const repos = git.scanGitRepos(gitConfig.projectDirs, gitConfig.exclude);

  if (repos.length === 0) {
    console.log(chalk.yellow('未找到 Git 仓库\n'));
    return;
  }

  const table = new Table({
    head: ['仓库', '分支', '状态', 'Remote', 'Ahead', 'Behind'],
    style: { head: ['cyan'] }
  });

  repos.forEach(repo => {
    const status = git.getRepoStatus(repo.path);
    const dirty = status.isDirty ? chalk.yellow('dirty') : chalk.green('clean');
    const remote = status.hasRemote ? chalk.green('✓') : chalk.gray('✗');
    const ahead = status.ahead > 0 ? chalk.yellow(String(status.ahead)) : chalk.gray('0');
    const behind = status.behind > 0 ? chalk.yellow(String(status.behind)) : chalk.gray('0');
    table.push([repo.name, status.branch, dirty, remote, ahead, behind]);
  });

  console.log(table.toString());
  console.log(chalk.gray(`\n共 ${repos.length} 个仓库\n`));
}

async function manageGitConfig(cfg) {
  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: '配置 Projects 目录:',
      choices: [
        { name: '查看当前配置', value: 'list' },
        { name: '添加目录', value: 'add' },
        { name: '删除目录', value: 'remove' },
        { name: '管理排除列表', value: 'exclude' },
        { name: '返回主菜单', value: 'back' }
      ]
    }
  ]);

  const gitConfig = config.getGitConfig(cfg);

  switch (action) {
    case 'list': {
      console.log(chalk.cyan('\n📋 Git 配置：\n'));
      if (gitConfig.projectDirs.length === 0) {
        console.log(chalk.yellow('  Projects 目录: (未配置)'));
      } else {
        console.log('  Projects 目录:');
        gitConfig.projectDirs.forEach(dir => console.log(chalk.gray(`    - ${dir}`)));
      }
      if (gitConfig.exclude.length > 0) {
        console.log('  排除列表:');
        gitConfig.exclude.forEach(name => console.log(chalk.gray(`    - ${name}`)));
      }
      console.log();
      break;
    }
    case 'add': {
      const { dir } = await inquirer.prompt([
        {
          type: 'input',
          name: 'dir',
          message: '输入 Projects 目录路径 (支持 ~):',
          validate: input => input.trim() ? true : '路径不能为空'
        }
      ]);
      const absDir = git.expandHome(dir.trim());
      if (!fs.existsSync(absDir)) {
        console.log(chalk.red(`\n✗ 目录不存在: ${absDir}\n`));
        break;
      }
      if (gitConfig.projectDirs.includes(dir.trim())) {
        console.log(chalk.yellow(`\n⚠ 目录已存在\n`));
        break;
      }
      gitConfig.projectDirs.push(dir.trim());
      config.setGitConfig(cfg, gitConfig);
      console.log(chalk.green(`\n✓ 已添加: ${dir.trim()}\n`));
      break;
    }
    case 'remove': {
      if (gitConfig.projectDirs.length === 0) {
        console.log(chalk.yellow('\n未配置任何目录\n'));
        break;
      }
      const { selected } = await inquirer.prompt([
        {
          type: 'checkbox',
          name: 'selected',
          message: '选择要删除的目录:',
          choices: gitConfig.projectDirs
        }
      ]);
      if (selected.length === 0) break;
      gitConfig.projectDirs = gitConfig.projectDirs.filter(d => !selected.includes(d));
      config.setGitConfig(cfg, gitConfig);
      console.log(chalk.green(`\n✓ 已删除 ${selected.length} 个目录\n`));
      break;
    }
    case 'exclude': {
      const { excludeAction } = await inquirer.prompt([
        {
          type: 'list',
          name: 'excludeAction',
          message: '管理排除列表:',
          choices: [
            { name: '查看排除列表', value: 'list' },
            { name: '添加排除项', value: 'add' },
            { name: '删除排除项', value: 'remove' },
            { name: '返回', value: 'back' }
          ]
        }
      ]);

      if (excludeAction === 'list') {
        if (gitConfig.exclude.length === 0) {
          console.log(chalk.yellow('\n排除列表为空\n'));
        } else {
          console.log(chalk.cyan('\n排除列表：'));
          gitConfig.exclude.forEach(name => console.log(chalk.gray(`  - ${name}`)));
          console.log();
        }
      } else if (excludeAction === 'add') {
        const { name } = await inquirer.prompt([
          {
            type: 'input',
            name: 'name',
            message: '输入要排除的仓库名称:',
            validate: input => input.trim() ? true : '名称不能为空'
          }
        ]);
        if (!gitConfig.exclude.includes(name.trim())) {
          gitConfig.exclude.push(name.trim());
          config.setGitConfig(cfg, gitConfig);
          console.log(chalk.green(`\n✓ 已添加排除: ${name.trim()}\n`));
        } else {
          console.log(chalk.yellow('\n⚠ 已存在\n'));
        }
      } else if (excludeAction === 'remove') {
        if (gitConfig.exclude.length === 0) {
          console.log(chalk.yellow('\n排除列表为空\n'));
        } else {
          const { selected } = await inquirer.prompt([
            {
              type: 'checkbox',
              name: 'selected',
              message: '选择要移除的排除项:',
              choices: gitConfig.exclude
            }
          ]);
          if (selected.length > 0) {
            gitConfig.exclude = gitConfig.exclude.filter(n => !selected.includes(n));
            config.setGitConfig(cfg, gitConfig);
            console.log(chalk.green(`\n✓ 已移除 ${selected.length} 个排除项\n`));
          }
        }
      }
      break;
    }
  }
}

// 启动
main().catch(error => {
  console.error(chalk.red('发生错误：'), error.message);
  process.exit(1);
});
