if (process.platform !== 'win32') {
  console.error('AI Config Sync 现在仅支持在 Windows 上运行桌面 GUI。');
  process.exit(1);
}

console.log('请使用 `npm start` 或双击 `start.bat` 启动桌面应用。');
