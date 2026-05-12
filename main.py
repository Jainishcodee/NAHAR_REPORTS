"""Clinic Report Manager — entry point.

A single-PC desktop app for creating, storing, and exporting medical reports.
All data lives in a local SQLite file (data/clinic.db). No server, no network.

Run:  python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_ORG
from app.db import Database
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)

    db = Database()
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
