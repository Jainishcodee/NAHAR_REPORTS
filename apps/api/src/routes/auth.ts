import type { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { prisma } from '../prisma.js';
import { verifyPassword, type AuthTokenPayload } from '../auth.js';
import { audit } from '../audit.js';
import type { Role } from '../constants.js';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export async function authRoutes(app: FastifyInstance) {
  app.post('/auth/login', async (req, reply) => {
    const body = loginSchema.safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: 'Invalid request' });

    const user = await prisma.user.findUnique({ where: { email: body.data.email } });
    const ok = user?.isActive && (await verifyPassword(user.passwordHash, body.data.password));
    if (!user || !ok) {
      await audit({
        action: 'LOGIN',
        entity: 'Auth',
        summary: `Failed login for ${body.data.email}`,
        ipAddress: req.ip,
      });
      return reply.code(401).send({ error: 'Invalid email or password' });
    }

    const payload: AuthTokenPayload = {
      sub: user.id,
      email: user.email,
      role: user.role as Role,
      fullName: user.fullName,
    };
    const token = await reply.jwtSign(payload);

    await audit({
      action: 'LOGIN',
      entity: 'Auth',
      entityId: user.id,
      summary: `Login: ${user.email}`,
      actorId: user.id,
      ipAddress: req.ip,
    });

    return { token, user: payload };
  });

  // Returns the caller's identity (handy for the desktop app on startup).
  app.get('/auth/me', { preHandler: [app.authenticate] }, async (req) => {
    return { user: req.user };
  });
}
