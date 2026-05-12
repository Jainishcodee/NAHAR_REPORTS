import fp from 'fastify-plugin';
import fastifyJwt from '@fastify/jwt';
import argon2 from 'argon2';
import type { FastifyReply, FastifyRequest } from 'fastify';
import { env } from './env.js';
import type { Role } from './constants.js';

/** Shape of the data we put inside the signed token. */
export interface AuthTokenPayload {
  sub: string; // user id
  email: string;
  role: Role;
  fullName: string;
}

declare module 'fastify' {
  interface FastifyInstance {
    /** Pre-handler: rejects the request with 401 unless a valid token is present. */
    authenticate: (req: FastifyRequest, reply: FastifyReply) => Promise<void>;
    /** Pre-handler factory: requires the caller to have one of the given roles. */
    requireRole: (
      ...roles: Role[]
    ) => (req: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: AuthTokenPayload;
    user: AuthTokenPayload;
  }
}

export const hashPassword = (plain: string) => argon2.hash(plain);
export const verifyPassword = (hash: string, plain: string) => argon2.verify(hash, plain);

export const authPlugin = fp(async (app) => {
  app.register(fastifyJwt, {
    secret: env.JWT_SECRET,
    sign: { expiresIn: '12h' },
  });

  app.decorate('authenticate', async (req: FastifyRequest, reply: FastifyReply) => {
    try {
      await req.jwtVerify();
    } catch {
      return reply.code(401).send({ error: 'Authentication required' });
    }
  });

  app.decorate('requireRole', (...roles: Role[]) => {
    return async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        await req.jwtVerify();
      } catch {
        return reply.code(401).send({ error: 'Authentication required' });
      }
      if (!roles.includes(req.user.role)) {
        return reply.code(403).send({ error: 'Insufficient permissions' });
      }
    };
  });
});
