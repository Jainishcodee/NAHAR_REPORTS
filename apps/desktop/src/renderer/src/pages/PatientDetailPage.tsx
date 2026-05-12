import { useEffect, useState } from 'react';
import {
  Anchor, Badge, Breadcrumbs, Button, Card, Group, SimpleGrid, Stack, Table, Text, Title, Loader, Center, Alert,
} from '@mantine/core';
import { IconFilePlus, IconArrowLeft, IconAlertTriangle } from '@tabler/icons-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import type { Patient, ReportStatus, ReportType } from '@shared/types';
import { StatusBadge } from '../components/StatusBadge';

type PatientWithReports = Patient & {
  reports: { id: string; reportNo: string; type: ReportType; title: string; status: ReportStatus; reportDate: string }[];
};

function field(label: string, value: React.ReactNode) {
  return (
    <div>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>{label}</Text>
      <Text>{value || '—'}</Text>
    </div>
  );
}

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [patient, setPatient] = useState<PatientWithReports | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { patient } = await api.getPatient(id!);
        setPatient(patient as PatientWithReports);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Failed to load patient');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading) return <Center h={300}><Loader /></Center>;
  if (error || !patient) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error ?? 'Not found'}</Alert>;

  const age = (() => {
    const dob = new Date(patient.dateOfBirth);
    const now = new Date();
    let a = now.getFullYear() - dob.getFullYear();
    if (now.getMonth() < dob.getMonth() || (now.getMonth() === dob.getMonth() && now.getDate() < dob.getDate())) a--;
    return a;
  })();

  return (
    <Stack gap="lg">
      <Breadcrumbs>
        <Anchor component={Link} to="/patients">Patients</Anchor>
        <Text>{patient.lastName}, {patient.firstName}</Text>
      </Breadcrumbs>

      <Group justify="space-between">
        <Group>
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={() => navigate('/patients')}>Back</Button>
          <Title order={2}>{patient.lastName}, {patient.firstName}</Title>
          <Badge variant="light">MRN {patient.mrn}</Badge>
        </Group>
        <Button leftSection={<IconFilePlus size={18} />} onClick={() => navigate(`/reports/new?patientId=${patient.id}`)}>
          New report for this patient
        </Button>
      </Group>

      <Card withBorder padding="lg" radius="md">
        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          {field('Date of birth', `${new Date(patient.dateOfBirth).toLocaleDateString()} (${age} yrs)`)}
          {field('Sex', patient.sex === 'M' ? 'Male' : patient.sex === 'F' ? 'Female' : 'Other')}
          {field('Phone', patient.phone)}
          {field('Email', patient.email)}
          {field('Address', patient.address)}
          {field('Notes', patient.notes)}
        </SimpleGrid>
      </Card>

      <Card withBorder padding="lg" radius="md">
        <Title order={4} mb="sm">Reports ({patient.reports.length})</Title>
        {patient.reports.length === 0 ? (
          <Text c="dimmed">No reports for this patient yet.</Text>
        ) : (
          <Table highlightOnHover striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Report No.</Table.Th>
                <Table.Th>Title</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Date</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {patient.reports.map((r) => (
                <Table.Tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/reports/${r.id}`)}>
                  <Table.Td><Text ff="monospace" size="sm">{r.reportNo}</Text></Table.Td>
                  <Table.Td>{r.title}</Table.Td>
                  <Table.Td><Badge variant="light">{r.type.replace(/_/g, ' ')}</Badge></Table.Td>
                  <Table.Td><StatusBadge status={r.status} /></Table.Td>
                  <Table.Td>{new Date(r.reportDate).toLocaleDateString()}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
