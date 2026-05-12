import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { prisma } from '../prisma.js';
import { auditFromRequest } from '../audit.js';
import { REPORT_TYPES, REPORT_STATUSES } from '../constants.js';

// Structured report body. `data` is intentionally generic so new report
// layouts don't need DB migrations — the desktop app renders it to PDF.
const reportData = z.object({
  summary: z.string().max(4000).optional(),
  sections: z
    .array(
      z.object({
        heading: z.string().min(1).max(200),
        text: z.string().max(8000).optional(),
        table: z
          .object({
            columns: z.array(z.string()).min(1),
            rows: z.array(z.array(z.string())),
          })
          .optional(),
      }),
    )
    .default([]),
});

const reportInput = z.object({
  patientId: z.string().min(1),
  type: z.enum(REPORT_TYPES),
  title: z.string().trim().min(1).max(200),
  reportDate: z.coerce.date().optional(),
  data: reportData,
});

async function nextReportNo(): Promise<string> {
  const year = new Date().getFullYear();
  const prefix = `RPT-${year}-`;
  const last = await prisma.report.findFirst({
    where: { reportNo: { startsWith: prefix } },
    orderBy: { reportNo: 'desc' },
    select: { reportNo: true },
  });
  const seq = last ? Number(last.reportNo.slice(prefix.length)) + 1 : 1;
  return `${prefix}${String(seq).padStart(6, '0')}`;
}

export async function reportRoutes(app: FastifyInstance) {
  app.addHook('preHandler', app.authenticate);

  // List recent reports (optionally filter by patient).
  app.get('/reports', async (req) => {
    const q = z.object({ patientId: z.string().optional() }).parse(req.query);
    const reports = await prisma.report.findMany({
      where: q.patientId ? { patientId: q.patientId } : {},
      orderBy: { reportDate: 'desc' },
      take: 200,
      include: { patient: { select: { id: true, mrn: true, firstName: true, lastName: true } } },
    });
    return { reports };
  });

  // Get one full report (the desktop app uses this to render the PDF).
  app.get('/reports/:id', async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const report = await prisma.report.findUnique({
      where: { id },
      include: { patient: true, author: { select: { id: true, fullName: true, email: true } } },
    });
    if (!report) return reply.code(404).send({ error: 'Report not found' });
    await auditFromRequest(req, { action: 'READ', entity: 'Report', entityId: id });
    return { report: { ...report, data: JSON.parse(report.data) } };
  });

  // Create a report (status DRAFT).
  app.post('/reports', async (req, reply) => {
    const body = reportInput.safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: 'Invalid request', details: body.error.flatten() });

    const patient = await prisma.patient.findUnique({ where: { id: body.data.patientId } });
    if (!patient) return reply.code(404).send({ error: 'Patient not found' });

    const report = await prisma.report.create({
      data: {
        reportNo: await nextReportNo(),
        type: body.data.type,
        title: body.data.title,
        status: 'DRAFT',
        data: JSON.stringify(body.data.data),
        reportDate: body.data.reportDate ?? new Date(),
        patientId: patient.id,
        authorId: req.user.sub,
      },
    });
    await auditFromRequest(req, {
      action: 'CREATE',
      entity: 'Report',
      entityId: report.id,
      summary: `Created ${report.reportNo} for MRN ${patient.mrn}`,
    });
    return reply.code(201).send({ report: { ...report, data: JSON.parse(report.data) } });
  });

  // Update report content / status. Finalising stamps finalizedAt.
  app.put('/reports/:id', async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const body = z
      .object({
        title: z.string().trim().min(1).max(200).optional(),
        type: z.enum(REPORT_TYPES).optional(),
        status: z.enum(REPORT_STATUSES).optional(),
        reportDate: z.coerce.date().optional(),
        data: reportData.optional(),
      })
      .safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: 'Invalid request', details: body.error.flatten() });

    const current = await prisma.report.findUnique({ where: { id } });
    if (!current) return reply.code(404).send({ error: 'Report not found' });

    const report = await prisma.report.update({
      where: { id },
      data: {
        title: body.data.title,
        type: body.data.type,
        status: body.data.status,
        reportDate: body.data.reportDate,
        data: body.data.data ? JSON.stringify(body.data.data) : undefined,
        finalizedAt:
          body.data.status === 'FINAL' && current.status !== 'FINAL' ? new Date() : undefined,
      },
    });
    await auditFromRequest(req, {
      action: 'UPDATE',
      entity: 'Report',
      entityId: id,
      summary: `Updated ${report.reportNo}${body.data.status ? ` → ${body.data.status}` : ''}`,
    });
    return { report: { ...report, data: JSON.parse(report.data) } };
  });

  // Record that a PDF was exported (called by the desktop app after saving).
  app.post('/reports/:id/pdf-exported', async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const { pdfPath } = z.object({ pdfPath: z.string().min(1) }).parse(req.body);
    const report = await prisma.report.update({ where: { id }, data: { pdfPath } }).catch(() => null);
    if (!report) return reply.code(404).send({ error: 'Report not found' });
    await auditFromRequest(req, {
      action: 'EXPORT_PDF',
      entity: 'Report',
      entityId: id,
      summary: `Exported PDF of ${report.reportNo} to ${pdfPath}`,
    });
    return { ok: true };
  });

  // Delete a report (ADMIN or DOCTOR).
  app.delete('/reports/:id', { preHandler: app.requireRole('ADMIN', 'DOCTOR') }, async (req, reply) => {
    const { id } = z.object({ id: z.string() }).parse(req.params);
    const deleted = await prisma.report.delete({ where: { id } }).catch(() => null);
    if (!deleted) return reply.code(404).send({ error: 'Report not found' });
    await auditFromRequest(req, {
      action: 'DELETE',
      entity: 'Report',
      entityId: id,
      summary: `Deleted ${deleted.reportNo}`,
    });
    return { ok: true };
  });
}
