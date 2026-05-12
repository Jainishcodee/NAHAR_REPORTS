import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { prisma } from '../prisma.js';
import { auditFromRequest } from '../audit.js';
import { SEXES } from '../constants.js';

const patientInput = z.object({
  mrn: z.string().trim().min(1).max(40),
  firstName: z.string().trim().min(1).max(100),
  lastName: z.string().trim().min(1).max(100),
  dateOfBirth: z.coerce.date(),
  sex: z.enum(SEXES),
  phone: z.string().trim().max(40).optional().or(z.literal('')),
  email: z.string().email().optional().or(z.literal('')),
  address: z.string().trim().max(400).optional().or(z.literal('')),
  notes: z.string().trim().max(2000).optional().or(z.literal('')),
});

const blankToNull = <T extends Record<string, unknown>>(o: T) =>
  Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === '' ? null : v]));

export async function patientRoutes(app: FastifyInstance) {
  app.addHook('preHandler', app.authenticate);

  // List / search patients.
  app.get('/patients', async (req) => {
    const q = z.object({ search: z.string().trim().optional() }).parse(req.query);
    const where = q.search
      ? {
          OR: [
            { firstName: { contains: q.search } },
            { lastName: { contains: q.search } },
            { mrn: { contains: q.search } },
          ],
        }
      : {};
    const patients = await prisma.patient.findMany({
      where,
      orderBy: [{ lastName: 'asc' }, { firstName: 'asc' }],
      take: 200,
    });
    return { patients };
  });

  // Get one patient with their reports.
  app.get('/patients/:id', async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const patient = await prisma.patient.findUnique({
      where: { id },
      include: {
        reports: {
          orderBy: { reportDate: 'desc' },
          select: { id: true, reportNo: true, type: true, title: true, status: true, reportDate: true },
        },
      },
    });
    if (!patient) return reply.code(404).send({ error: 'Patient not found' });
    await auditFromRequest(req, { action: 'READ', entity: 'Patient', entityId: id });
    return { patient };
  });

  // Create a patient.
  app.post('/patients', async (req, reply) => {
    const body = patientInput.safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: 'Invalid request', details: body.error.flatten() });

    const exists = await prisma.patient.findUnique({ where: { mrn: body.data.mrn } });
    if (exists) return reply.code(409).send({ error: `MRN ${body.data.mrn} already exists` });

    const patient = await prisma.patient.create({ data: blankToNull(body.data) as never });
    await auditFromRequest(req, {
      action: 'CREATE',
      entity: 'Patient',
      entityId: patient.id,
      summary: `Created patient ${patient.lastName}, ${patient.firstName} (MRN ${patient.mrn})`,
    });
    return reply.code(201).send({ patient });
  });

  // Update a patient.
  app.put('/patients/:id', async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const body = patientInput.partial().safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: 'Invalid request', details: body.error.flatten() });

    const patient = await prisma.patient
      .update({ where: { id }, data: blankToNull(body.data) as never })
      .catch(() => null);
    if (!patient) return reply.code(404).send({ error: 'Patient not found' });

    await auditFromRequest(req, {
      action: 'UPDATE',
      entity: 'Patient',
      entityId: id,
      summary: `Updated patient MRN ${patient.mrn}`,
    });
    return { patient };
  });

  // Delete a patient (ADMIN only). Cascades to their reports.
  app.delete('/patients/:id', { preHandler: app.requireRole('ADMIN') }, async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const deleted = await prisma.patient.delete({ where: { id } }).catch(() => null);
    if (!deleted) return reply.code(404).send({ error: 'Patient not found' });
    await auditFromRequest(req, {
      action: 'DELETE',
      entity: 'Patient',
      entityId: id,
      summary: `Deleted patient MRN ${deleted.mrn}`,
    });
    return { ok: true };
  });
}
