import { contextBridge, ipcRenderer } from 'electron';
import type { ClinicInfo, DesktopApi, ExportPdfResult, ReportFull } from '../shared/types';

const api: DesktopApi = {
  getAppVersion: () => ipcRenderer.invoke('app:version') as Promise<string>,
  exportReportPdf: (args: { report: ReportFull; clinic: ClinicInfo; defaultFileName: string }) =>
    ipcRenderer.invoke('report:export-pdf', args) as Promise<ExportPdfResult>,
  openPath: (filePath: string) => ipcRenderer.invoke('shell:open-path', filePath) as Promise<void>,
  showItemInFolder: (filePath: string) =>
    ipcRenderer.invoke('shell:show-item', filePath) as Promise<void>,
};

contextBridge.exposeInMainWorld('api', api);
