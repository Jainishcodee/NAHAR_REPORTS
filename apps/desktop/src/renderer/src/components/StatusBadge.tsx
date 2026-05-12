import { Badge } from '@mantine/core';
import type { ReportStatus } from '@shared/types';

const COLOR: Record<ReportStatus, string> = { DRAFT: 'yellow', FINAL: 'green', AMENDED: 'orange' };
const LABEL: Record<ReportStatus, string> = { DRAFT: 'Draft', FINAL: 'Final', AMENDED: 'Amended' };

export function StatusBadge({ status }: { status: ReportStatus }) {
  return <Badge color={COLOR[status] ?? 'gray'} variant="light">{LABEL[status] ?? status}</Badge>;
}
