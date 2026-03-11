const fs = require('fs');
const {
  getDefaultWslDistro,
  getWslHomeDir,
  listWslDistros,
  resolveEnvironmentTargets
} = require('./environment-service');
const { WINDOWS_HOME_TOKEN, WSL_HOME_TOKEN } = require('./tool-definitions');

function isTokenizedTarget(targetPath) {
  return targetPath.includes(WINDOWS_HOME_TOKEN) || targetPath.includes(WSL_HOME_TOKEN);
}

function isToolAvailable(rootPath, rawTargetPath) {
  if (!rootPath) {
    return false;
  }

  if (!isTokenizedTarget(rawTargetPath)) {
    return true;
  }

  return fs.existsSync(rootPath);
}

function buildWslRuntime(config, deps = {}) {
  const api = {
    getDefaultWslDistro,
    getWslHomeDir,
    listWslDistros,
    ...deps
  };
  const wslConfig = config.environments.wsl;

  if (!wslConfig.enabled && !wslConfig.selectedDistro) {
    return {
      available: false,
      distros: [],
      selectedDistro: null,
      homeDir: null,
      error: null
    };
  }

  try {
    const distros = api.listWslDistros();
    const defaultDistro = api.getDefaultWslDistro();
    const selectedDistro = wslConfig.selectedDistro || defaultDistro;
    const homeDir = selectedDistro ? api.getWslHomeDir(selectedDistro) : null;
    return {
      available: Boolean(selectedDistro && homeDir),
      distros,
      selectedDistro,
      homeDir,
      error: null
    };
  } catch (error) {
    return {
      available: false,
      distros: [],
      selectedDistro: wslConfig.selectedDistro,
      homeDir: null,
      error: error.message
    };
  }
}

function buildEnvironmentList(config, deps = {}) {
  const api = {
    resolveEnvironmentTargets,
    ...deps
  };
  const wslRuntime = buildWslRuntime(config, deps);
  const resolved = api.resolveEnvironmentTargets(config, {
    distro: wslRuntime.selectedDistro,
    wslHome: wslRuntime.homeDir
  });

  return {
    windows: {
      id: 'windows',
      enabled: true,
      label: 'Windows',
      rawTargets: config.environments.windows.targets,
      roots: resolved.windows.roots,
      targets: resolved.windows.targets,
      error: null
    },
    wsl: {
      id: 'wsl',
      enabled: Boolean(config.environments.wsl.enabled),
      label: wslRuntime.selectedDistro ? `WSL · ${wslRuntime.selectedDistro}` : 'WSL',
      rawTargets: config.environments.wsl.targets,
      roots: resolved.wsl.roots,
      targets: resolved.wsl.targets,
      error: config.environments.wsl.enabled ? wslRuntime.error : null,
      meta: wslRuntime
    }
  };
}

function buildAvailability(environment, kind, toolId) {
  if (environment.id === 'wsl' && environment.enabled && environment.error) {
    return { available: false, state: 'environment_error', message: environment.error };
  }

  if (environment.id === 'wsl' && environment.enabled && !environment.meta.available) {
    return { available: false, state: 'environment_error', message: '未能解析 WSL 发行版或主目录' };
  }

  const rawTarget = environment.rawTargets[kind][toolId];
  const rootPath = environment.roots[toolId];
  if (!isToolAvailable(rootPath, rawTarget)) {
    return { available: false, state: 'tool_unavailable', message: '工具目录不存在' };
  }

  return { available: true };
}

module.exports = {
  buildAvailability,
  buildEnvironmentList,
  buildWslRuntime
};
