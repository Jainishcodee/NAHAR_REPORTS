import type { FastifyRequest } from 'fastify';
import { prisma } from './prisma.js';
import type { AuditAction } from './constants.js';

interface AuditInput {
  action: AuditAction;
  entity: 'Patient' | 'Report' | 'User' | 'Auth';
  entityId?: string | null;
  summary?: string;
  actorId?: string | null;
  ipAddress?: string | null;
}

/**
 * Append a row to the audit trail. Fire-and-forget — auditing must never break
 * the request, but failures are logged so they don't pass silently.
 */
export async function audit(input: AuditInput): Promise<void> {
  try {
    await prisma.auditLog.create({
      data: {
        action: input.action,
        entity: input.entity,
        entityId: input.entityId ?? null,
        summary: input.summary ?? null,
        actorId: input.actorId ?? null,
        ipAddress: input.ipAddress ?? null,
      },
    });
  } catch (err) {
    console.error('[audit] failed to write audit log entry', err);
  }
}

/** Convenience wrapper that pulls actor + IP off an authenticated request. */
export function auditFromRequest(
  req: FastifyRequest,
  input: Omit<AuditInput, 'actorId' | 'ipAddress'>,
): Promise<void> {
  return audit({
    ...input,
    actorId: req.user?.sub ?? null,
    ipAddress: req.ip ?? null,
  });
}
