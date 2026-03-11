const { loadConfig, normalizeConfigShape, saveConfig } = require('./config-service');
const { getDefaultWslDistro, getWslHomeDir, listWslDistros, resolveEnvironmentTargets } = require('./environment-service');
const { scanResources } = require('./resource-service');
const { buildEnvironmentList, buildWslRuntime } = require('./runtime-service');
const { buildResourceStatuses, cleanupInvalidResources, syncConfiguredResources } = require('./resource-operation-service');
const updater = require('../updater');

function replaceResourceMap(config, kind, assignments) {
  const nextConfig = normalizeConfigShape({
    ...config,
    resources: {
      ...config.resources,
      [kind]: assignments
    }
  });
  return saveConfig(nextConfig);
}

function saveSettings(config, patch) {
  const nextConfig = normalizeConfigShape({
    ...config,
    ...patch,
    environments: {
      ...config.environments,
      ...(patch.environments || {})
    },
    sourceDirs: {
      ...config.sourceDirs,
      ...(patch.sourceDirs || {})
    }
  });
  return saveConfig(nextConfig);
}

function createAppService(overrides = {}) {
  const deps = {
    getDefaultWslDistro,
    getWslHomeDir,
    listWslDistros,
    loadConfig,
    resolveEnvironmentTargets,
    saveConfig,
    updateAllTools: updater.updateAllTools,
    ...overrides
  };

  return {
    cleanupInvalid() {
      const config = deps.loadConfig();
      const environmentList = buildEnvironmentList(config, deps);
      return cleanupInvalidResources(config, environmentList, deps.saveConfig);
    },
    getConfig() {
      return deps.loadConfig();
    },
    getStatus() {
      const config = deps.loadConfig();
      const environmentList = buildEnvironmentList(config, deps);
      return {
        config,
        environments: environmentList,
        skills: buildResourceStatuses(config, 'skills', environmentList),
        commands: buildResourceStatuses(config, 'commands', environmentList)
      };
    },
    getWslDistros() {
      const config = deps.loadConfig();
      return buildWslRuntime(config, deps);
    },
    saveConfig(patch) {
      const config = deps.loadConfig();
      return saveSettings(config, patch);
    },
    scanResources(kind) {
      const config = deps.loadConfig();
      return scanResources(config, kind);
    },
    replaceResourceMap(kind, assignments) {
      const config = deps.loadConfig();
      return replaceResourceMap(config, kind, assignments);
    },
    saveSettings(patch) {
      const config = deps.loadConfig();
      return saveSettings(config, patch);
    },
    syncAll() {
      const config = deps.loadConfig();
      const environmentList = buildEnvironmentList(config, deps);
      return {
        skills: syncConfiguredResources(config, 'skills', environmentList),
        commands: syncConfiguredResources(config, 'commands', environmentList)
      };
    },
    syncResources(kind, names) {
      const config = deps.loadConfig();
      const environmentList = buildEnvironmentList(config, deps);
      return syncConfiguredResources(config, kind, environmentList, names);
    },
    updateTools() {
      const config = deps.loadConfig();
      return deps.updateAllTools(config.updateTools);
    }
  };
}

module.exports = {
  createAppService
};
