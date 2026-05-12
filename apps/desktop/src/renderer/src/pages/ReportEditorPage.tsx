import { useEffect, useMemo, useState } from 'react';
import {
  ActionIcon, Alert, Button, Card, Center, Divider, Group, Loader, Select, Stack, Switch, Text, Textarea, TextInput, Title, Tooltip,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconDeviceFloppy, IconPlus, IconTrash, IconAlertTriangle, IconGripVertical } from '@tabler/icons-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import type { ReportData, ReportType } from '@shared/types';

const REPORT_TYPE_OPTIONS = [
  { value: 'LAB', label: 'Laboratory' },
  { value: 'RADIOLOGY', label: 'Radiology / Imaging' },
  { value: 'DISCHARGE_SUMMARY', label: 'Discharge summary' },
  { value: 'GENERAL', label: 'General' },
];

interface SectionDraft {
  heading: string;
  text: string;
  hasTable: boolean;
  columns: string; // comma-separated
  rows: string; // one row per line, cells separated by " | "
}

const emptySection = (): SectionDraft => ({ heading: '', text: '', hasTable: false, columns: 'Test, Result, Unit, Reference range', rows: '' });

function toReportData(summary: string, sections: SectionDraft[]): ReportData {
  return {
    summary: summary.trim() || undefined,
    sections: sections
      .filter((s) => s.heading.trim())
      .map((s) => {
        const out: ReportData['sections'][number] = { heading: s.heading.trim() };
        if (s.text.trim()) out.text = s.text.trim();
        if (s.hasTable) {
          const columns = s.columns.split(',').map((c) => c.trim()).filter(Boolean);
          if (columns.length) {
            const rows = s.rows
              .split('\n')
              .map((line) => line.trim())
              .filter(Boolean)
              .map((line) => {
                const cells = line.split('|').map((c) => c.trim());
                while (cells.length < columns.length) cells.push('');
                return cells.slice(0, columns.length);
              });
            out.table = { columns, rows };
          }
        }
        return out;
      }),
  };
}

function fromReportData(data: ReportData): { summary: string; sections: SectionDraft[] } {
  return {
    summary: data.summary ?? '',
    sections:
      data.sections.length === 0
        ? [emptySection()]
        : data.sections.map((s) => ({
            heading: s.heading,
            text: s.text ?? '',
            hasTable: !!s.table,
            columns: s.table?.columns.join(', ') ?? emptySection().columns,
            rows: s.table?.rows.map((r) => r.join(' | ')).join('\n') ?? '',
          })),
  };
}

export function ReportEditorPage({ mode }: { mode: 'create' | 'edit' }) {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const presetPatientId = searchParams.get('patientId');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [patientOptions, setPatientOptions] = useState<{ value: string; label: string }[]>([]);
  const [lockPatient, setLockPatient] = useState(false);

  const form = useForm<{
    patientId: string;
    type: ReportType;
    title: string;
    reportDate: Date | null;
    summary: string;
    sections: SectionDraft[];
  }>({
    initialValues: {
      patientId: presetPatientId ?? '',
      type: 'LAB',
      title: '',
      reportDate: new Date(),
      summary: '',
      sections: [emptySection()],
    },
    validate: {
      patientId: (v) => (v ? null : 'Select a patient'),
      title: (v) => (v.trim() ? null : 'Required'),
      reportDate: (v) => (v ? null : 'Required'),
    },
  });

  useEffect(() => {
    (async () => {
      try {
        const { patients } = await api.listPatients();
        setPatientOptions(patients.map((p) => ({ value: p.id, label: `${p.lastName}, ${p.firstName} — ${p.mrn}` })));

        if (mode === 'edit' && id) {
          const { report } = await api.getReport(id);
          const { summary, sections } = fromReportData(report.data);
          form.setValues({
            patientId: report.patient.id,
            type: report.type,
            title: report.title,
            reportDate: new Date(report.reportDate),
            summary,
            sections,
          });
          setLockPatient(true);
        } else if (presetPatientId) {
          setLockPatient(true);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Failed to load editor');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, id]);

  const patientLabel = useMemo(
    () => patientOptions.find((o) => o.value === form.values.patientId)?.label ?? form.values.patientId,
    [patientOptions, form.values.patientId],
  );

  const submit = form.onSubmit(async (values) => {
    setSaving(true);
    try {
      const data = toReportData(values.summary, values.sections);
      if (mode === 'create') {
        const { report } = await api.createReport({
          patientId: values.patientId,
          type: values.type,
          title: values.title.trim(),
          reportDate: values.reportDate!.toISOString(),
          data,
        });
        notifications.show({ color: 'green', message: `Report ${report.reportNo} created (draft)` });
        navigate(`/reports/${report.id}`);
      } else if (id) {
        const { report } = await api.updateReport(id, {
          type: values.type,
          title: values.title.trim(),
          reportDate: values.reportDate!.toISOString(),
          data,
        });
        notifications.show({ color: 'green', message: `Report ${report.reportNo} updated` });
        navigate(`/reports/${report.id}`);
      }
    } catch (err) {
      notifications.show({ color: 'red', title: 'Save failed', message: err instanceof ApiError ? err.message : 'Error' });
    } finally {
      setSaving(false);
    }
  });

  if (loading) return <Center h={300}><Loader /></Center>;
  if (error) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>;

  const sections = form.values.sections;

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Group>
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate(-1)}>Back</Button>
          <Title order={2}>{mode === 'create' ? 'New report' : 'Edit report'}</Title>
        </Group>
        <Button leftSection={<IconDeviceFloppy size={18} />} loading={saving} onClick={() => submit()}>
          {mode === 'create' ? 'Create draft' : 'Save changes'}
        </Button>
      </Group>

      <form onSubmit={submit}>
        <Stack gap="lg">
          <Card withBorder padding="lg" radius="md">
            <Stack gap="sm">
              {lockPatient ? (
                <TextInput label="Patient" value={patientLabel} readOnly />
              ) : (
                <Select label="Patient" withAsterisk searchable data={patientOptions} {...form.getInputProps('patientId')} />
              )}
              <Group grow>
                <Select label="Report type" data={REPORT_TYPE_OPTIONS} {...form.getInputProps('type')} />
                <DateInput label="Report date" withAsterisk valueFormat="DD MMM YYYY" {...form.getInputProps('reportDate')} />
              </Group>
              <TextInput label="Report title" withAsterisk placeholder="e.g. Complete Blood Count (CBC)" {...form.getInputProps('title')} />
              <Textarea label="Summary / impression" autosize minRows={2} placeholder="Short clinical summary that appears at the top of the report." {...form.getInputProps('summary')} />
            </Stack>
          </Card>

          <Group justify="space-between">
            <Title order={4}>Sections</Title>
            <Button variant="light" leftSection={<IconPlus size={16} />} onClick={() => form.insertListItem('sections', emptySection())}>
              Add section
            </Button>
          </Group>

          {sections.map((section, i) => (
            <Card key={i} withBorder padding="lg" radius="md">
              <Stack gap="sm">
                <Group justify="space-between">
                  <Group gap="xs">
                    <IconGripVertical size={16} color="var(--mantine-color-gray-5)" />
                    <Text fw={600}>Section {i + 1}</Text>
                  </Group>
                  <Tooltip label="Remove section">
                    <ActionIcon color="red" variant="subtle" disabled={sections.length === 1} onClick={() => form.removeListItem('sections', i)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
                <TextInput label="Heading" placeholder="e.g. Haematology" {...form.getInputProps(`sections.${i}.heading`)} />
                <Textarea label="Text" autosize minRows={2} placeholder="Free-text findings / comments for this section." {...form.getInputProps(`sections.${i}.text`)} />
                <Switch label="Include a results table" {...form.getInputProps(`sections.${i}.hasTable`, { type: 'checkbox' })} />
                {section.hasTable && (
                  <>
                    <Divider label="Table" labelPosition="left" />
                    <TextInput label="Columns" description="Comma-separated, e.g.  Test, Result, Unit, Reference range" {...form.getInputProps(`sections.${i}.columns`)} />
                    <Textarea
                      label="Rows"
                      description={'One row per line. Separate cells with " | ". Example:  Haemoglobin | 13.4 | g/dL | 12.0 – 15.5'}
                      autosize
                      minRows={3}
                      styles={{ input: { fontFamily: 'monospace' } }}
                      {...form.getInputProps(`sections.${i}.rows`)}
                    />
                  </>
                )}
              </Stack>
            </Card>
          ))}

          <Group justify="flex-end">
            <Button variant="default" onClick={() => navigate(-1)}>Cancel</Button>
            <Button type="submit" loading={saving} leftSection={<IconDeviceFloppy size={18} />}>
              {mode === 'create' ? 'Create draft' : 'Save changes'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Stack>
  );
}
