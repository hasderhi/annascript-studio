"""
# annaScript Studio

## main executable

To change certain application functions, please check the constants below the imports!
"""


# Imports
import sys
import html
import traceback
import tempfile
import os
import re
import webbrowser
import subprocess
import requests
from packaging.version import Version

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtCore import (
    Qt, QTimer, QUrl, QDir, QRegularExpression
)
from PySide6.QtGui import (
    QFont, QTextCursor, QTextDocument, QShortcut, QKeySequence, 
    QColor, QSyntaxHighlighter, QTextCharFormat, QIcon, QPixmap,
    QCursor, QAction, QGuiApplication, QDesktopServices
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPlainTextEdit,
    QHBoxLayout, QTabBar, QStackedWidget, QToolButton, QSizePolicy,
    QLabel, QGridLayout, QSplitter, QFileDialog, QDialog, 
    QLineEdit, QPushButton, QMessageBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QMenu, QCheckBox, QFrame, QScrollArea
)
from compiler_api import (
    render_to_tempfile, 
    cleanup_instance_directory,
    cleanup_force,
    export_standalone_html,
    build_standalone_html,
    BASE_DIR,
    THEMES_SRC
)
from logger import (
    debug,
    success,
    info,
    warning,
    error,
    title,
    website
)


# Constants
DO_NOT_CHECK_FOR_UPDATES = False

CURRENT_VERSION = "v1.2.3"
CURRENT_ANNASCRIPT_VERSION = "v1.2.1"

# change these if you've forked the repo
REPO_OWNER = "hasderhi"
REPO_NAME = "annascript-studio"

# needed to prevent the preview from opening web links internally
WEB_DOMAIN_REGEX = re.compile(
    r'(?:^|/|//)([a-z0-9]+([\-.][a-z0-9]+)*\.[a-z]{2,})(?::[0-9]+)?(?:/.*)?$', 
    re.IGNORECASE
)

# allowed extensions, everything else will not be opened by the preview.
# this is only a draft, will revisit it when the asset logic is implemented.
LOCAL_ASSET_EXTENSIONS = {
    '.html', '.htm', '.xhtml', '.xml', '.json', '.js', '.css',
    '.txt', '.md', '.pdf', '.csv', '.tsv',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.tiff',
    '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac',
    '.mp4', '.webm', '.ogv', '.mov', '.avi', '.mkv'
}


# Startup and helpers
title(CURRENT_VERSION)
website()

# sigh...
if sys.platform == "linux":
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    warning("Linux detected, expect graphic driver warnings (if the UI works, you can ignore them)")

DEFAULT_PATH = f"{QDir.homePath()}/Documents"

info(f"Default path set to {DEFAULT_PATH}")

def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def open_file_or_dir(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])

def get_latest_version(repo_owner, repo_name):
    headers = {
        "User-Agent": "Annascript-Studio-Updater"
    }
    try:
        if not DO_NOT_CHECK_FOR_UPDATES:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
            response = requests.get(url, timeout=(3.05, 5), headers=headers)
            response.raise_for_status()
            return response.json()["tag_name"]
        else:
            debug("Checking for updates is disabled, skipping...")
            return None
    except:
        warning("Could not determine latest release, skipping...")
        return None

update_available = False

LATEST_VERSION = get_latest_version(REPO_OWNER, REPO_NAME)

if LATEST_VERSION:
    if Version(LATEST_VERSION) > Version(CURRENT_VERSION):
        info(f"Update available: {CURRENT_VERSION} -> {LATEST_VERSION}")
        update_available = True
    else:
        success(f"{CURRENT_VERSION} is the newest version")
        update_available = False

if os.path.isfile(resource_path("annascript.png")) == False and os.path.isfile(resource_path("annascriptstudio.png")) == False:
    warning("Could not load icons, check if you are in src directory")


# Find/Replace
class FindReplaceDialog(QDialog):
    def __init__(self, editor, replace_mode=False, parent=None):
        super().__init__(parent)

        self.editor = editor
        self.replace_mode = replace_mode

        self.setWindowTitle("Find & Replace" if replace_mode else "Find")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(420)
        
        self.init_stylesheet()
        self.init_ui()

    def init_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
                color: #E0E0E0;
            }
            QLabel {
                font-size: 13px;
                color: #E0E0E0;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #444444;
                border-radius: 4px;
                selection-background-color: #444444;
            }
            QLineEdit:focus {
                border: 1px solid #8f0000;
            }
            QCheckBox {
                color: #E0E0E0;
                font-size: 12px;
                spacing: 6px;
            }
            QPushButton {
                background-color: #3C3C3C;
                color: white;
                padding: 6px 14px;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #b83b3b;
                border-color: #8f0000;
            }
            QFrame#separator {
                border-top: 1px solid #3E3E3E;
                margin-top: 5px;
                margin-bottom: 5px;
            }
        """)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        grid_layout.addWidget(QLabel("Find:"), 0, 0)
        self.find_edit = QLineEdit()
        grid_layout.addWidget(self.find_edit, 0, 1)

        if self.replace_mode:
            grid_layout.addWidget(QLabel("Replace:"), 1, 0)
            self.replace_edit = QLineEdit()
            grid_layout.addWidget(self.replace_edit, 1, 1)

        main_layout.addLayout(grid_layout)

        options_layout = QHBoxLayout()
        self.case_cb = QCheckBox("Match Case")
        self.whole_cb = QCheckBox("Whole Words")
        self.regex_cb = QCheckBox("Regex")
        
        options_layout.addWidget(self.case_cb)
        options_layout.addWidget(self.whole_cb)
        options_layout.addWidget(self.regex_cb)
        main_layout.addLayout(options_layout)

        sep = QFrame()
        sep.setObjectName("separator")
        main_layout.addWidget(sep)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        find_next_btn = QPushButton("Find Next")
        find_prev_btn = QPushButton("Find Prev")
        btn_layout.addWidget(find_next_btn)
        btn_layout.addWidget(find_prev_btn)

        find_next_btn.clicked.connect(self.find_next)
        find_prev_btn.clicked.connect(self.find_prev)

        if self.replace_mode:
            replace_btn = QPushButton("Replace")
            replace_all_btn = QPushButton("Replace All")
            btn_layout.addWidget(replace_btn)
            btn_layout.addWidget(replace_all_btn)

            replace_btn.clicked.connect(self.replace_one)
            replace_all_btn.clicked.connect(self.replace_all)

        main_layout.addLayout(btn_layout)

        self.find_edit.setFocus()

    def get_find_flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def find_next(self):
        text = self.find_edit.text()
        if not text:
            return False

        flags = self.get_find_flags()
        
        if self.regex_cb.isChecked():
            re_flags = QRegularExpression.PatternOption.NoPatternOption
            if not self.case_cb.isChecked():
                re_flags |= QRegularExpression.PatternOption.CaseInsensitiveOption
            
            expr = QRegularExpression(text, re_flags)
            found = self.editor.find(expr, flags)
        else:
            found = self.editor.find(text, flags)

        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            
            if self.regex_cb.isChecked():
                found = self.editor.find(QRegularExpression(text, re_flags), flags)
            else:
                found = self.editor.find(text, flags)
                
        return found

    def find_prev(self):
        text = self.find_edit.text()
        if not text:
            return

        flags = self.get_find_flags() | QTextDocument.FindFlag.FindBackward

        if self.regex_cb.isChecked():
            re_flags = QRegularExpression.PatternOption.NoPatternOption
            if not self.case_cb.isChecked():
                re_flags |= QRegularExpression.PatternOption.CaseInsensitiveOption
            
            expr = QRegularExpression(text, re_flags)
            found = self.editor.find(expr, flags)
        else:
            found = self.editor.find(text, flags)

        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)
            
            if self.regex_cb.isChecked():
                self.editor.find(QRegularExpression(text, re_flags), flags)
            else:
                self.editor.find(text, flags)

    def replace_one(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_edit.text())
            self.find_next()
        else:
            self.find_next()

    def replace_all(self):
        find_text = self.find_edit.text()
        if not find_text:
            return

        cursor = self.editor.textCursor()
        cursor.beginEditBlock()

        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)

        while self.find_next():
            current_cursor = self.editor.textCursor()
            current_cursor.insertText(self.replace_edit.text())

        cursor.endEditBlock()


# Ribbon Menu
class RibbonGroup(QWidget):
    def __init__(self, title, buttons, parent=None):
        super().__init__(parent)
        self.buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)

        grid = QGridLayout()
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)

        for row, row_buttons in enumerate(buttons):
            for col, text in enumerate(row_buttons):
                if text:
                    btn = QToolButton()
                    btn.setText(text)
                    btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                    btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                    btn.setMinimumWidth(75)
                    btn.setMinimumHeight(26)

                    grid.addWidget(btn, row, col)
                    self.buttons[text] = btn

        layout.addLayout(grid)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("GroupTitle")
        layout.addWidget(label)

        self.init_stylesheet()

    def init_stylesheet(self):
        self.setStyleSheet("""
            RibbonGroup {
                background-color: #252526;
                border: 1px solid #3E3E3E;
                border-radius: 6px;
            }
            QToolButton {
                background-color: #2D2D30; 
                color: #E0E0E0;
                font-size: 11px;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QToolButton:hover {
                background-color: #3E3E42;
                border-color: #555555;
                color: #FFFFFF;
            }
            QToolButton:pressed {
                background-color: #b83b3b;
                border-color: #8f0000;
                color: #FFFFFF;
            }
            QLabel#GroupTitle {
                font-size: 10px;
                font-weight: bold;
                color: #858585;
                background: transparent;
                text-transform: uppercase;
                margin-top: 4px;
            }
        """)


class RibbonMenu(QWidget):
    def __init__(self, file_ops, edit_ops, clipboard_ops, font_ops, insert_ops, export_ops, debug_ops, help_ops, parent=None):
        super().__init__(parent)

        self.file_ops = file_ops
        self.edit_ops = edit_ops
        self.clipboard_ops = clipboard_ops
        self.font_ops = font_ops
        self.insert_ops = insert_ops
        self.export_ops = export_ops
        self.debug_ops = debug_ops
        self.help_ops = help_ops

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_bar = QTabBar()
        for tab_name in ["Home", "Insert", "Export", "Advanced", "Help"]:
            self.tab_bar.addTab(tab_name)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)
        layout.addWidget(self.tab_bar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.home_tab = self.make_home_tab()
        self.insert_tab = self.make_insert_tab()
        self.export_tab = self.make_export_tab()
        self.advanced_tab = self.make_advanced_tab()
        self.help_tab = self.make_help_tab()

        self.stack.addWidget(self.home_tab)
        self.stack.addWidget(self.insert_tab)
        self.stack.addWidget(self.export_tab)
        self.stack.addWidget(self.advanced_tab)
        self.stack.addWidget(self.help_tab)

        self.tab_bar.currentChanged.connect(self.stack.setCurrentIndex)
        self.init_global_stylesheet()

    def init_global_stylesheet(self):
        self.setStyleSheet("""
            QTabBar {
                background-color: #1E1E1E;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                padding: 6px 20px;
                background-color: #1E1E1E;
                color: #969696;
                font-size: 12px;
                font-weight: 500;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:hover {
                color: #E0E0E0;
                background-color: #2D2D2D;
            }
            QTabBar::tab:selected {
                color: #FFFFFF;
                background-color: #2B2B2B;
                border-bottom: 2px solid #8f0000;
            }
            QWidget#RibbonContent {
                background-color: #272626;
                border-top: 1px solid #2D2D2D;
            }
        """)

    def make_home_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)

        file_group = RibbonGroup("File", [
            ["Save", "Save as"],
            ["Open", "New"]
        ])
        edit_group = RibbonGroup("Edit", [
            ["Undo", "Find"],
            ["Redo", "Find and Replace"]
        ])
        clipboard_group = RibbonGroup("Clipboard", [
            ["Cut", "Copy"],
            ["Paste", "Select All"]
        ])
        font_group = RibbonGroup("Font", [
            ["Bold", "Italic", "Underline", "Super", "Center"],
            ["Bold and Italic", "Code", "Highlight", "Sub", "Comment"],
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
        font_group.buttons["Underline"].clicked.connect(self.font_ops["underline"])
        font_group.buttons["Center"].clicked.connect(self.font_ops["center"])

        layout.addWidget(file_group)
        layout.addWidget(edit_group)
        layout.addWidget(clipboard_group)
        layout.addWidget(font_group)
        layout.addStretch()
        return tab

    def make_insert_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)

        insert_group = RibbonGroup("Insert", [
            ["Box", "Box Warning", "Note", "Table", "Pie Chart", "Root"],
            ["Box Danger", "Box Info", "Definition", "Coordinates", "Bar Chart", "Fraction"],
        ])

        insert_group.buttons["Box"].clicked.connect(self.insert_ops["box"])
        insert_group.buttons["Box Danger"].clicked.connect(self.insert_ops["box_danger"])
        insert_group.buttons["Box Warning"].clicked.connect(self.insert_ops["box_warning"])
        insert_group.buttons["Box Info"].clicked.connect(self.insert_ops["box_info"])
        insert_group.buttons["Note"].clicked.connect(self.insert_ops["note"])
        insert_group.buttons["Definition"].clicked.connect(self.insert_ops["def"])
        insert_group.buttons["Table"].clicked.connect(self.insert_ops["table"])
        insert_group.buttons["Coordinates"].clicked.connect(self.insert_ops["coordinates"])
        insert_group.buttons["Pie Chart"].clicked.connect(self.insert_ops["pie_chart"])
        insert_group.buttons["Bar Chart"].clicked.connect(self.insert_ops["bar_chart"])
        insert_group.buttons["Root"].clicked.connect(self.insert_ops["sqrt"])
        insert_group.buttons["Fraction"].clicked.connect(self.insert_ops["frac"])

        layout.addWidget(insert_group)
        layout.addStretch()
        return tab

    def make_export_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)

        export_group = RibbonGroup("Export", [
            ["Export File", "Print"],
            ["Export File as PDF", "Copy HTML"]
        ])

        export_group.buttons["Export File"].clicked.connect(self.export_ops["export"])
        export_group.buttons["Export File as PDF"].clicked.connect(self.export_ops["export_pdf"])
        export_group.buttons["Print"].clicked.connect(self.export_ops["print"])
        export_group.buttons["Copy HTML"].clicked.connect(self.export_ops["copy_html"])

        layout.addWidget(export_group)
        layout.addStretch()
        return tab
    
    def make_advanced_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")

        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)

        advanced_group = RibbonGroup("Advanced", [
            ["Cleanup temporary directories", "Open application directory"],
            ["Open temporary directory", "Open themes directory"]
        ])

        advanced_group.buttons["Cleanup temporary directories"].clicked.connect(self.debug_ops["cleanup_tempdir"])
        advanced_group.buttons["Open temporary directory"].clicked.connect(self.debug_ops["open_tempdir"])
        advanced_group.buttons["Open application directory"].clicked.connect(self.debug_ops["open_basedir"])
        advanced_group.buttons["Open themes directory"].clicked.connect(self.debug_ops["open_themesdir"])

        layout.addWidget(advanced_group)
        layout.addStretch()
        return tab

    def make_help_tab(self):
        tab = QWidget()
        tab.setObjectName("RibbonContent")
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)

        help_group = RibbonGroup("Help", [
            ["Report a Bug"],
            ["GitHub"]
        ])
        about_group = RibbonGroup("About", [
            ["About this Application", "License", "Symbol Reference"],
            ["Developer Website", "Developer GitHub", "Latest Release"]
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
        about_group.buttons["Symbol Reference"].clicked.connect(self.help_ops["show_symbol_ref"])
        about_group.buttons["Developer Website"].clicked.connect(lambda: open_url("https://tk-dev-software.com"))
        about_group.buttons["Developer GitHub"].clicked.connect(lambda: open_url("https://github.com/hasderhi/"))
        about_group.buttons["Latest Release"].clicked.connect(lambda: open_url("https://github.com/hasderhi/annascript-studio/releases/latest"))

        return tab
    

# Highlighter
class AScriptHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.colors = {
            "param_key":     QColor("#7AA2F7"),
            "param_value":   QColor("#93C5FD"),

            "comment":       QColor("#6A9955"),

            "heading":       QColor("#569CD6"),

            "italic":        QColor("#DCDCAA"),
            "bold":          QColor("#D7BA7D"),
            "bolditalic":    QColor("#CE9178"),
            
            "underline":     QColor("#4EC9B0"),

            "code":          QColor("#C586C0"),

            "supersub":      QColor("#D19A66"),

            "link_text":     QColor("#CE9178"),
            "link_url":      QColor("#9CDCFE"),

            "highlight":     QColor("#D1F1A3"),

            "list_lvl1":     QColor("#B48EAD"),
            "list_lvl2":     QColor("#D16474"),

            "macro_marker":  QColor("#FF79C6"),
            "macro_inside":  QColor("#BD93F9"),
            
            "inline_symbol": QColor("#4FC1FF"),

            "table_header":  QColor("#85E89D"),
            "table_value":   QColor("#B5CEA8"),
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

        self.rules.append((re.compile(r"(?<!\*)\*(?!\*)[^*]+?(?<!\*)\*(?!\*)"), self.formats["italic"]))

        self.rules.append((re.compile(r"(?<!\w)_(?!_)[^_]+(?<!_)_(?!\w)"), self.formats["underline"]))

        self.rules.append((re.compile(r"`[^`]+?`"), self.formats["code"]))

        self.rules.append((re.compile(r"\^\^[^\^]+?\^\^"), self.formats["supersub"]))
        self.rules.append((re.compile(r",,[^,]+?,,"), self.formats["supersub"]))

        self.rules.append((re.compile(r"\[[^\]]+?\]"), self.formats["link_text"]))
        self.rules.append((re.compile(r"\([^)]+?\)"), self.formats["link_url"]))

        self.rules.append((re.compile(r"(?<!\w)\\[A-Za-z]+(?:\{[^}]*\})*"), self.formats["inline_symbol"]))

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


# Editor
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
        
        if key == Qt.Key_Down:
            self.move_to_end()

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

    def move_to_end(self):
        # something I don't get why it isn't implemented in QPlainTextEdit 
        # in the first place. Almost every other text edit widget has it.
        cursor = self.textCursor()
        block = cursor.block()
        next_block = block.next()

        if next_block.isValid():
            return

        cursor.movePosition(cursor.MoveOperation.EndOfBlock)
        self.setTextCursor(cursor)


# the amount of code needed just to (reliably) prevent QtWebEngine from opening non-local 
# links is absolutely hilarious. well, i guess chromium just likes to open web pages.
class CustomWebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url: QUrl, _type, isMainFrame):
        url_str = url.toString()
        path_lower = url.path().lower()
        
        if _type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            if path_lower.endswith(('.ascr', '.ascript')):
                # future
                debug(f"annaScript transfer link detected: {url_str}")
                return False

            has_local_ext = any(path_lower.endswith(ext) for ext in LOCAL_ASSET_EXTENSIONS)
            is_localhost = url.host().lower() in ['localhost', '127.0.0.1'] or url.host().lower().endswith('.local')
            
            if has_local_ext or is_localhost:
                return super().acceptNavigationRequest(url, _type, isMainFrame)

            match = WEB_DOMAIN_REGEX.search(url_str)
            if match:
                extracted_domain = match.group(1)
                if not any(extracted_domain.endswith(ext) for ext in LOCAL_ASSET_EXTENSIONS):
                    if url.scheme() in ["http", "https"]:
                        QDesktopServices.openUrl(url)
                    else:
                        QDesktopServices.openUrl(QUrl(f"http://{extracted_domain}"))
                    return False
                    
            # Fallback
            if url.scheme() in ["http", "https"]:
                QDesktopServices.openUrl(url)
                return False

        return super().acceptNavigationRequest(url, _type, isMainFrame)


class FilterableTable(QTableWidget):
    def __init__(self, rows):
        super().__init__(len(rows), 3)
        self.rows_data = rows

        self.setHorizontalHeaderLabels(["Shortcut", "Symbol", "Description"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        self._populate(rows)
        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)

    def _populate(self, rows):
        self.setRowCount(len(rows))
        for r, (a, b, c) in enumerate(rows):
            self.setItem(r, 0, QTableWidgetItem(a))
            self.setItem(r, 1, QTableWidgetItem(b))
            self.setItem(r, 2, QTableWidgetItem(c))

    def filter(self, text):
        text = text.lower()
        for row in range(self.rowCount()):
            visible = any(
                text in self.item(row, col).text().lower()
                for col in range(3)
            )
            self.setRowHidden(row, not visible)

    def mouseDoubleClickEvent(self, event):
        row = self.currentRow()
        if row >= 0:
            QApplication.clipboard().setText(self.item(row, 1).text())
        super().mouseDoubleClickEvent(event)

    def _context_menu(self, pos):
        row = self.currentRow()
        if row < 0:
            return

        menu = QMenu(self)
        copy_shortcut = QAction("Copy Shortcut", self)
        copy_symbol = QAction("Copy Symbol", self)
        copy_desc = QAction("Copy Description", self)

        copy_shortcut.triggered.connect(
            lambda: QApplication.clipboard().setText(self.item(row, 0).text())
        )
        copy_symbol.triggered.connect(
            lambda: QApplication.clipboard().setText(self.item(row, 1).text())
        )
        copy_desc.triggered.connect(
            lambda: QApplication.clipboard().setText(self.item(row, 2).text())
        )

        menu.addAction(copy_shortcut)
        menu.addAction(copy_symbol)
        menu.addAction(copy_desc)
        menu.exec(self.viewport().mapToGlobal(pos))


class SymbolReferenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Symbol Reference")
        self.resize(760, 560)

        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            
            QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #8f0000;
                margin-bottom: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #8f0000;
                background-color: #1E1E1E;
            }

            QTabWidget::pane {
                border: 1px solid #2D2D2D;
                background-color: #252526;
                border-radius: 4px;
                top: -1px;
            }
            
            QTabBar::tab {
                background-color: transparent;
                color: #858585;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
                border-bottom: 2px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                color: #CCCCCC;
                background-color: #2D2D2D;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                color: #FFFFFF;
                background-color: #252526;
                border-bottom: 2px solid #8f0000;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }

            QPushButton {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 12px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #3E3E42;
                border-color: #555555;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #b83b3b;
                border-color: #8f0000;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search shortcut, symbol, or description…")
        self.search.textChanged.connect(self._filter_all)
        layout.addWidget(self.search)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tables = []
        self._add_tab("Math & Logic", self.math_symbols())
        self._add_tab("Greek (lowercase)", self.greek_lower())
        self._add_tab("Greek (uppercase)", self.greek_upper())
        self._add_tab("General", self.general_symbols())

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _add_tab(self, name, data):
        table = FilterableTable(data)
        self.tables.append(table)
        self.tabs.addTab(table, name)

    def _filter_all(self, text):
        for table in self.tables:
            table.filter(text)

    # this is going to be a real pain to update.
    # going to replace this in the next update.

    # update 19/04/2026 - I, in fact, did not replace it.

    # update 13/07/2026 - It's coming soon, I promise...
    def math_symbols(self):
        return [
            ("<->", "↔", "Logical equivalence / bidirectional arrow"),
            ("->", "→", "Right arrow"),
            ("=>", "⇒", "Implication"),
            ("<=>", "⇔", "Logical equivalence"),
            ("<=", "≤", "Less than or equal"),
            (">=", "≥", "Greater than or equal"),
            ("!=", "≠", "Not equal"),
            ("~ / ~~", "≈", "Approximately equal"),
            ("+-", "±", "Plus-minus"),
            ("-+", "∓", "Minus-plus"),
            ("<x>", "×", "Multiplication (with cross)"),
            ("<*>", "•", "Multiplication (with dot)"),

            (r"\frac{x}{y}", "x / y", "Fraction"),
            (r"\bar{x}", "x", "Bar over x"),
            (r"\sqrt{x}", "√x", "Square Root"),
            (r"\binom{x}{y}", "x  y", "x over y"),
            (r"\lim_{x \to y}", "lim x → y", "Limit"),
            (r"\vec{a}", "a→", "Vector"),

            (r"\infty", "∞", "Infinity"),
            (r"\propto", "∝", "Proportional to"),

            (r"\forall", "∀", "For all"),
            (r"\exists", "∃", "There exists"),
            (r"\neg", "¬", "Logical NOT"),

            (r"\in", "∈", "Element of"),
            (r"\notin", "∉", "Not element of"),
            (r"\cup", "∪", "Union"),
            (r"\cap", "∩", "Intersection"),
            (r"\emptyset", "∅", "Empty set"),

            (r"\sum", "∑", "Sum"),
            (r"\prod", "∏", "Product"),
            (r"\int", "∫", "Integral"),
            (r"\partial", "∂", "Partial derivative"),
            (r"\nabla", "∇", "Nabla / gradient"),

            (r"\N", "ℕ", "Natural numbers"),
            (r"\Z", "ℤ", "Integers"),
            (r"\Q", "ℚ", "Rational numbers"),
            (r"\R", "ℝ", "Real numbers"),
            (r"\C", "ℂ", "Complex numbers"),
            (r"\P", "ℙ", "Probability space"),
            (r"\N0", "ℕ₀", "Natural numbers incl. zero"),
            (r"\R+", "ℝ⁺", "Positive real numbers"),
            (r"\Z-", "ℤ⁻", "Negative integers"),

            (r"\subset", "⊂", "Subset"),
            (r"\supset", "⊃", "Superset"),
            (r"\subseteq", "⊆", "Subset or equal"),
            (r"\supseteq", "⊇", "Superset or equal"),

            (r"\therefore", "∴", "Therefore"),
            (r"\because", "∵", "Because"),
            (r"\degree", "°", "Degree"),

            (r"\equilibrium", "⇌", "Chemical equilibrium"),
            (r"\benzene", "⌬", "Benzene ring"),
            (r"\std", "⦵", "Standard state"),
            (r"\nuclear", "☢", "Radioactive / nuclear"),
        ]

    def greek_lower(self):
        return [(r"\alpha", "α", "Greek letter alpha"),
                (r"\beta", "β", "Greek letter beta"),
                (r"\gamma", "γ", "Greek letter gamma"),
                (r"\delta", "δ", "Greek letter delta"),
                (r"\epsilon", "ε", "Greek letter epsilon"),
                (r"\zeta", "ζ", "Greek letter zeta"),
                (r"\eta", "η", "Greek letter eta"),
                (r"\theta", "θ", "Greek letter theta"),
                (r"\iota", "ι", "Greek letter iota"),
                (r"\kappa", "κ", "Greek letter kappa"),
                (r"\lambda", "λ", "Greek letter lambda"),
                (r"\mu", "μ", "Greek letter mu"),
                (r"\nu", "ν", "Greek letter nu"),
                (r"\xi", "ξ", "Greek letter xi"),
                (r"\omicron", "ο", "Greek letter omicron"),
                (r"\pi", "π", "Greek letter pi"),
                (r"\rho", "ρ", "Greek letter rho"),
                (r"\sigma", "σ", "Greek letter sigma"),
                (r"\tau", "τ", "Greek letter tau"),
                (r"\upsilon", "υ", "Greek letter upsilon"),
                (r"\phi", "φ", "Greek letter phi"),
                (r"\chi", "χ", "Greek letter chi"),
                (r"\psi", "ψ", "Greek letter psi"),
                (r"\omega", "ω", "Greek letter omega")]

    def greek_upper(self):
        return [(r"\Alpha", "Α", "Greek capital alpha"),
                (r"\Beta", "Β", "Greek capital beta"),
                (r"\Gamma", "Γ", "Greek capital gamma"),
                (r"\Delta", "Δ", "Greek capital delta"),
                (r"\Epsilon", "Ε", "Greek capital epsilon"),
                (r"\Zeta", "Ζ", "Greek capital zeta"),
                (r"\Eta", "Η", "Greek capital eta"),
                (r"\Theta", "Θ", "Greek capital theta"),
                (r"\Iota", "Ι", "Greek capital iota"),
                (r"\Kappa", "Κ", "Greek capital kappa"),
                (r"\Lambda", "Λ", "Greek capital lambda"),
                (r"\Mu", "Μ", "Greek capital mu"),
                (r"\Nu", "Ν", "Greek capital nu"),
                (r"\Xi", "Ξ", "Greek capital xi"),
                (r"\Omicron", "Ο", "Greek capital omicron"),
                (r"\Pi", "Π", "Greek capital pi"),
                (r"\Rho", "Ρ", "Greek capital rho"),
                (r"\Sigma", "Σ", "Greek capital sigma"),
                (r"\Tau", "Τ", "Greek capital tau"),
                (r"\Upsilon", "Υ", "Greek capital upsilon"),
                (r"\Phi", "Φ", "Greek capital phi"),
                (r"\Chi", "Χ", "Greek capital chi"),
                (r"\Psi", "Ψ", "Greek capital psi"),
                (r"\Omega", "Ω", "Greek capital omega")]

    def general_symbols(self):
        return [
            (r"\copy", "©", "Copyright"),
            (r"\reg", "®", "Registered trademark"),
            (r"\tm", "™", "Trademark"),
            (r"\sm", "℠", "Service mark"),
            (r"\pcopy", "℗", "Phonogram copyright"),
            (r"\cmd", "⌘", "Command key"),
            (r"\opt", "⌥", "Option key"),
            (r"\shift", "⇧", "Shift key"),
            (r"\enter", "⏎", "Enter key"),
            (r"\back", "⌫", "Backspace"),
            (r"\blank", "␣", "Space"),
            (r"\settings", "⚙", "Settings"),
            (r"\para", "¶", "Paragraph mark"),
            (r"\dag", "†", "Dagger"),
            (r"\ddag", "‡", "Double dagger"),
            (r"\edit", "✎", "Edit"),
            (r"\ditto", "〃", "Ditto mark"),
            (r"\wat", "‽", "Interrobang"),
            (r"\sep", "⁂", "Asterism"),
            (r"\leaf", "❦", "Floral heart"),
            (r"\ok", "✓", "Success"),
            (r"\fail", "✗", "Failure"),
            (r"\warn", "⚠", "Warning"),
            (r"\mail", "✉", "Mail"),
            (r"\star", "★", "Star"),
            (r"\menu", "☰", "Menu"),
            (r"\power", "⏻", "Power"),
            (r"\folder", "🗀", "Folder"),
        ]


# Main
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("annaScript Studio")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 300)

        self.current_file = None
        self.last_preview_path = None
        self.document_modified = False

        splitter = QSplitter(Qt.Horizontal)

        self.editor = AScriptEditor()
        self.highlighter = AScriptHighlighter(self.editor.document())

        self.preview = QWebEngineView()
        self.preview.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.page = CustomWebEnginePage(self.preview)
        self.preview.setPage(self.page)

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
            "underline": lambda: self.apply_formatting("underline"),
            "bold": lambda: self.apply_formatting("bold"),
            "italic": lambda: self.apply_formatting("italic"),
            "bold_italic": lambda: self.apply_formatting("bold_italic"),
            "highlight": lambda: self.apply_formatting("highlight"),
            "sub": lambda: self.apply_formatting("sub"),
            "super": lambda: self.apply_formatting("super"),
            "code": lambda: self.apply_formatting("code"),
            "center": lambda: self.apply_formatting("center"),
            "comment": lambda: self.apply_formatting("underline"),
        }
        insert_ops = {
            "box": lambda: self.apply_formatting("box"),
            "box_danger": lambda: self.apply_formatting("box_danger"),
            "box_warning": lambda: self.apply_formatting("box_warning"),
            "box_info": lambda: self.apply_formatting("box_info"),
            "note": lambda: self.apply_formatting("note"),
            "def": lambda: self.apply_formatting("def"),
            "table": lambda: self.apply_formatting("table"),
            "coordinates": lambda: self.apply_formatting("coordinates"),
            "pie_chart": lambda: self.apply_formatting("pie_chart"),
            "bar_chart": lambda: self.apply_formatting("bar_chart"),
            "sqrt": lambda: self.apply_formatting("sqrt"),
            "frac": lambda: self.apply_formatting("frac"),
        }
        export_ops = {
            "export": self.export_file,
            "export_pdf": self.export_file_to_pdf,
            "print": self.print_document,
            "copy_html": self.copy_html,
        }
        debug_ops = {
            "cleanup_tempdir": self.cleanup_tempdir,
            "open_tempdir": self.open_tempdir,
            "open_themesdir": self.open_themesdir,
            "open_basedir": self.open_basedir,
        }
        help_ops = {
            "show_about": self.show_about,
            "show_license": self.show_license,
            "show_symbol_ref": self.show_symbol_ref,
        }

        self.ribbon = RibbonMenu(file_ops, edit_ops, clipboard_ops, font_ops, insert_ops, export_ops, debug_ops, help_ops)
        self.setMenuWidget(self.ribbon)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self.setup_shortcuts()

        self.update_preview()

        self.update_window_title()

        self.open_file_from_args()

        if update_available:
            self.show_update_dialog(LATEST_VERSION)

        welcome_html = f"""
        <html>
        <head>
        <style>
            body {{
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 20px;
                margin: 0;
            }}
            .welcome-card {{
                background-color: #252526;
                border-left: 4px solid #8f0000;
                border-top: 1px solid #3E3E3E;
                border-right: 1px solid #3E3E3E;
                border-bottom: 1px solid #3E3E3E;
                border-radius: 4px;
                padding: 20px;
                margin-bottom: 16px;
            }}
            h2 {{
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 600;
                margin-top: 0;
                margin-bottom: 8px;
            }}
            .subtitle {{
                color: #858585;
                font-size: 12px;
                font-style: italic;
                margin-bottom: 16px;
            }}
            p {{
                margin-top: 0;
                margin-bottom: 14px;
                color: #CCCCCC;
            }}
            .link-section {{
                background-color: #1A1A1A;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                padding: 12px 16px;
                margin-top: 16px;
            }}
            .link-section h3 {{
                color: #8f0000;
                font-size: 12px;
                margin-top: 0;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            ul {{
                margin: 0;
                padding-left: 20px;
                color: #B0B0B0;
            }}
            li {{
                margin-bottom: 6px;
            }}
            a {{
                color: #b83b3b;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
        </head>
        <body>

        <div class="welcome-card">
            <h2>Welcome to annaScript Studio!</h2>
            <div class="subtitle">Begin typing in the editor or open a file to dismiss this screen.</div>
            
            <p>
                Ready to write? Start a new document in the editor or open an existing one with <kbd>CTRL-O</kbd>.
                Hope you enjoy using annaScript!
            </p>

            <div class="link-section">
                <h3>Useful Resources</h3>
                <ul>
                    <li>Visit the project page: <a href="https://tk-dev-software.com/annascript">tk-dev-software.com/annascript</a></li>
                    <li>Read the setup guide: <a href="https://github.com/hasderhi/annascript-studio?tab=readme-ov-file">annaScript Studio README</a></li>
                    <li>Follow the developer: <a href="https://github.com/hasderhi">@hasderhi on GitHub</a></li>
                </ul>
            </div>
        </div>

        </body>
        </html>
        """
        self.preview.setHtml(welcome_html)

    def show_update_dialog(self, LATEST_VERSION):
        info("Notifying user...")
        msg_box = QMessageBox(self)

        pixmap = QPixmap(resource_path("annascriptstudio.png"))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                64, 64, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            msg_box.setIconPixmap(scaled_pixmap)
            
        msg_box.setWindowIcon(QIcon(resource_path("annascriptstudio.png")))
        msg_box.setWindowTitle("Update Available")
        msg_box.setText(f"A new version ({LATEST_VERSION}) is available!")
        msg_box.setInformativeText("Would you like to go to the download page?")
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1E1E1E;
            }
            QLabel {
                color: #D4D4D4;
                font-size: 13px;
                background: transparent;
            }
            QLabel#qt_msgbox_label {
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                min-width: 75px;
            }
            QPushButton:hover {
                background-color: #3E3E42;
                border-color: #555555;
                color: #FFFFFF;
            }
            QPushButton:default {
                background-color:#8f0000;
                border-color:#b83b3b;
                color: #FFFFFF;
            }
            QPushButton:default:hover {
                background-color:#b83b3b;
                border-color:#b83b3b;
            }
            QPushButton:pressed {
                background-color:#8f0000;
                border-color:#8f0000;
            }
        """)
        
        download_button = msg_box.addButton("Download", QMessageBox.ButtonRole.AcceptRole)
        dismiss_button = msg_box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(download_button)
        msg_box.exec()

        if msg_box.clickedButton() == download_button:
            webbrowser.open("https://github.com/hasderhi/annascript-studio/releases/latest")
            info("User chose to download update, opening browser and continuing with startup...")

    def setup_shortcuts(self):
            QShortcut(QKeySequence("Ctrl+N"), self, activated=self.new_file)
            QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_file)
            QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_file)
            QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_file_as)

            QShortcut(QKeySequence("Ctrl+U"), self, activated=lambda: self.apply_formatting("underline"))
            QShortcut(QKeySequence("Ctrl+B"), self, activated=lambda: self.apply_formatting("bold"))
            QShortcut(QKeySequence("Ctrl+I"), self, activated=lambda: self.apply_formatting("italic"))
            QShortcut(QKeySequence("Ctrl+Shift+B"), self, activated=lambda: self.apply_formatting("bold_italic"))
            QShortcut(QKeySequence("Ctrl+H"), self, activated=lambda: self.apply_formatting("highlight"))
            QShortcut(QKeySequence("Ctrl+/"), self, activated=lambda: self.apply_formatting("comment"))
            QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=lambda: self.apply_formatting("code"))
            QShortcut(QKeySequence("Ctrl+,"), self, activated=lambda: self.apply_formatting("sub"))
            QShortcut(QKeySequence("Ctrl+."), self, activated=lambda: self.apply_formatting("super"))

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

    def get_document_parameter(self, text: str, parameter_name: str) -> str: 
        # magical function that solves all my problems (or almost)
        prefix = f"@{parameter_name}:"
        
        for line in text.splitlines():
            line = line.strip()
            
            if not line or not line.startswith("@"):
                break
                
            if line.startswith(prefix):
                _, value = line.split(":", 1)
                return value.strip()
                            
        raise KeyError(f"Parameter '{parameter_name}' not found in the document header.")

    def update_window_title(self):
        base = "annaScript Studio"

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
        if getattr(sys, "frozen", False):
            # Build > relaunch exe without args
            subprocess.Popen([sys.executable])
        else:
            # Normal Python > relaunch script with interpreter
            subprocess.Popen([sys.executable, sys.argv[0]])

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()

        with open(self.current_file, "w", encoding="utf8") as f:
            f.write(self.editor.toPlainText())

        self.document_modified = False
        self.update_window_title()

    def save_file_as(self):
        editor_text = self.editor.toPlainText()
        try:
            default_filename = os.path.join(DEFAULT_PATH, f"{self.get_document_parameter(editor_text, 'title')}.ascr") 
        except:
            default_filename = os.path.join(DEFAULT_PATH, "untitled.ascr") 
        
        file_filter = "annaScript (*.ascr *.ascript)"
        
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save annaScript", default_filename, file_filter
        )
        if not path:
            return
            
        _, ext = os.path.splitext(path)
        if not ext:
            default_ext = file_filter.split('(')[1].split()[0].replace('*', '')
            path += default_ext

        directory, filename = os.path.split(path)
        base_name, file_ext = os.path.splitext(filename)

        base_name = base_name.strip(" .")

        reserved_pattern = r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$"
        if re.match(reserved_pattern, base_name, re.IGNORECASE):
            base_name = f"_{base_name}"
            path = os.path.join(directory, base_name + file_ext)
            
            QMessageBox.warning(
                self, 
                "Reserved Name Adjusted", 
                f"The name you chose may be reserved by the OS. It has been saved as '{base_name}{file_ext}' to prevent file corruption."
            )

        self.current_file = path
        self.save_file()

    def open_file(self):
        if not self.maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Open annaScript", DEFAULT_PATH, "annaScript (*.ascr *.ascript)"
        )
        if not path:
            return

        self.current_file = path
        with open(path, "r", encoding="utf8") as f:
            self.editor.setPlainText(f.read())

        self.document_modified = False
        self.update_window_title()

    def open_file_from_args(self):
        if len(sys.argv) < 2:
            return

        # Normalize & absolutize path
        path = os.path.abspath(sys.argv[1])

        if not os.path.isfile(path):
            return

        if not self.maybe_save():
            return

        self.current_file = path
        with open(path, "r", encoding="utf-8") as f:
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

        pdf_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            f"{DEFAULT_PATH}/output.pdf",
            "PDF Files (*.pdf)"
        )

        if not pdf_path:
            return

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp.close()

        export_standalone_html(text, tmp.name)

        self.convert_to_pdf(tmp.name, pdf_path)

    def convert_to_pdf(self, html_path: str, pdf_path: str):
        page = QWebEnginePage()

        def handle_load_finished(ok):
            if not ok:
                error("Failed to load HTML for PDF export.")
                return

            def finished(_):
                success(f"PDF exported successfully -> {pdf_path}")
                try:
                    os.remove(html_path) # cleanup temp file
                except OSError:
                    pass

            page.pdfPrintingFinished.connect(finished)
            page.printToPdf(pdf_path)

        url = QUrl.fromLocalFile(os.path.abspath(html_path))
        page.loadFinished.connect(handle_load_finished)
        page.load(url)

    def print_document(self):
        try:
            info("Initiating printing dialog...")

            try:
                editor_text = self.editor.toPlainText()
                darkmode_value = self.get_document_parameter(editor_text, "darkmode")
                if darkmode_value == "1" or darkmode_value == "true" or darkmode_value == "yes":
                    # if this is the case, the user probably doesn't want to continue - printer ink is expensive!

                    warning("Dark mode has been detected! Asking user before proceeding...")
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Dark Mode is enabled.")
                    msg.setText("Dark Mode is enabled.")
                    msg.setInformativeText("Do you want to print this document?")
                    msg.setStandardButtons(
                        QMessageBox.Yes |
                        QMessageBox.No
                    )
                    msg.setDefaultButton(QMessageBox.No)
                    result = msg.exec()
                    if result == QMessageBox.No:
                        warning("Aborting...")
                        return
                    if result == QMessageBox.Yes:
                        warning("Printing anyway...")
                        pass
            except KeyError:
                pass

            html = build_standalone_html(self.editor.toPlainText())
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            dialog.setWindowTitle("Print Document")

            if dialog.exec() != QPrintDialog.Accepted:
                return

            self.print_view = QWebEngineView() # must persist

            def handle_load_finished(ok):
                if not ok:
                    error("Failed to render document for printing.")
                    return

                self.print_view.print(printer)
                success("Document sent to printer.")

            self.print_view.loadFinished.connect(handle_load_finished)
            self.print_view.setHtml(html)
        except Exception as e:
            error(f"Failed to print document: {e}")

    def copy_html(self):
        html = build_standalone_html(self.editor.toPlainText())
        QGuiApplication.clipboard().setText(html)

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

    def apply_formatting(self, format_type):
        wraps = {
            "underline": ("_", "_"),
            "bold": ("**", "**"),
            "italic": ("*", "*"),
            "bold_italic": ("***", "***"),
            "highlight": ("==", "=="),
            "comment": ("// ", ""),
            "code": ("`", "`"),
            "sub": (",,", ",,"),
            "super": ("^^", "^^"),
            "center": ("::center\n", "\n::"),
            
            "box": ("::box\n", "\n::"),
            "box_danger": ("::box type=danger\n", "\n::"),
            "box_warning": ("::box type=warning\n", "\n::"),
            "box_info": ("::box type=info\n", "\n::"),
            "note": ("::note\n", "\n::"),
            "def": ("::def\n", "\n::"),
            "table": ("| ", " |"),
            "coordinates": ("::coordinates scale=20\n", "\n::"),
            "pie_chart": ("::chart type=pie\n", "\n::"),
            "bar_chart": ("::chart type=bar\n", "\n::"),

            "frac": ("\\frac{", "}{}"),
            "sqrt": ("\\sqrt{", "}"),
        }
        prefix, suffix = wraps.get(format_type, ("", ""))
        self.wrap_selection(prefix, suffix)

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
        cursor = self.editor.textCursor()

        try:
            out_path = render_to_tempfile(source, cursor)
            self.last_preview_path = out_path
            self.preview.setUrl(QUrl.fromLocalFile(out_path))

        except Exception as e:
            safe_tb = self.sanitize_traceback(e)
            error_html = f"""
            <html>
            <head>
            <style>
                body {{
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
                    font-size: 13px;
                    line-height: 1.5;
                    padding: 20px;
                    margin: 0;
                }}

                .error-card {{
                    background-color: #252526;
                    border-left: 4px solid #b83b3b;
                    border-top: 1px solid #3E3E3E;
                    border-right: 1px solid #3E3E3E;
                    border-bottom: 1px solid #3E3E3E;
                    border-radius: 4px;
                    padding: 16px;
                    margin-bottom: 16px;
                }}
                h2 {{
                    color: #8f0000;
                    font-size: 16px;
                    font-weight: 600;
                    margin-top: 0;
                    margin-bottom: 10px;
                }}
                p {{
                    margin-top: 0;
                    margin-bottom: 12px;
                    color: #CCCCCC;
                }}
                ul {{
                    margin: 0 0 16px 0;
                    padding-left: 20px;
                    color: #B0B0B0;
                }}
                li {{
                    margin-bottom: 6px;
                }}
                details {{
                    background-color: #1A1A1A;
                    border: 1px solid #2D2D2D;
                    border-radius: 4px;
                    margin-top: 12px;
                }}
                summary {{
                    padding: 8px 12px;
                    font-weight: 600;
                    color: #E57373;
                    cursor: pointer;
                    outline: none;
                    user-select: none;
                }}
                summary:hover {{
                    color: #EF9A9A;
                    background-color: #222222;
                }}
                pre {{
                    background-color: #111111;
                    padding: 12px;
                    margin: 0;
                    border-top: 1px solid #2D2D2D;
                    color: #FF8A80;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    overflow-x: auto;
                    white-space: pre-wrap; /* Wrap long tracebacks beautifully */
                }}
                .footer {{
                    font-size: 11px;
                    color: #858585;
                    margin-top: 16px;
                    border-top: 1px solid #2D2D2D;
                    padding-top: 12px;
                }}
            </style>
            </head>
            <body>
            <div class="error-card">
                <h2>Compiler Error</h2>
                <p>The compiler stopped because it encountered invalid annaScript syntax.</p>
                
                <ul>
                    <li>Check for missing brackets, macros, or keywords</li>
                    <li>Make sure all macros are properly closed</li>
                    <li>Verify indentation and nesting</li>
                </ul>

                <details>
                    <summary>Show details</summary>
                    <pre>{html.escape(safe_tb)}</pre>
                </details>
            </div>

            <div class="footer">
                If the error persists, contact the developer via <b>Help → Report a Bug</b>.
            </div>

            </body>
            </html>
            """
            self.preview.setHtml(error_html)
            if "NoneType" in str(e):
                error(f"Failed to compile: {e} (Likely caused by invalid macro syntax)")
            else:
                error(f"Failed to compile: {e}")

    def show_license(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("License")
        dlg.resize(550, 450)

        dlg.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            QScrollArea {
                border: 1px solid #2D2D2D;
                background-color: #1E1E1E;
            }
            QScrollBar:vertical {
                border: none;
                background: #1E1E1E;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4F4F4F;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 13px;
                line-height: 1.4;
            }
            h1 {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 5px;
            }
            h2 {
                color: #8f0000;
                font-size: 14px;
                font-weight: 600;
                margin-top: 15px;
                margin-bottom: 5px;
            }
            hr {
                border: none;
                border-top: 1px solid #333333;
            }
        """)

        main_layout = QVBoxLayout(dlg)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(16)
        
        icons_to_load = [
            ("apbl.png", 161, 60),
            ("annascriptstudio.png", 60, 60),
            ("annascript.png", 60, 60)
        ]

        for filename, width, height in icons_to_load:
            pixmap = QPixmap(resource_path(filename))
            if not pixmap.isNull():
                lbl = QLabel()
                lbl.setPixmap(pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl.setFixedSize(width, height)
                icon_row.addWidget(lbl)
                
        icon_row.addStretch()
        main_layout.addLayout(icon_row)

        scroll = QScrollArea(dlg)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content.setStyleSheet("background-color: #1E1E1E;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0)

        license_text = """
        <h1>License</h1>
        <p>The following part of the license applies to both <i>annaScript Studio</i> (The GUI editor) 
        and <i>annaScript</i> (The markup language):</p>

        <h2>MIT License</h2>
        <p>Copyright (c) 2025-2026 <b>Annabeth Kisling (tk_dev / hasderhi)</b></p>
        
        <p>Permission is hereby granted, free of charge, to any person obtaining a copy 
        of this software and associated documentation files (the "Software"), to deal 
        in the Software without restriction, including without limitation the rights 
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
        copies of the Software, and to permit persons to whom the Software is furnished 
        to do so, subject to the following conditions:</p>

        <p>The above copyright notice and this permission notice shall be included in all 
        copies or substantial portions of the Software.</p>

        <p style="font-family: monospace; color: #A0A0A0; font-size: 11px;">THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
        WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
        CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.</p>

        <hr>

        <p>The following part of the license <b>only</b> applies to <i>annaScript Studio</i> (The GUI editor):</p>

        <h2>Note on Third-Party Libraries</h2>
        <p>This application ("annaScript Studio") uses <b>PySide6</b> (Qt for Python) for its GUI framework. 
        PySide6 is licensed under the <b>LGPLv3</b>, which allows dynamic linking in your application.</p>

        <p>The editor font used in <i>annaScript Studio</i> is <b>JetBrains Mono</b> by <i>JetBrains s.r.o</i>. 
        This font is licensed under the <b>SIL Open Font License 1.1</b>.</p>
        """

        license_label = QLabel(license_text)
        license_label.setTextFormat(Qt.TextFormat.RichText)
        license_label.setWordWrap(True)

        scroll_layout.addWidget(license_label)
        scroll.setWidget(scroll_content)
        
        main_layout.addWidget(scroll)
        dlg.exec()

    def show_symbol_ref(self):
        dlg = SymbolReferenceDialog()
        dlg.exec()

    def show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About")
        dlg.setFixedSize(580, 360)

        dlg.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #D4D4D4;
            }
            QFrame#card {
                background-color: #252526;
                border: 1px solid #3E3E3E;
                border-radius: 6px;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 12px;
            }
            QLabel#Title {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#Version {
                color: #007ACC;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel#Author {
                color: #858585;
                font-size: 11px;
            }
            a {
                color: #569CD6;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        """)

        main_layout = QVBoxLayout(dlg)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)

        def create_product_card(logo_name, title, version, author):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 15, 15, 15)
            card_layout.setSpacing(6)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            pixmap = QPixmap(resource_path(logo_name))
            if not pixmap.isNull():
                icon_lbl = QLabel()
                icon_lbl.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                card_layout.addWidget(icon_lbl)

            t_lbl = QLabel(title)
            t_lbl.setObjectName("Title")
            t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(t_lbl)

            v_lbl = QLabel(f"Version {version}")
            v_lbl.setObjectName("Version")
            v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(v_lbl)

            a_lbl = QLabel(author)
            a_lbl.setObjectName("Author")
            a_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(a_lbl)

            links_layout = QHBoxLayout()
            links_layout.setSpacing(10)
            links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            def make_link(text, url):
                lbl = QLabel(f'<a href="{url}">{text}</a>')
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                lbl.setOpenExternalLinks(True)
                lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                return lbl

            links_layout.addWidget(make_link("Website", "https://tk-dev-software.com"))
            links_layout.addWidget(make_link("GitHub", "https://github.com/hasderhi"))
            card_layout.addLayout(links_layout)

            return card

        studio_card = create_product_card(
            "annascriptstudio.png", "annaScript Studio", f"{CURRENT_VERSION}", "Developed by Annabeth Kisling"
        )
        language_card = create_product_card(
            "annascript.png", "annaScript Core", f"{CURRENT_ANNASCRIPT_VERSION}", "Developed by Annabeth Kisling"
        )

        columns_layout.addWidget(studio_card)
        columns_layout.addWidget(language_card)
        main_layout.addLayout(columns_layout)

        dlg.exec()


    def cleanup_tempdir(self):
        cleanup_force()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Success")
        msg.setText("Successfully deleted all temporary files.")
        msg.setStandardButtons(
            QMessageBox.Ok
        )
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    def open_tempdir(self):
        open_file_or_dir(f"{tempfile.gettempdir()}/ascriptstudio")

    def open_themesdir(self):
        open_file_or_dir(THEMES_SRC)

    def open_basedir(self):
        open_file_or_dir(BASE_DIR)

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


# run entry
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("annascriptstudio.png")))

    app.setStyleSheet("""
    QMainWindow, QWidget {
        background-color: #202020;
        color: #ffffff;
    }
    """)
    
    # custom scrollbar because PySide defaults to a very 1995 one if global styles are overwritten
    app.setStyleSheet("""
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 15px;
        margin: 0px;
    }

    QScrollBar:horizontal {
        border: none;
        background: transparent;
        height: 10px;
        margin: 0px;
    }

    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #444444;
        min-height: 20px;
        min-width: 20px;
        border-radius: 5px;
        margin: 2px
    }

    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
        background: #666666;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
        height: 0px;
        width: 0px;
    }

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }""")

    win = MainWindow()
    win.show()
    success("Created main window")
    app.exec()


# exit
success("Process exited")