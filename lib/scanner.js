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

function getSkillType(skillName) {
  return skillName.endsWith('/') ? 'dir' : 'file';
}

module.exports = {
  scanSkills,
  getSkillType
};
