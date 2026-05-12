"""Small helpers around the SQLite rows (dates, ages, display names)."""
from datetime import date, datetime


def calculate_age(dob_iso):
    """Years between `dob_iso` ('YYYY-MM-DD' or ISO datetime) and today, or None."""
    if not dob_iso:
        return None
    try:
        dob = datetime.strptime(str(dob_iso)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def fmt_date(iso, with_time=False):
    """Format an ISO date/datetime string as e.g. '12 May 2026' (or with time)."""
    if not iso:
        return ""
    s = str(iso)
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return s
    return dt.strftime("%d %b %Y, %H:%M" if with_time else "%d %b %Y")


def patient_name(row):
    """Full name from a patient (or report-with-patient) row."""
    try:
        first = row["first_name"]
        last = row["last_name"]
    except (KeyError, IndexError):
        first = row["p_first"]
        last = row["p_last"]
    return f"{first or ''} {last or ''}".strip()
