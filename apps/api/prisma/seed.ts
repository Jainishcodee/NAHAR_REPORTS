/**
 * Seed script — creates a default admin and a couple of sample patients/reports
 * so the desktop app has something to show on first run.
 *
 *   npm run db:seed   (from the repo root, or `npm run db:seed -w @report/api`)
 */
import 'dotenv/config'; // load apps/api/.env so DATABASE_URL is available
import { PrismaClient } from '@prisma/client';
import argon2 from 'argon2';

const prisma = new PrismaClient();

async function main() {
  const adminEmail = 'admin@clinic.local';
  const admin = await prisma.user.upsert({
    where: { email: adminEmail },
    update: {},
    create: {
      email: adminEmail,
      fullName: 'Clinic Administrator',
      role: 'ADMIN',
      passwordHash: await argon2.hash('admin1234'),
    },
  });
  console.log(`✓ Admin user: ${adminEmail} / admin1234  (change this!)`);

  const doctor = await prisma.user.upsert({
    where: { email: 'dr.rao@clinic.local' },
    update: {},
    create: {
      email: 'dr.rao@clinic.local',
      fullName: 'Dr. A. Rao',
      role: 'DOCTOR',
      passwordHash: await argon2.hash('doctor1234'),
    },
  });

  const patient = await prisma.patient.upsert({
    where: { mrn: 'MRN-0001' },
    update: {},
    create: {
      mrn: 'MRN-0001',
      firstName: 'Asha',
      lastName: 'Verma',
      dateOfBirth: new Date('1988-04-12'),
      sex: 'F',
      phone: '+91 98765 43210',
      email: 'asha.verma@example.com',
      address: '14 MG Road, Pune 411001',
    },
  });

  const existing = await prisma.report.findFirst({ where: { reportNo: 'RPT-2026-000001' } });
  if (!existing) {
    await prisma.report.create({
      data: {
        reportNo: 'RPT-2026-000001',
        type: 'LAB',
        title: 'Complete Blood Count (CBC)',
        status: 'FINAL',
        finalizedAt: new Date(),
        patientId: patient.id,
        authorId: doctor.id,
        data: JSON.stringify({
          summary: 'All parameters within normal reference ranges. No action required.',
          sections: [
            {
              heading: 'Haematology',
              table: {
                columns: ['Test', 'Result', 'Unit', 'Reference range'],
                rows: [
                  ['Haemoglobin', '13.4', 'g/dL', '12.0 – 15.5'],
                  ['WBC count', '6.8', '10^3/µL', '4.0 – 11.0'],
                  ['Platelet count', '247', '10^3/µL', '150 – 450'],
                  ['Haematocrit', '40.1', '%', '36 – 46'],
                ],
              },
            },
            {
              heading: 'Comments',
              text: 'Specimen collected fasting. Reviewed and verified by Dr. A. Rao.',
            },
          ],
        }),
      },
    });
    console.log('✓ Sample report RPT-2026-000001 created');
  }

  console.log(`✓ Seed complete (admin id: ${admin.id})`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
