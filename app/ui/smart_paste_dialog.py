"""Dialog: paste raw text -> match against the current template -> fill the form."""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from app.parsers import match_to_params, parse_to_pairs
from app.templates import Param


_PLACEHOLDER = """\
Examples that work:

  Hemoglobin: 12.5
  WBC = 9000
  RBC count    5.2
  Platelets    150000

Excel paste (tab-separated):
  Hemoglobin\t12.5\tg/dL
  WBC\t9000\t/cumm

JSON (nested is fine; {"value": ...} wrappers are unwrapped):
  {"hemoglobin": 12.5, "wbc": 9000, "platelets": 250000}
"""


class SmartPasteDialog(QDialog):
    def __init__(self, parent, params: list[Param]):
        super().__init__(parent)
        self._params = params
        self._matched: dict[str, str] = {}
        self._total_keys = 0

        self.setWindowTitle("Smart paste — fill from raw input")
        self.setMinimumSize(580, 480)
        v = QVBoxLayout(self)

        head = QLabel(
            "Paste JSON, an Excel selection, or 'Name: value' lines below. "
            "Parameter names are matched automatically (case- and "
            "punctuation-insensitive)."
        )
        head.setWordWrap(True)
        v.addWidget(head)

        self.text_edit = QPlainTextEdit()
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.text_edit.setFont(mono)
        self.text_edit.setPlaceholderText(_PLACEHOLDER)
        v.addWidget(self.text_edit, 1)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #5a6573; padding: 4px 0;")
        v.addWidget(self.summary)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        preview_btn = QPushButton("Preview match")
        preview_btn.clicked.connect(self._preview)
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.setObjectName("PrimaryButton")
        apply_btn.clicked.connect(self._apply)
        buttons.addButton(preview_btn, QDialogButtonBox.ActionRole)
        buttons.addButton(apply_btn, QDialogButtonBox.AcceptRole)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    # ---------------------------------------------------------------- core
    def _parse_current(self):
        text = self.text_edit.toPlainText()
        pairs = parse_to_pairs(text)
        self._total_keys = len(pairs)
        self._matched = match_to_params(pairs, self._params) if pairs else {}

    def _preview(self):
        self._parse_current()
        if self._total_keys == 0:
            self.summary.setText("No keys detected in input.")
            return
        m = len(self._matched)
        names = sorted(self._matched.keys())
        shown = ", ".join(names[:6])
        more = f"  (+{m - 6} more)" if m > 6 else ""
        self.summary.setText(
            f"Matched {m} of {self._total_keys} keys → {shown}{more}"
        )

    def _apply(self):
        self._parse_current()
        if not self._matched:
            self.summary.setText(
                "Could not match any of the pasted keys to template parameters."
            )
            return
        self.accept()

    def matched_pairs(self):
        """Returns ({param.name: value_str}, total_keys_parsed)."""
        return self._matched, self._total_keys
