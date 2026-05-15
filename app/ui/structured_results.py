"""Table widget that renders a structured-report template and live-flags values.

Columns: Parameter · Result · Unit · Reference · Flag
Section header rows span the full width (gray, bold).
Flag is recomputed every time the user types in a Result cell, and every time
the patient's sex changes (which can change the reference range).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLineEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.templates import Param, compute_flag, reference_text


_SECTION_BG = QColor("#eef2f7")
_SECTION_FG = QColor("#14233b")
_FLAG_COLOURS = {
    "Low": QColor("#1d4ed8"),       # blue
    "High": QColor("#b91c1c"),      # red
    "Abnormal": QColor("#b91c1c"),  # red (qualitative)
    "Normal": QColor("#6b7280"),    # muted grey
}


class StructuredResultsWidget(QWidget):
    """Embeddable widget. Call `load_template(params)` then `set_patient_sex(...)`."""

    def __init__(self):
        super().__init__()
        self._entries: list[dict] = []
        self._sex: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Parameter", "Result", "Unit", "Reference", "Flag"]
        )
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(4, 90)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(True)
        layout.addWidget(self.table)

    # --------------------------------------------------------------- build
    def load_template(self, params: list[Param], sex: str = ""):
        """Rebuild the table from a template. Existing values are discarded."""
        self._sex = sex or ""
        self._entries = []
        self.table.clearSpans()
        self.table.setRowCount(0)

        current_section = object()  # sentinel different from any string / None
        for p in params:
            if p.section != current_section:
                current_section = p.section
                if p.section:
                    self._append_section_row(p.section)
            self._append_param_row(p)

        self.table.resizeRowsToContents()

    def _append_section_row(self, section: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QTableWidgetItem(section)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(QBrush(_SECTION_FG))
        item.setBackground(QBrush(_SECTION_BG))
        item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row, 0, item)
        # fill the rest of the row with same-colour blanks before spanning, so
        # the band reads continuously even if span rendering is off in some styles
        for col in range(1, 5):
            blank = QTableWidgetItem("")
            blank.setBackground(QBrush(_SECTION_BG))
            blank.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, col, blank)
        self.table.setSpan(row, 0, 1, 5)
        self.table.setRowHeight(row, 26)

    def _append_param_row(self, p: Param):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # parameter name (+ optional note on a second line)
        name_text = p.name + (f"\n{p.note}" if p.note else "")
        name_item = QTableWidgetItem(name_text)
        name_item.setFlags(Qt.ItemIsEnabled)
        if p.note:
            # render the note in a slightly smaller secondary tone via tooltip;
            # row height is bumped below
            name_item.setToolTip(p.note)
        self.table.setItem(row, 0, name_item)

        # result — live input
        line_edit = QLineEdit()
        line_edit.setFrame(False)
        line_edit.setPlaceholderText("—")
        line_edit.setStyleSheet(
            "QLineEdit { padding: 4px 6px; background: #ffffff; }"
        )
        idx = len(self._entries)
        line_edit.textChanged.connect(lambda _t, i=idx: self._on_value_changed(i))
        self.table.setCellWidget(row, 1, line_edit)

        unit_item = QTableWidgetItem(p.unit or "")
        unit_item.setFlags(Qt.ItemIsEnabled)
        unit_item.setForeground(QBrush(QColor("#5a6573")))
        self.table.setItem(row, 2, unit_item)

        ref_item = QTableWidgetItem(reference_text(p, self._sex))
        ref_item.setFlags(Qt.ItemIsEnabled)
        ref_item.setForeground(QBrush(QColor("#5a6573")))
        self.table.setItem(row, 3, ref_item)

        flag_item = QTableWidgetItem("")
        flag_item.setFlags(Qt.ItemIsEnabled)
        flag_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 4, flag_item)

        if p.note:
            self.table.setRowHeight(row, 40)
        else:
            self.table.setRowHeight(row, 30)

        self._entries.append({
            "param": p, "row": row,
            "line_edit": line_edit, "ref_item": ref_item, "flag_item": flag_item,
        })

    # ------------------------------------------------------------ updates
    def _on_value_changed(self, idx: int):
        if idx >= len(self._entries):
            return
        e = self._entries[idx]
        p: Param = e["param"]
        value = e["line_edit"].text()
        flag = compute_flag(value, p, self._sex)
        self._apply_flag(e, flag)

    def _apply_flag(self, e: dict, flag: str):
        item: QTableWidgetItem = e["flag_item"]
        # 'Normal' is shown as a muted tick; abnormal flags are bold + coloured.
        if flag == "Normal":
            item.setText("Normal")
            item.setForeground(QBrush(_FLAG_COLOURS["Normal"]))
            f = item.font(); f.setBold(False); item.setFont(f)
        elif flag in ("Low", "High", "Abnormal"):
            item.setText(flag.upper())
            item.setForeground(QBrush(_FLAG_COLOURS[flag]))
            f = item.font(); f.setBold(True); item.setFont(f)
            # also tint the result text the same colour
            e["line_edit"].setStyleSheet(
                f"QLineEdit {{ padding: 4px 6px; background: #ffffff; "
                f"color: {_FLAG_COLOURS[flag].name()}; font-weight: 600; }}"
            )
            return
        else:
            item.setText("")
            item.setForeground(QBrush(QColor("#5a6573")))
        # default result colour
        e["line_edit"].setStyleSheet(
            "QLineEdit { padding: 4px 6px; background: #ffffff; }"
        )

    def set_patient_sex(self, sex: str | None):
        """Re-display references for the new sex and re-flag every row."""
        self._sex = sex or ""
        for e in self._entries:
            e["ref_item"].setText(reference_text(e["param"], self._sex))
        for i in range(len(self._entries)):
            self._on_value_changed(i)

    # ------------------------------------------------------------- values
    def get_rows(self) -> list[dict]:
        """Return only rows the user actually filled in."""
        out = []
        for sort_order, e in enumerate(self._entries):
            value = e["line_edit"].text().strip()
            if not value:
                continue
            p: Param = e["param"]
            out.append({
                "section": p.section,
                "parameter": p.name,
                "value": value,
                "unit": p.unit,
                "reference": reference_text(p, self._sex),
                "flag": compute_flag(value, p, self._sex),
                "sort_order": sort_order,
            })
        return out

    def has_any_value(self) -> bool:
        return any(e["line_edit"].text().strip() for e in self._entries)

    def clear_values(self):
        for e in self._entries:
            e["line_edit"].blockSignals(True)
            e["line_edit"].clear()
            e["line_edit"].blockSignals(False)
            self._apply_flag(e, "")

    def populate_from_saved(self, saved_rows):
        """Fill values by matching saved rows' parameter names to template entries.

        Saved rows whose parameter name no longer matches anything in the
        current template are ignored (kept in DB until the next save).
        """
        by_name = {r["parameter"]: r["value"] or "" for r in saved_rows}
        for e in self._entries:
            value = by_name.get(e["param"].name, "")
            e["line_edit"].setText(value)

    def apply_pairs(self, matched: dict[str, str]) -> int:
        """Fill rows whose parameter name appears in `matched`.

        Returns the number of rows actually filled (i.e. param-name keys that
        existed in the current template).
        """
        filled = 0
        for e in self._entries:
            value = matched.get(e["param"].name)
            if value is None:
                continue
            e["line_edit"].setText(str(value))
            filled += 1
        return filled
