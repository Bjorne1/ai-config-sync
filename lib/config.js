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

const DEFAULT_UPDATE_TOOLS = {
  'Claude Code': { type: 'custom', command: 'claude update' },
  'Codex': { type: 'npm', package: '@openai/codex' },
  'OpenSpec': { type: 'npm', package: '@fission-ai/openspec' },
  'Auggie': { type: 'npm', package: '@augmentcode/auggie' },
  'ace-tool': { type: 'npm', package: 'ace-tool' }
};

const DEFAULT_GIT_CONFIG = {
  projectDirs: [],
  exclude: []
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
  return 'skills';  // 使用相对路径
}

function getDefaultCommandsSourceDir() {
  return 'commands';  // 使用相对路径
}

function resolveSourceDir(configPath) {
  if (!configPath) return null;
  // 如果是相对路径，基于 cwd 解析
  if (!path.isAbsolute(configPath)) {
    return path.join(process.cwd(), configPath);
  }
  // 如果是绝对路径但不存在（可能是跨平台问题），尝试使用默认相对路径
  if (!fs.existsSync(configPath)) {
    const basename = path.basename(configPath);
    const fallback = path.join(process.cwd(), basename);
    if (fs.existsSync(fallback)) {
      return fallback;
    }
  }
  return configPath;
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    return null;
  }

  try {
    const content = fs.readFileSync(CONFIG_FILE, 'utf8');
    const config = JSON.parse(content);
    // 运行时解析源目录路径，处理跨平台兼容
    if (config.sourceDir) {
      config.sourceDir = resolveSourceDir(config.sourceDir);
    }
    if (config.commandsSourceDir) {
      config.commandsSourceDir = resolveSourceDir(config.commandsSourceDir);
    }
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
    commandSubfolderSupport: { ...DEFAULT_COMMAND_SUBFOLDER_SUPPORT },
    git: { ...DEFAULT_GIT_CONFIG }
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

function getUpdateTools(config) {
  return config.updateTools || DEFAULT_UPDATE_TOOLS;
}

function setUpdateTools(config, tools) {
  config.updateTools = tools;
  saveConfig(config);
}

function getGitConfig(config) {
  return config.git || { ...DEFAULT_GIT_CONFIG };
}

function setGitConfig(config, gitConfig) {
  config.git = gitConfig;
  saveConfig(config);
}

module.exports = {
  loadConfig,
  saveConfig,
  initConfig,
  getTargets,
  getCommandTargets,
  getCommandSubfolderSupport,
  getUpdateTools,
  setUpdateTools,
  getGitConfig,
  setGitConfig,
  isToolInstalled,
  resolveSourceDir,
  DEFAULT_TARGETS,
  DEFAULT_COMMAND_TARGETS,
  DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
  DEFAULT_UPDATE_TOOLS,
  DEFAULT_GIT_CONFIG,
  TOOL_ROOT_DIRS,
  CONFIG_FILE
};
