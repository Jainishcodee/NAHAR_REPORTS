import { useState } from 'react';
import {
  Alert, Badge, Button, Card, Group, Stack, Text, Textarea, TextInput, Title, Code,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconCircleCheck, IconCircleX, IconDeviceFloppy, IconPlugConnected } from '@tabler/icons-react';
import { api, getApiBaseUrl, setApiBaseUrl } from '../lib/api';
import { DEFAULT_CLINIC, getClinicInfo, setClinicInfo } from '../lib/clinic';
import { useAuth } from '../lib/auth';
import type { ClinicInfo } from '@shared/types';

export function SettingsPage() {
  const { user } = useAuth();
  const [testState, setTestState] = useState<'idle' | 'ok' | 'fail'>('idle');
  const [testing, setTesting] = useState(false);

  const serverForm = useForm({
    initialValues: { serverUrl: getApiBaseUrl() },
    validate: { serverUrl: (v) => (/^https?:\/\//.test(v) ? null : 'Must start with http:// or https://') },
  });

  const clinic = getClinicInfo();
  const clinicForm = useForm({
    initialValues: {
      name: clinic.name,
      address: clinic.addressLines.join('\n'),
      phone: clinic.phone ?? '',
      email: clinic.email ?? '',
      website: clinic.website ?? '',
      registrationNo: clinic.registrationNo ?? '',
    },
    validate: { name: (v) => (v.trim() ? null : 'Required') },
  });

  const testConnection = async () => {
    setTesting(true);
    setTestState('idle');
    const previous = getApiBaseUrl();
    try {
      setApiBaseUrl(serverForm.values.serverUrl);
      await api.health();
      setTestState('ok');
    } catch {
      setTestState('fail');
      setApiBaseUrl(previous);
    } finally {
      setTesting(false);
    }
  };

  const saveServer = serverForm.onSubmit((values) => {
    setApiBaseUrl(values.serverUrl);
    notifications.show({ color: 'green', message: 'Server address saved. It will be used for new requests.' });
  });

  const saveClinic = clinicForm.onSubmit((values) => {
    const info: ClinicInfo = {
      name: values.name.trim(),
      addressLines: values.address.split('\n').map((l) => l.trim()).filter(Boolean),
      phone: values.phone.trim() || undefined,
      email: values.email.trim() || undefined,
      website: values.website.trim() || undefined,
      registrationNo: values.registrationNo.trim() || undefined,
    };
    setClinicInfo(info);
    notifications.show({ color: 'green', message: 'Clinic details saved. They appear on every generated PDF.' });
  });

  return (
    <Stack gap="lg" maw={760}>
      <Title order={2}>Settings</Title>

      <Card withBorder padding="lg" radius="md">
        <Title order={4} mb="xs">Server connection</Title>
        <Text size="sm" c="dimmed" mb="md">
          The address of the PC running the report server on your clinic network. Find its IP with{' '}
          <Code>ipconfig</Code> on that machine, then use <Code>http://THAT-IP:4000</Code>.
        </Text>
        <form onSubmit={saveServer}>
          <Stack gap="sm">
            <TextInput label="Server address" {...serverForm.getInputProps('serverUrl')} />
            <Group>
              <Button variant="light" leftSection={<IconPlugConnected size={16} />} loading={testing} onClick={testConnection}>
                Test connection
              </Button>
              {testState === 'ok' && <Badge color="green" leftSection={<IconCircleCheck size={14} />}>Reachable</Badge>}
              {testState === 'fail' && <Badge color="red" leftSection={<IconCircleX size={14} />}>Not reachable</Badge>}
              <Button type="submit" leftSection={<IconDeviceFloppy size={16} />}>Save</Button>
            </Group>
          </Stack>
        </form>
      </Card>

      <Card withBorder padding="lg" radius="md">
        <Title order={4} mb="xs">Clinic details (printed on PDFs)</Title>
        <form onSubmit={saveClinic}>
          <Stack gap="sm">
            <TextInput label="Clinic / hospital name" withAsterisk {...clinicForm.getInputProps('name')} />
            <Textarea label="Address" description="One line per row" autosize minRows={2} {...clinicForm.getInputProps('address')} />
            <Group grow>
              <TextInput label="Phone" {...clinicForm.getInputProps('phone')} />
              <TextInput label="Email" {...clinicForm.getInputProps('email')} />
            </Group>
            <Group grow>
              <TextInput label="Website" {...clinicForm.getInputProps('website')} />
              <TextInput label="Registration No." {...clinicForm.getInputProps('registrationNo')} />
            </Group>
            <Group>
              <Button type="submit" leftSection={<IconDeviceFloppy size={16} />}>Save clinic details</Button>
              <Button variant="subtle" color="gray" onClick={() => clinicForm.setValues({
                name: DEFAULT_CLINIC.name,
                address: DEFAULT_CLINIC.addressLines.join('\n'),
                phone: DEFAULT_CLINIC.phone ?? '',
                email: DEFAULT_CLINIC.email ?? '',
                website: DEFAULT_CLINIC.website ?? '',
                registrationNo: DEFAULT_CLINIC.registrationNo ?? '',
              })}>
                Reset to sample
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>

      <Card withBorder padding="lg" radius="md">
        <Title order={4} mb="xs">Signed in as</Title>
        <Group>
          <Text>{user?.fullName}</Text>
          <Badge variant="light">{user?.role}</Badge>
          <Text c="dimmed">{user?.email}</Text>
        </Group>
        <Alert mt="md" variant="light" color="blue">
          User accounts, password changes and the audit log live on the server. A future build can expose
          an admin screen here; for now manage users with <Code>npm run db:studio -w @report/api</Code>.
        </Alert>
      </Card>
    </Stack>
  );
}
