"""Dialogs to build / edit a report type's structured template.

`TemplateEditorDialog` manages the list of parameters for one report type.
`ParamEditDialog` edits a single parameter (name, unit, section, reference).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.templates import Param


def _num(text):
    """Parse a number field; blank or invalid -> None."""
    s = (text or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _fmt(n):
    if n is None:
        return ""
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def _rng(lo, hi):
    if lo is not None and hi is not None:
        return f"{_fmt(lo)} – {_fmt(hi)}"
    if hi is not None:
        return f"≤ {_fmt(hi)}"
    if lo is not None:
        return f"≥ {_fmt(lo)}"
    return ""


def ref_summary(p: Param) -> str:
    """One-line human summary of a parameter's reference, for the list view."""
    if p.expected:
        return f"Expected: {p.expected}"
    if any(v is not None for v in (p.ref_low_male, p.ref_high_male,
                                   p.ref_low_female, p.ref_high_female)):
        return f"M: {_rng(p.ref_low_male, p.ref_high_male) or '—'}   " \
               f"F: {_rng(p.ref_low_female, p.ref_high_female) or '—'}"
    return _rng(p.ref_low, p.ref_high) or "—"


# ---------------------------------------------------------------- single param
_KINDS = [
    ("range", "Numeric range (low – high)"),
    ("atmost", "At most (≤ value)"),
    ("atleast", "At least (≥ value)"),
    ("qual", "Qualitative (expected text)"),
    ("none", "No reference"),
]


class ParamEditDialog(QDialog):
    def __init__(self, parent, param: Param | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit parameter" if param else "Add parameter")
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.section_edit = QLineEdit()
        self.section_edit.setPlaceholderText("e.g. BLOOD PRESSURE  (groups rows; optional)")
        self.name_edit = QLineEdit()
        self.unit_edit = QLineEdit()
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("e.g. Calculated  (optional)")
        self.kind_combo = QComboBox()
        for code, label in _KINDS:
            self.kind_combo.addItem(label, code)
        self.kind_combo.currentIndexChanged.connect(self._update_visibility)

        form.addRow("Section", self.section_edit)
        form.addRow("Parameter name *", self.name_edit)
        form.addRow("Unit", self.unit_edit)
        form.addRow("Reference", self.kind_combo)
        v.addLayout(form)

        # numeric range inputs
        self.low = QLineEdit(); self.low.setPlaceholderText("low")
        self.high = QLineEdit(); self.high.setPlaceholderText("high")
        self.sex_specific = QCheckBox("Different ranges for male / female")
        self.sex_specific.toggled.connect(self._update_visibility)
        self.male_low = QLineEdit(); self.male_low.setPlaceholderText("male low")
        self.male_high = QLineEdit(); self.male_high.setPlaceholderText("male high")
        self.female_low = QLineEdit(); self.female_low.setPlaceholderText("female low")
        self.female_high = QLineEdit(); self.female_high.setPlaceholderText("female high")
        self.expected = QLineEdit(); self.expected.setPlaceholderText('e.g. "Negative"')

        self.ref_form = QFormLayout()
        self._row_low = self._add_row("Low", self.low)
        self._row_high = self._add_row("High", self.high)
        self._row_sex = self._add_row("", self.sex_specific)
        self._row_ml = self._add_row("Male low", self.male_low)
        self._row_mh = self._add_row("Male high", self.male_high)
        self._row_fl = self._add_row("Female low", self.female_low)
        self._row_fh = self._add_row("Female high", self.female_high)
        self._row_exp = self._add_row("Expected value", self.expected)
        v.addLayout(self.ref_form)

        form2 = QFormLayout()
        form2.setLabelAlignment(Qt.AlignRight)
        form2.addRow("Note", self.note_edit)
        v.addLayout(form2)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        if param is not None:
            self._load(param)
        self._update_visibility()

    def _add_row(self, label, widget):
        lbl = QLabel(label)
        self.ref_form.addRow(lbl, widget)
        return (lbl, widget)

    @staticmethod
    def _set_row_visible(row, visible):
        lbl, widget = row
        lbl.setVisible(visible)
        widget.setVisible(visible)

    def _update_visibility(self, *_):
        kind = self.kind_combo.currentData()
        sex = self.sex_specific.isChecked()
        self._set_row_visible(self._row_low, kind in ("range", "atleast") and not (kind == "range" and sex))
        self._set_row_visible(self._row_high, kind in ("range", "atmost") and not (kind == "range" and sex))
        self._set_row_visible(self._row_sex, kind == "range")
        for row in (self._row_ml, self._row_mh, self._row_fl, self._row_fh):
            self._set_row_visible(row, kind == "range" and sex)
        self._set_row_visible(self._row_exp, kind == "qual")

    def _load(self, p: Param):
        self.section_edit.setText(p.section or "")
        self.name_edit.setText(p.name or "")
        self.unit_edit.setText(p.unit or "")
        self.note_edit.setText(p.note or "")
        sex_specific = any(v is not None for v in (p.ref_low_male, p.ref_high_male,
                                                   p.ref_low_female, p.ref_high_female))
        if p.expected:
            kind = "qual"
        elif sex_specific:
            kind = "range"
        elif p.ref_low is not None and p.ref_high is not None:
            kind = "range"
        elif p.ref_high is not None:
            kind = "atmost"
        elif p.ref_low is not None:
            kind = "atleast"
        else:
            kind = "none"
        self.kind_combo.setCurrentIndex(
            next(i for i, (c, _l) in enumerate(_KINDS) if c == kind)
        )
        self.sex_specific.setChecked(sex_specific)
        self.low.setText(_fmt(p.ref_low))
        self.high.setText(_fmt(p.ref_high))
        self.male_low.setText(_fmt(p.ref_low_male))
        self.male_high.setText(_fmt(p.ref_high_male))
        self.female_low.setText(_fmt(p.ref_low_female))
        self.female_high.setText(_fmt(p.ref_high_female))
        self.expected.setText(p.expected or "")

    def _accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Missing name", "Parameter name is required.")
            return
        self.accept()

    def to_param(self) -> Param:
        kind = self.kind_combo.currentData()
        kw = dict(
            name=self.name_edit.text().strip(),
            unit=self.unit_edit.text().strip(),
            section=self.section_edit.text().strip(),
            note=self.note_edit.text().strip(),
        )
        if kind == "range":
            if self.sex_specific.isChecked():
                kw.update(
                    ref_low_male=_num(self.male_low.text()),
                    ref_high_male=_num(self.male_high.text()),
                    ref_low_female=_num(self.female_low.text()),
                    ref_high_female=_num(self.female_high.text()),
                )
            else:
                kw.update(ref_low=_num(self.low.text()), ref_high=_num(self.high.text()))
        elif kind == "atmost":
            kw.update(ref_high=_num(self.high.text()))
        elif kind == "atleast":
            kw.update(ref_low=_num(self.low.text()))
        elif kind == "qual":
            kw.update(expected=(self.expected.text().strip() or None))
        return Param(**kw)


# ---------------------------------------------------------------- whole template
class TemplateEditorDialog(QDialog):
    def __init__(self, parent, type_name: str, params: list[Param]):
        super().__init__(parent)
        self.setWindowTitle(f"Template — {type_name}")
        self.setMinimumSize(680, 460)
        self._params: list[Param] = list(params)

        v = QVBoxLayout(self)
        hint = QLabel(
            "Define the fields that appear when creating a report of this type. "
            "Each parameter can have a recommended reference range; values are "
            "auto-flagged Low / High when a report is filled in."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Section", "Parameter", "Unit", "Reference"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        v.addWidget(self.table, 1)

        row = QHBoxLayout()
        add_btn = QPushButton("Add parameter")
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit)
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("DangerButton")
        remove_btn.clicked.connect(self._remove)
        up_btn = QPushButton("↑")
        up_btn.setToolTip("Move up")
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn = QPushButton("↓")
        down_btn.setToolTip("Move down")
        down_btn.clicked.connect(lambda: self._move(1))
        for b in (add_btn, edit_btn, remove_btn):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(up_btn)
        row.addWidget(down_btn)
        v.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Save template")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        self._reload()

    # --------------------------------------------------------------- helpers
    def _reload(self, keep_row=None):
        self.table.setRowCount(0)
        for p in self._params:
            i = self.table.rowCount()
            self.table.insertRow(i)
            cells = [p.section or "", p.name + (f"   ({p.note})" if p.note else ""),
                     p.unit or "", ref_summary(p)]
            for c, text in enumerate(cells):
                self.table.setItem(i, c, QTableWidgetItem(text))
        if keep_row is not None and 0 <= keep_row < self.table.rowCount():
            self.table.selectRow(keep_row)

    def _selected(self):
        r = self.table.currentRow()
        return r if 0 <= r < len(self._params) else None

    # --------------------------------------------------------------- actions
    def _add(self):
        dlg = ParamEditDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._params.append(dlg.to_param())
            self._reload(self.table.rowCount())

    def _edit(self, *_):
        idx = self._selected()
        if idx is None:
            QMessageBox.information(self, "Select a parameter", "Please select a parameter first.")
            return
        dlg = ParamEditDialog(self, self._params[idx])
        if dlg.exec() == QDialog.Accepted:
            self._params[idx] = dlg.to_param()
            self._reload(idx)

    def _remove(self):
        idx = self._selected()
        if idx is None:
            return
        del self._params[idx]
        self._reload(min(idx, len(self._params) - 1))

    def _move(self, delta):
        idx = self._selected()
        if idx is None:
            return
        j = idx + delta
        if not (0 <= j < len(self._params)):
            return
        self._params[idx], self._params[j] = self._params[j], self._params[idx]
        self._reload(j)

    def result_params(self) -> list[Param]:
        return self._params
