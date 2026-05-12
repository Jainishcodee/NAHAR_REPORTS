"""All reports: search, filter by type / date, view, edit, delete."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox, QMessageBox,
)
from PySide6.QtCore import QDate

from app.models import fmt_date


class ReportsPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self._ids = []

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel("Reports")
        title.setObjectName("PageTitle")
        top.addWidget(title)
        top.addStretch(1)
        new_btn = QPushButton("+  New Report")
        new_btn.setObjectName("PrimaryButton")
        new_btn.clicked.connect(lambda: self.main.go_new_report())
        top.addWidget(new_btn)
        v.addLayout(top)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search report no, patient, MRN…")
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(self._reload)
        filters.addWidget(self.search)
        self.type_filter = QComboBox()
        self.type_filter.currentIndexChanged.connect(self._reload)
        filters.addWidget(self.type_filter)
        self.use_dates = QCheckBox("Date range:")
        self.use_dates.toggled.connect(self._reload)
        filters.addWidget(self.use_dates)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd MMM yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self._reload)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd MMM yyyy")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self._reload)
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel("to"))
        filters.addWidget(self.date_to)
        filters.addStretch(1)
        v.addLayout(filters)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Report No", "Patient", "Type", "Date", "Status"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._open_selected)
        v.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        view_btn = QPushButton("View / Preview")
        view_btn.setObjectName("PrimaryButton")
        view_btn.clicked.connect(self._open_selected)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_selected)
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("DangerButton")
        del_btn.clicked.connect(self._delete_selected)
        for b in (view_btn, edit_btn, del_btn):
            actions.addWidget(b)
        v.addLayout(actions)

    # ----------------------------------------------------------------- data
    def refresh(self):
        previous = self.type_filter.currentText()
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem("All types", "")
        for t in self.main.db.get_report_types(active_only=False):
            self.type_filter.addItem(t["name"], t["name"])
        idx = self.type_filter.findText(previous)
        self.type_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.type_filter.blockSignals(False)
        self._reload()

    def _reload(self, *_):
        if self.use_dates.isChecked():
            df = self.date_from.date().toString("yyyy-MM-dd")
            dt = self.date_to.date().toString("yyyy-MM-dd")
        else:
            df = dt = ""
        rows = self.main.db.list_reports(
            self.search.text().strip(), self.type_filter.currentData() or "", df, dt
        )
        self.table.setRowCount(0)
        self._ids = []
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            self._ids.append(r["id"])
            name = f'{r["first_name"]} {r["last_name"]}'.strip()
            values = [r["report_no"] or "", f'{name}   ·   {r["mrn"] or ""}',
                      r["report_type_name"] or "", fmt_date(r["report_date"]), r["status"] or ""]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(str(value)))

    def _selected_id(self):
        row = self.table.currentRow()
        return self._ids[row] if 0 <= row < len(self._ids) else None

    # -------------------------------------------------------------- actions
    def _open_selected(self, *_):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Select a report", "Please select a report first.")
            return
        self.main.show_preview(rid)

    def _edit_selected(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Select a report", "Please select a report first.")
            return
        self.main.edit_report(rid)

    def _delete_selected(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "Select a report", "Please select a report first.")
            return
        if QMessageBox.question(self, "Delete report",
                                "Delete this report? This cannot be undone.") == QMessageBox.Yes:
            self.main.db.delete_report(rid)
            self._reload()
