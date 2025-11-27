from dataclasses import dataclass
import re

@dataclass
class Token:
    type: str
    value: str | None = None
    lineno: int | None = None
    indent: int | None = 0

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, line={self.lineno}, indent={self.indent})"


def _count_indent(s: str) -> int:
    # treat tabs as 4 spaces (Yes, one tab are exactly 4 spaces and no, I won't change my mind)
    s_expanded = s.replace("\t", " " * 4)
    return len(s_expanded) - len(s_expanded.lstrip(" "))


def tokenize(text: str):
    lines = text.splitlines()
    tokens: list[Token] = []

    for idx, raw_line in enumerate(lines, start=1):
        indent = _count_indent(raw_line)
        line = raw_line.rstrip("\r\n")

        if line.strip().startswith("//"):
            tokens.append(Token("COMMENT", line.strip(), lineno=idx, indent=indent))
            continue

        if line.startswith("@"):
            tokens.append(Token("META", line, lineno=idx, indent=indent))
            continue

        if not line.strip():
            tokens.append(Token("BLANK", None, lineno=idx, indent=indent))
            continue

        if re.match(r'^\s*#{1,6}\s+', line):
            tokens.append(Token("HEADING", line.strip(), lineno=idx, indent=indent))
            continue

        if line.strip().startswith("::") and line.strip() != "::":
            tokens.append(Token("MACRO_START", line.strip(), lineno=idx, indent=indent))
            continue

        if line.strip() == "::":
            tokens.append(Token("MACRO_END", "::", lineno=idx, indent=indent))
            continue

        if re.match(r'^\s*-\s+', line):
            tokens.append(Token("UL_ITEM", line.rstrip(), lineno=idx, indent=indent))
            continue

        if re.match(r'^\s*\d+\.\s+', line):
            tokens.append(Token("OL_ITEM", line.rstrip(), lineno=idx, indent=indent))
            continue

        if line.strip().startswith("|"):
            tokens.append(Token("TABLE_ROW", line.strip(), lineno=idx, indent=indent))
            continue

        tokens.append(Token("TEXT", line.rstrip(), lineno=idx, indent=indent))

    tokens.append(Token("EOF", None, lineno=len(lines) + 1, indent=0))
    return tokens
