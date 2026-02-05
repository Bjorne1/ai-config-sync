const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

function ensureTargetDir(targetDir) {
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }
}

function isValidSymlink(targetPath, expectedSource) {
  try {
    if (!fs.existsSync(targetPath)) {
      return false;
    }

    const stats = fs.lstatSync(targetPath);
    if (!stats.isSymbolicLink()) {
      return false;
    }

    const linkTarget = fs.readlinkSync(targetPath);
    const resolvedTarget = path.resolve(path.dirname(targetPath), linkTarget);
    const resolvedExpected = path.resolve(expectedSource);

    return resolvedTarget === resolvedExpected;
  } catch (error) {
    return false;
  }
}

function createSymlink(sourcePath, targetPath, isDirectory) {
  try {
    // 检查源是否存在
    if (!fs.existsSync(sourcePath)) {
      return {
        success: false,
        message: '源文件不存在'
      };
    }

    // 如果目标已存在
    if (fs.existsSync(targetPath)) {
      // 检查是否是有效的软链接
      if (isValidSymlink(targetPath, sourcePath)) {
        return {
          success: true,
          skipped: true,
          message: '已存在有效链接'
        };
      }

      // 存在冲突，需要用户确认
      return {
        success: false,
        conflict: true,
        message: '目标位置已存在文件或目录'
      };
    }

    // 创建软链接
    const type = isDirectory ? 'dir' : 'file';
    fs.symlinkSync(sourcePath, targetPath, type);

    return {
      success: true,
      message: '创建成功'
    };
  } catch (error) {
    // 权限错误 (Windows: EPERM, Linux: EACCES)
    if (error.code === 'EPERM' || error.code === 'EACCES') {
      return {
        success: false,
        permission: true,
        message: '权限不足'
      };
    }

    return {
      success: false,
      message: error.message
    };
  }
}

function removeSymlink(targetPath) {
  try {
    if (!fs.existsSync(targetPath)) {
      return {
        success: true,
        skipped: true,
        message: '链接不存在'
      };
    }

    const stats = fs.lstatSync(targetPath);
    if (!stats.isSymbolicLink()) {
      return {
        success: false,
        message: '目标不是软链接，拒绝删除'
      };
    }

    fs.unlinkSync(targetPath);

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

function checkSymlinkPermission() {
  const testDir = path.join(process.cwd(), '.test-symlink');
  const testSource = path.join(testDir, 'source');
  const testTarget = path.join(testDir, 'target');

  try {
    // 创建测试目录
    fs.mkdirSync(testDir, { recursive: true });
    fs.writeFileSync(testSource, 'test');

    // 尝试创建软链接
    fs.symlinkSync(testSource, testTarget, 'file');

    // 清理
    fs.unlinkSync(testTarget);
    fs.unlinkSync(testSource);
    fs.rmdirSync(testDir);

    return { hasPermission: true };
  } catch (error) {
    // 清理
    try {
      if (fs.existsSync(testTarget)) fs.unlinkSync(testTarget);
      if (fs.existsSync(testSource)) fs.unlinkSync(testSource);
      if (fs.existsSync(testDir)) fs.rmdirSync(testDir);
    } catch (e) {}

    if (error.code === 'EPERM' || error.code === 'EACCES') {
      return {
        hasPermission: false,
        error: error.message
      };
    }

    return { hasPermission: false, error: error.message };
  }
}

module.exports = {
  checkSymlinkPermission,
  isValidSymlink,
  createSymlink,
  removeSymlink,
  ensureTargetDir
};
