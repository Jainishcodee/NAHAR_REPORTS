import { BrowserWindow, dialog } from 'electron';
import { writeFile } from 'node:fs/promises';
import { buildReportHtml } from '../shared/reportHtml';
import type { ClinicInfo, ExportPdfResult, ReportFull } from '../shared/types';

interface ExportArgs {
  report: ReportFull;
  clinic: ClinicInfo;
  defaultFileName: string;
}

/**
 * Render the report to a PDF using Chromium's print engine, then ask the user
 * where to save it. The "hidden window loads an HTML string" approach gives us
 * pixel-perfect, fully-styled PDFs without any extra PDF library.
 */
export async function exportReportPdf(
  parent: BrowserWindow | undefined,
  { report, clinic, defaultFileName }: ExportArgs,
): Promise<ExportPdfResult> {
  let renderWin: BrowserWindow | null = null;
  try {
    const html = buildReportHtml(report, clinic);

    renderWin = new BrowserWindow({
      show: false,
      webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false },
    });

    await renderWin.loadURL('data:text/html;charset=UTF-8,' + encodeURIComponent(html));
    // Give the layout a tick to settle (fonts, table column widths).
    await new Promise((r) => setTimeout(r, 150));

    // preferCSSPageSize honours the `@page { size: A4; margin: ... }` rule in the
    // template, so the report's own CSS fully controls the printed layout.
    const pdf = await renderWin.webContents.printToPDF({
      printBackground: true,
      preferCSSPageSize: true,
      pageSize: 'A4',
    });

    renderWin.destroy();
    renderWin = null;

    const safeName = defaultFileName.replace(/[\\/:*?"<>|]+/g, '_');
    const result = await dialog.showSaveDialog(parent!, {
      title: 'Save report as PDF',
      defaultPath: safeName.toLowerCase().endsWith('.pdf') ? safeName : `${safeName}.pdf`,
      filters: [{ name: 'PDF document', extensions: ['pdf'] }],
    });

    if (result.canceled || !result.filePath) return { status: 'cancelled' };

    await writeFile(result.filePath, pdf);
    return { status: 'saved', filePath: result.filePath };
  } catch (err) {
    return { status: 'error', message: err instanceof Error ? err.message : String(err) };
  } finally {
    if (renderWin && !renderWin.isDestroyed()) renderWin.destroy();
  }
}
