const fs = require('fs');
const path = require('path');
const fileSync = require('../file-sync');
const linker = require('../linker');

function ensureParentDir(targetPath) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}

function validateTarget(mode, sourcePath, targetPath) {
  return mode === 'copy'
    ? fileSync.isSyncedCopy(sourcePath, targetPath)
    : linker.isValidSymlink(targetPath, sourcePath);
}

function describeTargetState(mode, sourcePath, targetPath) {
  if (!fs.existsSync(sourcePath)) {
    return { state: 'source_missing', message: '源文件不存在' };
  }

  if (validateTarget(mode, sourcePath, targetPath)) {
    return { state: 'healthy', message: '已同步' };
  }

  if (!fileSync.hasPath(targetPath)) {
    return { state: 'missing', message: '目标缺失' };
  }

  return {
    state: 'conflict',
    message: mode === 'copy' ? '目标内容与源不一致' : '目标存在冲突或链接无效'
  };
}

function syncSymlink(sourcePath, targetPath, isDirectory) {
  ensureParentDir(targetPath);
  const created = linker.createSymlink(sourcePath, targetPath, isDirectory);
  if (created.success || !created.conflict) {
    return created;
  }

  const removed = fileSync.removePath(targetPath);
  if (!removed.success) {
    return { success: false, message: `清理失败 - ${removed.message}` };
  }

  return linker.createSymlink(sourcePath, targetPath, isDirectory);
}

function syncEntry(options) {
  const { isDirectory, mode, sourcePath, targetPath } = options;
  if (mode === 'copy') {
    ensureParentDir(targetPath);
    return fileSync.syncCopy(sourcePath, targetPath);
  }

  return syncSymlink(sourcePath, targetPath, isDirectory);
}

function removeTarget(targetPath) {
  return fileSync.removePath(targetPath);
}

module.exports = {
  describeTargetState,
  removeTarget,
  syncEntry,
  validateTarget
};
