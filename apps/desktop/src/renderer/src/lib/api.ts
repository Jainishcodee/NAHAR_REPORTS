// Thin wrapper around fetch(). The Electron renderer talks to the Fastify API
// directly over the LAN; the base URL is configured by the user in Settings and
// kept in localStorage so it survives restarts.

import type {
  AuthUser,
  Patient,
  ReportData,
  ReportFull,
  ReportStatus,
  ReportType,
  Sex,
} from '@shared/types';

const BASE_URL_KEY = 'report.apiBaseUrl';
const TOKEN_KEY = 'report.authToken';

export function getApiBaseUrl(): string {
  return (
    localStorage.getItem(BASE_URL_KEY) ||
    import.meta.env.VITE_API_BASE_URL ||
    'http://localhost:4000'
  ).replace(/\/+$/, '');
}
export function setApiBaseUrl(url: string): void {
  localStorage.setItem(BASE_URL_KEY, url.trim().replace(/\/+$/, ''));
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check the server address in Settings.');
  }

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, (body as { error?: string }).error ?? `Request failed (${res.status})`, body);
  }
  return body as T;
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(data ?? {}) });
const put = <T>(path: string, data: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(data) });
const del = <T>(path: string) => request<T>(path, { method: 'DELETE' });

// ---- Endpoint helpers --------------------------------------------------------

export interface PatientListItem extends Patient {}
export interface ReportListItem {
  id: string;
  reportNo: string;
  type: ReportType;
  title: string;
  status: ReportStatus;
  reportDate: string;
  patient: { id: string; mrn: string; firstName: string; lastName: string };
}

export interface PatientInput {
  mrn: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string; // ISO date
  sex: Sex;
  phone?: string;
  email?: string;
  address?: string;
  notes?: string;
}

export interface ReportInput {
  patientId: string;
  type: ReportType;
  title: string;
  reportDate?: string;
  data: ReportData;
}

export const api = {
  health: () => get<{ ok: boolean; time: string }>('/health'),

  login: (email: string, password: string) =>
    post<{ token: string; user: AuthUser }>('/api/auth/login', { email, password }),
  me: () => get<{ user: AuthUser }>('/api/auth/me'),

  listPatients: (search?: string) =>
    get<{ patients: PatientListItem[] }>(`/api/patients${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  getPatient: (id: string) =>
    get<{ patient: Patient & { reports: Omit<ReportListItem, 'patient'>[] } }>(`/api/patients/${id}`),
  createPatient: (input: PatientInput) => post<{ patient: Patient }>('/api/patients', input),
  updatePatient: (id: string, input: Partial<PatientInput>) =>
    put<{ patient: Patient }>(`/api/patients/${id}`, input),

  listReports: (patientId?: string) =>
    get<{ reports: ReportListItem[] }>(`/api/reports${patientId ? `?patientId=${patientId}` : ''}`),
  getReport: (id: string) => get<{ report: ReportFull }>(`/api/reports/${id}`),
  createReport: (input: ReportInput) => post<{ report: ReportFull }>('/api/reports', input),
  updateReport: (
    id: string,
    input: Partial<{
      title: string;
      type: ReportType;
      status: ReportStatus;
      reportDate: string;
      data: ReportData;
    }>,
  ) => put<{ report: ReportFull }>(`/api/reports/${id}`, input),
  markPdfExported: (id: string, pdfPath: string) =>
    post<{ ok: true }>(`/api/reports/${id}/pdf-exported`, { pdfPath }),
  deleteReport: (id: string) => del<{ ok: true }>(`/api/reports/${id}`),
};
