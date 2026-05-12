"""Dashboard: a few counts + recent reports."""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from app.models import fmt_date


class StatCard(QFrame):
    def __init__(self, caption):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumWidth(180)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 18, 14)
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 26pt; font-weight: 600; color: #14233b;")
        cap = QLabel(caption)
        cap.setObjectName("Muted")
        v.addWidget(self.value_label)
        v.addWidget(cap)

    def set_value(self, value):
        self.value_label.setText(str(value))


class HomePage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self._ids = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        new_btn = QPushButton("+  New Report")
        new_btn.setObjectName("PrimaryButton")
        new_btn.clicked.connect(lambda: self.main.go_new_report())
        header.addWidget(new_btn)
        outer.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.card_patients = StatCard("Patients registered")
        self.card_reports = StatCard("Reports created")
        self.card_today = StatCard("Reports today")
        for card in (self.card_patients, self.card_reports, self.card_today):
            cards.addWidget(card)
        cards.addStretch(1)
        outer.addLayout(cards)

        recent = QLabel("Recent reports")
        recent.setObjectName("SectionTitle")
        outer.addWidget(recent)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Report No", "Patient", "Type", "Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._open_selected)
        outer.addWidget(self.table, 1)

        hint = QLabel("Double-click a report to preview it.")
        hint.setObjectName("Muted")
        outer.addWidget(hint)

    def refresh(self):
        db = self.main.db
        self.card_patients.set_value(db.count_patients())
        self.card_reports.set_value(db.count_reports())
        self.card_today.set_value(db.count_reports_on(date.today().isoformat()))

        self.table.setRowCount(0)
        self._ids = []
        for r in db.recent_reports(15):
            i = self.table.rowCount()
            self.table.insertRow(i)
            self._ids.append(r["id"])
            name = f'{r["first_name"]} {r["last_name"]}'.strip()
            values = [r["report_no"] or "", name, r["report_type_name"] or "",
                      fmt_date(r["report_date"]), r["status"] or ""]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(str(value)))

    def _open_selected(self, *_):
        row = self.table.currentRow()
        if 0 <= row < len(self._ids):
            self.main.show_preview(self._ids[row])
