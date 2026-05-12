export const ROLES = ['ADMIN', 'DOCTOR', 'STAFF'] as const;
export type Role = (typeof ROLES)[number];

export const SEXES = ['M', 'F', 'OTHER'] as const;
export type Sex = (typeof SEXES)[number];

export const REPORT_TYPES = ['LAB', 'RADIOLOGY', 'DISCHARGE_SUMMARY', 'GENERAL'] as const;
export type ReportType = (typeof REPORT_TYPES)[number];

export const REPORT_STATUSES = ['DRAFT', 'FINAL', 'AMENDED'] as const;
export type ReportStatus = (typeof REPORT_STATUSES)[number];

export const AUDIT_ACTIONS = [
  'CREATE',
  'READ',
  'UPDATE',
  'DELETE',
  'LOGIN',
  'EXPORT_PDF',
  'PRINT',
] as const;
export type AuditAction = (typeof AUDIT_ACTIONS)[number];
