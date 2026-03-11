const path = require('path');

const TOOL_LAYOUTS = Object.freeze({
  claude: Object.freeze({
    label: 'Claude',
    root: ['.claude'],
    skills: ['.claude', 'skills'],
    commands: ['.claude', 'commands']
  }),
  codex: Object.freeze({
    label: 'Codex',
    root: ['.codex'],
    skills: ['.codex', 'skills'],
    commands: ['.codex', 'prompts']
  }),
  gemini: Object.freeze({
    label: 'Gemini',
    root: ['.gemini'],
    skills: ['.gemini', 'skills'],
    commands: ['.gemini', 'commands']
  }),
  antigravity: Object.freeze({
    label: 'Antigravity',
    root: ['.gemini', 'antigravity'],
    skills: ['.gemini', 'antigravity', 'skills'],
    commands: ['.gemini', 'antigravity', 'global_workflows']
  })
});

const TOOL_IDS = Object.freeze(Object.keys(TOOL_LAYOUTS));
const TOOL_KIND_IDS = Object.freeze(['skills', 'commands']);

const DEFAULT_COMMAND_SUBFOLDER_SUPPORT = Object.freeze({
  default: false,
  tools: Object.freeze({ claude: true })
});

const DEFAULT_UPDATE_TOOLS = Object.freeze({
  'Claude Code': Object.freeze({ type: 'custom', command: 'claude update' }),
  Codex: Object.freeze({ type: 'npm', package: '@openai/codex' }),
  OpenSpec: Object.freeze({ type: 'npm', package: '@fission-ai/openspec' }),
  Auggie: Object.freeze({ type: 'npm', package: '@augmentcode/auggie' }),
  'ace-tool': Object.freeze({ type: 'npm', package: 'ace-tool' })
});

const DEFAULT_SYNC_MODE = 'symlink';
const CONFIG_VERSION = 2;
const WINDOWS_HOME_TOKEN = '%USERPROFILE%';
const WSL_HOME_TOKEN = '$HOME';

function getToolLayout(toolId) {
  return TOOL_LAYOUTS[toolId];
}

function buildTargetMap(homeToken, kind, pathModule) {
  return TOOL_IDS.reduce((targets, toolId) => {
    const layout = getToolLayout(toolId);
    const segments = layout[kind];
    return {
      ...targets,
      [toolId]: pathModule.join(homeToken, ...segments)
    };
  }, {});
}

function buildRootMap(homeToken, pathModule) {
  return TOOL_IDS.reduce((targets, toolId) => {
    const layout = getToolLayout(toolId);
    return {
      ...targets,
      [toolId]: pathModule.join(homeToken, ...layout.root)
    };
  }, {});
}

module.exports = {
  buildRootMap,
  buildTargetMap,
  CONFIG_VERSION,
  DEFAULT_COMMAND_SUBFOLDER_SUPPORT,
  DEFAULT_SYNC_MODE,
  DEFAULT_UPDATE_TOOLS,
  TOOL_IDS,
  TOOL_KIND_IDS,
  TOOL_LAYOUTS,
  WINDOWS_HOME_TOKEN,
  WSL_HOME_TOKEN
};
