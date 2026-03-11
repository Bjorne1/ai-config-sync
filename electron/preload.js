const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('deskSync', {
  cleanupInvalid() {
    return ipcRenderer.invoke('app:cleanup-invalid');
  },
  getConfig() {
    return ipcRenderer.invoke('app:get-config');
  },
  getStatus() {
    return ipcRenderer.invoke('app:get-status');
  },
  getWslDistros() {
    return ipcRenderer.invoke('app:get-wsl-distros');
  },
  replaceResourceMap(kind, assignments) {
    return ipcRenderer.invoke('app:replace-resource-map', kind, assignments);
  },
  saveConfig(patch) {
    return ipcRenderer.invoke('app:save-config', patch);
  },
  scanCommands() {
    return ipcRenderer.invoke('app:scan-commands');
  },
  scanSkills() {
    return ipcRenderer.invoke('app:scan-skills');
  },
  syncAll() {
    return ipcRenderer.invoke('app:sync-all');
  },
  syncResources(kind, names) {
    return ipcRenderer.invoke('app:sync-resources', kind, names);
  },
  updateTools() {
    return ipcRenderer.invoke('app:update-tools');
  }
});
