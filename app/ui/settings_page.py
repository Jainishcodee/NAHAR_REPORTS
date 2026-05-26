"""Settings: clinic / lab details (used on every report) and report-type list."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QInputDialog, QFrame, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class SettingsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        v.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(self._build_clinic_card(), 1)
        body.addWidget(self._build_types_card(), 1)
        v.addLayout(body, 1)

    # ---------------------------------------------------------- clinic card
    def _build_clinic_card(self):
        card = QFrame()
        card.setObjectName("Card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 16, 18, 16)
        cv.setSpacing(10)
        lbl = QLabel("Clinic / laboratory information")
        lbl.setObjectName("SectionTitle")
        cv.addWidget(lbl)
        hint = QLabel("Shown in the header of every report.")
        hint.setObjectName("Muted")
        cv.addWidget(hint)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.name_edit = QLineEdit()
        self.addr_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.logo_edit = QLineEdit()
        self.logo_edit.setReadOnly(True)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.logo_edit, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._pick_logo)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.logo_edit.clear)
        logo_row.addWidget(browse_btn)
        logo_row.addWidget(clear_btn)
        form.addRow("Name", self.name_edit)
        form.addRow("Address", self.addr_edit)
        form.addRow("Phone", self.phone_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Logo", logo_row)
        cv.addLayout(form)
        cv.addStretch(1)
        save_btn = QPushButton("Save clinic info")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._save_clinic)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(save_btn)
        cv.addLayout(row)
        return card

    # ----------------------------------------------------------- types card
    def _build_types_card(self):
        card = QFrame()
        card.setObjectName("Card")
        tv = QVBoxLayout(card)
        tv.setContentsMargins(18, 16, 18, 16)
        tv.setSpacing(10)
        lbl = QLabel("Report types")
        lbl.setObjectName("SectionTitle")
        tv.addWidget(lbl)
        hint = QLabel("Options in the 'Report type' dropdown. 'Edit fields' defines a "
                      "type's structured table (parameters + recommended reference values).")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        tv.addWidget(hint)

        self.types_list = QListWidget()
        self.types_list.doubleClicked.connect(self._edit_template)
        tv.addWidget(self.types_list, 1)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add type")
        add_btn.clicked.connect(self._add_type)
        fields_btn = QPushButton("Edit fields…")
        fields_btn.setObjectName("PrimaryButton")
        fields_btn.clicked.connect(self._edit_template)
        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._rename_type)
        toggle_btn = QPushButton("Enable / Disable")
        toggle_btn.clicked.connect(self._toggle_type)
        for b in (add_btn, fields_btn, rename_btn, toggle_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        tv.addLayout(btns)
        return card

    # ----------------------------------------------------------------- data
    def refresh(self):
        s = self.main.db.get_settings()
        self.name_edit.setText(s["clinic_name"] or "")
        self.addr_edit.setText(s["address"] or "")
        self.phone_edit.setText(s["phone"] or "")
        self.email_edit.setText(s["email"] or "")
        self.logo_edit.setText(s["logo_path"] or "")
        self._reload_types()

    def _reload_types(self):
        self.types_list.clear()
        for t in self.main.db.get_report_types(active_only=False):
            n = len(self.main.db.get_template_params(t["id"]))
            fields = f"{n} field{'s' if n != 1 else ''}" if n else "free-text"
            label = f'{t["name"]}   ({t["code"]})   ·   {fields}'
            if not t["is_active"]:
                label += "   — disabled"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t["id"])
            if not t["is_active"]:
                item.setForeground(QColor("#9aa3b0"))
            self.types_list.addItem(item)

    # -------------------------------------------------------- clinic actions
    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose logo image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.logo_edit.setText(path)

    def _save_clinic(self):
        try:
            self.main.db.update_settings(
                self.name_edit.text().strip(), self.addr_edit.text().strip(),
                self.phone_edit.text().strip(), self.email_edit.text().strip(),
                self.logo_edit.text().strip(),
            )
        except Exception:  # noqa: BLE001
            self.main.toast_error("Could not save clinic info")
            return
        self.main.toast_success("Clinic info saved")

    # --------------------------------------------------------- type actions
    def _selected_type_id(self):
        item = self.types_list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _type_name(self, type_id):
        for t in self.main.db.get_report_types(active_only=False):
            if t["id"] == type_id:
                return t["name"]
        return ""

    def _add_type(self):
        name, ok = QInputDialog.getText(self, "Add report type", "Name (e.g. 'Blood Pressure'):")
        if not ok or not name.strip():
            return
        code, ok = QInputDialog.getText(self, "Add report type", "Short code (e.g. 'BP'):")
        if not ok or not code.strip():
            return
        try:
            new_id = self.main.db.add_report_type(code.strip(), name.strip())
        except Exception:  # noqa: BLE001 - most likely a duplicate code
            self.main.toast_error("Could not add — that code may already exist")
            return
        self._reload_types()
        self.main.toast_success("Report type added")
        # immediately offer to define its fields (Cancel leaves it as free-text)
        self._open_template_editor(new_id, name.strip())

    def _edit_template(self, *_):
        type_id = self._selected_type_id()
        if type_id is None:
            self.main.toast_error("Select a report type first")
            return
        self._open_template_editor(type_id, self._type_name(type_id))

    def _open_template_editor(self, type_id, type_name):
        from app.ui.template_editor import TemplateEditorDialog
        params = self.main.db.get_template_params(type_id)
        dlg = TemplateEditorDialog(self, type_name, params)
        if dlg.exec() == QDialog.Accepted:
            self.main.db.replace_template_params(type_id, dlg.result_params())
            self._reload_types()
            self.main.toast_success("Template saved")

    def _rename_type(self):
        type_id = self._selected_type_id()
        if type_id is None:
            self.main.toast_error("Select a report type first")
            return
        name, ok = QInputDialog.getText(self, "Rename report type", "New name:",
                                        text=self._type_name(type_id))
        if ok and name.strip():
            self.main.db.update_report_type(type_id, name.strip())
            self._reload_types()
            self.main.toast_success("Report type renamed")

    def _toggle_type(self):
        type_id = self._selected_type_id()
        if type_id is None:
            self.main.toast_error("Select a report type first")
            return
        for t in self.main.db.get_report_types(active_only=False):
            if t["id"] == type_id:
                self.main.db.set_report_type_active(type_id, not t["is_active"])
                break
        self._reload_types()
