"""Clinic Report Manager — entry point.

A single-PC desktop app for creating, storing, and exporting medical reports.
All data lives in a local SQLite file (data/clinic.db). No server, no network.

Run:  python main.py
"""
import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_ORG
from app.db import Database
from app.ui.main_window import MainWindow


def _apply_light_theme(app: QApplication) -> None:
    """Force a consistent light theme regardless of the OS theme.

    Without this, on a Windows dark-mode machine the unstyled QWidget backgrounds
    (page bodies, calendar popup, menus) follow the system palette and come out
    black. Fusion + an explicit palette makes the app look identical everywhere.
    """
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#f4f6f9"))
    p.setColor(QPalette.WindowText, QColor("#1f2933"))
    p.setColor(QPalette.Base, QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase, QColor("#f0f3f8"))
    p.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    p.setColor(QPalette.ToolTipText, QColor("#1f2933"))
    p.setColor(QPalette.Text, QColor("#1f2933"))
    p.setColor(QPalette.Button, QColor("#ffffff"))
    p.setColor(QPalette.ButtonText, QColor("#2b3648"))
    p.setColor(QPalette.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.Link, QColor("#2f6fde"))
    p.setColor(QPalette.Highlight, QColor("#2f6fde"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#9aa3b0"))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor("#a4adba"))
    app.setPalette(p)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    _apply_light_theme(app)

    db = Database()
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
