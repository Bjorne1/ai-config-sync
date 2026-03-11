const { execFileSync } = require('child_process');
const os = require('os');
const path = require('path');
const { buildRootMap, TOOL_IDS, WINDOWS_HOME_TOKEN, WSL_HOME_TOKEN } = require('./tool-definitions');

function assertWindowsHost(platform = process.platform) {
  if (platform !== 'win32') {
    throw new Error('This application only supports running on Windows.');
  }
}

function resolveWindowsHome(env = process.env, homeDir = os.homedir()) {
  return env.USERPROFILE || homeDir;
}

function expandWindowsPath(inputPath, env = process.env, homeDir = os.homedir()) {
  const profile = resolveWindowsHome(env, homeDir);
  return inputPath.replaceAll(WINDOWS_HOME_TOKEN, profile);
}

function expandWslPath(inputPath, homeDir) {
  if (!homeDir) {
    throw new Error('WSL home directory is required to resolve WSL targets.');
  }

  return inputPath.replaceAll(WSL_HOME_TOKEN, homeDir);
}

function listWslDistros(executor = execFileSync) {
  const output = executor('wsl.exe', ['-l', '-q'], { encoding: 'utf8' });
  return output
    .split(/\r?\n/)
    .map(line => line.replace(/\0/g, '').trim())
    .filter(Boolean);
}

function getDefaultWslDistro(executor = execFileSync) {
  const output = executor('wsl.exe', ['-l', '-v'], { encoding: 'utf8' });
  const lines = output.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const defaultLine = lines.find(line => line.startsWith('*'));
  return defaultLine ? defaultLine.replace(/^\*\s*/, '').split(/\s{2,}|\t+/)[0] : null;
}

function getWslHomeDir(distro, executor = execFileSync) {
  if (!distro) {
    throw new Error('A WSL distro must be selected before resolving its home directory.');
  }

  const output = executor(
    'wsl.exe',
    ['-d', distro, 'sh', '-lc', 'printf %s "$HOME"'],
    { encoding: 'utf8' }
  );

  return output.trim();
}

function linuxPathToUnc(distro, linuxPath) {
  const sanitizedPath = linuxPath.replace(/^\/+/, '').replaceAll('/', '\\');
  return `\\\\wsl.localhost\\${distro}\\${sanitizedPath}`;
}

function resolveEnvironmentTargets(config, options = {}) {
  const env = options.env || process.env;
  const homeDir = options.homeDir || os.homedir();
  const wslHome = options.wslHome || null;
  const distro = options.distro || config.environments.wsl.selectedDistro;
  const windowsTargets = config.environments.windows.targets;
  const wslTargets = config.environments.wsl.targets;

  return {
    windows: {
      enabled: true,
      targets: {
        skills: Object.fromEntries(
          TOOL_IDS.map(toolId => [toolId, expandWindowsPath(windowsTargets.skills[toolId], env, homeDir)])
        ),
        commands: Object.fromEntries(
          TOOL_IDS.map(toolId => [toolId, expandWindowsPath(windowsTargets.commands[toolId], env, homeDir)])
        )
      },
      roots: buildRootMap(resolveWindowsHome(env, homeDir), path.win32)
    },
    wsl: {
      enabled: Boolean(config.environments.wsl.enabled && distro && wslHome),
      selectedDistro: distro,
      targets: {
        skills: Object.fromEntries(
          TOOL_IDS.map(toolId => {
            const resolved = expandWslPath(wslTargets.skills[toolId], wslHome || WSL_HOME_TOKEN);
            return [toolId, distro && wslHome ? linuxPathToUnc(distro, resolved) : null];
          })
        ),
        commands: Object.fromEntries(
          TOOL_IDS.map(toolId => {
            const resolved = expandWslPath(wslTargets.commands[toolId], wslHome || WSL_HOME_TOKEN);
            return [toolId, distro && wslHome ? linuxPathToUnc(distro, resolved) : null];
          })
        )
      },
      roots: distro && wslHome
        ? buildRootMap(linuxPathToUnc(distro, wslHome), path.win32)
        : Object.fromEntries(TOOL_IDS.map(toolId => [toolId, null]))
    }
  };
}

module.exports = {
  assertWindowsHost,
  expandWindowsPath,
  expandWslPath,
  getDefaultWslDistro,
  getWslHomeDir,
  linuxPathToUnc,
  listWslDistros,
  resolveEnvironmentTargets,
  resolveWindowsHome
};
