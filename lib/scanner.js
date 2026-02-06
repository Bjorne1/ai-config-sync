const fs = require('fs');
const path = require('path');

function scanSkills(sourceDir) {
  if (!fs.existsSync(sourceDir)) {
    return [];
  }

  const items = fs.readdirSync(sourceDir);
  const skills = [];

  items.forEach(item => {
    // 跳过隐藏文件和 .gitkeep
    if (item.startsWith('.') || item === '.gitkeep') {
      return;
    }

    const fullPath = path.join(sourceDir, item);
    const stat = fs.statSync(fullPath);

    // 添加文件或目录
    if (stat.isFile() || stat.isDirectory()) {
      skills.push({
        name: item,
        path: fullPath,
        isDirectory: stat.isDirectory()
      });
    }
  });

  return skills;
}

function scanCommands(sourceDir) {
  if (!fs.existsSync(sourceDir)) {
    return [];
  }

  const items = fs.readdirSync(sourceDir);
  const commands = [];

  items.forEach(item => {
    if (item.startsWith('.')) return;

    const fullPath = path.join(sourceDir, item);
    const stat = fs.statSync(fullPath);

    if (stat.isFile()) {
      if (!item.endsWith('.md')) return;
      commands.push({
        name: item,
        path: fullPath,
        isDirectory: false,
        parent: null
      });
    } else if (stat.isDirectory()) {
      const children = [];
      const subItems = fs.readdirSync(fullPath);

      subItems.forEach(subItem => {
        if (subItem.startsWith('.')) return;

        const subPath = path.join(fullPath, subItem);
        const subStat = fs.statSync(subPath);

        if (subStat.isDirectory()) {
          console.log(`⚠ 跳过二级嵌套: ${item}/${subItem}`);
          return;
        }

        if (subStat.isFile() && subItem.endsWith('.md')) {
          children.push(subItem);
        }
      });

      commands.push({
        name: item,
        path: fullPath,
        isDirectory: true,
        children
      });
    }
  });

  return commands;
}

function getSkillType(skillName) {
  return skillName.endsWith('/') ? 'dir' : 'file';
}

function flattenCommandName(folderName, fileName) {
  return `${folderName}-${fileName}`;
}

function expandCommandsForTool(commands, tool, subfolderSupport) {
  const expanded = [];

  commands.forEach(cmd => {
    if (!cmd.isDirectory) {
      expanded.push({
        name: cmd.name,
        sourcePath: cmd.path,
        isFlattened: false
      });
    } else if (subfolderSupport) {
      expanded.push({
        name: cmd.name,
        sourcePath: cmd.path,
        isDirectory: true,
        isFlattened: false
      });
    } else {
      cmd.children.forEach(child => {
        expanded.push({
          name: flattenCommandName(cmd.name, child),
          sourcePath: require('path').join(cmd.path, child),
          isFlattened: true,
          originalFolder: cmd.name
        });
      });
    }
  });

  return expanded;
}

module.exports = {
  scanSkills,
  scanCommands,
  getSkillType,
  flattenCommandName,
  expandCommandsForTool
};
