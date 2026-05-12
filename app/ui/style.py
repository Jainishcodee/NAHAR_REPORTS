"""Qt style sheet for the application chrome (not the report HTML)."""

STYLESHEET = """
* { font-family: "Segoe UI", Arial, sans-serif; }
QWidget { font-size: 10pt; color: #1f2933; }
QMainWindow, QStackedWidget { background: #f4f6f9; }

/* ---- sidebar ---- */
#Sidebar { background: #14233b; }
#SidebarTitle { color: #eaf0f7; font-size: 13pt; font-weight: 600; }
#SidebarFooter { color: #6b7c95; font-size: 8.5pt; }
QPushButton#NavButton {
    text-align: left; padding: 11px 18px; border: none; border-radius: 0;
    color: #b9c4d4; background: transparent; font-size: 10.5pt;
}
QPushButton#NavButton:hover { background: rgba(255,255,255,0.06); color: #ffffff; }
QPushButton#NavButton:checked {
    background: #1e3a63; color: #ffffff; border-left: 3px solid #5aa0f7;
}

/* ---- headings ---- */
#PageTitle { font-size: 18pt; font-weight: 600; color: #14233b; }
#SectionTitle { font-size: 11pt; font-weight: 600; color: #14233b; }
#Muted { color: #6b7280; }

/* ---- cards ---- */
#Card { background: #ffffff; border: 1px solid #e1e6ee; border-radius: 10px; }

/* ---- buttons ---- */
QPushButton {
    background: #ffffff; border: 1px solid #c7cfdb; border-radius: 7px;
    padding: 7px 14px; color: #2b3648;
}
QPushButton:hover { background: #f0f3f8; border-color: #9fb0c6; }
QPushButton:pressed { background: #e6ebf2; }
QPushButton:disabled { color: #9aa3b0; background: #f3f4f6; border-color: #dde1e8; }
QPushButton#PrimaryButton { background: #2f6fde; border-color: #2f6fde; color: #ffffff; font-weight: 600; }
QPushButton#PrimaryButton:hover { background: #2a63c6; border-color: #2a63c6; }
QPushButton#PrimaryButton:pressed { background: #2456ad; }
QPushButton#DangerButton { background: #ffffff; border-color: #e2b6b6; color: #b3261e; }
QPushButton#DangerButton:hover { background: #fbeaea; }

/* ---- inputs ---- */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
    background: #ffffff; border: 1px solid #c7cfdb; border-radius: 7px; padding: 6px 8px;
    selection-background-color: #2f6fde; selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
    border: 1px solid #2f6fde;
}
QLineEdit:read-only { background: #f3f5f8; color: #5a6573; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: #ffffff; selection-background-color: #e3edff; selection-color: #14233b; }

/* ---- tables ---- */
QTableWidget, QListWidget {
    background: #ffffff; border: 1px solid #e1e6ee; border-radius: 8px; gridline-color: #eef1f6;
}
QHeaderView::section {
    background: #f0f3f8; color: #5a6573; padding: 8px; border: none;
    border-bottom: 1px solid #e1e6ee; font-weight: 600;
}
QTableWidget::item, QListWidget::item { padding: 6px; }
QTableWidget::item:selected, QListWidget::item:selected { background: #e3edff; color: #14233b; }
QTableCornerButton::section { background: #f0f3f8; border: none; }

/* ---- report preview ---- */
QTextBrowser#ReportView { background: #ffffff; border: 1px solid #e1e6ee; border-radius: 8px; padding: 26px; }

/* ---- scrollbars ---- */
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar::handle:vertical { background: #c2cad6; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #aab4c2; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c2cad6; border-radius: 5px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background: #aab4c2; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QCheckBox { spacing: 6px; }
QDialog, QMessageBox { background: #ffffff; }
"""
