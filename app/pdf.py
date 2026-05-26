"""Render a report to HTML, and from there to PDF / printer.

The on-screen preview and the PDF/print output all come from the same HTML,
so what you see is what you get. PDF generation uses Qt's built-in
QTextDocument -> QPrinter pipeline, so there is no extra dependency.
"""
import html as _html
from datetime import datetime

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from app.models import calculate_age, fmt_date


# ---------------------------------------------------------------- helpers
def _esc(value):
    return _html.escape(str(value)) if value not in (None, "") else ""


def _row_get(row, key, default=""):
    try:
        v = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return v if v not in (None, "") else default


def _content_html(text):
    if not text or not str(text).strip():
        return '<p style="color:#888;">&mdash; no content &mdash;</p>'
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    parts = [p for p in text.split("\n\n")]
    out = []
    for p in parts:
        if p.strip() == "":
            continue
        out.append("<p>" + _esc(p).replace("\n", "<br/>") + "</p>")
    return "\n".join(out) if out else '<p style="color:#888;">&mdash; no content &mdash;</p>'


# Flag -> text colour for the result + reference cells in tabular reports.
_FLAG_COLOR = {
    "Low": "#1d4ed8",       # blue
    "High": "#b91c1c",      # red
    "Abnormal": "#b91c1c",  # red (qualitative mismatch)
}


def _tabular_body_html(test_rows):
    """Image-2-style table: Investigation | Result | Reference | Unit.

    Section names from `templates.py` become coloured full-width header rows.
    Abnormal rows tint the Result and Reference cells; the flag word is shown
    as a bold prefix in the Reference cell.
    """
    if not test_rows:
        return ""
    parts = [
        '<table width="100%" cellspacing="0" cellpadding="6" border="0">',
        '<tr>'
        '<th align="left" width="40%" bgcolor="#f4f6f9" '
        'style="color: #14315a; font-size: 10pt;">Investigation</th>'
        '<th align="left" width="20%" bgcolor="#f4f6f9" '
        'style="color: #14315a; font-size: 10pt;">Result</th>'
        '<th align="left" width="25%" bgcolor="#f4f6f9" '
        'style="color: #14315a; font-size: 10pt;">Reference Value</th>'
        '<th align="left" width="15%" bgcolor="#f4f6f9" '
        'style="color: #14315a; font-size: 10pt;">Unit</th>'
        '</tr>',
        '<tr><td colspan="4" bgcolor="#14315a" height="2"></td></tr>',
    ]
    current_section = None
    for r in test_rows:
        # accept both sqlite3.Row and plain dict
        section = (r["section"] if "section" in r.keys() else r.get("section")) if hasattr(r, "keys") else r.get("section")
        section = section or ""
        if section != current_section:
            current_section = section
            if section:
                parts.append(
                    f'<tr><td colspan="4" bgcolor="#eef2f7" '
                    f'style="font-weight: bold; color: #14315a; font-size: 10pt;">'
                    f'{_esc(section)}</td></tr>'
                )
        param = _row_get(r, "parameter")
        value = _row_get(r, "value")
        unit = _row_get(r, "unit")
        reference = _row_get(r, "reference")
        flag = _row_get(r, "flag")

        colour = _FLAG_COLOR.get(flag, "")
        value_style = (
            f'color: {colour}; font-weight: 600;' if colour else 'font-weight: 600;'
        )
        ref_style = f'color: {colour};' if colour else 'color: #5a6573;'
        flag_prefix = (
            f'<b>{_esc(flag)}</b>&nbsp;&nbsp;' if flag in ("Low", "High", "Abnormal") else ''
        )
        parts.append(
            f'<tr>'
            f'<td><b>{_esc(param)}</b></td>'
            f'<td style="{value_style}">{_esc(value)}</td>'
            f'<td style="{ref_style}">{flag_prefix}{_esc(reference)}</td>'
            f'<td style="color: #5a6573;">{_esc(unit)}</td>'
            f'</tr>'
        )
        description = _row_get(r, "description")
        if description and str(description).strip():
            parts.append(
                f'<tr><td colspan="4" '
                f'style="padding: 0 6px 8px 24px; color: #5a6573; '
                f'font-style: italic; font-size: 9.5pt;">'
                f'↳ {_esc(description)}</td></tr>'
            )
    parts.append('</table>')
    return "".join(parts)


def _age_sex(report):
    age = calculate_age(_row_get(report, "p_dob", None))
    sex = _row_get(report, "p_sex")
    if age is not None and sex:
        return f"{age} yrs / {sex}"
    if age is not None:
        return f"{age} yrs"
    return sex or "—"


# ---------------------------------------------------------------- HTML
def render_report_html(report, settings, test_rows=None):
    """Build the report HTML. If `test_rows` is non-empty, render the tabular
    body (image-2 style); otherwise fall back to the free-text content."""
    clinic_name = _row_get(settings, "clinic_name", "Diagnostic Centre")
    address = _row_get(settings, "address")
    phone = _row_get(settings, "phone")
    email = _row_get(settings, "email")
    logo = _row_get(settings, "logo_path")

    full_name = f'{_row_get(report, "p_first")} {_row_get(report, "p_last")}'.strip() or "—"
    title_text = (_row_get(report, "title") or _row_get(report, "report_type_name")
                  or "Medical Report").upper()
    status = _row_get(report, "status", "Draft")
    is_draft = status.lower() != "final"

    logo_html = f'<img src="{_esc(logo)}" height="54" />' if logo else "&nbsp;"
    contact_bits = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(
        b for b in [_esc(address), ("Ph: " + _esc(phone)) if phone else "", _esc(email)] if b
    )

    impression = _row_get(report, "impression")
    impression_html = ""
    if impression and str(impression).strip():
        impression_html = (
            '<p class="section-h">IMPRESSION / CONCLUSION</p>' + _content_html(impression)
        )

    reported_by = _esc(_row_get(report, "reported_by")) or "&nbsp;"
    draft_banner = (
        '<p class="draft">DRAFT &mdash; not finalised</p>' if is_draft else ""
    )
    footer_note = ("This is an electronically generated report &mdash; verify with the "
                   "laboratory before clinical use." if is_draft
                   else "This is an electronically generated report.")

    if test_rows:
        body_html = _tabular_body_html(test_rows)
    else:
        body_html = (
            '<p class="section-h">FINDINGS / REPORT</p>'
            + _content_html(_row_get(report, "content"))
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a1a; font-size: 11pt; }}
.clinic {{ font-size: 19pt; font-weight: bold; color: #14315a; }}
.contact {{ font-size: 9pt; color: #555555; }}
hr.rule {{ border: 0; border-top: 2px solid #14315a; }}
td {{ vertical-align: top; padding: 2px 4px; }}
.meta td {{ font-size: 10pt; }}
.label {{ color: #666666; }}
.title {{ text-align: center; font-size: 14pt; font-weight: bold; letter-spacing: 1px;
          padding: 6px 0; border-top: 1px solid #bbbbbb; border-bottom: 1px solid #bbbbbb; }}
.section-h {{ font-weight: bold; color: #14315a; font-size: 11pt; }}
p {{ margin: 4px 0; line-height: 140%; }}
.sign td {{ vertical-align: bottom; }}
.sign .line {{ border-top: 1px solid #333333; font-size: 9pt; color: #555555; }}
.footer {{ border-top: 1px solid #cccccc; font-size: 8.5pt; color: #777777; text-align: center; }}
.draft {{ color: #b00000; font-weight: bold; font-size: 10pt; }}
</style></head><body>

<table width="100%"><tr>
  <td width="40%">{logo_html}</td>
  <td width="60%" align="right">
    <div class="clinic">{_esc(clinic_name)}</div>
    <div class="contact">{contact_bits}</div>
  </td>
</tr></table>
<hr class="rule"/>

<table class="meta" width="100%"><tr>
  <td width="56%">
    <span class="label">Patient&nbsp;Name:</span>&nbsp; <b>{_esc(full_name)}</b><br/>
    <span class="label">Patient&nbsp;ID:</span>&nbsp; {_esc(_row_get(report, "p_mrn")) or "—"}<br/>
    <span class="label">Age&nbsp;/&nbsp;Sex:</span>&nbsp; {_esc(_age_sex(report))}
  </td>
  <td width="44%">
    <span class="label">Report&nbsp;No:</span>&nbsp; <b>{_esc(_row_get(report, "report_no")) or "—"}</b><br/>
    <span class="label">Report&nbsp;Date:</span>&nbsp; {_esc(fmt_date(_row_get(report, "report_date"))) or "—"}<br/>
    <span class="label">Referring&nbsp;Doctor:</span>&nbsp; {_esc(_row_get(report, "referring_doctor")) or "—"}
  </td>
</tr></table>
{draft_banner}

<p class="title">{_esc(title_text)}</p>

{body_html}

{impression_html}

<br/><br/>
<table class="sign" width="100%"><tr>
  <td width="55%">&nbsp;</td>
  <td width="45%" align="right">
    <br/><br/><br/>
    <div class="line">{reported_by}<br/>(Signature &amp; Stamp)</div>
  </td>
</tr></table>

<br/>
<p class="footer">{footer_note}<br/>Printed: {_esc(datetime.now().strftime("%d %b %Y, %H:%M"))}</p>

</body></html>"""


# ---------------------------------------------------------------- PDF / print
def _make_printer(output_path=None):
    printer = QPrinter(QPrinter.HighResolution)
    if output_path:
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(output_path))
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setPageMargins(QMarginsF(15, 14, 15, 14), QPageLayout.Millimeter)
    return printer


def _document(report, settings, test_rows=None):
    doc = QTextDocument()
    doc.setHtml(render_report_html(report, settings, test_rows))
    return doc


def export_report_pdf(report, settings, output_path, test_rows=None):
    """Write the report to `output_path` as a PDF. Raises on failure."""
    printer = _make_printer(output_path)
    _document(report, settings, test_rows).print_(printer)


def print_report(report, settings, parent=None, test_rows=None):
    """Show the system print dialog and print the report. Returns True if printed."""
    printer = _make_printer()
    dialog = QPrintDialog(printer, parent)
    if dialog.exec() != QPrintDialog.Accepted:
        return False
    _document(report, settings, test_rows).print_(printer)
    return True


def default_pdf_name(report):
    raw = f'{_row_get(report, "report_no", "report")}_{_row_get(report, "p_first")}_{_row_get(report, "p_last")}'
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in raw).strip("_")
    return (safe or "report") + ".pdf"
