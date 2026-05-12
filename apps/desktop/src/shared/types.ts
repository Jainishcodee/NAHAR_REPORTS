// Types shared between the Electron main process, the preload bridge and the
// React renderer. Keep this file dependency-free (no Node, no DOM imports) so
// every build target can use it.

export type Role = 'ADMIN' | 'DOCTOR' | 'STAFF';
export type Sex = 'M' | 'F' | 'OTHER';
export type ReportType = 'LAB' | 'RADIOLOGY' | 'DISCHARGE_SUMMARY' | 'GENERAL';
export type ReportStatus = 'DRAFT' | 'FINAL' | 'AMENDED';

export interface AuthUser {
  sub: string;
  email: string;
  role: Role;
  fullName: string;
}

export interface Patient {
  id: string;
  mrn: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  sex: Sex;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  notes?: string | null;
}

export interface ReportSection {
  heading: string;
  text?: string;
  table?: { columns: string[]; rows: string[][] };
}

export interface ReportData {
  summary?: string;
  sections: ReportSection[];
}

export interface ReportSummary {
  id: string;
  reportNo: string;
  type: ReportType;
  title: string;
  status: ReportStatus;
  reportDate: string;
}

export interface ReportFull extends ReportSummary {
  data: ReportData;
  pdfPath?: string | null;
  finalizedAt?: string | null;
  patient: Patient;
  author: { id: string; fullName: string; email: string };
}

/** Clinic / organisation details printed in the PDF header & footer. */
export interface ClinicInfo {
  name: string;
  addressLines: string[];
  phone?: string;
  email?: string;
  website?: string;
  registrationNo?: string;
}

/** Result of an "export PDF" request handled by the main process. */
export type ExportPdfResult =
  | { status: 'saved'; filePath: string }
  | { status: 'cancelled' }
  | { status: 'error'; message: string };

/** The API surface the preload script exposes on `window.api`. */
export interface DesktopApi {
  getAppVersion: () => Promise<string>;
  exportReportPdf: (args: {
    report: ReportFull;
    clinic: ClinicInfo;
    defaultFileName: string;
  }) => Promise<ExportPdfResult>;
  openPath: (filePath: string) => Promise<void>;
  showItemInFolder: (filePath: string) => Promise<void>;
}
