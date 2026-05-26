"""Create (or edit) a report.

Flow: pick patient -> pick type -> enter content -> Submit.

If the chosen report type has a structured template (CBC, Lipid Profile, …)
the content area becomes a parameter table with live Low/Normal/High flags
based on the patient's sex and the reference ranges in `app/templates.py`.
For narrative types (MRI, X-Ray, …) the original free-text editor is used.
"""
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget,
)

from app.models import calculate_age
from app.templates import rows_to_text
from app.ui.patient_form import PatientDialog
from app.ui.structured_results import StructuredResultsWidget


_TITLE_SUFFIX = " — Report"

# Indices into the content stack
_MODE_FREE = 0
_MODE_STRUCTURED = 1


class _Card(QFrame):
    """A white rounded panel with a section title."""

    def __init__(self, title):
        super().__init__()
        self.setObjectName("Card")
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(18, 16, 18, 16)
        self._v.setSpacing(10)
        lbl = QLabel(title)
        lbl.setObjectName("SectionTitle")
        self._v.addWidget(lbl)

    def add_widget(self, w):
        self._v.addWidget(w)

    def add_layout(self, layout):
        self._v.addLayout(layout)


class NewReportPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.editing_id = None
        self._structured_params = []        # list[Param] currently in the table
        self._structured_type_id = None     # which report-type id the table is for

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        inner = QWidget()
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)

        self.title_label = QLabel("New Report")
        self.title_label.setObjectName("PageTitle")
        v.addWidget(self.title_label)

        # ---- patient ----
        patient_card = _Card("Patient")
        prow = QHBoxLayout()
        self.patient_combo = QComboBox()
        self.patient_combo.setMinimumWidth(340)
        self.patient_combo.currentIndexChanged.connect(self._patient_changed)
        prow.addWidget(self.patient_combo, 1)
        new_pt_btn = QPushButton("+  New patient")
        new_pt_btn.clicked.connect(self._create_patient)
        prow.addWidget(new_pt_btn)
        patient_card.add_layout(prow)
        self.patient_info = QLabel("")
        self.patient_info.setObjectName("Muted")
        patient_card.add_widget(self.patient_info)
        v.addWidget(patient_card)

        # ---- report details ----
        details_card = _Card("Report details")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.title_edit = QLineEdit()
        self.doctor_edit = QLineEdit()
        self.reported_by_edit = QLineEdit()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd MMM yyyy")
        self.date_edit.setDate(QDate.currentDate())
        grid.addWidget(QLabel("Report type *"), 0, 0)
        grid.addWidget(self.type_combo, 0, 1)
        grid.addWidget(QLabel("Report date"), 0, 2)
        grid.addWidget(self.date_edit, 0, 3)
        grid.addWidget(QLabel("Title"), 1, 0)
        grid.addWidget(self.title_edit, 1, 1, 1, 3)
        grid.addWidget(QLabel("Referring doctor"), 2, 0)
        grid.addWidget(self.doctor_edit, 2, 1)
        grid.addWidget(QLabel("Reported by"), 2, 2)
        grid.addWidget(self.reported_by_edit, 2, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        details_card.add_layout(grid)
        v.addWidget(details_card)

        # ---- content (two modes: free-text vs structured table) ----
        content_card = _Card("Report content")

        self.content_stack = QStackedWidget()
        # ----- free-text page -----
        free_page = QWidget()
        fv = QVBoxLayout(free_page)
        fv.setContentsMargins(0, 0, 0, 0)
        fv.setSpacing(6)
        fv.addWidget(QLabel("Findings / report content *"))
        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText("Paste or type the raw report data / findings here…")
        self.content_edit.setMinimumHeight(220)
        fv.addWidget(self.content_edit)
        self.content_stack.addWidget(free_page)  # index _MODE_FREE

        # ----- structured page -----
        struct_page = QWidget()
        sv = QVBoxLayout(struct_page)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(6)
        header_row = QHBoxLayout()
        self._structured_header = QLabel("Test results *")
        header_row.addWidget(self._structured_header)
        header_row.addStretch(1)
        self.smart_paste_btn = QPushButton("Smart paste…")
        self.smart_paste_btn.setToolTip(
            "Paste raw JSON, an Excel selection, or 'Name: value' lines and "
            "auto-fill the table."
        )
        self.smart_paste_btn.clicked.connect(self._smart_paste)
        header_row.addWidget(self.smart_paste_btn)
        sv.addLayout(header_row)
        self.structured = StructuredResultsWidget()
        self.structured.setMinimumHeight(360)
        sv.addWidget(self.structured)
        self.content_stack.addWidget(struct_page)  # index _MODE_STRUCTURED

        content_card.add_widget(self.content_stack)

        content_card.add_widget(QLabel("Impression / conclusion (optional)"))
        self.impression_edit = QPlainTextEdit()
        self.impression_edit.setMinimumHeight(90)
        content_card.add_widget(self.impression_edit)

        v.addWidget(content_card)

        # ---- actions ----
        actions = QHBoxLayout()
        self.left_btn = QPushButton("Clear")
        self.left_btn.clicked.connect(self._left_clicked)
        actions.addWidget(self.left_btn)
        actions.addStretch(1)
        self.draft_btn = QPushButton("Save as Draft")
        self.draft_btn.clicked.connect(lambda: self._submit(status="Draft", preview=False))
        actions.addWidget(self.draft_btn)
        self.submit_btn = QPushButton("Submit  →  Preview")
        self.submit_btn.setObjectName("PrimaryButton")
        self.submit_btn.clicked.connect(lambda: self._submit(status="Final", preview=True))
        actions.addWidget(self.submit_btn)
        v.addLayout(actions)
        v.addStretch(1)

    # ----------------------------------------------------------- populate
    def _load_patients(self, select_id=None):
        self.patient_combo.blockSignals(True)
        self.patient_combo.clear()
        self.patient_combo.addItem("— Select patient —", None)
        rows = sorted(self.main.db.list_patients(),
                      key=lambda r: ((r["first_name"] or "").lower(), (r["last_name"] or "").lower()))
        for r in rows:
            label = f'{r["first_name"]} {r["last_name"]}'.strip() + f'   ·   {r["mrn"] or ""}'
            self.patient_combo.addItem(label, r["id"])
        self.patient_combo.blockSignals(False)
        idx = self.patient_combo.findData(select_id) if select_id is not None else 0
        self.patient_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._patient_changed()

    def _load_types(self, select_id=None, include_inactive=False):
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem("— Select type —", None)
        for t in self.main.db.get_report_types(active_only=not include_inactive):
            self.type_combo.addItem(t["name"], (t["id"], t["name"], t["code"]))
        self.type_combo.blockSignals(False)
        target = 0
        if select_id is not None:
            for i in range(self.type_combo.count()):
                data = self.type_combo.itemData(i)
                if data and data[0] == select_id:
                    target = i
                    break
        self.type_combo.setCurrentIndex(target)

    def _current_type(self):
        """Return (type_id, type_name, type_code) or (None, '', '')."""
        data = self.type_combo.currentData()
        if not data:
            return (None, "", "")
        if len(data) == 2:
            return (data[0], data[1], "")
        return (data[0], data[1], data[2] or "")

    # ---------------------------------------------------- mode handling
    def _switch_to_structured(self, params, type_id, sex="", saved_rows=None):
        self._structured_params = list(params)
        self._structured_type_id = type_id
        suggestions = self.main.db.get_description_suggestions(
            [p.name for p in self._structured_params]
        )
        self.structured.load_template(
            self._structured_params, sex=sex, description_suggestions=suggestions,
        )
        if saved_rows:
            self.structured.populate_from_saved(saved_rows)
        self._structured_header.setText(f"Test results *  ·  {len(self._structured_params)} parameters")
        self.content_stack.setCurrentIndex(_MODE_STRUCTURED)

    def _switch_to_free_text(self):
        self._structured_params = []
        self._structured_type_id = None
        self.content_stack.setCurrentIndex(_MODE_FREE)

    def _is_structured_mode(self) -> bool:
        return self.content_stack.currentIndex() == _MODE_STRUCTURED

    def _current_patient_sex(self) -> str:
        pid = self.patient_combo.currentData()
        if pid is None:
            return ""
        p = self.main.db.get_patient(pid)
        return (p["sex"] if p else "") or ""

    # --------------------------------------------------------- entry points
    def start_new(self, patient_id=None):
        self.editing_id = None
        self.title_label.setText("New Report")
        self.submit_btn.setText("Submit  →  Preview")
        self.left_btn.setText("Clear")
        self.draft_btn.setVisible(True)
        self._load_types()
        self.title_edit.clear()
        self.doctor_edit.clear()
        self.reported_by_edit.clear()
        self.date_edit.setDate(QDate.currentDate())
        self.content_edit.clear()
        self.impression_edit.clear()
        self.structured.load_template([])  # clear table
        self._switch_to_free_text()
        self._load_patients(patient_id)

    def load_report(self, report_id):
        r = self.main.db.get_report(report_id)
        if r is None:
            self.main.toast_error("Report not found")
            self.main.go_reports()
            return
        self.editing_id = report_id
        self.title_label.setText(f"Edit Report  ·  {r['report_no'] or report_id}")
        self.submit_btn.setText("Update  →  Preview")
        self.left_btn.setText("Cancel")
        self.draft_btn.setVisible(True)
        self._load_types(r["report_type_id"], include_inactive=True)
        if self.type_combo.currentIndex() == 0 and r["report_type_name"]:
            self.type_combo.addItem(
                r["report_type_name"],
                (r["report_type_id"], r["report_type_name"], ""),
            )
            self.type_combo.setCurrentIndex(self.type_combo.count() - 1)
        self.title_edit.setText(r["title"] or "")
        self.doctor_edit.setText(r["referring_doctor"] or "")
        self.reported_by_edit.setText(r["reported_by"] or "")
        qd = QDate.fromString(str(r["report_date"] or "")[:10], "yyyy-MM-dd")
        self.date_edit.setDate(qd if qd.isValid() else QDate.currentDate())
        self.impression_edit.setPlainText(r["impression"] or "")
        self._load_patients(r["patient_id"])  # also sets sex on structured if active

        # Decide mode: structured if test_results exist; else free-text
        saved_rows = self.main.db.get_test_results(report_id) if self.main.db.has_test_results(report_id) else []
        if saved_rows:
            type_id = self._current_type()[0]
            params = self.main.db.get_template_params(type_id)
            if params:
                self._switch_to_structured(params, type_id,
                                           sex=self._current_patient_sex(), saved_rows=saved_rows)
            else:
                # Type lost its template — show the data as text
                self.content_edit.setPlainText(rows_to_text([dict(r) for r in saved_rows]))
                self._switch_to_free_text()
        else:
            self.content_edit.setPlainText(r["content"] or "")
            self._switch_to_free_text()

    # -------------------------------------------------------------- events
    def _patient_changed(self, *_):
        pid = self.patient_combo.currentData()
        if pid is None:
            self.patient_info.setText("")
            self.structured.set_patient_sex("")
            return
        p = self.main.db.get_patient(pid)
        if p is None:
            self.patient_info.setText("")
            self.structured.set_patient_sex("")
            return
        bits = [f'{p["first_name"]} {p["last_name"]}'.strip(), p["mrn"] or ""]
        age = calculate_age(p["dob"])
        if age is not None:
            bits.append(f"{age} yrs")
        if p["sex"]:
            bits.append(p["sex"])
        if p["phone"]:
            bits.append(p["phone"])
        self.patient_info.setText("    ·    ".join(b for b in bits if b))
        if p["referring_doctor"] and not self.doctor_edit.text().strip():
            self.doctor_edit.setText(p["referring_doctor"])
        # push sex into the structured editor — affects reference ranges
        self.structured.set_patient_sex(p["sex"] or "")

    def _type_changed(self, *_):
        type_id, type_name, type_code = self._current_type()
        if not type_id and not type_name:
            return
        # title suggestion (only when empty or still the previous auto value)
        current = self.title_edit.text().strip()
        if not current or current.endswith(_TITLE_SUFFIX.strip()):
            self.title_edit.setText(f"{type_name}{_TITLE_SUFFIX}")
        # mode swap — only auto-switch for NEW reports.
        # When editing, the mode was already decided by load_report based on
        # whether the report actually has test_results saved.
        if self.editing_id is not None:
            return
        params = self.main.db.get_template_params(type_id)
        if params:
            if self._structured_type_id != type_id:
                self._switch_to_structured(params, type_id, sex=self._current_patient_sex())
        else:
            self._switch_to_free_text()

    def _create_patient(self):
        dlg = PatientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            pid = self.main.db.add_patient(**dlg.values())
            self._load_patients(pid)

    def _smart_paste(self):
        from app.ui.smart_paste_dialog import SmartPasteDialog
        if not self._structured_params:
            self.main.toast_error("Pick a structured report type first")
            return
        dlg = SmartPasteDialog(self, self._structured_params)
        if dlg.exec() != QDialog.Accepted:
            return
        matched, total = dlg.matched_pairs()
        filled = self.structured.apply_pairs(matched)
        if filled:
            extra = f"  ·  {total - len(matched)} unmatched" if total > len(matched) else ""
            self.main.toast_success(
                f"Filled {filled} field{'s' if filled != 1 else ''}{extra}"
            )
        else:
            self.main.toast_error("Could not match any parameters")

    def _left_clicked(self):
        if self.editing_id:
            self.main.go_reports()
        else:
            self.start_new()

    # ---------------------------------------------------------------- save
    def _collect(self):
        pid = self.patient_combo.currentData()
        type_id, type_name, _type_code = self._current_type()
        title = self.title_edit.text().strip()
        if not title:
            title = f"{type_name}{_TITLE_SUFFIX}" if type_name else "Medical Report"

        if self._is_structured_mode():
            rows = self.structured.get_rows()
            content_text = rows_to_text(rows)
        else:
            rows = None
            content_text = self.content_edit.toPlainText().rstrip()

        return {
            "patient_id": pid,
            "report_type_id": type_id,
            "report_type_name": type_name,
            "title": title,
            "referring_doctor": self.doctor_edit.text().strip(),
            "content": content_text,
            "impression": self.impression_edit.toPlainText().rstrip(),
            "reported_by": self.reported_by_edit.text().strip(),
            "report_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "_structured_rows": rows,  # not a DB column — stripped before insert
        }

    def _submit(self, status, preview):
        data = self._collect()
        rows = data.pop("_structured_rows")

        if data["patient_id"] is None:
            self.main.toast_error("Please select or create a patient")
            return
        if not data["report_type_name"]:
            self.main.toast_error("Please choose a report type")
            return
        if rows is not None:
            if not rows:
                self.main.toast_error("Please enter at least one test result")
                return
        else:
            if not data["content"]:
                self.main.toast_error("Please enter the report content")
                return

        try:
            if self.editing_id:
                update = {k: v for k, v in data.items() if k != "patient_id"}
                update["status"] = status
                self.main.db.update_report(self.editing_id, **update)
                report_id = self.editing_id
            else:
                report_id = self.main.db.create_report(status=status, **data)
            # persist structured rows (or wipe them if we just switched to free-text)
            if rows is not None:
                self.main.db.replace_test_results(report_id, rows)
            elif self.editing_id:
                self.main.db.replace_test_results(report_id, [])
        except Exception:  # noqa: BLE001
            self.main.toast_error("Could not save the report")
            return

        action = "updated" if self.editing_id else "saved"
        self.main.toast_success(f"Report {action} as {status}")
        if preview:
            self.main.show_preview(report_id)
        else:
            self.main.go_reports()
