import { app, BrowserWindow, ipcMain, session, shell } from 'electron';
import { join } from 'node:path';
import { exportReportPdf } from './pdf';
import type { ClinicInfo, ReportFull } from '../shared/types';

const isDev = !app.isPackaged;

// Locked-down CSP for the packaged app. `connect-src` allows http/https so the
// renderer can reach the API on the clinic LAN by IP. In dev we leave the CSP
// off so Vite's dev server and React Fast Refresh keep working.
const PROD_CSP =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "img-src 'self' data: blob:; font-src 'self' data:; " +
  "connect-src 'self' http: https:; frame-src 'self' data:";

function applyContentSecurityPolicy() {
  if (isDev) return;
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: { ...details.responseHeaders, 'Content-Security-Policy': [PROD_CSP] },
    });
  });
}

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    title: 'Clinic Report Manager',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.once('ready-to-show', () => win.show());

  // Open external links (e.g. mailto:) in the OS, never inside the app.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:|^mailto:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });

  const devUrl = process.env['ELECTRON_RENDERER_URL'];
  if (isDev && devUrl) {
    win.loadURL(devUrl);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'));
  }

  return win;
}

function registerIpc(): void {
  ipcMain.handle('app:version', () => app.getVersion());

  ipcMain.handle(
    'report:export-pdf',
    async (event, args: { report: ReportFull; clinic: ClinicInfo; defaultFileName: string }) => {
      const parent = BrowserWindow.fromWebContents(event.sender) ?? undefined;
      return exportReportPdf(parent, args);
    },
  );

  ipcMain.handle('shell:open-path', async (_e, filePath: string) => {
    await shell.openPath(filePath);
  });

  ipcMain.handle('shell:show-item', (_e, filePath: string) => {
    shell.showItemInFolder(filePath);
  });
}

app.whenReady().then(() => {
  app.setAppUserModelId('com.medclinic.reportsoftware');
  applyContentSecurityPolicy();
  registerIpc();
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
