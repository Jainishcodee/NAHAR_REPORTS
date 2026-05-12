# Clinic Report Manager

A Windows desktop application for a medical company: manage patients, create
medical reports, and generate **PDF reports** that are easy to share (save to a
shared folder / USB, email, print). Built so several clinic PCs can work off one
central database on the local network.

> **Status:** scaffold — a working skeleton with auth, patients, reports, an
> audit trail, a styled PDF template and a real "Export PDF" flow. Fill in the
> rest of your domain logic on top of it.

## Tech stack

| Layer | Choice |
|---|---|
| Desktop shell | **Electron** (packaged to a Windows `.exe` with **electron-builder**) |
| UI | **React + TypeScript + Vite** ([electron-vite](https://electron-vite.org)) + **Mantine** |
| PDF generation | **Chromium `webContents.printToPDF`** rendering a styled HTML template — no extra PDF library |
| Backend | **Fastify** API service (runs on one "server" PC; workstations connect over the LAN) |
| Database | **Prisma ORM** — SQLite for development, **PostgreSQL** for production |
| Auth | JWT (`@fastify/jwt`), Argon2 password hashing, role-based access (`ADMIN` / `DOCTOR` / `STAFF`) |
| Compliance basics | Append-only **audit log** of every create/read/update/delete/login/PDF-export |

```
report_software/
├─ apps/
│  ├─ api/        Fastify + Prisma backend (the "server")
│  └─ desktop/    Electron + React app (the workstation client) → builds the .exe
└─ package.json   npm workspaces + root scripts
```

## Prerequisites

- **Node.js 20+** (tested on 22)
- Windows 10/11 to build the `.exe` (electron-builder targets the host OS)

## Quick start (development)

From the repo root:

```bash
npm install

# 1) configure the API
copy apps\api\.env.example apps\api\.env        # PowerShell: Copy-Item apps\api\.env.example apps\api\.env
# (the default uses a local SQLite file — nothing else to install)

# 2) create the database and load demo data
npm run db:migrate -w @report/api -- --name init
npm run db:seed -w @report/api

# 3) run the API + the desktop app together
npm run dev
```

Then log in with the seeded admin account:

- **Email:** `admin@clinic.local`
- **Password:** `admin1234`  ← change this immediately in a real deployment

(There is also `dr.rao@clinic.local` / `doctor1234`.)

You'll land on the Dashboard with one sample patient and one sample report. Open
the report → **Preview** shows exactly what the PDF will look like → **Export
PDF** renders it and lets you choose where to save.

### Useful root scripts

| Command | What it does |
|---|---|
| `npm run dev` | runs the API and the Electron app together (hot reload) |
| `npm run dev:api` / `npm run dev:desktop` | run just one side |
| `npm run db:migrate` | create/apply a Prisma migration (dev) |
| `npm run db:seed` | seed the demo admin/patient/report |
| `npm run db:studio` | open Prisma Studio to browse/edit data, manage users |
| `npm run typecheck` | typecheck both apps |
| `npm run build` | production build of both apps |

## Building the Windows `.exe`

```bash
npm run package -w @report/desktop
```

Output lands in **`apps/desktop/release/`**:

- `Clinic Report Manager Setup <version>.exe` — NSIS installer (Start-menu &
  desktop shortcuts, choose install location)
- `Clinic Report Manager <version>.exe` — single-file **portable** build (no
  install; good for running off a USB stick)

Add a `build/icon.ico` and uncomment `win.icon` in
`apps/desktop/electron-builder.yml` for a custom icon. For silent auto-updates
across clinic PCs later, add `electron-updater` and point `publish` at a shared
folder or a tiny update server.

## Running it in a clinic (production sketch)

1. **Server PC** — install PostgreSQL, create a database & user, then in
   `apps/api/.env` set
   `DATABASE_URL="postgresql://USER:PASS@SERVER-IP:5432/report_db?schema=public"`
   and change `provider` in `apps/api/prisma/schema.prisma` to `postgresql`.
   Run `npm run build -w @report/api`, `npx prisma migrate deploy -w @report/api`,
   then `npm start -w @report/api` (use a service wrapper like NSSM / PM2 / a
   Windows Service so it stays up). Open TCP port `4000` on the LAN.
2. **Each workstation** — run the installer `.exe`. On first launch click
   *"Change server address"* on the login screen and enter
   `http://SERVER-IP:4000`. Also fill in **Settings → Clinic details** (these
   print on every PDF).
3. **Users & passwords** — create staff accounts (currently via
   `npm run db:studio -w @report/api`; an in-app admin screen is a natural next
   feature). Passwords are Argon2-hashed.

### Before going live with real patient data

This scaffold gives you the *shape* of a compliant app, not a finished one. At
minimum, add: TLS between client and server, disk encryption on the DB machine,
automated encrypted backups, password-policy + change-password UI, session
timeout, and review your jurisdiction's rules (HIPAA / India DPDP Act 2023 /
GDPR — retention, consent, breach handling). The audit log is already there;
make sure it is backed up and tamper-evident.

## How PDF generation works

`apps/desktop/src/shared/reportHtml.ts` is a pure function that turns a report +
clinic info into a complete, self-contained HTML document (A4 `@page` rules,
inline CSS, header/footer, draft watermark). It's used in two places:

- the **renderer** shows it in an `<iframe srcDoc>` for a live preview, and
- the **main process** (`apps/desktop/src/main/pdf.ts`) loads it into a hidden
  window and calls `webContents.printToPDF({ preferCSSPageSize: true })`, then
  shows a save dialog and writes the file. The renderer is told the saved path
  so it records an `EXPORT_PDF` entry in the audit log.

To restyle the PDF, edit `reportHtml.ts` — that's the single source of truth for
both the preview and the exported file. Add a logo by inlining a base64 image in
the header.

## API surface (all under `/api`, JWT-protected except `/auth/login` and `/health`)

```
POST   /auth/login                 → { token, user }
GET    /auth/me                     → { user }
GET    /patients?search=            → list/search patients
POST   /patients                    → create
GET    /patients/:id                → patient + their reports
PUT    /patients/:id                → update
DELETE /patients/:id                → delete (ADMIN)
GET    /reports?patientId=          → list reports
POST   /reports                     → create (DRAFT)
GET    /reports/:id                  → full report (data parsed)
PUT    /reports/:id                  → update content / status (FINAL stamps finalizedAt)
POST   /reports/:id/pdf-exported     → record a PDF export (audit + pdfPath)
DELETE /reports/:id                  → delete (ADMIN, DOCTOR)
```

## Ideas for next steps

- In-app user management (create/disable users, change password, view audit log)
- More report types & templates; per-type structured fields
- Attach images/scans to reports (radiology)
- Digitally sign PDFs (PDF/A) for archival
- One-click "email this report" via SMTP from the server
- `electron-updater` auto-updates from a shared folder
