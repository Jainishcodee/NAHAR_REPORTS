"""Reusable patient form widget + a dialog wrapper around it."""
from PySide6.QtWidgets import (
    QWidget, QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QDateEdit, QPlainTextEdit, QCheckBox, QDialogButtonBox, QMessageBox,
)
from PySide6.QtCore import Qt, QDate

from app.config import SEX_OPTIONS


class PatientFormWidget(QWidget):
    """The set of patient fields. Used inside PatientDialog (and elsewhere)."""

    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignRight)

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDisplayFormat("dd MMM yyyy")
        self.dob.setMaximumDate(QDate.currentDate())
        self.dob.setDate(QDate(2000, 1, 1))
        self.dob_unknown = QCheckBox("Date of birth not known")
        self.sex = QComboBox()
        self.sex.addItems(SEX_OPTIONS)
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.address = QLineEdit()
        self.referring_doctor = QLineEdit()
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(64)

        form.addRow("First name *", self.first_name)
        form.addRow("Last name", self.last_name)
        form.addRow("Date of birth", self.dob)
        form.addRow("", self.dob_unknown)
        form.addRow("Sex", self.sex)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Address", self.address)
        form.addRow("Referring doctor", self.referring_doctor)
        form.addRow("Notes", self.notes)

        self.dob_unknown.toggled.connect(self.dob.setDisabled)

    def set_values(self, row):
        self.first_name.setText(row["first_name"] or "")
        self.last_name.setText(row["last_name"] or "")
        dob = row["dob"]
        if dob:
            qd = QDate.fromString(str(dob)[:10], "yyyy-MM-dd")
            if qd.isValid():
                self.dob.setDate(qd)
                self.dob_unknown.setChecked(False)
            else:
                self.dob_unknown.setChecked(True)
        else:
            self.dob_unknown.setChecked(True)
        idx = self.sex.findText(row["sex"] or "")
        self.sex.setCurrentIndex(idx if idx >= 0 else 0)
        self.phone.setText(row["phone"] or "")
        self.email.setText(row["email"] or "")
        self.address.setText(row["address"] or "")
        self.referring_doctor.setText(row["referring_doctor"] or "")
        self.notes.setPlainText(row["notes"] or "")

    def clear(self):
        self.first_name.clear()
        self.last_name.clear()
        self.dob.setDate(QDate(2000, 1, 1))
        self.dob_unknown.setChecked(False)
        self.sex.setCurrentIndex(0)
        self.phone.clear()
        self.email.clear()
        self.address.clear()
        self.referring_doctor.clear()
        self.notes.clear()

    def get_values(self):
        return {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "dob": None if self.dob_unknown.isChecked() else self.dob.date().toString("yyyy-MM-dd"),
            "sex": self.sex.currentText(),
            "phone": self.phone.text().strip(),
            "email": self.email.text().strip(),
            "address": self.address.text().strip(),
            "referring_doctor": self.referring_doctor.text().strip(),
            "notes": self.notes.toPlainText().strip(),
        }

    def validate(self):
        if not self.first_name.text().strip():
            return False, "First name is required."
        return True, ""


class PatientDialog(QDialog):
    def __init__(self, parent=None, patient_row=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Patient" if patient_row else "New Patient")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        self.form = PatientFormWidget()
        layout.addWidget(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        if patient_row is not None:
            self.form.set_values(patient_row)

    def _accept(self):
        ok, msg = self.form.validate()
        if not ok:
            QMessageBox.warning(self, "Missing information", msg)
            return
        self.accept()

    def values(self):
        return self.form.get_values()
