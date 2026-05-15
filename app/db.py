"""SQLite storage layer: schema creation, seeding, and all data access.

Single-file local database. No server. No network. The whole app talks to
one `Database` instance held by the main window.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import DB_PATH, DEFAULT_REPORT_TYPES, DEFAULT_CLINIC


SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    mrn              TEXT UNIQUE,
    first_name       TEXT NOT NULL,
    last_name        TEXT NOT NULL DEFAULT '',
    dob              TEXT,
    sex              TEXT,
    phone            TEXT,
    email            TEXT,
    address          TEXT,
    referring_doctor TEXT,
    notes            TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_types (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    code      TEXT UNIQUE NOT NULL,
    name      TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_no        TEXT UNIQUE,
    patient_id       INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    report_type_id   INTEGER REFERENCES report_types(id),
    report_type_name TEXT,
    title            TEXT,
    referring_doctor TEXT,
    content          TEXT,
    impression       TEXT,
    reported_by      TEXT,
    status           TEXT NOT NULL DEFAULT 'Draft',
    report_date      TEXT,
    pdf_path         TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    clinic_name TEXT,
    address     TEXT,
    phone       TEXT,
    email       TEXT,
    logo_path   TEXT
);

CREATE TABLE IF NOT EXISTS test_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id  INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section    TEXT,
    parameter  TEXT NOT NULL,
    value      TEXT,
    unit       TEXT,
    reference  TEXT,
    flag       TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date);
CREATE INDEX IF NOT EXISTS idx_test_results_report ON test_results(report_id);
"""

# Columns the UI is allowed to update on an existing report.
_REPORT_UPDATE_COLS = (
    "report_type_id", "report_type_name", "title", "referring_doctor",
    "content", "impression", "reported_by", "status", "report_date",
)


class Database:
    def __init__(self, path=None):
        self.path = str(path or DB_PATH)
        self._init_schema()

    # ------------------------------------------------------------------ core
    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="seconds")

    def _init_schema(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            if conn.execute("SELECT COUNT(*) AS c FROM report_types").fetchone()["c"] == 0:
                conn.executemany(
                    "INSERT INTO report_types (code, name) VALUES (?, ?)", DEFAULT_REPORT_TYPES
                )
            if conn.execute("SELECT COUNT(*) AS c FROM settings").fetchone()["c"] == 0:
                conn.execute(
                    "INSERT INTO settings (id, clinic_name, address, phone, email, logo_path) "
                    "VALUES (1, ?, ?, ?, ?, ?)",
                    (DEFAULT_CLINIC["clinic_name"], DEFAULT_CLINIC["address"],
                     DEFAULT_CLINIC["phone"], DEFAULT_CLINIC["email"], DEFAULT_CLINIC["logo_path"]),
                )

    # -------------------------------------------------------------- settings
    def get_settings(self):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()

    def update_settings(self, clinic_name, address, phone, email, logo_path):
        with self.connect() as conn:
            conn.execute(
                "UPDATE settings SET clinic_name=?, address=?, phone=?, email=?, logo_path=? WHERE id=1",
                (clinic_name, address, phone, email, logo_path),
            )

    # ---------------------------------------------------------- report types
    def get_report_types(self, active_only=True):
        q = "SELECT * FROM report_types"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY name COLLATE NOCASE"
        with self.connect() as conn:
            return conn.execute(q).fetchall()

    def add_report_type(self, code, name):
        with self.connect() as conn:
            conn.execute("INSERT INTO report_types (code, name) VALUES (?, ?)",
                         (code.strip().upper(), name.strip()))

    def update_report_type(self, type_id, name):
        with self.connect() as conn:
            conn.execute("UPDATE report_types SET name=? WHERE id=?", (name.strip(), type_id))

    def set_report_type_active(self, type_id, active):
        with self.connect() as conn:
            conn.execute("UPDATE report_types SET is_active=? WHERE id=?",
                         (1 if active else 0, type_id))

    # --------------------------------------------------------------- patients
    def add_patient(self, **f):
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO patients
                   (first_name, last_name, dob, sex, phone, email, address, referring_doctor, notes, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (f.get("first_name", "").strip(), f.get("last_name", "").strip(), f.get("dob"),
                 f.get("sex"), f.get("phone"), f.get("email"), f.get("address"),
                 f.get("referring_doctor"), f.get("notes"), self._now()),
            )
            pid = cur.lastrowid
            conn.execute("UPDATE patients SET mrn=? WHERE id=?", (f"MRN-{pid:06d}", pid))
            return pid

    def update_patient(self, patient_id, **f):
        with self.connect() as conn:
            conn.execute(
                """UPDATE patients SET first_name=?, last_name=?, dob=?, sex=?, phone=?, email=?,
                   address=?, referring_doctor=?, notes=? WHERE id=?""",
                (f.get("first_name", "").strip(), f.get("last_name", "").strip(), f.get("dob"),
                 f.get("sex"), f.get("phone"), f.get("email"), f.get("address"),
                 f.get("referring_doctor"), f.get("notes"), patient_id),
            )

    def delete_patient(self, patient_id):
        with self.connect() as conn:
            conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))

    def get_patient(self, patient_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()

    def list_patients(self, search=""):
        with self.connect() as conn:
            if search:
                like = f"%{search}%"
                return conn.execute(
                    """SELECT * FROM patients
                       WHERE first_name LIKE ? OR last_name LIKE ? OR mrn LIKE ? OR phone LIKE ?
                          OR (first_name || ' ' || last_name) LIKE ?
                       ORDER BY id DESC""",
                    (like, like, like, like, like),
                ).fetchall()
            return conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()

    def count_patients(self):
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) AS c FROM patients").fetchone()["c"]

    # ---------------------------------------------------------------- reports
    def create_report(self, patient_id, report_type_id, report_type_name, title,
                      referring_doctor, content, impression, reported_by,
                      status="Draft", report_date=None):
        with self.connect() as conn:
            now = self._now()
            cur = conn.execute(
                """INSERT INTO reports
                   (patient_id, report_type_id, report_type_name, title, referring_doctor,
                    content, impression, reported_by, status, report_date, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (patient_id, report_type_id, report_type_name, title, referring_doctor,
                 content, impression, reported_by, status, report_date or now[:10], now, now),
            )
            rid = cur.lastrowid
            report_no = f"RPT-{datetime.now().year}-{rid:05d}"
            conn.execute("UPDATE reports SET report_no=? WHERE id=?", (report_no, rid))
            return rid

    def update_report(self, report_id, **f):
        sets, vals = [], []
        for col in _REPORT_UPDATE_COLS:
            if col in f:
                sets.append(f"{col}=?")
                vals.append(f[col])
        sets.append("updated_at=?")
        vals.append(self._now())
        vals.append(report_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE reports SET {', '.join(sets)} WHERE id=?", vals)

    def set_report_status(self, report_id, status):
        with self.connect() as conn:
            conn.execute("UPDATE reports SET status=?, updated_at=? WHERE id=?",
                         (status, self._now(), report_id))

    def set_report_pdf_path(self, report_id, path):
        with self.connect() as conn:
            conn.execute("UPDATE reports SET pdf_path=? WHERE id=?", (path, report_id))

    def delete_report(self, report_id):
        with self.connect() as conn:
            conn.execute("DELETE FROM reports WHERE id=?", (report_id,))

    def get_report(self, report_id):
        """A report row joined with its patient (patient cols prefixed `p_`)."""
        with self.connect() as conn:
            return conn.execute(
                """SELECT r.*,
                          p.mrn AS p_mrn, p.first_name AS p_first, p.last_name AS p_last,
                          p.dob AS p_dob, p.sex AS p_sex, p.phone AS p_phone,
                          p.email AS p_email, p.address AS p_address
                   FROM reports r JOIN patients p ON r.patient_id = p.id
                   WHERE r.id = ?""",
                (report_id,),
            ).fetchone()

    def list_reports(self, search="", type_name="", date_from="", date_to=""):
        q = """SELECT r.id, r.report_no, r.report_type_name, r.title, r.status, r.report_date,
                      p.first_name, p.last_name, p.mrn, p.id AS patient_id
               FROM reports r JOIN patients p ON r.patient_id = p.id"""
        conds, params = [], []
        if search:
            like = f"%{search}%"
            conds.append("(r.report_no LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? "
                         "OR (p.first_name || ' ' || p.last_name) LIKE ? OR p.mrn LIKE ?)")
            params += [like, like, like, like, like]
        if type_name:
            conds.append("r.report_type_name = ?")
            params.append(type_name)
        if date_from:
            conds.append("r.report_date >= ?")
            params.append(date_from)
        if date_to:
            conds.append("r.report_date <= ?")
            params.append(date_to)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY r.id DESC"
        with self.connect() as conn:
            return conn.execute(q, params).fetchall()

    def list_reports_for_patient(self, patient_id):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM reports WHERE patient_id=? ORDER BY id DESC", (patient_id,)
            ).fetchall()

    def count_reports(self):
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]

    def count_reports_on(self, date_iso):
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS c FROM reports WHERE report_date = ?", (date_iso,)
            ).fetchone()["c"]

    # ----------------------------------------------------------- test results
    def replace_test_results(self, report_id, rows):
        """Wipe existing rows for this report and insert the new set (atomic)."""
        with self.connect() as conn:
            conn.execute("DELETE FROM test_results WHERE report_id=?", (report_id,))
            if rows:
                conn.executemany(
                    """INSERT INTO test_results
                       (report_id, section, parameter, value, unit, reference, flag, sort_order)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    [
                        (report_id, r.get("section", ""), r["parameter"],
                         r.get("value", ""), r.get("unit", ""), r.get("reference", ""),
                         r.get("flag", ""), r.get("sort_order", i))
                        for i, r in enumerate(rows)
                    ],
                )

    def get_test_results(self, report_id):
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM test_results WHERE report_id=? ORDER BY sort_order, id",
                (report_id,),
            ).fetchall()

    def has_test_results(self, report_id) -> bool:
        with self.connect() as conn:
            return conn.execute(
                "SELECT EXISTS(SELECT 1 FROM test_results WHERE report_id=?) AS e",
                (report_id,),
            ).fetchone()["e"] == 1

    def recent_reports(self, limit=12):
        with self.connect() as conn:
            return conn.execute(
                """SELECT r.id, r.report_no, r.report_type_name, r.report_date, r.status,
                          p.first_name, p.last_name
                   FROM reports r JOIN patients p ON r.patient_id = p.id
                   ORDER BY r.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
