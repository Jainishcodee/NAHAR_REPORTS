import { buildServer } from './server.js';
import { env } from './env.js';
import { prisma } from './prisma.js';

const app = await buildServer();

try {
  await app.listen({ port: env.PORT, host: env.HOST });
  app.log.info(`API ready — clinic workstations connect to http://<this-pc-ip>:${env.PORT}`);
} catch (err) {
  app.log.error(err);
  process.exit(1);
}

for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.on(signal, async () => {
    app.log.info(`${signal} received, shutting down`);
    await app.close();
    await prisma.$disconnect();
    process.exit(0);
  });
}
