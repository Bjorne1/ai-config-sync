const path = require('path');
const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { createAppService } = require('../lib/services/app-service');
const { assertWindowsHost } = require('../lib/services/environment-service');
const { scanResources } = require('../lib/services/resource-service');

const appService = createAppService();

function getRendererEntry() {
  return path.join(__dirname, '..', 'dist', 'renderer', 'index.html');
}

async function loadRenderer(window) {
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    await window.loadURL(devServerUrl);
    return;
  }

  await window.loadFile(getRendererEntry());
}

function createMainWindow() {
  return new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: '#16110f',
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });
}

function registerIpcHandlers() {
  ipcMain.handle('app:get-config', () => appService.getConfig());
  ipcMain.handle('app:save-config', (_, patch) => appService.saveConfig(patch));
  ipcMain.handle('app:get-status', () => appService.getStatus());
  ipcMain.handle('app:get-wsl-distros', () => appService.getWslDistros());
  ipcMain.handle('app:scan-skills', () => {
    return scanResources(appService.getConfig(), 'skills');
  });
  ipcMain.handle('app:scan-commands', () => {
    return scanResources(appService.getConfig(), 'commands');
  });
  ipcMain.handle('app:replace-resource-map', (_, kind, assignments) => {
    return appService.replaceResourceMap(kind, assignments);
  });
  ipcMain.handle('app:sync-all', () => appService.syncAll());
  ipcMain.handle('app:sync-resources', (_, kind, names) => appService.syncResources(kind, names));
  ipcMain.handle('app:cleanup-invalid', () => appService.cleanupInvalid());
  ipcMain.handle('app:update-tools', () => appService.updateTools());
}

async function bootstrap() {
  assertWindowsHost();
  registerIpcHandlers();
  const window = createMainWindow();
  await loadRenderer(window);
}

app.whenReady()
  .then(bootstrap)
  .catch(error => {
    dialog.showErrorBox('启动失败', error.message);
    app.exit(1);
  });

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
