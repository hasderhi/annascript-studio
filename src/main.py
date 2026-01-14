import sys
import html
import traceback
import tempfile
import os
import re
import webbrowser
import subprocess, sys


from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import (
    Qt, QTimer, QUrl, QDir
)
from PySide6.QtGui import (
    QFont, QTextCursor, QTextDocument, QShortcut, QKeySequence, 
    QColor, QSyntaxHighlighter, QTextCharFormat, QIcon, QPixmap,
    QCursor
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPlainTextEdit,
    QHBoxLayout, QTabBar, QStackedWidget, QToolButton, QSizePolicy,
    QLabel, QGridLayout, QSplitter, QFileDialog, QDialog, 
    QLineEdit, QPushButton, QMessageBox
)
from compiler_api import (
    render_to_tempfile, 
    cleanup_instance_directory, 
    export_standalone_html
)

DEFAULT_PATH = f"{QDir.homePath()}/Documents"
print(f"[ascript] Default path set to {DEFAULT_PATH}")

def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)



class FindReplaceDialog(QDialog):
    def __init__(self, editor: QPlainTextEdit, replace_mode=False, parent=None):
        super().__init__(parent)

        self.editor = editor
        self.replace_mode = replace_mode

        self.setWindowTitle("Find & Replace" if replace_mode else "Find")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background: #2B2B2B;
                color: white;
            }
            QLabel {
                font-size: 13px;
            }
            QLineEdit {
                background: #1E1E1E;
                color: #FFFFFF;
                padding: 4px;
                border: 1px solid #444444;
            }
            QPushButton {
                background: #3C3C3C;
                color: white;
                padding: 6px 12px;
                border: 1px solid #555555;
            }
            QPushButton:hover {
                background: #505050;
            }
            QPushButton:pressed {
                background: #666666;
            }
        """)

        layout = QVBoxLayout(self)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        self.find_edit = QLineEdit()
        find_row.addWidget(self.find_edit)
        layout.addLayout(find_row)

        if self.replace_mode:
            replace_row = QHBoxLayout()
            replace_row.addWidget(QLabel("Replace:"))
            self.replace_edit = QLineEdit()
            replace_row.addWidget(self.replace_edit)
            layout.addLayout(replace_row)

        btn_row = QHBoxLayout()

        find_next_btn = QPushButton("Find Next")
        find_prev_btn = QPushButton("Find Prev")
        btn_row.addWidget(find_next_btn)
        btn_row.addWidget(find_prev_btn)

        find_next_btn.clicked.connect(self.find_next)
        find_prev_btn.clicked.connect(self.find_prev)

        if self.replace_mode:
            replace_btn = QPushButton("Replace")
            replace_all_btn = QPushButton("Replace All")
            btn_row.addWidget(replace_btn)
            btn_row.addWidget(replace_all_btn)

            replace_btn.clicked.connect(self.replace_one)
            replace_all_btn.clicked.connect(self.replace_all)

        layout.addLayout(btn_row)

    def find_next(self):
        text = self.find_edit.text()
        if not text:
            return

        if not self.editor.find(text):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text)

    def find_prev(self):
        text = self.find_edit.text()
        if not text:
            return
        
        if not self.editor.find(text, QTextDocument.FindBackward):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, QTextDocument.FindBackward)

    def replace_one(self):
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()

        cursor = self.editor.textCursor()
        selected = cursor.selectedText()

        if selected == find_text:
            cursor.insertText(replace_text)
        else:
            self.find_next()
            cursor = self.editor.textCursor()
            if cursor.selectedText() == find_text:
                cursor.insertText(replace_text)

    def replace_all(self):
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()

        text = self.editor.toPlainText()
        new_text = text.replace(find_text, replace_text)
        self.editor.setPlainText(new_text)




class RibbonGroup(QWidget):
    def __init__(self, title, buttons):
        super().__init__()
        self.buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 2)
        layout.setSpacing(2)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(3)

        for row, row_buttons in enumerate(buttons):
            for col, text in enumerate(row_buttons):
                if text:
                    btn = QToolButton()
                    btn.setText(text)
                    btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
                    btn.setMinimumWidth(70)
                    btn.setMinimumHeight(28)

                    grid.addWidget(btn, row, col)
                    self.buttons[text] = btn

        layout.addLayout(grid)

        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 10px; color: #ffffff; margin-top: 2px;")
        layout.addWidget(label)

        self.setStyleSheet("""
        RibbonGroup {
            background: #2b2b2b;
            border: 1px solid #444;
        }
        QToolButton {
            background: #3c3c3c;
            color: #eee;
            font-size: 11px;
            border: 1px solid #555;
            padding: 3px 10px;
        }
        QToolButton:hover {
            background: #505050;
        }
        QToolButton:pressed {
            background: #666666;
        }
        """)


class RibbonMenu(QWidget):
    def __init__(self, file_ops, edit_ops, clipboard_ops, font_ops, export_ops, help_ops):
        super().__init__()

        self.file_ops = file_ops
        self.edit_ops = edit_ops
        self.clipboard_ops = clipboard_ops
        self.font_ops = font_ops
        self.export_ops = export_ops
        self.help_ops = help_ops

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_bar = QTabBar()
        for tab_name in ["Home", "Export", "Help"]:
            self.tab_bar.addTab(tab_name)
        self.tab_bar.setExpanding(False)
        layout.addWidget(self.tab_bar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.home_tab = self.make_home_tab()
        self.export_tab = self.make_export_tab()
        self.help_tab = self.make_help_tab()

        self.stack.addWidget(self.home_tab)
        self.stack.addWidget(self.export_tab)
        self.stack.addWidget(self.help_tab)

        self.tab_bar.currentChanged.connect(self.stack.setCurrentIndex)

        self.setStyleSheet("""
        QTabBar::tab {
            padding: 4px 18px;
            background: #3c3c3c;
            color: #eee;
            
            font-weight: 600;
            font-size: 13px;
            border: none;
            margin-right: 1px;
        }
        QTabBar::tab:selected {
            background: #8f0000;
        }
        QTabBar::tab:hover {
            background: #b83b3b;
        }
        QWidget#RibbonContent {
            background: #2b2b2b;
        }
        """)

    def make_home_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(8)

        font_group = RibbonGroup("Font", [
            ["Bold", "Italic", "Super", "Code"],
            ["Bold and Italic", "Highlight","Sub", "Comment"],
        ])

        clipboard_group = RibbonGroup("Clipboard", [
            ["Cut", "Copy"],
            ["Paste", "Select All"]
        ])

        edit_group = RibbonGroup("Edit", [
            ["Undo", "Find"],
            ["Redo", "Find and Replace"]
        ])

        file_group = RibbonGroup("File", [
            ["Save", "Save as"],
            ["Open", "New"]
        ])
        
        file_group.buttons["Save"].clicked.connect(self.file_ops["save"])
        file_group.buttons["Save as"].clicked.connect(self.file_ops["save_as"])
        file_group.buttons["Open"].clicked.connect(self.file_ops["open"])
        file_group.buttons["New"].clicked.connect(self.file_ops["new"])

        edit_group.buttons["Undo"].clicked.connect(self.edit_ops["undo"])
        edit_group.buttons["Redo"].clicked.connect(self.edit_ops["redo"])
        edit_group.buttons["Find"].clicked.connect(self.edit_ops["open_find_dialog"])
        edit_group.buttons["Find and Replace"].clicked.connect(self.edit_ops["open_find_replace_dialog"])

        clipboard_group.buttons["Cut"].clicked.connect(self.clipboard_ops["cut"])
        clipboard_group.buttons["Copy"].clicked.connect(self.clipboard_ops["copy"])
        clipboard_group.buttons["Paste"].clicked.connect(self.clipboard_ops["paste"])
        clipboard_group.buttons["Select All"].clicked.connect(self.clipboard_ops["select_all"])

        font_group.buttons["Bold"].clicked.connect(self.font_ops["bold"])
        font_group.buttons["Bold and Italic"].clicked.connect(self.font_ops["bold_italic"])
        font_group.buttons["Italic"].clicked.connect(self.font_ops["italic"])
        font_group.buttons["Code"].clicked.connect(self.font_ops["code"])
        font_group.buttons["Comment"].clicked.connect(self.font_ops["comment"])
        font_group.buttons["Sub"].clicked.connect(self.font_ops["sub"])
        font_group.buttons["Super"].clicked.connect(self.font_ops["super"])
        font_group.buttons["Highlight"].clicked.connect(self.font_ops["highlight"])
        

        layout.addWidget(file_group)
        layout.addWidget(edit_group)
        layout.addWidget(clipboard_group)
        layout.addWidget(font_group)
        layout.addStretch()
        return tab


    def make_export_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(8)

        export_group = RibbonGroup("Export", [
            ["Export File"],
            ["Export File as PDF"]
        ])

        export_group.buttons["Export File"].clicked.connect(self.export_ops["export"])
        export_group.buttons["Export File as PDF"].clicked.connect(self.export_ops["export_pdf"])

        layout.addWidget(export_group)
        layout.addStretch()
        return tab


    def make_help_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(10)

        help_group = RibbonGroup("Help", [
            ["Report a Bug"],
            ["GitHub"]
        ])
        about_group = RibbonGroup("About", [
            ["About this Application", "License"],
            ["Developer Website", "Developer GitHub"]
        ])

        layout.addWidget(help_group)
        layout.addWidget(about_group)
        layout.addStretch()

        def open_url(url):
            webbrowser.open(url)

        help_group.buttons["Report a Bug"].clicked.connect(lambda: open_url("https://tk-dev-software.com/support/"))
        help_group.buttons["GitHub"].clicked.connect(lambda: open_url("https://github.com/hasderhi/annascript-studio"))

        about_group.buttons["About this Application"].clicked.connect(self.help_ops["show_about"])
        about_group.buttons["License"].clicked.connect(self.help_ops["show_license"])
        about_group.buttons["Developer Website"].clicked.connect(lambda: open_url("https://tk-dev-software.com"))
        about_group.buttons["Developer GitHub"].clicked.connect(lambda: open_url("https://github.com/hasderhi/"))

        return tab
    





class AScriptHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.colors = {
            "param_key":     QColor("#7CC4FF"),
            "param_value":   QColor("#A9DBFF"),

            "comment":       QColor("#8A8A8A"),

            "heading":       QColor("#52D7FF"),

            "italic":        QColor("#DDBF84"),
            "bold":          QColor("#F7C96E"),
            "bolditalic":    QColor("#FFE39C"),

            "code":          QColor("#C792EA"),

            "supersub":      QColor("#E0A869"),

            "link_text":     QColor("#FF9C6B"),
            "link_url":      QColor("#FF4A3D"),

            "highlight":     QColor("#DFFF8A"),

            "list_lvl1":     QColor("#9A8BDB"),
            "list_lvl2":     QColor("#CF76C3"),

            "macro_marker":  QColor("#CE8CFF"),
            "macro_inside":  QColor("#9546FD"),

            "table_header":  QColor("#A8FAC0"),
            "table_value":   QColor("#B4AB28"),
        }


        def fmt(color):
            f = QTextCharFormat()
            f.setForeground(color)
            return f

        self.formats = {k: fmt(v) for k, v in self.colors.items()}
        self.param_pattern = re.compile(r"^(@[A-Za-z0-9_]+)(\s*:\s*)(.*)$")
        self.param_key_format   = self.formats["param_key"]
        self.param_value_format = self.formats["param_value"]

        self.rules = []

        self.rules.append((re.compile(r"//.*$"), self.formats["comment"]))

        self.rules.append((re.compile(r"^#{1,4} .*"), self.formats["heading"]))

        self.rules.append((re.compile(r"\*\*\*[^*]+?\*\*\*"), self.formats["bolditalic"]))

        self.rules.append((re.compile(r"\*\*[^*]+?\*\*"), self.formats["bold"]))

        self.rules.append((re.compile(r"\*[^*]+?\*"), self.formats["italic"]))

        self.rules.append((re.compile(r"`[^`]+?`"), self.formats["code"]))

        self.rules.append((re.compile(r"\^\^[^\^]+?\^\^"), self.formats["supersub"]))
        self.rules.append((re.compile(r",,[^,]+?,,"), self.formats["supersub"]))

        self.rules.append((re.compile(r"\[[^\]]+?\]"), self.formats["link_text"]))
        self.rules.append((re.compile(r"\([^)]+?\)"), self.formats["link_url"]))

        self.rules.append((re.compile(r"==[^=]+?=="), self.formats["highlight"]))

        self.rules.append((re.compile(r"^\s*-\s+.+$"), self.formats["list_lvl1"]))
        self.rules.append((re.compile(r"^\s{4}-\s+.+$"), self.formats["list_lvl2"]))
        self.rules.append((re.compile(r"^\s*[0-9]+\.\s+.+$"), self.formats["list_lvl1"]))

        self.rules.append((re.compile(r"^::[A-Za-z0-9_]+"), self.formats["macro_marker"]))
        self.rules.append((re.compile(r"^::$"), self.formats["macro_marker"]))

        self.rules.append((re.compile(r"^\|(\s*[-A-Za-z0-9 ]+\s*\|)+$"), self.formats["table_header"]))
        self.rules.append((re.compile(r"^\|.*\|$"), self.formats["table_value"]))

    def highlightBlock(self, text):
        in_macro = (self.previousBlockState() == 1)

        if text.startswith("::") and not text.startswith(":::"):
            if text.strip() == "::":
                self.setFormat(0, len(text), self.formats["macro_marker"])
                self.setCurrentBlockState(0)
                return
            else:
                self.setFormat(0, len(text), self.formats["macro_marker"])
                self.setCurrentBlockState(1)
                return

        if in_macro:
            self.setFormat(0, len(text), self.formats["macro_inside"])
            if text.strip() == "::":
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
            return

        self.setCurrentBlockState(0)

        m = self.param_pattern.match(text)
        if m:
            key, colon, value = m.groups()

            self.setFormat(0, len(key), self.param_key_format)

            start = len(key) + len(colon)
            self.setFormat(start, len(value), self.param_value_format)

            return

        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)



class AScriptEditor(QPlainTextEdit):
    TAB = " " * 4

    def __init__(self):
        super().__init__()
        self.setFont(QFont("JetBrains Mono", 12))
        self.setStyleSheet("""
            QPlainTextEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: none;
                padding: 6px;
            }
        """)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Tab and not modifiers:
            self.indent_selection()
            return

        if key == Qt.Key_Backtab:
            self.unindent_selection()
            return

        super().keyPressEvent(event)

    def indent_selection(self):
        cursor = self.textCursor()
        doc = self.document()

        self.blockSignals(True)
        cursor.beginEditBlock()

        if cursor.hasSelection():
            start = doc.findBlock(cursor.selectionStart())
            end   = doc.findBlock(cursor.selectionEnd())

            block = start
            while True:
                pos = block.position()

                c = QTextCursor(block)
                c.insertText(self.TAB)

                if block == end:
                    break
                block = block.next()

        else:
            cursor.insertText(self.TAB)

        cursor.endEditBlock()
        self.blockSignals(False)
        self.textChanged.emit()

    def unindent_selection(self):
        cursor = self.textCursor()
        doc = self.document()

        self.blockSignals(True)
        cursor.beginEditBlock()

        if cursor.hasSelection():
            start = doc.findBlock(cursor.selectionStart())
            end   = doc.findBlock(cursor.selectionEnd())

            block = start
            while True:
                text = block.text()

                if text.startswith(self.TAB):
                    c = QTextCursor(block)
                    c.setPosition(block.position())
                    for _ in range(len(self.TAB)):
                        c.deleteChar()

                if block == end:
                    break
                block = block.next()

        else:
            block = doc.findBlock(cursor.position())
            text = block.text()
            if text.startswith(self.TAB):
                c = QTextCursor(block)
                c.setPosition(block.position())
                for _ in range(len(self.TAB)):
                    c.deleteChar()

        cursor.endEditBlock()
        self.blockSignals(False)
        self.textChanged.emit()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("aScript Studio")
        self.resize(1400, 900)

        self.current_file = None
        self.last_preview_path = None
        self.document_modified = False

        splitter = QSplitter(Qt.Horizontal)

        self.editor = AScriptEditor()
        self.highlighter = AScriptHighlighter(self.editor.document())
        self.preview = QWebEngineView()
        self.preview.setContextMenuPolicy(Qt.NoContextMenu)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([750, 650])

        self.update_timer = QTimer()
        self.update_timer.setInterval(150)
        self.update_timer.setSingleShot(True)
        self.editor.textChanged.connect(lambda: self.update_timer.start())
        self.update_timer.timeout.connect(self.update_preview)

        self.editor.textChanged.connect(self.on_text_changed)

        file_ops = {
            "save": self.save_file,
            "save_as": self.save_file_as,
            "open": self.open_file,
            "new": self.new_file
        }
        edit_ops = {
            "undo": self.undo,
            "redo": self.redo,
            "open_find_dialog": self.open_find_dialog,
            "open_find_replace_dialog": self.open_find_replace_dialog,
        }
        clipboard_ops = {
            "cut": self.cut,
            "copy": self.copy,
            "paste": self.paste,
            "select_all": self.select_all
        }
        font_ops = {
            "bold": self.make_bold,
            "italic": self.make_italic,
            "bold_italic": self.make_bold_italic,
            "highlight": self.make_highlight,
            "sub": self.make_sub,
            "super": self.make_super,
            "code": self.make_code,
            "comment": self.make_comment,
        }
        export_ops = {
            "export": self.export_file,
            "export_pdf": self.export_file_to_pdf,
        }
        help_ops = {
            "show_about": self.show_about,
            "show_license": self.show_license
        }

        self.ribbon = RibbonMenu(file_ops, edit_ops, clipboard_ops, font_ops, export_ops, help_ops)
        self.setMenuWidget(self.ribbon)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self.setup_shortcuts()

        self.update_preview()

        self.update_window_title()

        


    def setup_shortcuts(self):
            QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_file)
            QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_file)
            QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_file)
            QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_file_as)

            QShortcut(QKeySequence("Ctrl+B"), self, activated=self.make_bold)
            QShortcut(QKeySequence("Ctrl+I"), self, activated=self.make_italic)
            QShortcut(QKeySequence("Ctrl+Shift+B"), self, activated=self.make_bold_italic)
            QShortcut(QKeySequence("Ctrl+H"), self, activated=self.make_highlight)
            QShortcut(QKeySequence("Ctrl+/"), self, activated=self.make_comment)
            QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self.make_code)
            QShortcut(QKeySequence("Ctrl+,"), self, activated=self.make_sub)
            QShortcut(QKeySequence("Ctrl+."), self, activated=self.make_super)

            QShortcut(QKeySequence("Ctrl+F"), self, activated=self.open_find_dialog)
            QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=self.open_find_replace_dialog)

            QShortcut(QKeySequence("Ctrl+E"), self, activated=self.export_file)
            QShortcut(QKeySequence("Ctrl+Shift+E"), self, activated=self.export_file_to_pdf)

    def insert_text(self, text):
        cursor = self.editor.textCursor()
        cursor.insertText(text)

    def on_text_changed(self):
        self.document_modified = True
        self.update_window_title()


    def update_window_title(self):
        base = "aScript Studio"

        if not self.current_file:
            if self.document_modified:
                self.setWindowTitle(f"{base} – Untitled File *")
            else:
                self.setWindowTitle(f"{base} – Untitled File")
            return

        name = os.path.basename(self.current_file)

        if self.document_modified:
            self.setWindowTitle(f"{base} – {name} *")
        else:
            self.setWindowTitle(f"{base} – {name}")



    def maybe_save(self) -> bool:
            if not self.document_modified:
                return True

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Unsaved Changes")
            msg.setText("You have unsaved changes.")
            msg.setInformativeText("Do you want to save them before proceeding?")
            msg.setStandardButtons(
                QMessageBox.Save |
                QMessageBox.Discard |
                QMessageBox.Cancel
            )
            msg.setDefaultButton(QMessageBox.Save)

            result = msg.exec()

            if result == QMessageBox.Save:
                return self.save_file()

            if result == QMessageBox.Discard:
                return True

            return False


    def new_file(self):
        subprocess.Popen([sys.executable, sys.argv[0]])

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()

        with open(self.current_file, "w", encoding="utf8") as f:
            f.write(self.editor.toPlainText())

        self.document_modified = False
        self.update_window_title()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save aScript", DEFAULT_PATH, "aScript (*.ascr *.ascript)"
        )
        if not path:
            return
        self.current_file = path
        self.save_file()


    def open_file(self):
        if not self.maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Open aScript", DEFAULT_PATH, "aScript (*.ascr *.ascript)"
        )
        if not path:
            return

        self.current_file = path
        with open(path, "r", encoding="utf8") as f:
            self.editor.setPlainText(f.read())

        self.document_modified = False
        self.update_window_title()


    def export_file(self):
        text = self.editor.toPlainText()
        outfile, _ = QFileDialog.getSaveFileName(
            self,
            "Export HTML",
            f"{DEFAULT_PATH}/output.html",
            "HTML Files (*.html)"
        )

        if outfile:
            export_standalone_html(text, outfile)

    def export_file_to_pdf(self):
        text = self.editor.toPlainText()

        outfile, _ = QFileDialog.getSaveFileName(
            self,
            "Export HTML for PDF conversion",
            f"{DEFAULT_PATH}/output.html",
            "HTML Files (*.html)"
        )

        if not outfile:
            return

        export_standalone_html(text, outfile)

        pdf_path = outfile.replace(".html", ".pdf")
        self.convert_to_pdf(outfile, pdf_path)

    def convert_to_pdf(self, html_path: str, pdf_path: str):
        page = QWebEnginePage()

        def handle_load_finished(ok):
            if not ok:
                print("[aScript] Failed to load HTML for PDF export.")
                return

            page.printToPdf(pdf_path)
            print(f"[aScript] PDF exported successfully → {pdf_path}")

        url = QUrl.fromLocalFile(os.path.abspath(html_path))
        page.loadFinished.connect(handle_load_finished)
        page.load(url)
    
    def undo(self):
        self.editor.undo()

    def redo(self):
        self.editor.redo()

    def cut(self):
        self.editor.cut()

    def copy(self):
        self.editor.copy()

    def paste(self):
        self.editor.paste()

    def select_all(self):
        self.editor.selectAll()

    def open_find_dialog(self):
        dlg = FindReplaceDialog(self.editor, replace_mode=False, parent=self)
        dlg.show()

    def open_find_replace_dialog(self):
        dlg = FindReplaceDialog(self.editor, replace_mode=True, parent=self)
        dlg.show()

    def make_bold(self):
        self.wrap_selection("**", "**")

    def make_italic(self):
        self.wrap_selection("*", "*")

    def make_bold_italic(self):
        self.wrap_selection("***", "***")

    def make_highlight(self):
        self.wrap_selection("==", "==")

    def make_comment(self):
        self.wrap_selection("// ", "")

    def make_code(self):
        self.wrap_selection("`", "`")

    def make_sub(self):
        self.wrap_selection(",,", ",,")

    def make_super(self):
        self.wrap_selection("^^", "^^")

    
    def wrap_selection(self, prefix: str, suffix: str):
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()

        cursor.beginEditBlock()

        if selected_text:
            start = cursor.selectionStart()
            end = cursor.selectionEnd()

            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

            cursor.insertText(prefix + selected_text + suffix)

            cursor.setPosition(
                start + len(prefix) + len(selected_text),
                QTextCursor.MoveMode.MoveAnchor
            )

        else:
            cursor.insertText(prefix + suffix)
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.MoveAnchor,
                len(suffix)
            )

        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)


    def sanitize_traceback(self, exc: Exception) -> str:
        tb = traceback.extract_tb(exc.__traceback__)
        lines = []

        for frame in tb:
            filename = frame.filename.split("\\")[-1].split("/")[-1]
            lines.append(f"{filename}:{frame.lineno} → {frame.name}")

        return (
            "Error chain:\n"
            + "\n".join(lines)
            + f"\n\n{type(exc).__name__}: {exc}"
        )


    def update_preview(self):
        source = self.editor.toPlainText()

        try:
            out_path = render_to_tempfile(source)
            self.last_preview_path = out_path
            self.preview.setUrl(QUrl.fromLocalFile(out_path))

        except Exception as e:
            safe_tb = self.sanitize_traceback(e)
            error_html = f"""
            <html>
            <body style="background:#1e1e1e;color:#e6e6e6;padding:1.5rem;font-family:Segoe UI, Arial;">
            <h2 style="color:#ff7777;">Compiler Error</h2>

            <p>
                The compiler stopped because it encountered invalid annaScript syntax.
            </p>

            <ul>
                <li>Check for missing brackets, macros, or keywords</li>
                <li>Make sure all macros are properly closed</li>
                <li>Verify indentation and nesting</li>
            </ul>

            <details style="margin-top:1rem;">
                <summary style="cursor:pointer;color:#ffaaaa;">
                Show technical details
                </summary>
                <pre style="background:#111;padding:0.75rem;border-radius:4px;color:#ff9999;">
{html.escape(safe_tb)}
                </pre>
            </details>

            <p style="margin-top:1rem;font-size:0.9em;color:#bbbbbb;">
                If the error persists, contact the developer via
                <b>Help → Report a Bug</b>.
            </p>
            </body>
            </html>
            """
            self.preview.setHtml(error_html)


    def show_license(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("License")
        dlg.resize(400, 300)

        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(0)  # no gap
        icon_row.setContentsMargins(0, 0, 0, 0)

        pixmap = QPixmap(resource_path("annascriptstudio.png"))
        if not pixmap.isNull():
            icon_label = QLabel(dlg)
            icon_label.setPixmap(
                pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            icon_label.setFixedSize(64, 64)
            icon_row.addWidget(icon_label)

        pixmap_an = QPixmap(resource_path("annascript.png"))
        if not pixmap_an.isNull():
            icon_label_an = QLabel(dlg)
            icon_label_an.setPixmap(
                pixmap_an.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            icon_label_an.setAlignment(Qt.AlignCenter)
            icon_label_an.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            icon_label_an.setFixedSize(64, 64)
            icon_row.addWidget(icon_label_an)

        layout.addLayout(icon_row)


        title_label = QLabel("License", dlg)
        title_font = QFont("Arial", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        license_label = QLabel("""
The following part of the license applies to both<br>
<i>annaScript Studio</i> (The GUI editor) and <i>annaScript</i> (The markup language):<br>

<b>MIT License</b><br><br>

Copyright (c) 2025 <i>Tobias Kisling (Annabeth / tk_dev / hasderhi)</i><br><br>

Permission is hereby granted, free of charge, to any person obtaining a copy<br>
of this software and associated documentation files (the "Software"), to deal<br>
in the Software without restriction, including without limitation the rights<br>
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell<br>
copies of the Software, and to permit persons to whom the Software is furnished<br>
to do so, subject to the following conditions:<br><br>

The above copyright notice and this permission notice shall be included in all<br>
copies or substantial portions of the Software.<br><br>

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR<br>
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,<br>
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE<br>
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,<br>
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN<br>
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.<br><br>

<hr><br>
                               
The following part of the license <b>only</b> applies to <i>annaScript Studio</i> (The GUI editor):

Note on third-party libraries:<br><br>

This application ("annaScript Studio") uses <b>PySide6</b> (Qt for Python) for its GUI framework. PySide6<br>
is licensed under the <b>LGPLv3</b>, which allows dynamic linking in your application.
""", dlg)
        license_label.setAlignment(Qt.AlignCenter)
        license_label.setTextFormat(Qt.RichText)
        layout.addWidget(license_label)



        dlg.exec()

    def show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About annaScript Studio")
        dlg.resize(400, 300)

        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        pixmap = QPixmap(resource_path("annascriptstudio.png"))
        if not pixmap.isNull():
            icon_label = QLabel(dlg)
            icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)

        title_label = QLabel("annaScript Studio", dlg)
        title_font = QFont("Arial", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        version_label = QLabel("v1.0.1", dlg)
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        dev_label = QLabel("Developed by Annabeth Kisling", dlg)
        dev_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(dev_label)

        website_label = QLabel('<a href="https://tk-dev-software.com">tk-dev-software.com</a>', dlg)
        website_label.setAlignment(Qt.AlignCenter)
        website_label.setTextFormat(Qt.RichText)
        website_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        website_label.setOpenExternalLinks(True)
        website_label.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(website_label)

        github_label = QLabel('<a href="https://github.com/hasderhi">@hasderhi on GitHub</a>', dlg)
        github_label.setAlignment(Qt.AlignCenter)
        github_label.setTextFormat(Qt.RichText)
        github_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        github_label.setOpenExternalLinks(True)
        github_label.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(github_label)

        separator_label = QLabel('<hr>', dlg)
        separator_label.setAlignment(Qt.AlignCenter)
        separator_label.setTextFormat(Qt.RichText)
        layout.addWidget(separator_label)

        pixmap_an = QPixmap(resource_path("annascript.png"))
        if not pixmap_an.isNull():
            icon_label_an = QLabel(dlg)
            icon_label_an.setPixmap(pixmap_an.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label_an.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label_an)

        title_label_an = QLabel("annaScript", dlg)
        title_font_an = QFont("Arial", 18, QFont.Bold)
        title_label_an.setFont(title_font_an)
        title_label_an.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label_an)

        version_label_an = QLabel("v1.0.0", dlg)
        version_label_an.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label_an)

        dev_label_an = QLabel("Developed by Annabeth Kisling", dlg)
        dev_label_an.setAlignment(Qt.AlignCenter)
        layout.addWidget(dev_label_an)

        website_label_an = QLabel('<a href="https://tk-dev-software.com">tk-dev-software.com</a>', dlg)
        website_label_an.setAlignment(Qt.AlignCenter)
        website_label_an.setTextFormat(Qt.RichText)
        website_label_an.setTextInteractionFlags(Qt.TextBrowserInteraction)
        website_label_an.setOpenExternalLinks(True)
        website_label_an.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(website_label_an)

        github_label_an = QLabel('<a href="https://github.com/hasderhi">@hasderhi on GitHub</a>', dlg)
        github_label_an.setAlignment(Qt.AlignCenter)
        github_label_an.setTextFormat(Qt.RichText)
        github_label_an.setTextInteractionFlags(Qt.TextBrowserInteraction)
        github_label_an.setOpenExternalLinks(True)
        github_label_an.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(github_label_an)
        dlg.exec()


    def closeEvent(self, event):
        if self.maybe_save():
            try:
                import glob
                for f in glob.glob(os.path.join(tempfile.gettempdir(), "ascript_preview_*.html")):
                    os.remove(f)
                cleanup_instance_directory()
                super().closeEvent(event)
            except:
                pass
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("annascriptstudio.png")))
    win = MainWindow()
    win.show()
    app.exec()
