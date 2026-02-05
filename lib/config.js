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
    skills: {}
  };

  // 创建源目录
  if (!fs.existsSync(defaultConfig.sourceDir)) {
    fs.mkdirSync(defaultConfig.sourceDir, { recursive: true });
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

module.exports = {
  loadConfig,
  saveConfig,
  initConfig,
  getTargets,
  isToolInstalled,
  DEFAULT_TARGETS,
  TOOL_ROOT_DIRS,
  CONFIG_FILE
};
