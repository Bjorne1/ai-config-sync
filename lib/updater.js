const { execSync, spawn } = require('child_process');

function getNpmVersion(packageName) {
  try {
    const output = execSync(`npm list -g ${packageName} --json`, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
    const data = JSON.parse(output);
    const deps = data.dependencies || {};
    return deps[packageName]?.version || null;
  } catch {
    return null;
  }
}

function updateNpmTool(packageName) {
  return new Promise((resolve) => {
    const proc = spawn('npm', ['update', '-g', packageName], { stdio: 'inherit', shell: true });
    proc.on('close', (code) => resolve(code === 0));
    proc.on('error', () => resolve(false));
  });
}

function updateCustomTool(command) {
  return new Promise((resolve) => {
    const [cmd, ...args] = command.split(/\s+/);
    const proc = spawn(cmd, args, { stdio: 'inherit', shell: true });
    proc.on('close', (code) => resolve(code === 0));
    proc.on('error', () => resolve(false));
  });
}

async function updateAllTools(tools, onProgress) {
  const results = [];
  const entries = Object.entries(tools);

  for (let i = 0; i < entries.length; i++) {
    const [name, cfg] = entries[i];
    const result = { name, type: cfg.type, versionBefore: null, versionAfter: null, success: false };

    if (cfg.type === 'npm') {
      result.versionBefore = getNpmVersion(cfg.package);
    }

    onProgress?.(name, i + 1, entries.length, 'updating');

    if (cfg.type === 'npm') {
      result.success = await updateNpmTool(cfg.package);
      result.versionAfter = getNpmVersion(cfg.package);
    } else if (cfg.type === 'custom') {
      result.success = await updateCustomTool(cfg.command);
    }

    results.push(result);
  }

  return results;
}

module.exports = { getNpmVersion, updateNpmTool, updateCustomTool, updateAllTools };
