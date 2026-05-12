import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, SimpleGrid, Stack, Table, Text, Title, Loader, Center, Alert } from '@mantine/core';
import { IconFilePlus, IconUsers, IconReportMedical, IconAlertTriangle } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError, type ReportListItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';

export function DashboardPage() {
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [patientCount, setPatientCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [{ reports }, { patients }] = await Promise.all([api.listReports(), api.listPatients()]);
        setReports(reports);
        setPatientCount(patients.length);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Center h={300}><Loader /></Center>;

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Dashboard</Title>
        <Button leftSection={<IconFilePlus size={18} />} onClick={() => navigate('/reports/new')}>
          New report
        </Button>
      </Group>

      {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <StatCard icon={<IconUsers size={26} />} label="Patients" value={patientCount ?? '—'} onClick={() => navigate('/patients')} />
        <StatCard icon={<IconReportMedical size={26} />} label="Reports" value={reports.length} />
        <StatCard
          icon={<IconReportMedical size={26} />}
          label="Drafts pending"
          value={reports.filter((r) => r.status === 'DRAFT').length}
        />
      </SimpleGrid>

      <Card withBorder padding="lg" radius="md">
        <Title order={4} mb="sm">Recent reports</Title>
        {reports.length === 0 ? (
          <Text c="dimmed">No reports yet. Create one from “New report”.</Text>
        ) : (
          <Table highlightOnHover striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Report No.</Table.Th>
                <Table.Th>Patient</Table.Th>
                <Table.Th>Title</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Date</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {reports.slice(0, 12).map((r) => (
                <Table.Tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/reports/${r.id}`)}>
                  <Table.Td><Text ff="monospace" size="sm">{r.reportNo}</Text></Table.Td>
                  <Table.Td>{r.patient.lastName}, {r.patient.firstName} <Text span c="dimmed" size="xs">({r.patient.mrn})</Text></Table.Td>
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

function StatCard({ icon, label, value, onClick }: { icon: React.ReactNode; label: string; value: React.ReactNode; onClick?: () => void }) {
  return (
    <Card withBorder padding="lg" radius="md" style={{ cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <Group>
        {icon}
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>{label}</Text>
          <Text size="xl" fw={700}>{value}</Text>
        </div>
      </Group>
    </Card>
  );
}
