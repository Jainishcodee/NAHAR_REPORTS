import Fastify from 'fastify';
import cors from '@fastify/cors';
import { env } from './env.js';
import { authPlugin } from './auth.js';
import { authRoutes } from './routes/auth.js';
import { patientRoutes } from './routes/patients.js';
import { reportRoutes } from './routes/reports.js';

export async function buildServer() {
  const app = Fastify({
    logger: {
      level: env.NODE_ENV === 'development' ? 'info' : 'warn',
      transport:
        env.NODE_ENV === 'development'
          ? { target: 'pino-pretty', options: { translateTime: 'HH:MM:ss', ignore: 'pid,hostname' } }
          : undefined,
    },
  });

  await app.register(cors, {
    // The packaged Electron app loads from file:// (Origin is "null" or absent),
    // which @fastify/cors allows when origin is a function returning true for it.
    origin: (origin, cb) => {
      if (!origin || origin === 'null' || origin === env.CORS_ORIGIN) return cb(null, true);
      cb(null, false);
    },
  });

  await app.register(authPlugin);

  app.get('/health', async () => ({ ok: true, time: new Date().toISOString() }));

  await app.register(authRoutes, { prefix: '/api' });
  await app.register(patientRoutes, { prefix: '/api' });
  await app.register(reportRoutes, { prefix: '/api' });

  return app;
}
