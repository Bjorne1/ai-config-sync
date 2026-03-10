const fs = require('fs');
const path = require('path');

function getPathStats(targetPath) {
  try {
    return fs.lstatSync(targetPath);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return null;
    }
    throw error;
  }
}

function hasPath(targetPath) {
  return getPathStats(targetPath) !== null;
}

function isFileCopySynced(sourcePath, targetPath) {
  const targetStats = getPathStats(targetPath);
  if (!targetStats || targetStats.isSymbolicLink() || !targetStats.isFile()) {
    return false;
  }

  const sourceStats = fs.statSync(sourcePath);
  if (sourceStats.size !== targetStats.size) {
    return false;
  }

  const sourceContent = fs.readFileSync(sourcePath);
  const targetContent = fs.readFileSync(targetPath);
  return sourceContent.equals(targetContent);
}

function listEntries(dirPath) {
  return fs.readdirSync(dirPath).sort();
}

function isDirectoryCopySynced(sourcePath, targetPath) {
  const targetStats = getPathStats(targetPath);
  if (!targetStats || targetStats.isSymbolicLink() || !targetStats.isDirectory()) {
    return false;
  }

  const sourceEntries = listEntries(sourcePath);
  const targetEntries = listEntries(targetPath);

  if (sourceEntries.length !== targetEntries.length) {
    return false;
  }

  for (let index = 0; index < sourceEntries.length; index++) {
    if (sourceEntries[index] !== targetEntries[index]) {
      return false;
    }
  }

  return sourceEntries.every(entry => {
    const sourceEntry = path.join(sourcePath, entry);
    const targetEntry = path.join(targetPath, entry);
    return isSyncedCopy(sourceEntry, targetEntry);
  });
}

function isSyncedCopy(sourcePath, targetPath) {
  if (!fs.existsSync(sourcePath)) {
    return false;
  }

  const sourceStats = fs.statSync(sourcePath);
  if (sourceStats.isDirectory()) {
    return isDirectoryCopySynced(sourcePath, targetPath);
  }

  return isFileCopySynced(sourcePath, targetPath);
}

function ensureParentDir(targetPath) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}

function createCopy(sourcePath, targetPath) {
  try {
    if (!fs.existsSync(sourcePath)) {
      return {
        success: false,
        message: '源文件不存在'
      };
    }

    if (hasPath(targetPath)) {
      if (isSyncedCopy(sourcePath, targetPath)) {
        return {
          success: true,
          skipped: true,
          message: '已存在最新副本'
        };
      }

      return {
        success: false,
        conflict: true,
        message: '目标位置已存在文件或目录'
      };
    }

    ensureParentDir(targetPath);
    fs.cpSync(sourcePath, targetPath, { recursive: true });

    return {
      success: true,
      message: '复制成功'
    };
  } catch (error) {
    return {
      success: false,
      message: error.message
    };
  }
}

function removePath(targetPath) {
  try {
    const stats = getPathStats(targetPath);
    if (!stats) {
      return {
        success: true,
        skipped: true,
        message: '目标不存在'
      };
    }

    if (stats.isDirectory() && !stats.isSymbolicLink()) {
      fs.rmSync(targetPath, { recursive: true });
    } else {
      fs.unlinkSync(targetPath);
    }

    return {
      success: true,
      message: '删除成功'
    };
  } catch (error) {
    return {
      success: false,
      message: error.message
    };
  }
}

function syncCopy(sourcePath, targetPath) {
  const copyResult = createCopy(sourcePath, targetPath);
  if (copyResult.success || !copyResult.conflict) {
    return copyResult;
  }

  const removeResult = removePath(targetPath);
  if (!removeResult.success) {
    return {
      success: false,
      message: `清理失败 - ${removeResult.message}`
    };
  }

  const retryResult = createCopy(sourcePath, targetPath);
  if (!retryResult.success) {
    return retryResult;
  }

  return {
    success: true,
    message: '同步成功'
  };
}

module.exports = {
  createCopy,
  hasPath,
  isSyncedCopy,
  removePath,
  syncCopy
};
