import { useEffect, useState } from 'react';
import {
  Button, Group, Modal, Stack, Table, Text, TextInput, Title, Loader, Center, Alert, Select, Textarea, ActionIcon,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconPlus, IconSearch, IconUserPlus, IconAlertTriangle, IconChevronRight } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError, type PatientInput, type PatientListItem } from '../lib/api';

export function PatientsPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = async (q?: string) => {
    setLoading(true);
    try {
      const { patients } = await api.listPatients(q);
      setPatients(patients);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const form = useForm<{
    mrn: string; firstName: string; lastName: string; dateOfBirth: Date | null;
    sex: PatientInput['sex']; phone: string; email: string; address: string; notes: string;
  }>({
    initialValues: { mrn: '', firstName: '', lastName: '', dateOfBirth: null, sex: 'F', phone: '', email: '', address: '', notes: '' },
    validate: {
      mrn: (v) => (v.trim() ? null : 'Required'),
      firstName: (v) => (v.trim() ? null : 'Required'),
      lastName: (v) => (v.trim() ? null : 'Required'),
      dateOfBirth: (v) => (v ? null : 'Required'),
      email: (v) => (!v || /^\S+@\S+$/.test(v) ? null : 'Invalid email'),
    },
  });

  const submit = form.onSubmit(async (values) => {
    setSaving(true);
    try {
      const { patient } = await api.createPatient({
        mrn: values.mrn.trim(),
        firstName: values.firstName.trim(),
        lastName: values.lastName.trim(),
        dateOfBirth: values.dateOfBirth!.toISOString(),
        sex: values.sex,
        phone: values.phone || undefined,
        email: values.email || undefined,
        address: values.address || undefined,
        notes: values.notes || undefined,
      });
      notifications.show({ color: 'green', message: `Patient ${patient.lastName}, ${patient.firstName} added` });
      setModalOpen(false);
      form.reset();
      navigate(`/patients/${patient.id}`);
    } catch (err) {
      notifications.show({ color: 'red', title: 'Could not add patient', message: err instanceof ApiError ? err.message : 'Error' });
    } finally {
      setSaving(false);
    }
  });

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Title order={2}>Patients</Title>
        <Button leftSection={<IconUserPlus size={18} />} onClick={() => setModalOpen(true)}>Add patient</Button>
      </Group>

      <Group>
        <TextInput
          flex={1}
          leftSection={<IconSearch size={16} />}
          placeholder="Search by name or MRN…"
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          onKeyDown={(e) => e.key === 'Enter' && load(search)}
        />
        <Button variant="light" onClick={() => load(search)}>Search</Button>
        {search && <Button variant="subtle" onClick={() => { setSearch(''); load(); }}>Clear</Button>}
      </Group>

      {error && <Alert color="red" icon={<IconAlertTriangle size={16} />}>{error}</Alert>}

      {loading ? (
        <Center h={200}><Loader /></Center>
      ) : patients.length === 0 ? (
        <Text c="dimmed">No patients found.</Text>
      ) : (
        <Table highlightOnHover striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>MRN</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Date of birth</Table.Th>
              <Table.Th>Sex</Table.Th>
              <Table.Th>Phone</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {patients.map((p) => (
              <Table.Tr key={p.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/patients/${p.id}`)}>
                <Table.Td><Text ff="monospace" size="sm">{p.mrn}</Text></Table.Td>
                <Table.Td>{p.lastName}, {p.firstName}</Table.Td>
                <Table.Td>{new Date(p.dateOfBirth).toLocaleDateString()}</Table.Td>
                <Table.Td>{p.sex}</Table.Td>
                <Table.Td>{p.phone ?? '—'}</Table.Td>
                <Table.Td><ActionIcon variant="subtle"><IconChevronRight size={16} /></ActionIcon></Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Add patient" size="lg">
        <form onSubmit={submit}>
          <Stack gap="sm">
            <Group grow>
              <TextInput label="MRN (Medical Record No.)" withAsterisk {...form.getInputProps('mrn')} />
              <Select label="Sex" withAsterisk data={[{ value: 'F', label: 'Female' }, { value: 'M', label: 'Male' }, { value: 'OTHER', label: 'Other' }]} {...form.getInputProps('sex')} />
            </Group>
            <Group grow>
              <TextInput label="First name" withAsterisk {...form.getInputProps('firstName')} />
              <TextInput label="Last name" withAsterisk {...form.getInputProps('lastName')} />
            </Group>
            <Group grow>
              <DateInput label="Date of birth" withAsterisk valueFormat="DD MMM YYYY" maxDate={new Date()} {...form.getInputProps('dateOfBirth')} />
              <TextInput label="Phone" {...form.getInputProps('phone')} />
            </Group>
            <TextInput label="Email" {...form.getInputProps('email')} />
            <Textarea label="Address" autosize minRows={2} {...form.getInputProps('address')} />
            <Textarea label="Notes" autosize minRows={2} {...form.getInputProps('notes')} />
            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button type="submit" loading={saving} leftSection={<IconPlus size={16} />}>Add patient</Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}
