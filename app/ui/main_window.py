"""Main window: a dark sidebar + a stack of pages."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QPushButton,
    QLabel, QFrame,
)

from app.config import APP_NAME, APP_VERSION
from app.db import Database
from app.ui.style import STYLESHEET
from app.ui.home_page import HomePage
from app.ui.patients_page import PatientsPage
from app.ui.new_report_page import NewReportPage
from app.ui.reports_page import ReportsPage
from app.ui.report_preview import ReportPreviewPage
from app.ui.settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)

        # pages
        self.home_page = HomePage(self)
        self.patients_page = PatientsPage(self)
        self.new_report_page = NewReportPage(self)
        self.reports_page = ReportsPage(self)
        self.preview_page = ReportPreviewPage(self)
        self.settings_page = SettingsPage(self)

        self.stack = QStackedWidget()
        for page in (self.home_page, self.patients_page, self.new_report_page,
                     self.reports_page, self.preview_page, self.settings_page):
            self.stack.addWidget(page)

        self.nav_buttons = {}
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.setStyleSheet(STYLESHEET)

        self.go_home()

    # ------------------------------------------------------------- sidebar
    def _build_sidebar(self):
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(212)
        v = QVBoxLayout(bar)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        title = QLabel("Clinic Report\nManager")
        title.setObjectName("SidebarTitle")
        title.setContentsMargins(18, 22, 18, 20)
        v.addWidget(title)

        items = [
            ("home", "  Home", self.go_home),
            ("patients", "  Patients", self.go_patients),
            ("new_report", "  New Report", lambda: self.go_new_report()),
            ("reports", "  Reports", self.go_reports),
            ("settings", "  Settings", self.go_settings),
        ]
        for key, label, slot in items:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(slot)
            v.addWidget(btn)
            self.nav_buttons[key] = btn

        v.addStretch(1)
        footer = QLabel(f"v{APP_VERSION}  ·  local single-PC")
        footer.setObjectName("SidebarFooter")
        footer.setContentsMargins(18, 10, 18, 16)
        v.addWidget(footer)
        return bar

    def _activate_nav(self, key):
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

    # ---------------------------------------------------------- navigation
    def go_home(self):
        self.home_page.refresh()
        self.stack.setCurrentWidget(self.home_page)
        self._activate_nav("home")

    def go_patients(self):
        self.patients_page.refresh()
        self.stack.setCurrentWidget(self.patients_page)
        self._activate_nav("patients")

    def go_new_report(self, patient_id=None):
        self.new_report_page.start_new(patient_id)
        self.stack.setCurrentWidget(self.new_report_page)
        self._activate_nav("new_report")

    def edit_report(self, report_id):
        self.new_report_page.load_report(report_id)
        self.stack.setCurrentWidget(self.new_report_page)
        self._activate_nav("new_report")

    def go_reports(self):
        self.reports_page.refresh()
        self.stack.setCurrentWidget(self.reports_page)
        self._activate_nav("reports")

    def go_settings(self):
        self.settings_page.refresh()
        self.stack.setCurrentWidget(self.settings_page)
        self._activate_nav("settings")

    def show_preview(self, report_id):
        self.preview_page.show_report(report_id)
        self.stack.setCurrentWidget(self.preview_page)
        self._activate_nav("reports")
