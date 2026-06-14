const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('zenithDesktop', {
  platform: process.platform,
  isDesktopShell: true,
});
