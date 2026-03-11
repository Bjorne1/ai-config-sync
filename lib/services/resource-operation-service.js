const fs = require('fs');
const path = require('path');
const {
  expandResourceItems,
  getConfiguredResources,
  getResourceCatalog,
  getResourceEntry,
  listManagedNames
} = require('./resource-service');
const { buildAvailability } = require('./runtime-service');
const { describeTargetState, removeTarget, syncEntry } = require('./sync-engine');
const { TOOL_IDS } = require('./tool-definitions');

function aggregateStates(states) {
  const kinds = states.map(state => state.state);
  if (states.length === 0) {
    return { state: 'missing', message: '未发现可同步项' };
  }
  if (kinds.includes('conflict')) {
    return { state: 'conflict', message: '部分目标存在冲突' };
  }
  if (kinds.includes('source_missing')) {
    return { state: 'source_missing', message: '源文件不存在' };
  }
  if (kinds.includes('tool_unavailable')) {
    return { state: 'tool_unavailable', message: '工具目录不存在' };
  }
  if (kinds.includes('environment_error')) {
    return { state: 'environment_error', message: '环境不可用' };
  }
  if (kinds.every(kind => kind === 'healthy')) {
    return { state: 'healthy', message: '已同步' };
  }
  if (kinds.every(kind => kind === 'missing')) {
    return { state: 'missing', message: '目标缺失' };
  }
  return { state: 'partial', message: '部分目标已同步' };
}

function buildTargetPaths(baseTarget, items) {
  if (!baseTarget) {
    return [];
  }

  return items.map(item => path.join(baseTarget, item.name));
}

function buildStatesForTargets(mode, items, targetPaths, availability) {
  if (!availability.available) {
    return targetPaths.length === 0
      ? [{ state: availability.state, message: availability.message, targetPath: null }]
      : targetPaths.map(targetPath => ({
          state: availability.state,
          message: availability.message,
          targetPath
        }));
  }

  return items.map((item, index) => {
    const targetPath = targetPaths[index];
    const state = describeTargetState(mode, item.sourcePath, targetPath);
    return { ...state, targetPath };
  });
}

function iterEnabledEnvironments(environmentList) {
  return Object.values(environmentList).filter(environment => {
    return environment.id === 'windows' || environment.enabled;
  });
}

function buildResourceStatuses(config, kind, environmentList) {
  const catalog = getResourceCatalog(config);
  const index = kind === 'skills' ? catalog.skillIndex : catalog.commandIndex;
  return listManagedNames(config, kind, index).map(name => {
    const resource = getResourceEntry(config, kind, name, index);
    const configuredTools = getConfiguredResources(config, kind)[name] || [];
    const entries = TOOL_IDS.flatMap(toolId => {
      if (!configuredTools.includes(toolId)) {
        return [];
      }

      const items = expandResourceItems(config, kind, resource, toolId);
      return iterEnabledEnvironments(environmentList).map(environment => {
        const availability = buildAvailability(environment, kind, toolId);
        const baseTarget = environment.targets[kind][toolId];
        const targetPaths = buildTargetPaths(baseTarget, items);
        const states = buildStatesForTargets(config.syncMode, items, targetPaths, availability);
        const summary = aggregateStates(states);
        return {
          environmentId: environment.id,
          toolId,
          state: summary.state,
          message: summary.message,
          itemCount: items.length,
          targetPath: baseTarget,
          targets: targetPaths
        };
      });
    });

    return {
      kind,
      name,
      sourcePath: resource.path,
      isDirectory: resource.isDirectory,
      configuredTools,
      entries
    };
  });
}

function syncConfiguredResources(config, kind, environmentList, requestedNames) {
  const catalog = getResourceCatalog(config);
  const index = kind === 'skills' ? catalog.skillIndex : catalog.commandIndex;
  const configured = getConfiguredResources(config, kind);
  const names = requestedNames && requestedNames.length > 0
    ? requestedNames
    : Object.keys(configured);

  return names.flatMap(name => {
    const resource = getResourceEntry(config, kind, name, index);
    const tools = configured[name] || [];
    return tools.flatMap(toolId => {
      const items = expandResourceItems(config, kind, resource, toolId);
      return iterEnabledEnvironments(environmentList).flatMap(environment => {
        const availability = buildAvailability(environment, kind, toolId);
        if (!availability.available) {
          return [{
            kind,
            name,
            toolId,
            environmentId: environment.id,
            success: false,
            skipped: true,
            message: availability.message
          }];
        }

        return items.map(item => {
          const targetPath = path.join(environment.targets[kind][toolId], item.name);
          const result = syncEntry({
            mode: config.syncMode,
            sourcePath: item.sourcePath,
            targetPath,
            isDirectory: item.isDirectory
          });
          return {
            kind,
            name,
            toolId,
            environmentId: environment.id,
            targetPath,
            ...result
          };
        });
      });
    });
  });
}

function cleanupInvalidResources(config, environmentList, saveConfig) {
  const nextConfig = {
    ...config,
    resources: {
      ...config.resources,
      skills: { ...config.resources.skills },
      commands: { ...config.resources.commands }
    }
  };
  const cleaned = [];

  ['skills', 'commands'].forEach(kind => {
    buildResourceStatuses(config, kind, environmentList).forEach(resource => {
      const hasMissingSource = resource.entries.some(entry => entry.state === 'source_missing');
      if (hasMissingSource) {
        delete nextConfig.resources[kind][resource.name];
      }

      resource.entries
        .filter(entry => ['conflict', 'missing', 'source_missing'].includes(entry.state))
        .forEach(entry => {
          getCleanupTargets(resource.kind, resource.name, entry).forEach(targetPath => {
            const result = removeTarget(targetPath);
            cleaned.push({ ...entry, ...result, kind, name: resource.name, targetPath });
          });
        });
    });
  });

  return {
    cleaned,
    config: saveConfig(nextConfig)
  };
}

function getCleanupTargets(kind, resourceName, entry) {
  if (entry.targets.length > 0 && kind !== 'commands') {
    return entry.targets;
  }

  if (!entry.targetPath) {
    return entry.targets;
  }

  if (kind !== 'commands') {
    return [path.join(entry.targetPath, resourceName)];
  }

  const directPath = path.join(entry.targetPath, resourceName);
  const flattened = fs.existsSync(entry.targetPath)
    ? fs.readdirSync(entry.targetPath)
        .filter(name => name.startsWith(`${resourceName}-`))
        .map(name => path.join(entry.targetPath, name))
    : [];

  return Array.from(new Set([...entry.targets, directPath, ...flattened]));
}

module.exports = {
  buildResourceStatuses,
  cleanupInvalidResources,
  syncConfiguredResources
};
