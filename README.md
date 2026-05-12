# Clinic Report Manager

A small **single-PC desktop app** (Python + PySide6) for a clinic / diagnostic
centre to create, store and export **medical reports**.

Workflow: pick an existing patient (or create a new one) → choose a report type
(MRI, CT, X-Ray, CBC, Lipid Profile, …) → paste the raw findings text → **Submit**.
You get a finished report you can preview on screen, **export to PDF**, or **print**.

All data is stored locally in `data/clinic.db` (SQLite). There is no server, no
LAN database, and no cloud — everything runs on one machine.

---

## Requirements

- **Python 3.11+** (Windows / macOS / Linux)
- The Python packages in `requirements.txt` (just `PySide6`)

## Run it (development)

```bash
pip install -r requirements.txt
python main.py
```

On first launch the app creates `data/clinic.db` with a default set of report
types and placeholder clinic info — change the clinic name / address / phone /
email / logo under **Settings**.

## Where things live

| Path | What |
|---|---|
| `data/clinic.db` | the SQLite database (patients, reports, settings) — **back this file up** |
| `output/` | default folder offered when you export a PDF |
| `assets/` | put your clinic `logo.png` here, then select it in Settings |

> `data/` and `output/` are git-ignored — patient data must not be committed.

## Project layout

```
main.py                 entry point
app/
  config.py             paths, defaults, constants
  db.py                 SQLite schema + all data access
  models.py             small helpers (age from DOB, date formatting, …)
  pdf.py                report HTML + PDF export + print
  ui/
    main_window.py      sidebar + page stack
    home_page.py        dashboard
    patients_page.py    patient registry (list / add / edit / delete)
    new_report_page.py  the create / edit report flow
    reports_page.py     all reports (search / filter / view / delete)
    report_preview.py   on-screen report + Export PDF / Print
    settings_page.py    clinic info + report types
    patient_form.py     reusable patient form + dialog
    style.py            Qt style sheet
```

## Build a Windows .exe

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "ClinicReportManager" main.py
```

The app is then in `dist/ClinicReportManager/`. It keeps its `data/` and
`output/` folders next to the `.exe`. (Drop a `assets/icon.ico` and add
`--icon assets/icon.ico` for a custom icon.)

## Scope (v1)

- Report content is **free text** — you paste the raw data and it's typeset into
  the report. Per-type **structured templates** (e.g. a real CBC table with
  reference ranges and automatic High/Low flags) are a planned v2; the
  `report_types` table already leaves room for it.
- No user accounts / login (single PC, single operator).
- No cloud, no LAN, no auto-update.
