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
