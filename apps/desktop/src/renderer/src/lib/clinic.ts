import type { ClinicInfo } from '@shared/types';

const KEY = 'report.clinicInfo';

export const DEFAULT_CLINIC: ClinicInfo = {
  name: 'Sunrise Medical Centre',
  addressLines: ['Plot 12, Health City Road', 'Pune, Maharashtra 411001'],
  phone: '+91 20 1234 5678',
  email: 'reports@sunrisemed.example',
  website: 'www.sunrisemed.example',
  registrationNo: 'MH/CLINIC/2026/00123',
};

export function getClinicInfo(): ClinicInfo {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return DEFAULT_CLINIC;
    const parsed = JSON.parse(raw) as Partial<ClinicInfo>;
    return {
      ...DEFAULT_CLINIC,
      ...parsed,
      addressLines: parsed.addressLines?.length ? parsed.addressLines : DEFAULT_CLINIC.addressLines,
    };
  } catch {
    return DEFAULT_CLINIC;
  }
}

export function setClinicInfo(info: ClinicInfo): void {
  localStorage.setItem(KEY, JSON.stringify(info));
}
