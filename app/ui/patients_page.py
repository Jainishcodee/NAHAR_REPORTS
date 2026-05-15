"""Patients registry: search, list, add, edit, delete; jump to a new report."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QDialog,
)

from app.models import calculate_age, fmt_date
from app.ui.patient_form import PatientDialog


class PatientsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self._ids = []

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel("Patients")
        title.setObjectName("PageTitle")
        top.addWidget(title)
        top.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name, MRN or phone…")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._reload)
        top.addWidget(self.search)
        add_btn = QPushButton("+  New Patient")
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add_patient)
        top.addWidget(add_btn)
        v.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["MRN", "Name", "Age / Sex", "Phone", "Referring Dr", "Registered"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._edit_patient)
        v.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_report = QPushButton("New Report for Patient")
        self.btn_report.clicked.connect(self._new_report)
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self._edit_patient)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_delete.clicked.connect(self._delete_patient)
        for b in (self.btn_report, self.btn_edit, self.btn_delete):
            actions.addWidget(b)
        v.addLayout(actions)

    # ----------------------------------------------------------------- data
    def refresh(self):
        self._reload()

    def _reload(self, *_):
        rows = self.main.db.list_patients(self.search.text().strip())
        self.table.setRowCount(0)
        self._ids = []
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            self._ids.append(r["id"])
            age = calculate_age(r["dob"])
            age_sex = f'{age} / {r["sex"]}' if age is not None else (r["sex"] or "—")
            values = [r["mrn"] or "", f'{r["first_name"]} {r["last_name"]}'.strip(), age_sex,
                      r["phone"] or "—", r["referring_doctor"] or "—", fmt_date(r["created_at"])]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(str(value)))

    def _selected_id(self):
        row = self.table.currentRow()
        return self._ids[row] if 0 <= row < len(self._ids) else None

    # -------------------------------------------------------------- actions
    def _add_patient(self):
        dlg = PatientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self.main.db.add_patient(**dlg.values())
            except Exception:  # noqa: BLE001 - surface any DB failure as a toast
                self.main.toast_error("Could not add patient")
                return
            self._reload()
            self.main.toast_success("Patient registered")

    def _edit_patient(self, *_):
        pid = self._selected_id()
        if pid is None:
            self.main.toast_error("Select a patient first")
            return
        row = self.main.db.get_patient(pid)
        if row is None:
            return
        dlg = PatientDialog(self, patient_row=row)
        if dlg.exec() == QDialog.Accepted:
            try:
                self.main.db.update_patient(pid, **dlg.values())
            except Exception:  # noqa: BLE001
                self.main.toast_error("Could not update patient")
                return
            self._reload()
            self.main.toast_success("Patient updated")

    def _delete_patient(self):
        pid = self._selected_id()
        if pid is None:
            self.main.toast_error("Select a patient first")
            return
        row = self.main.db.get_patient(pid)
        name = f'{row["first_name"]} {row["last_name"]}'.strip()
        confirm = QMessageBox.question(
            self, "Delete patient",
            f"Delete patient '{name}' and ALL their reports?\nThis cannot be undone.",
        )
        if confirm == QMessageBox.Yes:
            self.main.db.delete_patient(pid)
            self._reload()
            self.main.toast_success("Patient deleted")

    def _new_report(self):
        pid = self._selected_id()
        if pid is None:
            self.main.toast_error("Select a patient first")
            return
        self.main.go_new_report(pid)
