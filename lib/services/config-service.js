const fs = require('fs');
const path = require('path');
const {
  buildTargetMap,
  CONFIG_VERSION,
  DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
  DEFAULT_SYNC_MODE,
  DEFAULT_UPDATE_TOOLS,
  TOOL_IDS,
  WINDOWS_HOME_TOKEN,
  WSL_HOME_TOKEN
} = require('./tool-definitions');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const CONFIG_FILE = path.join(PROJECT_ROOT, 'config.json');

function resolveSourceDir(configPath) {
  if (!configPath) {
    return null;
  }

  if (path.isAbsolute(configPath)) {
    return configPath;
  }

  return path.resolve(PROJECT_ROOT, configPath);
}

function normalizeToolList(input) {
  const items = Array.isArray(input) ? input : [];
  return Array.from(new Set(items.filter(item => TOOL_IDS.includes(item))));
}

function normalizeResourceMap(input) {
  const entries = input && typeof input === 'object' ? Object.entries(input) : [];
  return entries.reduce((resources, [name, tools]) => {
    const normalizedTools = normalizeToolList(tools);
    if (normalizedTools.length === 0) {
      return resources;
    }

    return {
      ...resources,
      [name]: normalizedTools
    };
  }, {});
}

function normalizeCommandSubfolderSupport(input) {
  const support = input && typeof input === 'object' ? input : {};
  const tools = support.tools && typeof support.tools === 'object' ? support.tools : {};
  const normalizedTools = Object.entries(tools).reduce((result, [toolId, enabled]) => {
    if (!TOOL_IDS.includes(toolId)) {
      return result;
    }

    return {
      ...result,
      [toolId]: Boolean(enabled)
    };
  }, {});

  return {
    default: support.default ?? DEFAULT_COMMAND_SUBFOLDER_SUPPORT.default,
    tools: {
      ...DEFAULT_COMMAND_SUBFOLDER_SUPPORT.tools,
      ...normalizedTools
    }
  };
}

function normalizeUpdateTools(input) {
  if (!input || typeof input !== 'object') {
    return { ...DEFAULT_UPDATE_TOOLS };
  }

  return Object.entries(input).reduce((tools, [name, value]) => {
    if (!value || typeof value !== 'object' || !value.type) {
      return tools;
    }

    return {
      ...tools,
      [name]: { ...value }
    };
  }, {});
}

function createDefaultConfig() {
  return {
    version: CONFIG_VERSION,
    syncMode: DEFAULT_SYNC_MODE,
    sourceDirs: {
      skills: resolveSourceDir('skills'),
      commands: resolveSourceDir('commands')
    },
    environments: {
      windows: {
        enabled: true,
        targets: {
          skills: buildTargetMap(WINDOWS_HOME_TOKEN, 'skills', path.win32),
          commands: buildTargetMap(WINDOWS_HOME_TOKEN, 'commands', path.win32)
        }
      },
      wsl: {
        enabled: false,
        selectedDistro: null,
        targets: {
          skills: buildTargetMap(WSL_HOME_TOKEN, 'skills', path.posix),
          commands: buildTargetMap(WSL_HOME_TOKEN, 'commands', path.posix)
        }
      }
    },
    resources: {
      skills: {},
      commands: {}
    },
    commandSubfolderSupport: normalizeCommandSubfolderSupport(null),
    updateTools: normalizeUpdateTools(null)
  };
}

function isLegacyConfig(config) {
  return !config || !config.version || !config.sourceDirs || !config.environments || !config.resources;
}

function mergeTargets(defaultTargets, overrides) {
  const source = overrides && typeof overrides === 'object' ? overrides : {};
  return TOOL_IDS.reduce((targets, toolId) => {
    return {
      ...targets,
      [toolId]: source[toolId] || defaultTargets[toolId]
    };
  }, {});
}

function migrateLegacyConfig(legacyConfig) {
  const defaults = createDefaultConfig();
  const legacy = legacyConfig && typeof legacyConfig === 'object' ? legacyConfig : {};

  return {
    version: CONFIG_VERSION,
    syncMode: legacy.syncMode || DEFAULT_SYNC_MODE,
    sourceDirs: {
      skills: resolveSourceDir(legacy.sourceDir || defaults.sourceDirs.skills),
      commands: resolveSourceDir(legacy.commandsSourceDir || defaults.sourceDirs.commands)
    },
    environments: {
      windows: {
        enabled: true,
        targets: {
          skills: mergeTargets(defaults.environments.windows.targets.skills, legacy.targets),
          commands: mergeTargets(defaults.environments.windows.targets.commands, legacy.commandTargets)
        }
      },
      wsl: {
        enabled: Boolean(legacy.wslEnabled),
        selectedDistro: legacy.wslDistro || null,
        targets: {
          skills: mergeTargets(defaults.environments.wsl.targets.skills, legacy.wslTargets?.skills),
          commands: mergeTargets(defaults.environments.wsl.targets.commands, legacy.wslTargets?.commands)
        }
      }
    },
    resources: {
      skills: normalizeResourceMap(legacy.skills),
      commands: normalizeResourceMap(legacy.commands)
    },
    commandSubfolderSupport: normalizeCommandSubfolderSupport(legacy.commandSubfolderSupport),
    updateTools: normalizeUpdateTools(legacy.updateTools || DEFAULT_UPDATE_TOOLS)
  };
}

function normalizeConfigShape(config) {
  const defaults = createDefaultConfig();
  const input = config && typeof config === 'object' ? config : {};
  const environments = input.environments && typeof input.environments === 'object' ? input.environments : {};
  const windows = environments.windows && typeof environments.windows === 'object' ? environments.windows : {};
  const wsl = environments.wsl && typeof environments.wsl === 'object' ? environments.wsl : {};

  return {
    version: CONFIG_VERSION,
    syncMode: input.syncMode === 'copy' ? 'copy' : DEFAULT_SYNC_MODE,
    sourceDirs: {
      skills: resolveSourceDir(input.sourceDirs?.skills || defaults.sourceDirs.skills),
      commands: resolveSourceDir(input.sourceDirs?.commands || defaults.sourceDirs.commands)
    },
    environments: {
      windows: {
        enabled: true,
        targets: {
          skills: mergeTargets(defaults.environments.windows.targets.skills, windows.targets?.skills),
          commands: mergeTargets(defaults.environments.windows.targets.commands, windows.targets?.commands)
        }
      },
      wsl: {
        enabled: Boolean(wsl.enabled),
        selectedDistro: wsl.selectedDistro || null,
        targets: {
          skills: mergeTargets(defaults.environments.wsl.targets.skills, wsl.targets?.skills),
          commands: mergeTargets(defaults.environments.wsl.targets.commands, wsl.targets?.commands)
        }
      }
    },
    resources: {
      skills: normalizeResourceMap(input.resources?.skills),
      commands: normalizeResourceMap(input.resources?.commands)
    },
    commandSubfolderSupport: normalizeCommandSubfolderSupport(input.commandSubfolderSupport),
    updateTools: normalizeUpdateTools(input.updateTools)
  };
}

function parseConfigFile(rawContent) {
  const parsed = JSON.parse(rawContent);
  if (isLegacyConfig(parsed)) {
    return {
      config: migrateLegacyConfig(parsed),
      migrated: true
    };
  }

  return {
    config: normalizeConfigShape(parsed),
    migrated: false
  };
}

function ensureConfigDirectories(config) {
  [config.sourceDirs.skills, config.sourceDirs.commands].forEach(dirPath => {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
  });
}

function saveConfig(config) {
  const normalized = normalizeConfigShape(config);
  const content = JSON.stringify(normalized, null, 2);
  fs.writeFileSync(CONFIG_FILE, content, 'utf8');
  return normalized;
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    const created = createDefaultConfig();
    ensureConfigDirectories(created);
    return saveConfig(created);
  }

  const rawContent = fs.readFileSync(CONFIG_FILE, 'utf8');
  const { config, migrated } = parseConfigFile(rawContent);
  ensureConfigDirectories(config);

  if (migrated || rawContent.trim() !== JSON.stringify(config, null, 2)) {
    return saveConfig(config);
  }

  return config;
}

module.exports = {
  CONFIG_FILE,
  PROJECT_ROOT,
  createDefaultConfig,
  loadConfig,
  migrateLegacyConfig,
  normalizeCommandSubfolderSupport,
  normalizeConfigShape,
  normalizeResourceMap,
  parseConfigFile,
  resolveSourceDir,
  saveConfig
};
