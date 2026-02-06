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

const DEFAULT_COMMAND_TARGETS = {
  claude: path.join(homeDir, '.claude', 'commands'),
  codex: path.join(homeDir, '.codex', 'prompts'),
  gemini: path.join(homeDir, '.gemini', 'commands'),
  antigravity: path.join(homeDir, '.gemini', 'antigravity', 'global_workflows')
};

const DEFAULT_COMMAND_SUBFOLDER_SUPPORT = {
  default: false,
  tools: { claude: true }
};

// 工具根目录（用于判断工具是否已安装）
const TOOL_ROOT_DIRS = {
  claude: path.join(homeDir, '.claude'),
  codex: path.join(homeDir, '.codex'),
  gemini: path.join(homeDir, '.gemini'),
  antigravity: path.join(homeDir, '.gemini', 'antigravity')
};

function isToolInstalled(tool) {
  const rootDir = TOOL_ROOT_DIRS[tool];
  return rootDir && fs.existsSync(rootDir);
}

function getDefaultSourceDir() {
  return path.join(process.cwd(), 'skills');
}

function getDefaultCommandsSourceDir() {
  return path.join(process.cwd(), 'commands');
}

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

function saveConfig(config) {
  const content = JSON.stringify(config, null, 2);
  fs.writeFileSync(CONFIG_FILE, content, 'utf8');
}

function initConfig() {
  const defaultConfig = {
    sourceDir: getDefaultSourceDir(),
    targets: {},
    skills: {},
    commandsSourceDir: getDefaultCommandsSourceDir(),
    commandTargets: {},
    commands: {},
    commandSubfolderSupport: { ...DEFAULT_COMMAND_SUBFOLDER_SUPPORT }
  };

  // 创建源目录
  if (!fs.existsSync(defaultConfig.sourceDir)) {
    fs.mkdirSync(defaultConfig.sourceDir, { recursive: true });
  }

  // 创建 commands 源目录
  if (!fs.existsSync(defaultConfig.commandsSourceDir)) {
    fs.mkdirSync(defaultConfig.commandsSourceDir, { recursive: true });
  }

  saveConfig(defaultConfig);
  return defaultConfig;
}

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

function getCommandTargets(config) {
  const targets = { ...DEFAULT_COMMAND_TARGETS };

  if (config.commandTargets) {
    Object.keys(config.commandTargets).forEach(tool => {
      if (config.commandTargets[tool]) {
        targets[tool] = config.commandTargets[tool];
      }
    });
  }

  return targets;
}

function getCommandSubfolderSupport(config, tool) {
  const support = config.commandSubfolderSupport || DEFAULT_COMMAND_SUBFOLDER_SUPPORT;
  if (support.tools && support.tools[tool] !== undefined) {
    return support.tools[tool];
  }
  return support.default ?? false;
}

module.exports = {
  loadConfig,
  saveConfig,
  initConfig,
  getTargets,
  getCommandTargets,
  getCommandSubfolderSupport,
  isToolInstalled,
  DEFAULT_TARGETS,
  DEFAULT_COMMAND_TARGETS,
  DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
  TOOL_ROOT_DIRS,
  CONFIG_FILE
};
