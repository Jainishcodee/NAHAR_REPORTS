import { useEffect, useMemo, useState } from 'react';
import {
  Alert, Anchor, Badge, Breadcrumbs, Button, Card, Center, Group, Loader, Menu, Paper, Stack, Text, Title, Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconArrowLeft, IconEdit, IconFileTypePdf, IconCheck, IconDots, IconFolderOpen, IconAlertTriangle, IconCircleCheck,
} from '@tabler/icons-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { buildReportHtml } from '@shared/reportHtml';
import type { ReportFull } from '@shared/types';
import { getClinicInfo } from '../lib/clinic';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../lib/auth';

export function ReportViewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [report, setReport] = useState<ReportFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    const { report } = await api.getReport(id!);
    setReport(report);
  };

  useEffect(() => {
    (async () => {
      try {
        await reload();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Failed to load report');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const previewHtml = useMemo(() => (report ? buildReportHtml(report, getClinicInfo()) : ''), [report]);

  if (loading) return <Center h={300}><Loader /></Center>;
  if (error || !report) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error ?? 'Not found'}</Alert>;

  const canFinalize = user?.role === 'ADMIN' || user?.role === 'DOCTOR';
  const fileName = `${report.reportNo}_${report.patient.lastName}_${report.patient.firstName}`;

  const setStatus = async (status: ReportFull['status']) => {
    setBusy(true);
    try {
      await api.updateReport(report.id, { status });
      await reload();
      notifications.show({ color: 'green', message: `Report marked ${status.toLowerCase()}` });
    } catch (err) {
      notifications.show({ color: 'red', message: err instanceof ApiError ? err.message : 'Update failed' });
    } finally {
      setBusy(false);
    }
  };

  const exportPdf = async () => {
    setBusy(true);
    try {
      const res = await window.api.exportReportPdf({ report, clinic: getClinicInfo(), defaultFileName: fileName });
      if (res.status === 'cancelled') return;
      if (res.status === 'error') {
        notifications.show({ color: 'red', title: 'PDF export failed', message: res.message });
        return;
      }
      await api.markPdfExported(report.id, res.filePath).catch(() => undefined);
      await reload();
      notifications.show({
        color: 'green',
        title: 'PDF saved',
        message: (
          <Text size="sm">
            {res.filePath}{' '}
            <Anchor size="sm" onClick={() => window.api.openPath(res.filePath)}>Open</Anchor>{' · '}
            <Anchor size="sm" onClick={() => window.api.showItemInFolder(res.filePath)}>Show in folder</Anchor>
          </Text>
        ),
        autoClose: 8000,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap="lg">
      <Breadcrumbs>
        <Anchor component={Link} to="/">Dashboard</Anchor>
        <Anchor component={Link} to={`/patients/${report.patient.id}`}>{report.patient.lastName}, {report.patient.firstName}</Anchor>
        <Text>{report.reportNo}</Text>
      </Breadcrumbs>

      <Group justify="space-between" align="flex-start">
        <Group>
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate(-1)}>Back</Button>
          <div>
            <Title order={2}>{report.title}</Title>
            <Group gap="xs" mt={4}>
              <Text ff="monospace" size="sm">{report.reportNo}</Text>
              <Badge variant="light">{report.type.replace(/_/g, ' ')}</Badge>
              <StatusBadge status={report.status} />
            </Group>
          </div>
        </Group>
        <Group>
          <Button variant="default" leftSection={<IconEdit size={16} />} onClick={() => navigate(`/reports/${report.id}/edit`)}>
            Edit
          </Button>
          {report.status === 'DRAFT' && canFinalize && (
            <Button leftSection={<IconCheck size={16} />} loading={busy} onClick={() => setStatus('FINAL')}>
              Finalize
            </Button>
          )}
          <Button color="red" variant="light" leftSection={<IconFileTypePdf size={16} />} loading={busy} onClick={exportPdf}>
            Export PDF
          </Button>
          <Menu position="bottom-end" withArrow>
            <Menu.Target><Button variant="subtle" px="xs"><IconDots size={18} /></Button></Menu.Target>
            <Menu.Dropdown>
              {report.pdfPath && (
                <>
                  <Menu.Item leftSection={<IconFolderOpen size={16} />} onClick={() => window.api.openPath(report.pdfPath!)}>
                    Open last exported PDF
                  </Menu.Item>
                  <Menu.Divider />
                </>
              )}
              {report.status === 'FINAL' && canFinalize && (
                <Menu.Item leftSection={<IconCircleCheck size={16} />} onClick={() => setStatus('AMENDED')}>
                  Mark as amended
                </Menu.Item>
              )}
              {report.status === 'AMENDED' && canFinalize && (
                <Menu.Item leftSection={<IconCheck size={16} />} onClick={() => setStatus('FINAL')}>
                  Re-finalize
                </Menu.Item>
              )}
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      {report.status === 'DRAFT' && (
        <Alert color="yellow" icon={<IconAlertTriangle size={16} />} variant="light">
          This report is a <b>draft</b>. Exported PDFs are watermarked “DRAFT” until you finalize it.
        </Alert>
      )}
      {report.pdfPath && (
        <Text size="xs" c="dimmed">
          <Tooltip label={report.pdfPath}><span>Last PDF exported to:&nbsp;</span></Tooltip>
          <Anchor size="xs" onClick={() => window.api.openPath(report.pdfPath!)}>{report.pdfPath}</Anchor>
        </Text>
      )}

      <Card withBorder padding="xs" radius="md">
        <Text size="xs" c="dimmed" mb="xs" px="xs">Preview — this is exactly what the PDF will contain.</Text>
        <Paper withBorder radius="sm" style={{ overflow: 'hidden', background: '#fff' }}>
          <iframe
            title="Report preview"
            srcDoc={previewHtml}
            style={{ width: '100%', height: '80vh', border: 'none', display: 'block' }}
          />
        </Paper>
      </Card>
    </Stack>
  );
}
