"""
Braille Text Editor — PyQt6
A light GUI for converting text to braille and exporting for RepRap printing.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QSplitter, QFrame, QScrollArea,
    QGridLayout, QStatusBar, QToolBar, QFileDialog, QMessageBox,
    QComboBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCharFormat, QAction, QIcon

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

def text_to_braille_grid(text: str) -> list[list[str]]:
    """
    Returns a list of rows, each row a list of braille chars.
    Useful for toolpath generation — each cell = one braille character position.
    """
    lines = text.strip().split('\n')
    return [[text_to_braille(ch) for ch in line] for line in lines]

def braille_to_dot_matrix(braille_char: str) -> list[list[int]]:
    """
    Convert a single braille Unicode character to a 2×4 dot matrix.
    Standard braille cell: dots 1-3 on the left, 4-6 on the right, 7-8 on the bottom row.
    """
    if not braille_char or braille_char == '⠀':
        return [[0, 0], [0, 0], [0, 0], [0, 0]]
    try:
        offset = ord(braille_char) - 0x2800
        dots = [(offset >> i) & 1 for i in range(8)]
        # dots[0]=1, dots[1]=2, dots[2]=3, dots[3]=4, dots[4]=5, dots[5]=6, dots[6]=7, dots[7]=8
        return [
            [dots[0], dots[3]],  # row 1: dot 1, dot 4
            [dots[1], dots[4]],  # row 2: dot 2, dot 5
            [dots[2], dots[5]],  # row 3: dot 3, dot 6
            [dots[6], dots[7]],  # row 4: dot 7, dot 8 (Grade 2 / extended)
        ]
    except Exception:
        return [[0, 0], [0, 0], [0, 0], [0, 0]]


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

/* ── Panels ── */
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

/* ── Text Areas ── */
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

#brailleOutput {
    font-size: 22px;
    letter-spacing: 3px;
    line-height: 2;
    color: #f0e8d0;
}

/* ── Buttons ── */
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

/* ── Toolbar ── */
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

/* ── Combo / Spin ── */
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

/* ── Status Bar ── */
QStatusBar {
    background-color: #16181a;
    color: #6a7080;
    border-top: 1px solid #2e3035;
    font-size: 11px;
    padding: 2px 8px;
}
QStatusBar::item { border: none; }

/* ── Char Map ── */
#charMapCell {
    background-color: #252729;
    border: 1px solid #2e3035;
    border-radius: 2px;
    padding: 4px;
    font-size: 11px;
    color: #a09080;
    text-align: center;
}

/* ── Scrollbar ── */
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

        letters = 'abcdefghijklmnopqrstuvwxyz'
        for i, ch in enumerate(letters):
            braille = BRAILLE_MAP.get(ch, '?')
            cell = QLabel(f"{ch.upper()}\n{braille}")
            cell.setObjectName("charMapCell")
            cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell.setFixedSize(44, 44)
            cell.setFont(QFont("Courier New", 10))
            cell.setStyleSheet("""
                background-color: #252729;
                border: 1px solid #2e3035;
                border-radius: 2px;
                color: #a09080;
                padding: 2px;
            """)
            grid.addWidget(cell, i // 6, i % 6)

        self.setWidget(container)
        self.setStyleSheet("border: none; background: transparent;")


# ── Dot Preview Widget ────────────────────────────────────────────────────────
class DotPreviewWidget(QWidget):
    """Shows the 2×3 dot matrix of the character under cursor."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dots = [[0,0],[0,0],[0,0],[0,0]]
        self.setFixedSize(80, 100)

    def set_char(self, braille_char: str):
        self.dots = braille_to_dot_matrix(braille_char)
        self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush, QPen
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
                painter.drawEllipse(x - dot_r, y - dot_r, dot_r*2, dot_r*2)

        painter.end()


# ── Main Window ───────────────────────────────────────────────────────────────
class BrailleEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Braille Editor — RepRap Print Tool")
        self.setMinimumSize(900, 620)
        self.resize(1120, 700)

        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()

        self.setStyleSheet(STYLESHEET)

        # Live preview timer (debounce)
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_braille)
        self.input_edit.textChanged.connect(lambda: self._update_timer.start(150))

    # ── Toolbar ──────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        self.addToolBar(tb)

        lbl_grade = QLabel("  GRADE: ")
        lbl_grade.setStyleSheet("color: #6a7080; font-size: 10px; letter-spacing: 1px;")
        tb.addWidget(lbl_grade)
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(["Grade 1 (Uncontracted)", "Grade 2 (Contracted — WIP)"])
        tb.addWidget(self.grade_combo)

        tb.addSeparator()

        lbl_dpi = QLabel("  DOT SPACING (mm): ")
        lbl_dpi.setStyleSheet("color: #6a7080; font-size: 10px; letter-spacing: 1px;")
        tb.addWidget(lbl_dpi)
        self.dot_spacing_spin = QSpinBox()
        self.dot_spacing_spin.setRange(1, 10)
        self.dot_spacing_spin.setValue(2)
        self.dot_spacing_spin.setSuffix(" mm")
        tb.addWidget(self.dot_spacing_spin)

        tb.addSeparator()

        lbl_cell = QLabel("  CELL SPACING (mm): ")
        lbl_cell.setStyleSheet("color: #6a7080; font-size: 10px; letter-spacing: 1px;")
        tb.addWidget(lbl_cell)
        self.cell_spacing_spin = QSpinBox()
        self.cell_spacing_spin.setRange(2, 20)
        self.cell_spacing_spin.setValue(6)
        self.cell_spacing_spin.setSuffix(" mm")
        tb.addWidget(self.cell_spacing_spin)

        tb.addSeparator()

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy(),
            spacer.sizePolicy().verticalPolicy()
        )
        from PyQt6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        open_action = QAction("📂 Open", self)
        open_action.triggered.connect(self._open_file)
        tb.addAction(open_action)

        save_action = QAction("💾 Save Text", self)
        save_action.triggered.connect(self._save_text)
        tb.addAction(save_action)

        export_action = QAction("⬇ Export Braille", self)
        export_action.triggered.connect(self._export_braille)
        tb.addAction(export_action)

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
            "Braille preview updates live on the right."
        )
        self.input_edit.setFont(QFont("Courier New", 13))
        left_layout.addWidget(self.input_edit)

        splitter.addWidget(left)

        # ── Middle: Braille Output ────────────────────────────────────────
        mid = QFrame()
        mid.setObjectName("panel")
        mid_layout = QVBoxLayout(mid)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        hdr_out = QLabel("  ⣿  BRAILLE OUTPUT  (unicode preview)")
        hdr_out.setObjectName("panelHeader")
        mid_layout.addWidget(hdr_out)

        self.braille_edit = QTextEdit()
        self.braille_edit.setObjectName("brailleOutput")
        self.braille_edit.setReadOnly(True)
        self.braille_edit.setFont(QFont("Segoe UI Symbol", 20))
        mid_layout.addWidget(self.braille_edit)

        # Print button
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

        # Update dot preview on cursor move
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
    def _update_braille(self):
        text = self.input_edit.toPlainText()
        braille = text_to_braille(text)
        self.braille_edit.setPlainText(braille)

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
                    f.write(self.braille_edit.toPlainText())
                self.status.showMessage(f"Braille exported: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _send_to_printer(self):
        """
        Hook for toolpath generation.
        Exposes: raw text, braille string, dot grid, and print settings.
        Replace the message box body with your RepRap pipeline call.
        """
        text = self.input_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Nothing to print", "Please enter some text first.")
            return

        braille_str = text_to_braille(text)
        dot_grid = text_to_braille_grid(text)          # list[list[str]]  — per character
        dot_spacing_mm = self.dot_spacing_spin.value()
        cell_spacing_mm = self.cell_spacing_spin.value()

        # ── Replace below with your toolpath / GCode generation ──────────
        # Example:
        #   gcode = generate_gcode(dot_grid, dot_spacing_mm, cell_spacing_mm)
        #   send_to_printer(gcode)
        # ─────────────────────────────────────────────────────────────────

        msg = (
            f"Ready to print!\n\n"
            f"  Characters : {len(text.replace(chr(10), ''))}\n"
            f"  Braille cells : {len(braille_str.replace(chr(10),'').replace('⠀',''))}\n"
            f"  Lines : {text.count(chr(10)) + 1}\n"
            f"  Dot spacing : {dot_spacing_mm} mm\n"
            f"  Cell spacing : {cell_spacing_mm} mm\n\n"
            f"(Wire up _send_to_printer() to your GCode pipeline.)"
        )
        QMessageBox.information(self, "Send to Printer", msg)
        self.status.showMessage("Print job prepared.")


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Braille Editor")

    # Smooth font rendering
    from PyQt6.QtGui import QFont
    app.setFont(QFont("Courier New", 11))

    window = BrailleEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
