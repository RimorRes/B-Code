"""
Braille Text Editor — PyQt6
A light GUI for converting text to braille and exporting for RepRap printing.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QSplitter, QFrame, QScrollArea,
    QGridLayout, QStatusBar, QToolBar, QFileDialog, QMessageBox,
    QComboBox, QSpinBox, QProgressDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QRectF
from PyQt6.QtGui import QFont, QColor, QAction, QPainter, QBrush, QPen

from translate import braille_to_dot_matrix

# ── Braille Translation Table (Grade 1 — Latin alphabet + punctuation) ──────
BRAILLE_MAP = {
    'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑',
    'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚',
    'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕',
    'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞',
    'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽', 'z': '⠵',
    '0': '⠴', '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲',
    '5': '⠢', '6': '⠖', '7': '⠶', '8': '⠦', '9': '⠔',
    ' ': '⠀', ',': '⠂', ';': '⠆', ':': '⠒', '.': '⠲',
    '!': '⠖', '(': '⠶', ')': '⠶', '?': '⠦', "'": '⠄',
    '-': '⠤', '\n': '\n',
}
NUMBER_PREFIX = '⠼'
CAPITAL_PREFIX = '⠠'


def text_to_braille(text: str) -> str:
    """Convert plain text to Grade 1 braille Unicode."""
    result = []
    in_number = False
    for char in text:
        if char.isdigit():
            if not in_number:
                result.append(NUMBER_PREFIX)
                in_number = True
            result.append(BRAILLE_MAP.get(char, '?'))
        else:
            in_number = False
            if char.isupper():
                result.append(CAPITAL_PREFIX)
                result.append(BRAILLE_MAP.get(char.lower(), '?'))
            else:
                result.append(BRAILLE_MAP.get(char, '?'))
    return ''.join(result)


def max_cells_per_page_line(cell_spacing_mm: float) -> int:
    """Return how many braille cells fit across the printable page width."""
    usable_mm = PagePreviewWidget._PAGE_W - (2 * PagePreviewWidget._MARGIN)
    if cell_spacing_mm <= 0:
        return 1
    return max(1, int(usable_mm // cell_spacing_mm) + 1)


def text_to_braille_grid(text: str, max_cells_per_line: int | None = None) -> list[list[str]]:
    """
    Returns a list of rows, each row a list of single braille Unicode chars.
    Converts each input line to braille first, then splits into individual cells
    so prefixes (capital ⠠, number ⠼) each occupy their own grid cell.
    """
    result = []
    wrap_width = max_cells_per_line if max_cells_per_line and max_cells_per_line > 0 else None

    space_cell = BRAILLE_MAP[' ']

    for line in text.split('\n'):
        braille_str = text_to_braille(line)
        row = list(braille_str)

        if wrap_width is None:
            result.append(row)
            continue

        if not row:
            result.append([])
            continue

        remaining = row
        while len(remaining) > wrap_width:
            split_at = -1
            for i in range(wrap_width - 1, -1, -1):
                if remaining[i] == space_cell:
                    split_at = i
                    break

            if split_at <= 0:
                result.append(remaining[:wrap_width])
                remaining = remaining[wrap_width:]
                continue

            result.append(remaining[:split_at])
            remaining = remaining[split_at + 1:]

            # Avoid carrying wrap-boundary spaces to the start of the next line.
            while remaining and remaining[0] == space_cell:
                remaining = remaining[1:]

        result.append(remaining)

    if not result:
        result.append([])

    return result


# ── Stylesheet ────────────────────────────────────────────────────────────────
STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1c1e;
    color: #e8dcc8;
    font-family: 'Courier New', 'Consolas', monospace;
}

QSplitter::handle {
    background-color: #2e3035;
    width: 3px;
}

#panel {
    background-color: #1f2124;
    border: 1px solid #2e3035;
    border-radius: 4px;
}

#panelHeader {
    background-color: #252729;
    border-bottom: 1px solid #2e3035;
    padding: 6px 12px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #c0a060;
    text-transform: uppercase;
}

QTextEdit {
    background-color: #16181a;
    color: #e8dcc8;
    border: none;
    border-radius: 0px;
    font-size: 14px;
    padding: 12px;
    selection-background-color: #c0a060;
    selection-color: #1a1c1e;
}

QPushButton {
    background-color: #252729;
    color: #e8dcc8;
    border: 1px solid #3a3d42;
    border-radius: 3px;
    padding: 7px 16px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    letter-spacing: 1px;
}
QPushButton:hover {
    background-color: #2e3035;
    border-color: #c0a060;
    color: #f0e8d0;
}
QPushButton:pressed {
    background-color: #c0a060;
    color: #1a1c1e;
}
QPushButton#printBtn {
    background-color: #8b4513;
    border-color: #c0a060;
    color: #f0e8d0;
    font-weight: bold;
    font-size: 12px;
    padding: 10px 24px;
}
QPushButton#printBtn:hover {
    background-color: #a0522d;
}

QToolBar {
    background-color: #16181a;
    border-bottom: 1px solid #2e3035;
    spacing: 4px;
    padding: 4px 8px;
}
QToolBar QLabel {
    font-size: 10px;
    letter-spacing: 1px;
    color: #c0a060;
}

QComboBox, QSpinBox {
    background-color: #252729;
    color: #e8dcc8;
    border: 1px solid #3a3d42;
    border-radius: 3px;
    padding: 4px 8px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    min-width: 80px;
}
QComboBox:hover, QSpinBox:hover {
    border-color: #c0a060;
}
QComboBox QAbstractItemView {
    background-color: #252729;
    color: #e8dcc8;
    selection-background-color: #c0a060;
    selection-color: #1a1c1e;
}

QStatusBar {
    background-color: #16181a;
    color: #6a7080;
    border-top: 1px solid #2e3035;
    font-size: 11px;
    padding: 2px 8px;
}
QStatusBar::item { border: none; }

#charMapCell {
    background-color: #252729;
    border: 1px solid #2e3035;
    border-radius: 2px;
    padding: 4px;
    font-size: 11px;
    color: #a09080;
    text-align: center;
}

QScrollBar:vertical {
    background: #1a1c1e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3d42;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #c0a060; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# ── Char Map Widget ───────────────────────────────────────────────────────────
class CharMapWidget(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(4)
        grid.setContentsMargins(8, 8, 8, 8)

        for i, ch in enumerate('abcdefghijklmnopqrstuvwxyz'):
            braille = BRAILLE_MAP.get(ch, '?')
            cell = QLabel(f"{ch.upper()}\n{braille}")
            cell.setObjectName("charMapCell")
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setFixedSize(44, 44)
            cell.setFont(QFont("Courier New", 10))
            cell.setStyleSheet(
                "background-color: #252729; border: 1px solid #2e3035;"
                "border-radius: 2px; color: #a09080; padding: 2px;"
            )
            grid.addWidget(cell, i // 6, i % 6)

        self.setWidget(container)
        self.setStyleSheet("border: none; background: transparent;")


# ── Dot Preview Widget ────────────────────────────────────────────────────────
class DotPreviewWidget(QWidget):
    """Shows the 2×3 dot matrix of the character under the cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dots = [[0, 0], [0, 0], [0, 0], [0, 0]]
        self.setFixedSize(80, 100)

    def set_char(self, braille_char: str) -> None:
        self.dots = braille_to_dot_matrix(braille_char)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1f2124"))

        dot_r = 10
        cols = [18, 48]
        rows = [14, 36, 58, 80]

        for r, row in enumerate(self.dots):
            for c, active in enumerate(row):
                x, y = cols[c], rows[r]
                if active:
                    painter.setBrush(QBrush(QColor("#c0a060")))
                    painter.setPen(Qt.PenStyle.NoPen)
                else:
                    painter.setBrush(QBrush(QColor("#2a2d31")))
                    painter.setPen(QPen(QColor("#3a3d42"), 1))
                painter.drawEllipse(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2)

        painter.end()


# ── Page Preview Widget ───────────────────────────────────────────────────────
class PagePreviewWidget(QWidget):
    """
    Renders a braille grid as a physical A4 page with embossed dots.
    Active dots appear as dark raised bumps on cream paper; inactive dot
    positions show as faint guides so the cell grid is still legible.
    """

    _SCALE = 3.5       # pixels per mm
    _PAGE_W = 210.0    # A4 width mm
    _PAGE_H = 297.0    # A4 height mm
    _MARGIN = 10.0     # page margin mm
    _PAPER  = QColor("#f5f0e8")
    _DOT_ON = QColor("#3d2b1f")
    _DOT_OFF = QColor("#e0d8cc")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid: list[list[str]] = []
        self._dot_spc = 2.5
        self._cell_spc = 6.0
        self._line_spc = 10.0
        self._recalc_size()

    def set_content(
        self,
        braille_grid: list[list[str]],
        dot_spc: float,
        cell_spc: float,
        line_spc: float = 10.0,
    ) -> None:
        self._grid = braille_grid
        self._dot_spc = dot_spc
        self._cell_spc = cell_spc
        self._line_spc = line_spc
        self._recalc_size()
        self.update()

    def _recalc_size(self) -> None:
        s = self._SCALE
        self.setFixedSize(int(self._PAGE_W * s) + 40, int(self._PAGE_H * s) + 40)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#16181a"))

        s = self._SCALE
        ox, oy = 20, 20
        pw = int(self._PAGE_W * s)
        ph = int(self._PAGE_H * s)

        # Drop shadow then paper
        painter.fillRect(ox + 4, oy + 4, pw, ph, QColor(0, 0, 0, 60))
        painter.fillRect(ox, oy, pw, ph, self._PAPER)

        dot_r = max(2.0, self._dot_spc * s * 0.28)

        for row_idx, row in enumerate(self._grid):
            for col_idx, char in enumerate(row):
                matrix = braille_to_dot_matrix(char)
                cx_mm = self._MARGIN + col_idx * self._cell_spc
                cy_mm = self._MARGIN + row_idx * self._line_spc

                for dr, dot_cols in enumerate(matrix[:3]):
                    for dc, active in enumerate(dot_cols):
                        px = ox + (cx_mm + dc * self._dot_spc) * s
                        py = oy + (cy_mm + dr * self._dot_spc) * s
                        painter.setBrush(QBrush(self._DOT_ON if active else self._DOT_OFF))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(
                            QRectF(px - dot_r, py - dot_r, dot_r * 2, dot_r * 2)
                        )

        painter.end()


# ── Print Worker Thread ───────────────────────────────────────────────────────
class PrintWorker(QThread):
    """Sends a G-code job to the printer on a background thread."""

    progress = pyqtSignal(int, int)  # (done, total)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, port: str, gcode_lines: list[str]):
        super().__init__()
        self._port = port
        self._gcode = gcode_lines

    def run(self) -> None:
        from pathgen import PrinterConnection
        try:
            with PrinterConnection(self._port) as conn:
                cmds = [
                    l for l in self._gcode
                    if l.strip() and not l.strip().startswith(";")
                ]
                total = len(cmds)
                for i, cmd in enumerate(cmds):
                    conn.send(cmd)
                    self.progress.emit(i + 1, total)
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


# ── Main Window ───────────────────────────────────────────────────────────────
class BrailleEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B-Code — BrailleRAP Print Tool")
        self.setMinimumSize(900, 620)
        self.resize(1120, 700)

        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()

        self.setStyleSheet(STYLESHEET)

        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_preview)
        self.input_edit.textChanged.connect(lambda: self._update_timer.start(150))
        self.dot_spacing_spin.valueChanged.connect(lambda: self._update_timer.start(150))
        self.cell_spacing_spin.valueChanged.connect(lambda: self._update_timer.start(150))
        self.line_spacing_spin.valueChanged.connect(lambda: self._update_timer.start(150))

    # ── Toolbar ──────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        def lbl(text):
            w = QLabel(text)
            w.setStyleSheet("color: #6a7080; font-size: 10px; letter-spacing: 1px;")
            return w

        tb.addWidget(lbl("  GRADE: "))
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(["Grade 1 (Uncontracted)", "Grade 2 (Contracted — WIP)"])
        tb.addWidget(self.grade_combo)

        tb.addSeparator()
        tb.addWidget(lbl("  DOT SPACING (mm): "))
        self.dot_spacing_spin = QSpinBox()
        self.dot_spacing_spin.setRange(1, 10)
        self.dot_spacing_spin.setValue(2)
        self.dot_spacing_spin.setSuffix(" mm")
        tb.addWidget(self.dot_spacing_spin)

        tb.addSeparator()
        tb.addWidget(lbl("  CELL SPACING (mm): "))
        self.cell_spacing_spin = QSpinBox()
        self.cell_spacing_spin.setRange(2, 20)
        self.cell_spacing_spin.setValue(6)
        self.cell_spacing_spin.setSuffix(" mm")
        tb.addWidget(self.cell_spacing_spin)

        tb.addSeparator()
        tb.addWidget(lbl("  LINE SPACING (mm): "))
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(4, 30)
        self.line_spacing_spin.setValue(10)
        self.line_spacing_spin.setSuffix(" mm")
        tb.addWidget(self.line_spacing_spin)

        tb.addSeparator()
        tb.addWidget(lbl("  PORT: "))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        tb.addWidget(self.port_combo)
        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedWidth(28)
        refresh_btn.setToolTip("Refresh port list")
        refresh_btn.clicked.connect(self._refresh_ports)
        tb.addWidget(refresh_btn)
        self._refresh_ports()

        tb.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        open_act = QAction("📂 Open", self)
        open_act.triggered.connect(self._open_file)
        tb.addAction(open_act)

        save_act = QAction("💾 Save Text", self)
        save_act.triggered.connect(self._save_text)
        tb.addAction(save_act)

        export_braille_act = QAction("⬇ Export Braille", self)
        export_braille_act.triggered.connect(self._export_braille)
        tb.addAction(export_braille_act)

        export_gcode_act = QAction("⬇ Export G-code", self)
        export_gcode_act.triggered.connect(self._export_gcode)
        tb.addAction(export_gcode_act)

    # ── Central UI ───────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # ── Left: Text Input ──────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        hdr_in = QLabel("  ◈  PLAIN TEXT INPUT")
        hdr_in.setObjectName("panelHeader")
        left_layout.addWidget(hdr_in)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Type or paste your text here…\n\n"
            "Physical page preview updates live on the right."
        )
        self.input_edit.setFont(QFont("Courier New", 13))
        left_layout.addWidget(self.input_edit)

        splitter.addWidget(left)

        # ── Middle: Physical Page Preview ────────────────────────────────
        mid = QFrame()
        mid.setObjectName("panel")
        mid_layout = QVBoxLayout(mid)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        hdr_out = QLabel("  ⣿  PHYSICAL PAGE PREVIEW")
        hdr_out.setObjectName("panelHeader")
        mid_layout.addWidget(hdr_out)

        self.page_preview = PagePreviewWidget()
        page_scroll = QScrollArea()
        page_scroll.setWidget(self.page_preview)
        page_scroll.setWidgetResizable(False)
        page_scroll.setStyleSheet("border: none; background: #16181a;")
        mid_layout.addWidget(page_scroll)

        # Print button bar
        print_bar = QWidget()
        print_bar.setStyleSheet("background: #1f2124; border-top: 1px solid #2e3035;")
        pb_layout = QHBoxLayout(print_bar)
        pb_layout.setContentsMargins(12, 8, 12, 8)

        self.print_btn = QPushButton("▶  SEND TO PRINTER")
        self.print_btn.setObjectName("printBtn")
        self.print_btn.clicked.connect(self._send_to_printer)
        pb_layout.addStretch()
        pb_layout.addWidget(self.print_btn)

        mid_layout.addWidget(print_bar)
        splitter.addWidget(mid)

        # ── Right: Sidebar ────────────────────────────────────────────────
        right = QFrame()
        right.setObjectName("panel")
        right.setFixedWidth(200)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        hdr_dot = QLabel("  ⠿  DOT PREVIEW")
        hdr_dot.setObjectName("panelHeader")
        right_layout.addWidget(hdr_dot)

        dot_wrap = QWidget()
        dot_wrap_l = QVBoxLayout(dot_wrap)
        dot_wrap_l.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        dot_wrap_l.setContentsMargins(12, 12, 12, 0)

        self.dot_preview = DotPreviewWidget()
        dot_wrap_l.addWidget(self.dot_preview)

        self.dot_char_label = QLabel("—")
        self.dot_char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dot_char_label.setStyleSheet("font-size: 11px; color: #6a7080; margin-top: 4px;")
        dot_wrap_l.addWidget(self.dot_char_label)

        right_layout.addWidget(dot_wrap)

        hdr_map = QLabel("  ⠿  CHAR MAP")
        hdr_map.setObjectName("panelHeader")
        right_layout.addWidget(hdr_map)

        self.char_map = CharMapWidget()
        right_layout.addWidget(self.char_map)

        splitter.addWidget(right)
        splitter.setSizes([380, 480, 200])

        root.addWidget(splitter)

        self.input_edit.cursorPositionChanged.connect(self._update_dot_preview)

    # ── Status Bar ───────────────────────────────────────────────────────────
    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.char_count_lbl = QLabel("chars: 0")
        self.braille_count_lbl = QLabel("braille cells: 0")
        self.status.addPermanentWidget(self.char_count_lbl)
        self.status.addPermanentWidget(QLabel("  |  "))
        self.status.addPermanentWidget(self.braille_count_lbl)
        self.status.showMessage("Ready.")

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _update_preview(self):
        text = self.input_edit.toPlainText()
        cell_spacing = float(self.cell_spacing_spin.value())
        line_spacing = float(self.line_spacing_spin.value())
        braille_grid = text_to_braille_grid(
            text,
            max_cells_per_line=max_cells_per_page_line(cell_spacing),
        )
        self.page_preview.set_content(
            braille_grid,
            self.dot_spacing_spin.value(),
            cell_spacing,
            line_spacing,
        )
        braille = text_to_braille(text)
        n_chars = len(text.replace('\n', ''))
        n_cells = len(braille.replace('\n', '').replace('⠀', ''))
        self.char_count_lbl.setText(f"chars: {n_chars}")
        self.braille_count_lbl.setText(f"braille cells: {n_cells}")

    def _update_dot_preview(self):
        cursor = self.input_edit.textCursor()
        pos = cursor.position()
        text = self.input_edit.toPlainText()
        if 0 <= pos < len(text):
            ch = text[pos]
            braille_ch = BRAILLE_MAP.get(ch.lower(), '⠀')
            self.dot_preview.set_char(braille_ch)
            self.dot_char_label.setText(f"'{ch}'  →  {braille_ch}")
        else:
            self.dot_preview.set_char('⠀')
            self.dot_char_label.setText("—")

    # ── File Actions ──────────────────────────────────────────────────────────
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Text File", "", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.input_edit.setPlainText(f.read())
                self.status.showMessage(f"Opened: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _save_text(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Text", "document.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.input_edit.toPlainText())
                self.status.showMessage(f"Saved: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_braille(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Braille", "braille_output.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text_to_braille(self.input_edit.toPlainText()))
                self.status.showMessage(f"Braille exported: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_gcode(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Nothing to export", "Please enter some text first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export G-code", "braille_job.gcode",
            "G-code Files (*.gcode *.nc);;All Files (*)"
        )
        if path:
            try:
                from pathgen import generate_gcode
                cell_spacing = float(self.cell_spacing_spin.value())
                line_spacing = float(self.line_spacing_spin.value())
                gcode = generate_gcode(
                    text_to_braille_grid(
                        text,
                        max_cells_per_line=max_cells_per_page_line(cell_spacing),
                    ),
                    dot_spacing_mm=self.dot_spacing_spin.value(),
                    cell_spacing_mm=cell_spacing,
                    line_spacing_mm=line_spacing,
                )
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(gcode) + '\n')
                self.status.showMessage(f"G-code exported: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    # ── Printer Actions ───────────────────────────────────────────────────────
    def _refresh_ports(self):
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            ports = []
        self.port_combo.clear()
        self.port_combo.addItems(ports if ports else ["—"])

    def _send_to_printer(self):
        text = self.input_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Nothing to print", "Please enter some text first.")
            return

        port = self.port_combo.currentText()
        if not port or port == "—":
            QMessageBox.warning(self, "No Port", "Select a serial port first.")
            return

        from pathgen import generate_gcode
        cell_spacing = float(self.cell_spacing_spin.value())
        line_spacing = float(self.line_spacing_spin.value())
        braille_grid = text_to_braille_grid(
            text,
            max_cells_per_line=max_cells_per_page_line(cell_spacing),
        )
        gcode = generate_gcode(
            braille_grid,
            dot_spacing_mm=self.dot_spacing_spin.value(),
            cell_spacing_mm=cell_spacing,
            line_spacing_mm=line_spacing,
        )
        cmds = [l for l in gcode if l.strip() and not l.strip().startswith(";")]

        reply = QMessageBox.question(
            self, "Send to Printer",
            f"Send job to {port}?\n\n"
            f"  Lines : {len(braille_grid)}\n"
            f"  G-code commands : {len(cmds)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog("Sending to printer…", "Cancel", 0, len(cmds), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        self._worker = PrintWorker(port, gcode)
        self._worker.progress.connect(lambda done, _t: progress.setValue(done))
        self._worker.finished.connect(lambda: self._on_print_done(progress))
        self._worker.error.connect(lambda msg: self._on_print_error(progress, msg))
        progress.canceled.connect(self._worker.terminate)
        self.print_btn.setEnabled(False)
        self._worker.start()
        self.status.showMessage(f"Sending to {port}…")

    def _on_print_done(self, progress):
        progress.close()
        self.print_btn.setEnabled(True)
        self.status.showMessage("Print job complete.")

    def _on_print_error(self, progress, msg):
        progress.close()
        self.print_btn.setEnabled(True)
        QMessageBox.critical(self, "Printer Error", msg)
        self.status.showMessage("Print failed.")


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Braille Editor")
    app.setFont(QFont("Courier New", 11))

    window = BrailleEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
