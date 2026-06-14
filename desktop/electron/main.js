const { app, BrowserWindow, shell, Menu } = require('electron');
const path = require('path');

let autoUpdater;
if (app.isPackaged) {
  try {
    ({ autoUpdater } = require('electron-updater'));
    autoUpdater.autoDownload = false;
  } catch {
    autoUpdater = null;
  }
}

const DEFAULT_URL = process.env.ZENITH_APP_URL || 'https://rajverse.me';

/** @type {BrowserWindow | null} */
let mainWindow = null;

function getAppUrl() {
  return process.env.ZENITH_APP_URL || DEFAULT_URL;
}

function buildMenu() {
  const template = [
    ...(process.platform === 'darwin'
      ? [
          {
            label: app.name,
            submenu: [
              { role: 'about' },
              { type: 'separator' },
              { role: 'services' },
              { type: 'separator' },
              { role: 'hide' },
              { role: 'hideOthers' },
              { role: 'unhide' },
              { type: 'separator' },
              { role: 'quit' },
            ],
          },
        ]
      : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'Open in Browser',
          click: () => {
            shell.openExternal(getAppUrl());
          },
        },
        { type: 'separator' },
        process.platform === 'darwin' ? { role: 'close' } : { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Window',
      submenu: [{ role: 'minimize' }, { role: 'zoom' }],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createWindow() {
  const iconPath = path.join(__dirname, '..', 'build', 'icon.png');

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: '#050505',
    show: false,
    icon: iconPath,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
    title: 'Zenith',
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  mainWindow.loadURL(getAppUrl());

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  buildMenu();
  createWindow();

  if (autoUpdater && process.env.ZENITH_DISABLE_UPDATES !== '1') {
    autoUpdater.checkForUpdates().catch(() => {
      // Unsigned beta builds may fail update checks — safe to ignore
    });
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
