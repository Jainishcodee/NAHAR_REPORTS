"""A small in-app toast: a green tick or red cross that fades in/out.

Replaces blocking QMessageBox 'Saved' / 'Failed' popups for routine actions
like add patient, save report, save settings. Usage from anywhere with a
reference to the main window:

    self.main.toast_success("Patient registered")
    self.main.toast_error("Please select a patient")
"""
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget,
)


_SUCCESS = "#22a06b"
_ERROR = "#d23a3a"
_BORDER = "#e1e6ee"


class _IconBadge(QWidget):
    """A coloured circle with a hand-drawn tick or cross."""

    def __init__(self, kind):
        super().__init__()
        self._kind = kind
        self.setFixedSize(28, 28)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        colour = QColor(_SUCCESS if self._kind == "success" else _ERROR)
        painter.setBrush(QBrush(colour))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)

        pen = QPen(QColor("#ffffff"), 2.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        if self._kind == "success":
            path = QPainterPath()
            path.moveTo(8, 15)
            path.lineTo(12.5, 19.5)
            path.lineTo(21, 10)
            painter.drawPath(path)
        else:
            painter.drawLine(10, 10, 18, 18)
            painter.drawLine(10, 18, 18, 10)


class Toast(QWidget):
    """A short-lived overlay anchored to its parent's bottom-right corner."""

    DEFAULT_HOLD_MS = 1600

    def __init__(self, parent, text, kind="success", hold_ms=DEFAULT_HOLD_MS):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setObjectName("Toast")
        self._kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 16, 10)
        layout.setSpacing(10)
        layout.addWidget(_IconBadge(kind))
        label = QLabel(text)
        label.setStyleSheet("color: #1f2933; font-weight: 500;")
        layout.addWidget(label)

        accent = _SUCCESS if kind == "success" else _ERROR
        self.setStyleSheet(
            f"QWidget#Toast {{ background: #ffffff; border: 1px solid {_BORDER}; "
            f"border-left: 4px solid {accent}; border-radius: 8px; }}"
        )

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self.adjustSize()
        self._place()

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(280)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.deleteLater)

        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.setInterval(hold_ms)
        self._hold.timeout.connect(self._fade_out.start)
        self._fade_in.finished.connect(self._hold.start)

    def _place(self):
        parent = self.parent()
        if parent is None:
            return
        rect = parent.rect()
        margin = 24
        x = rect.right() - self.width() - margin
        y = rect.bottom() - self.height() - margin
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self._fade_in.start()
