"""Small QPainter charts: line chart, payoff heat map, move strip."""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QToolTip, QWidget

PALETTE = ["#2f6db5", "#d1495b", "#3a9a5b", "#e0a030", "#7b4fa8", "#1f9eb0",
           "#c2672b", "#5d6d7e", "#b04f8f", "#88a838", "#2c3e8f", "#a83232"]
C_COLOUR = QColor("#3a9a5b")
D_COLOUR = QColor("#d1495b")


def colour(i: int) -> QColor:
    return QColor(PALETTE[i % len(PALETTE)])


def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    step = 10 ** math.floor(math.log10((hi - lo) / n))
    for m in (1, 2, 2.5, 5, 10):
        if (hi - lo) / (step * m) <= n:
            step *= m
            break
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-9:
        out.append(round(t, 10))
        t += step
    return out


class LineChart(QWidget):
    """series: list of (label, values); x runs 0..len-1 (or given xs)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.series = []
        self.title = ""
        self.xlabel = ""
        self.ylabel = ""
        self.ymin = None
        self.ymax = None
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._plot = QRectF()
        self._n = 0

    def set_data(self, series, title="", xlabel="", ylabel="", ymin=None, ymax=None):
        self.series = series
        self.title, self.xlabel, self.ylabel = title, xlabel, ylabel
        self.ymin, self.ymax = ymin, ymax
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        fg = pal.color(pal.ColorRole.WindowText)
        p.fillRect(self.rect(), pal.color(pal.ColorRole.Base))
        if not self.series:
            p.setPen(fg)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data yet")
            return
        vals = [v for _, s in self.series for v in s if v is not None and not math.isnan(v)]
        lo = self.ymin if self.ymin is not None else min(vals)
        hi = self.ymax if self.ymax is not None else max(vals)
        if hi - lo < 1e-9:
            hi = lo + 1
        n = max(len(s) for _, s in self.series)
        self._n = n
        fm = p.fontMetrics()
        left, top, right, bottom = 56, 28, 16, 40
        legend_w = 0
        if len(self.series) > 1:
            legend_w = min(220, max(fm.horizontalAdvance(lbl) for lbl, _ in self.series) + 30)
        r = QRectF(left, top, self.width() - left - right - legend_w, self.height() - top - bottom)
        self._plot = r
        p.setPen(fg)
        if self.title:
            f = QFont(p.font())
            f.setBold(True)
            p.setFont(f)
            p.drawText(QRectF(0, 4, self.width(), 20), Qt.AlignmentFlag.AlignHCenter, self.title)
            p.setFont(self.font())
        grid = QColor(fg)
        grid.setAlpha(40)
        for t in nice_ticks(lo, hi):
            y = r.bottom() - (t - lo) / (hi - lo) * r.height()
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(fg)
            lab = f"{t:g}"
            p.drawText(QRectF(0, y - 8, left - 6, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, lab)
        for t in nice_ticks(0, max(1, n - 1), 8):
            x = r.left() + t / max(1, n - 1) * r.width()
            p.setPen(fg)
            p.drawText(QRectF(x - 30, r.bottom() + 2, 60, 16), Qt.AlignmentFlag.AlignHCenter, f"{t:g}")
        p.drawText(QRectF(r.left(), r.bottom() + 18, r.width(), 18), Qt.AlignmentFlag.AlignHCenter, self.xlabel)
        p.save()
        p.translate(12, r.center().y())
        p.rotate(-90)
        p.drawText(QRectF(-r.height() / 2, -10, r.height(), 20), Qt.AlignmentFlag.AlignHCenter, self.ylabel)
        p.restore()
        p.setPen(QPen(fg, 1))
        p.drawLine(r.bottomLeft(), r.bottomRight())
        p.drawLine(r.bottomLeft(), r.topLeft())
        for i, (label, s) in enumerate(self.series):
            path = QPainterPath()
            first = True
            for k, v in enumerate(s):
                if v is None or math.isnan(v):
                    continue
                x = r.left() + k / max(1, n - 1) * r.width()
                y = r.bottom() - (min(max(v, lo), hi) - lo) / (hi - lo) * r.height()
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            p.setPen(QPen(colour(i), 2))
            p.drawPath(path)
        if legend_w:
            y = top
            for i, (label, _) in enumerate(self.series):
                if y > self.height() - 20:
                    break
                p.fillRect(QRectF(r.right() + 12, y + 4, 12, 4), colour(i))
                p.setPen(fg)
                p.drawText(QRectF(r.right() + 28, y - 2, legend_w - 30, 16),
                           Qt.AlignmentFlag.AlignVCenter, fm.elidedText(label, Qt.TextElideMode.ElideRight, legend_w - 30))
                y += 17

    def mouseMoveEvent(self, ev):
        r = self._plot
        if not self.series or not r.contains(ev.position()):
            return
        k = round((ev.position().x() - r.left()) / r.width() * max(1, self._n - 1))
        rows = []
        for label, s in sorted(self.series, key=lambda ls: -(ls[1][k] if k < len(ls[1]) and ls[1][k] is not None else -1e9))[:12]:
            if k < len(s) and s[k] is not None:
                rows.append(f"{label}: {s[k]:.3f}")
        QToolTip.showText(ev.globalPosition().toPoint(), f"{self.xlabel} {k}\n" + "\n".join(rows), self)


class HeatMap(QWidget):
    """matrix[i][j] = row player's mean score per turn against column player."""
    CELL = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.names = []
        self.matrix = []
        self.lo, self.hi = 0.0, 5.0
        self.setMouseTracking(True)
        self.label_w = 180

    def set_data(self, names, matrix, lo, hi):
        self.names, self.matrix, self.lo, self.hi = names, matrix, lo, hi
        fm = self.fontMetrics()
        self.label_w = max([fm.horizontalAdvance(n) for n in names] + [60]) + 10
        n = len(names)
        self.setFixedSize(self.label_w + n * self.CELL + 10, self.label_w + n * self.CELL + 10)
        self.update()

    def cell_colour(self, v):
        if v is None or math.isnan(v):
            return QColor("#888888")
        t = (v - self.lo) / (self.hi - self.lo) if self.hi > self.lo else 0.5
        t = min(1.0, max(0.0, t))
        # red (low) -> pale yellow -> green (high)
        if t < 0.5:
            a, b, u = QColor("#c0392b"), QColor("#f4e8b0"), t / 0.5
        else:
            a, b, u = QColor("#f4e8b0"), QColor("#2e8b57"), (t - 0.5) / 0.5
        return QColor(int(a.red() + (b.red() - a.red()) * u), int(a.green() + (b.green() - a.green()) * u),
                      int(a.blue() + (b.blue() - a.blue()) * u))

    def paintEvent(self, ev):
        p = QPainter(self)
        pal = self.palette()
        fg = pal.color(pal.ColorRole.WindowText)
        p.fillRect(self.rect(), pal.color(pal.ColorRole.Base))
        L, c = self.label_w, self.CELL
        p.setPen(fg)
        for i, name in enumerate(self.names):
            p.drawText(QRectF(0, L + i * c, L - 6, c), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)
            p.save()
            p.translate(L + i * c + c / 2 + 5, L - 6)
            p.rotate(-90)
            p.drawText(QRectF(0, -c / 2, L, c), Qt.AlignmentFlag.AlignVCenter, name)
            p.restore()
        for i, row in enumerate(self.matrix):
            for j, v in enumerate(row):
                p.fillRect(QRectF(L + j * c, L + i * c, c - 1, c - 1), self.cell_colour(v))

    def mouseMoveEvent(self, ev):
        L, c = self.label_w, self.CELL
        x, y = ev.position().x() - L, ev.position().y() - L
        if x < 0 or y < 0:
            return
        i, j = int(y // c), int(x // c)
        if i < len(self.names) and j < len(self.names):
            v = self.matrix[i][j]
            w = self.matrix[j][i]
            QToolTip.showText(ev.globalPosition().toPoint(),
                              f"{self.names[i]} vs {self.names[j]}\n"
                              f"{self.names[i]} scored {v:.3f} a turn\n{self.names[j]} scored {w:.3f} a turn", self)


class MoveStrip(QWidget):
    """Two players' moves, wrapped into rows of `per_row` moves (a multiple
    of 10 that fits the width)."""
    CELL = 11
    LEFT = 64

    def __init__(self, parent=None):
        super().__init__(parent)
        self.a, self.b = [], []
        self.na = self.nb = ""
        self.per_row = 100
        self.setMouseTracking(True)

    def set_moves(self, a, b, na, nb):
        self.a, self.b, self.na, self.nb = a, b, na, nb
        self._layout()
        self.update()

    def row_h(self):
        return 2 * self.CELL + 14

    def _layout(self):
        fit = (self.width() - self.LEFT - 10) // self.CELL
        self.per_row = max(10, fit // 10 * 10)
        rows = max(1, math.ceil(len(self.a) / self.per_row))
        self.setMinimumHeight(rows * self.row_h() + 16)

    def resizeEvent(self, ev):
        self._layout()
        super().resizeEvent(ev)

    def paintEvent(self, ev):
        p = QPainter(self)
        pal = self.palette()
        fg = pal.color(pal.ColorRole.WindowText)
        p.fillRect(self.rect(), pal.color(pal.ColorRole.Base))
        c = self.CELL
        f = QFont(p.font())
        f.setPointSizeF(max(6.0, f.pointSizeF() * 0.8))
        p.setFont(f)
        p.setPen(fg)
        for k in range(0, len(self.a), self.per_row):
            row = k // self.per_row
            y = 8 + row * self.row_h()
            p.drawText(QRectF(0, y, self.LEFT - 22, 2 * c), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(k + 1))
            p.drawText(QRectF(self.LEFT - 18, y, 14, c), Qt.AlignmentFlag.AlignCenter, "A")
            p.drawText(QRectF(self.LEFT - 18, y + c, 14, c), Qt.AlignmentFlag.AlignCenter, "B")
            for m in range(k, min(k + self.per_row, len(self.a))):
                x = self.LEFT + (m - k) * c
                p.fillRect(QRectF(x, y, c - 1, c - 1), C_COLOUR if self.a[m] == "C" else D_COLOUR)
                p.fillRect(QRectF(x, y + c, c - 1, c - 1), C_COLOUR if self.b[m] == "C" else D_COLOUR)

    def mouseMoveEvent(self, ev):
        c = self.CELL
        x, y = ev.position().x() - self.LEFT, ev.position().y() - 8
        if x < 0 or y < 0:
            return
        row = int(y // self.row_h())
        col = int(x // c)
        if col >= self.per_row:
            return
        m = row * self.per_row + col
        if m < len(self.a):
            QToolTip.showText(ev.globalPosition().toPoint(),
                              f"Move {m + 1}: {self.na} {self.a[m]}, {self.nb} {self.b[m]}", self)
