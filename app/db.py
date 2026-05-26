"""SQLite storage layer: schema creation, seeding, and all data access.

Single-file local database. No server. No network. The whole app talks to
one `Database` instance held by the main window.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import DB_PATH, DEFAULT_REPORT_TYPES, DEFAULT_CLINIC
from app.templates import Param, TEMPLATES


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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id   INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section     TEXT,
    parameter   TEXT NOT NULL,
    value       TEXT,
    unit        TEXT,
    reference   TEXT,
    flag        TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    description TEXT DEFAULT ''
);

-- Editable structured-report templates. One row per parameter of a report type.
CREATE TABLE IF NOT EXISTS template_params (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type_id  INTEGER NOT NULL REFERENCES report_types(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    section         TEXT,
    name            TEXT NOT NULL,
    unit            TEXT,
    ref_low         REAL,
    ref_high        REAL,
    ref_low_male    REAL,
    ref_high_male   REAL,
    ref_low_female  REAL,
    ref_high_female REAL,
    expected        TEXT,
    note            TEXT
);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date);
CREATE INDEX IF NOT EXISTS idx_test_results_report ON test_results(report_id);
CREATE INDEX IF NOT EXISTS idx_template_params_type ON template_params(report_type_id);
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
            self._apply_migrations(conn)
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
            self._seed_templates(conn)

    @staticmethod
    def _apply_migrations(conn):
        """Idempotent column additions for databases created before a column existed."""
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(test_results)").fetchall()}
        if "description" not in existing:
            conn.execute("ALTER TABLE test_results ADD COLUMN description TEXT DEFAULT ''")

    @staticmethod
    def _insert_params(conn, type_id, params):
        conn.executemany(
            """INSERT INTO template_params
               (report_type_id, sort_order, section, name, unit, ref_low, ref_high,
                ref_low_male, ref_high_male, ref_low_female, ref_high_female, expected, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (type_id, i, p.section, p.name, p.unit, p.ref_low, p.ref_high,
                 p.ref_low_male, p.ref_high_male, p.ref_low_female, p.ref_high_female,
                 p.expected, p.note)
                for i, p in enumerate(params)
            ],
        )

    def _seed_templates(self, conn):
        """Populate template_params from the built-in TEMPLATES, once.

        Runs for fresh AND existing databases (gated by an app_meta flag) so
        the built-in templates appear without wiping any edits the user later
        makes. After seeding, templates are fully DB-driven and editable.
        """
        flag = conn.execute(
            "SELECT value FROM app_meta WHERE key='templates_seeded'"
        ).fetchone()
        if flag and flag["value"] == "1":
            return
        type_by_code = {
            r["code"]: r["id"]
            for r in conn.execute("SELECT id, code FROM report_types").fetchall()
        }
        for code, params in TEMPLATES.items():
            tid = type_by_code.get(code)
            if tid is None:
                continue
            already = conn.execute(
                "SELECT 1 FROM template_params WHERE report_type_id=? LIMIT 1", (tid,)
            ).fetchone()
            if already:
                continue
            self._insert_params(conn, tid, params)
        conn.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('templates_seeded', '1')"
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
            cur = conn.execute("INSERT INTO report_types (code, name) VALUES (?, ?)",
                               (code.strip().upper(), name.strip()))
            return cur.lastrowid

    def update_report_type(self, type_id, name):
        with self.connect() as conn:
            conn.execute("UPDATE report_types SET name=? WHERE id=?", (name.strip(), type_id))

    def set_report_type_active(self, type_id, active):
        with self.connect() as conn:
            conn.execute("UPDATE report_types SET is_active=? WHERE id=?",
                         (1 if active else 0, type_id))

    # --------------------------------------------------- template params
    @staticmethod
    def _row_to_param(r) -> Param:
        return Param(
            name=r["name"],
            unit=r["unit"] or "",
            section=r["section"] or "",
            ref_low=r["ref_low"], ref_high=r["ref_high"],
            ref_low_male=r["ref_low_male"], ref_high_male=r["ref_high_male"],
            ref_low_female=r["ref_low_female"], ref_high_female=r["ref_high_female"],
            expected=r["expected"], note=r["note"] or "",
        )

    def get_template_params(self, type_id) -> list[Param]:
        """Return the template (as Param objects) for a report-type id."""
        if type_id is None:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM template_params WHERE report_type_id=? ORDER BY sort_order, id",
                (type_id,),
            ).fetchall()
        return [self._row_to_param(r) for r in rows]

    def type_has_template(self, type_id) -> bool:
        if type_id is None:
            return False
        with self.connect() as conn:
            return conn.execute(
                "SELECT 1 FROM template_params WHERE report_type_id=? LIMIT 1", (type_id,)
            ).fetchone() is not None

    def replace_template_params(self, type_id, params):
        """Overwrite the whole template for a report type with `params` (list[Param])."""
        with self.connect() as conn:
            conn.execute("DELETE FROM template_params WHERE report_type_id=?", (type_id,))
            self._insert_params(conn, type_id, params)

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
                       (report_id, section, parameter, value, unit, reference, flag,
                        sort_order, description)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    [
                        (report_id, r.get("section", ""), r["parameter"],
                         r.get("value", ""), r.get("unit", ""), r.get("reference", ""),
                         r.get("flag", ""), r.get("sort_order", i),
                         r.get("description", "") or "")
                        for i, r in enumerate(rows)
                    ],
                )

    def get_description_suggestions(self, param_names):
        """Return {parameter_name: [past descriptions, most recent first]}.

        Powers the auto-complete on the per-parameter note field — so a description
        the user has written once for, say, 'Hemoglobin (Hb)' is offered as a
        suggestion the next time they create a report with that parameter.
        """
        if not param_names:
            return {}
        placeholders = ",".join(["?"] * len(param_names))
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT parameter, description, MAX(id) AS recent
                    FROM test_results
                    WHERE parameter IN ({placeholders})
                      AND description IS NOT NULL AND TRIM(description) != ''
                    GROUP BY parameter, description
                    ORDER BY recent DESC""",
                list(param_names),
            ).fetchall()
        out = {name: [] for name in param_names}
        for r in rows:
            out[r["parameter"]].append(r["description"])
        return out

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
