const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

function expandHome(p) {
  if (p.startsWith('~')) {
    return path.join(os.homedir(), p.slice(1));
  }
  return p;
}

function gitExec(cwd, args) {
  try {
    return execSync(`git ${args}`, { cwd, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
  } catch {
    return null;
  }
}

function runGitCommand(args, cwd, timeout = 60000) {
  return new Promise((resolve) => {
    const proc = spawn('git', args, { cwd, stdio: 'pipe', shell: true });
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data; });
    proc.stderr.on('data', (data) => { stderr += data; });

    const timer = setTimeout(() => {
      proc.kill();
      resolve({ success: false, stdout, stderr, message: '超时' });
    }, timeout);

    proc.on('close', (code) => {
      clearTimeout(timer);
      resolve({ success: code === 0, stdout: stdout.trim(), stderr: stderr.trim(), message: code === 0 ? '' : stderr.trim() });
    });

    proc.on('error', (err) => {
      clearTimeout(timer);
      resolve({ success: false, stdout, stderr, message: err.message });
    });
  });
}

function scanGitRepos(projectDirs, exclude = []) {
  const repos = [];
  const seen = new Set();

  for (const dir of projectDirs) {
    const absDir = expandHome(dir);
    if (!fs.existsSync(absDir)) continue;

    const entries = fs.readdirSync(absDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (exclude.includes(entry.name)) continue;

      const repoPath = path.join(absDir, entry.name);
      const gitDir = path.join(repoPath, '.git');
      if (!fs.existsSync(gitDir)) continue;

      const realPath = fs.realpathSync(repoPath);
      if (seen.has(realPath)) continue;
      seen.add(realPath);

      repos.push({ name: entry.name, path: repoPath });
    }
  }

  return repos.sort((a, b) => a.name.localeCompare(b.name));
}

function getRepoStatus(repoPath) {
  const branch = gitExec(repoPath, 'rev-parse --abbrev-ref HEAD') || 'unknown';
  const porcelain = gitExec(repoPath, 'status --porcelain');
  const isDirty = porcelain !== null && porcelain !== '';
  const remote = gitExec(repoPath, 'remote');
  const hasRemote = remote !== null && remote !== '';

  let ahead = 0;
  let behind = 0;

  if (hasRemote) {
    const counts = gitExec(repoPath, `rev-list --left-right --count ${branch}...@{u}`);
    if (counts) {
      const parts = counts.split(/\s+/);
      ahead = parseInt(parts[0], 10) || 0;
      behind = parseInt(parts[1], 10) || 0;
    }
  }

  return { branch, isDirty, hasRemote, ahead, behind };
}

async function gitPull(repoPath, timeout = 60000) {
  const status = getRepoStatus(repoPath);

  if (!status.hasRemote) {
    return { success: true, skipped: true, message: '无远程仓库' };
  }

  if (status.isDirty) {
    return { success: true, skipped: true, message: '工作区有未提交更改' };
  }

  if (status.behind === 0) {
    return { success: true, skipped: true, message: '已是最新' };
  }

  const result = await runGitCommand(['pull', '--ff-only'], repoPath, timeout);

  if (result.success) {
    return { success: true, skipped: false, message: result.stdout || '拉取成功' };
  }
  return { success: false, skipped: false, message: result.message || '拉取失败' };
}

async function gitPush(repoPath, timeout = 60000) {
  const status = getRepoStatus(repoPath);

  if (!status.hasRemote) {
    return { success: true, skipped: true, message: '无远程仓库' };
  }

  if (status.ahead === 0) {
    return { success: true, skipped: true, message: '无需推送' };
  }

  const result = await runGitCommand(['push'], repoPath, timeout);

  if (result.success) {
    return { success: true, skipped: false, message: '推送成功' };
  }
  return { success: false, skipped: false, message: result.message || '推送失败' };
}

async function pullAll(repos, onProgress) {
  const results = [];

  for (let i = 0; i < repos.length; i++) {
    const repo = repos[i];
    onProgress?.(repo.name, i + 1, repos.length);
    const result = await gitPull(repo.path);
    results.push({ name: repo.name, path: repo.path, ...result });
  }

  return results;
}

async function pushAll(repos, onProgress) {
  const results = [];

  for (let i = 0; i < repos.length; i++) {
    const repo = repos[i];
    onProgress?.(repo.name, i + 1, repos.length);
    const result = await gitPush(repo.path);
    results.push({ name: repo.name, path: repo.path, ...result });
  }

  return results;
}

module.exports = {
  expandHome,
  gitExec,
  runGitCommand,
  scanGitRepos,
  getRepoStatus,
  gitPull,
  gitPush,
  pullAll,
  pushAll
};
