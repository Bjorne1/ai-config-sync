const inquirer = require('inquirer');
const chalk = require('chalk');
const Table = require('cli-table3');
const path = require('path');
const fs = require('fs');
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

async function removeSkill(cfg) {
  console.log(chalk.yellow('功能开发中...'));
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
