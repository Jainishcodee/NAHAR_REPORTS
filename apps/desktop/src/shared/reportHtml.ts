// Pure function that turns a report + clinic info into a complete, self-contained
// HTML document (inline CSS, no external assets). Used in two places:
//   • the renderer shows it in an <iframe srcDoc> for a live preview
//   • the main process loads it into a hidden window and calls webContents.printToPDF
// Keep it dependency-free.

import type { ClinicInfo, ReportFull } from './types';

const esc = (s: unknown): string =>
  String(s ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

const fmtDate = (iso?: string | null): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? esc(iso)
    : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' });
};

const fmtDateTime = (iso?: string | null): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? esc(iso) : d.toLocaleString();
};

const yearsBetween = (dobIso: string, refIso: string): number | null => {
  const dob = new Date(dobIso);
  const ref = new Date(refIso);
  if (Number.isNaN(dob.getTime()) || Number.isNaN(ref.getTime())) return null;
  let age = ref.getFullYear() - dob.getFullYear();
  const m = ref.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && ref.getDate() < dob.getDate())) age--;
  return age;
};

const SEX_LABEL: Record<string, string> = { M: 'Male', F: 'Female', OTHER: 'Other' };
const STATUS_LABEL: Record<string, string> = {
  DRAFT: 'Draft — not finalised',
  FINAL: 'Final',
  AMENDED: 'Amended',
};

function sectionHtml(section: ReportFull['data']['sections'][number]): string {
  const parts: string[] = [`<h2 class="sec">${esc(section.heading)}</h2>`];
  if (section.text) parts.push(`<p class="sec-text">${esc(section.text).replace(/\n/g, '<br>')}</p>`);
  if (section.table) {
    const head = section.table.columns.map((c) => `<th>${esc(c)}</th>`).join('');
    const body = section.table.rows
      .map((row) => `<tr>${row.map((cell) => `<td>${esc(cell)}</td>`).join('')}</tr>`)
      .join('');
    parts.push(
      `<table class="data"><thead><tr>${head}</tr></thead><tbody>${body || `<tr><td colspan="${section.table.columns.length}" class="muted">No rows</td></tr>`}</tbody></table>`,
    );
  }
  return `<section class="block">${parts.join('')}</section>`;
}

export function buildReportHtml(report: ReportFull, clinic: ClinicInfo): string {
  const p = report.patient;
  const age = yearsBetween(p.dateOfBirth, report.reportDate);
  const draftWatermark =
    report.status === 'DRAFT'
      ? `<div class="watermark">DRAFT</div>`
      : report.status === 'AMENDED'
        ? `<div class="watermark amended">AMENDED</div>`
        : '';

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>${esc(report.reportNo)} — ${esc(report.title)}</title>
<style>
  @page { size: A4; margin: 16mm 14mm 18mm 14mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1a1f2b; font-size: 12px; line-height: 1.5;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .page { position: relative; padding: 0; }
  .watermark {
    position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
    font-size: 120px; font-weight: 800; color: rgba(220,38,38,0.08);
    transform: rotate(-30deg); pointer-events: none; z-index: 0; letter-spacing: 8px;
  }
  .watermark.amended { color: rgba(217,119,6,0.10); }
  header.clinic { display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 2px solid #0b6bcb; padding-bottom: 10px; margin-bottom: 14px; position: relative; z-index: 1; }
  .clinic-name { font-size: 18px; font-weight: 700; color: #0b6bcb; margin: 0 0 2px; }
  .clinic-meta { font-size: 10.5px; color: #4b5563; }
  .doc-title { text-align: right; }
  .doc-title .kind { font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: #6b7280; }
  .doc-title .title { font-size: 15px; font-weight: 700; max-width: 280px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 9.5px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px; }
  .badge.FINAL { background: #dcfce7; color: #166534; }
  .badge.DRAFT { background: #fef9c3; color: #854d0e; }
  .badge.AMENDED { background: #ffedd5; color: #9a3412; }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; margin: 0 0 16px;
    background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 14px; position: relative; z-index: 1; }
  .meta-grid .row { display: flex; gap: 8px; }
  .meta-grid .k { color: #6b7280; min-width: 120px; }
  .meta-grid .v { font-weight: 600; }
  h2.sec { font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.6px; color: #0b6bcb;
    border-bottom: 1px solid #dbeafe; padding-bottom: 3px; margin: 18px 0 8px; position: relative; z-index: 1; }
  .block { position: relative; z-index: 1; page-break-inside: avoid; }
  .sec-text { margin: 0 0 6px; }
  table.data { width: 100%; border-collapse: collapse; margin: 4px 0 10px; font-size: 11px; }
  table.data th { background: #eff6ff; text-align: left; padding: 6px 8px; border: 1px solid #cbd5e1; font-weight: 700; }
  table.data td { padding: 5px 8px; border: 1px solid #e2e8f0; }
  table.data tbody tr:nth-child(even) td { background: #f8fafc; }
  .muted { color: #9ca3af; }
  .summary { background: #f0f9ff; border-left: 4px solid #0b6bcb; padding: 8px 12px; border-radius: 0 6px 6px 0;
    margin: 0 0 14px; position: relative; z-index: 1; }
  .sign { margin-top: 36px; display: flex; justify-content: flex-end; position: relative; z-index: 1; page-break-inside: avoid; }
  .sign .box { width: 240px; text-align: center; }
  .sign .line { border-top: 1px solid #1a1f2b; margin-top: 40px; padding-top: 4px; font-size: 10.5px; }
  footer.foot { position: fixed; bottom: 6mm; left: 14mm; right: 14mm; border-top: 1px solid #e5e7eb;
    padding-top: 4px; font-size: 9px; color: #9ca3af; display: flex; justify-content: space-between; }
</style>
</head>
<body>
<div class="page">
  ${draftWatermark}
  <header class="clinic">
    <div>
      <p class="clinic-name">${esc(clinic.name)}</p>
      <div class="clinic-meta">
        ${clinic.addressLines.map((l) => esc(l)).join('<br>')}
        ${clinic.phone ? `<br>Tel: ${esc(clinic.phone)}` : ''}
        ${clinic.email ? ` &nbsp;|&nbsp; ${esc(clinic.email)}` : ''}
        ${clinic.website ? ` &nbsp;|&nbsp; ${esc(clinic.website)}` : ''}
        ${clinic.registrationNo ? `<br>Reg. No: ${esc(clinic.registrationNo)}` : ''}
      </div>
    </div>
    <div class="doc-title">
      <div class="kind">${esc(report.type.replace(/_/g, ' '))} report</div>
      <div class="title">${esc(report.title)}</div>
      <div style="margin-top:6px"><span class="badge ${esc(report.status)}">${esc(STATUS_LABEL[report.status] ?? report.status)}</span></div>
    </div>
  </header>

  <div class="meta-grid">
    <div class="row"><span class="k">Patient</span><span class="v">${esc(p.lastName)}, ${esc(p.firstName)}</span></div>
    <div class="row"><span class="k">Report No.</span><span class="v">${esc(report.reportNo)}</span></div>
    <div class="row"><span class="k">MRN</span><span class="v">${esc(p.mrn)}</span></div>
    <div class="row"><span class="k">Report date</span><span class="v">${fmtDate(report.reportDate)}</span></div>
    <div class="row"><span class="k">Date of birth</span><span class="v">${fmtDate(p.dateOfBirth)}${age != null ? ` (${age} yrs)` : ''}</span></div>
    <div class="row"><span class="k">Sex</span><span class="v">${esc(SEX_LABEL[p.sex] ?? p.sex)}</span></div>
    <div class="row"><span class="k">Referring / Author</span><span class="v">${esc(report.author.fullName)}</span></div>
    <div class="row"><span class="k">Finalised</span><span class="v">${fmtDateTime(report.finalizedAt)}</span></div>
  </div>

  ${report.data.summary ? `<div class="summary"><strong>Summary:</strong> ${esc(report.data.summary).replace(/\n/g, '<br>')}</div>` : ''}

  ${report.data.sections.map(sectionHtml).join('\n')}

  <div class="sign">
    <div class="box">
      <div class="line">${esc(report.author.fullName)}<br><span class="muted">${esc(report.author.email)}</span></div>
    </div>
  </div>
</div>
<footer class="foot">
  <span>${esc(clinic.name)} — ${esc(report.reportNo)}</span>
  <span>This report was generated electronically on ${esc(new Date().toLocaleString())}.</span>
</footer>
</body>
</html>`;
}
