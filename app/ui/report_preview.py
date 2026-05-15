"""Preview a report (the same HTML used for PDF / print), with export & print."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from app import pdf as pdfmod
from app.config import OUTPUT_DIR


class ReportPreviewPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.report_id = None

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        top = QHBoxLayout()
        back = QPushButton("←  Back to Reports")
        back.clicked.connect(self.main.go_reports)
        top.addWidget(back)
        self.title_label = QLabel("Report")
        self.title_label.setObjectName("PageTitle")
        top.addWidget(self.title_label)
        top.addStretch(1)
        self.status_btn = QPushButton("Mark as Final")
        self.status_btn.clicked.connect(self._toggle_status)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit)
        print_btn = QPushButton("Print")
        print_btn.clicked.connect(self._print)
        pdf_btn = QPushButton("Export PDF")
        pdf_btn.setObjectName("PrimaryButton")
        pdf_btn.clicked.connect(self._export_pdf)
        for b in (self.status_btn, edit_btn, print_btn, pdf_btn):
            top.addWidget(b)
        v.addLayout(top)

        self.browser = QTextBrowser()
        self.browser.setObjectName("ReportView")
        self.browser.setOpenExternalLinks(False)
        v.addWidget(self.browser, 1)

    # -------------------------------------------------------------- display
    def show_report(self, report_id):
        self.report_id = report_id
        report = self.main.db.get_report(report_id)
        if report is None:
            QMessageBox.warning(self, "Not found", "Report not found.")
            self.main.go_reports()
            return
        settings = self.main.db.get_settings()
        test_rows = [dict(r) for r in self.main.db.get_test_results(report_id)]
        self.title_label.setText(f"{report['report_no'] or ''}   ·   {report['title'] or ''}".strip(" ·"))
        self.browser.setHtml(pdfmod.render_report_html(report, settings, test_rows))
        is_final = (report["status"] or "").lower() == "final"
        self.status_btn.setText("Mark as Draft" if is_final else "Mark as Final")

    def _report_and_settings(self):
        return self.main.db.get_report(self.report_id), self.main.db.get_settings()

    def _test_rows(self):
        if self.report_id is None:
            return []
        return [dict(r) for r in self.main.db.get_test_results(self.report_id)]

    # -------------------------------------------------------------- actions
    def _toggle_status(self):
        report = self.main.db.get_report(self.report_id)
        if report is None:
            return
        new_status = "Draft" if (report["status"] or "").lower() == "final" else "Final"
        self.main.db.set_report_status(self.report_id, new_status)
        self.show_report(self.report_id)

    def _edit(self):
        if self.report_id is not None:
            self.main.edit_report(self.report_id)

    def _export_pdf(self):
        report, settings = self._report_and_settings()
        if report is None:
            return
        default_path = OUTPUT_DIR / pdfmod.default_pdf_name(report)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export report PDF", str(default_path), "PDF files (*.pdf)"
        )
        if not path:
            return
        try:
            pdfmod.export_report_pdf(report, settings, path, self._test_rows())
        except Exception as exc:  # noqa: BLE001 - surface any Qt/IO failure to the user
            QMessageBox.critical(self, "PDF error", f"Could not create the PDF:\n{exc}")
            return
        self.main.db.set_report_pdf_path(self.report_id, path)
        if QMessageBox.question(self, "PDF saved",
                                f"Saved to:\n{path}\n\nOpen it now?") == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _print(self):
        report, settings = self._report_and_settings()
        if report is None:
            return
        try:
            pdfmod.print_report(report, settings, self, self._test_rows())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Print error", f"Could not print:\n{exc}")
