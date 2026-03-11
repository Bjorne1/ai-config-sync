const path = require('path');
const scanner = require('../scanner');

function getSourceDir(config, kind) {
  return config.sourceDirs[kind];
}

function scanResources(config, kind) {
  const sourceDir = getSourceDir(config, kind);
  return kind === 'skills'
    ? scanner.scanSkills(sourceDir)
    : scanner.scanCommands(sourceDir);
}

function indexResources(resources) {
  return resources.reduce((index, resource) => {
    return {
      ...index,
      [resource.name]: resource
    };
  }, {});
}

function getResourceCatalog(config) {
  const skills = scanResources(config, 'skills');
  const commands = scanResources(config, 'commands');
  return {
    skills,
    commands,
    skillIndex: indexResources(skills),
    commandIndex: indexResources(commands)
  };
}

function getConfiguredResources(config, kind) {
  return config.resources[kind] || {};
}

function listManagedNames(config, kind, index) {
  const configuredNames = Object.keys(getConfiguredResources(config, kind));
  const scannedNames = Object.keys(index);
  return Array.from(new Set([...scannedNames, ...configuredNames])).sort();
}

function buildVirtualResource(config, kind, name) {
  const sourceDir = getSourceDir(config, kind);
  return {
    name,
    path: path.join(sourceDir, name),
    isDirectory: false,
    children: []
  };
}

function getResourceEntry(config, kind, name, index) {
  return index[name] || buildVirtualResource(config, kind, name);
}

function expandResourceItems(config, kind, resource, toolId) {
  if (kind === 'skills') {
    return [{
      name: resource.name,
      sourcePath: resource.path,
      isDirectory: resource.isDirectory
    }];
  }

  const supportsSubfolders = config.commandSubfolderSupport.tools[toolId]
    ?? config.commandSubfolderSupport.default;
  return scanner.expandCommandsForTool([resource], toolId, supportsSubfolders).map(item => ({
    ...item,
    isDirectory: Boolean(item.isDirectory)
  }));
}

module.exports = {
  expandResourceItems,
  getConfiguredResources,
  getResourceCatalog,
  getResourceEntry,
  getSourceDir,
  listManagedNames,
  scanResources
};
