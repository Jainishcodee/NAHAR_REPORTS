import { useState } from 'react';
import {
  Button, Center, Paper, PasswordInput, Stack, Text, TextInput, Title, Alert, Anchor, Collapse, Group,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertCircle, IconStethoscope } from '@tabler/icons-react';
import { useAuth } from '../lib/auth';
import { ApiError, getApiBaseUrl, setApiBaseUrl } from '../lib/api';

export function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showServer, setShowServer] = useState(false);

  const form = useForm({
    initialValues: {
      email: 'admin@clinic.local',
      password: '',
      serverUrl: getApiBaseUrl(),
    },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : 'Enter a valid email'),
      password: (v) => (v.length ? null : 'Required'),
      serverUrl: (v) => (/^https?:\/\//.test(v) ? null : 'Must start with http:// or https://'),
    },
  });

  const onSubmit = form.onSubmit(async (values) => {
    setError(null);
    setSubmitting(true);
    try {
      setApiBaseUrl(values.serverUrl);
      await login(values.email.trim(), values.password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <Center h="100vh" bg="var(--mantine-color-gray-0)">
      <Paper withBorder shadow="md" p="xl" radius="md" w={420}>
        <Stack gap="md">
          <Group gap="xs" justify="center">
            <IconStethoscope size={28} />
            <Title order={3}>Clinic Report Manager</Title>
          </Group>
          <Text c="dimmed" size="sm" ta="center">Sign in to manage patients and generate reports.</Text>

          {error && (
            <Alert color="red" icon={<IconAlertCircle size={16} />} variant="light">
              {error}
            </Alert>
          )}

          <form onSubmit={onSubmit}>
            <Stack gap="sm">
              <TextInput label="Email" autoComplete="username" {...form.getInputProps('email')} />
              <PasswordInput label="Password" autoComplete="current-password" {...form.getInputProps('password')} />

              <Anchor size="xs" onClick={() => setShowServer((s) => !s)}>
                {showServer ? 'Hide' : 'Change'} server address
              </Anchor>
              <Collapse in={showServer}>
                <TextInput
                  label="Server address"
                  description="The PC running the report server, e.g. http://192.168.1.10:4000"
                  {...form.getInputProps('serverUrl')}
                />
              </Collapse>

              <Button type="submit" loading={submitting} fullWidth mt="xs">
                Sign in
              </Button>
            </Stack>
          </form>

          <Text size="xs" c="dimmed" ta="center">
            Demo login after seeding: <b>admin@clinic.local</b> / <b>admin1234</b>
          </Text>
        </Stack>
      </Paper>
    </Center>
  );
}
