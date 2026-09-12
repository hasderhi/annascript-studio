import re
import html

_PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield", "match", "case",
}

_C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool", "_Complex",
    "_Imaginary",
}

_CPP_KEYWORDS = _C_KEYWORDS | {
    "alignas", "alignof", "and", "and_eq", "asm", "bitand", "bitor",
    "bool", "catch", "class", "compl", "concept", "consteval",
    "constexpr", "constinit", "const_cast", "decltype", "delete",
    "dynamic_cast", "explicit", "export", "false", "friend", "mutable",
    "namespace", "new", "noexcept", "not", "not_eq", "nullptr",
    "operator", "or", "or_eq", "override", "private", "protected",
    "public", "reinterpret_cast", "requires", "static_assert",
    "static_cast", "template", "this", "thread_local", "throw", "true",
    "try", "typeid", "typename", "using", "virtual", "wchar_t", "xor",
    "xor_eq",
}

_CSHARP_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch",
    "char", "checked", "class", "const", "continue", "decimal",
    "default", "delegate", "do", "double", "else", "enum", "event",
    "explicit", "extern", "false", "finally", "fixed", "float", "for",
    "foreach", "goto", "if", "implicit", "in", "int", "interface",
    "internal", "is", "lock", "long", "namespace", "new", "null",
    "object", "operator", "out", "override", "params", "private",
    "protected", "public", "readonly", "record", "ref", "return",
    "sbyte", "sealed", "short", "sizeof", "stackalloc", "static",
    "string", "struct", "switch", "this", "throw", "true", "try",
    "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort", "using",
    "var", "virtual", "void", "volatile", "while", "yield", "async",
    "await", "get", "set", "nameof",
}

_JS_KEYWORDS = {
    "break", "case", "catch", "class", "const", "continue", "debugger",
    "default", "delete", "do", "else", "export", "extends", "false",
    "finally", "for", "function", "if", "import", "in", "instanceof",
    "let", "new", "null", "of", "return", "static", "super", "switch",
    "this", "throw", "true", "try", "typeof", "undefined", "var",
    "void", "while", "with", "yield", "async", "await", "get", "set",
}

_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "record", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw",
    "throws", "transient", "try", "var", "void", "volatile", "while",
    "true", "false", "null", "yield", "sealed", "permits",
}

_LANGUAGE_ALIASES = {
    "python": "python", "py": "python", "python3": "python",
    "c": "c",
    "c++": "cpp", "cpp": "cpp", "cplusplus": "cpp",
    "c#": "csharp", "csharp": "csharp", "cs": "csharp",
    "javascript": "javascript", "js": "javascript", "jsx": "javascript",
    "typescript": "javascript", "ts": "javascript", "tsx": "javascript",
    "java": "java",
}

_KEYWORD_SETS = {
    "python": _PY_KEYWORDS,
    "c": _C_KEYWORDS,
    "cpp": _CPP_KEYWORDS,
    "csharp": _CSHARP_KEYWORDS,
    "javascript": _JS_KEYWORDS,
    "java": _JAVA_KEYWORDS,
}


def normalize_language(lang: str | None) -> str | None:
    if not lang:
        return None
    key = lang.strip().lower()
    return _LANGUAGE_ALIASES.get(key)


_TOKEN_SPEC = [
    ("COMMENT_LINE", r"//[^\n]*|\#[^\n]*"),
    ("COMMENT_BLOCK", r"/\*.*?\*/"),
    ("STRING", r'"""(?:\\.|[^\\])*?"""|\'\'\'(?:\\.|[^\\])*?\'\'\''
               r'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`'),
    ("FLOAT", r"\b\d+\.\d+(?:[eE][+-]?\d+)?[fFdDlL]?\b|\b\d+[eE][+-]?\d+[fFdDlL]?\b"),
    ("INT", r"\b0[xX][0-9a-fA-F]+\b|\b0[bB][01]+\b|\b\d+[uUlLfF]*\b"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OPERATOR", r"(?:\*\*=|//=|<<=|>>=|->|=>|<=|>=|==|!=|&&|\|\||\+\+|--|"
                  r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|::|<<|>>|[+\-*/%=<>!&|^~])"),
    ("PUNCTUATION", r"[(){}\[\];:,.\?]"),
    ("WHITESPACE", r"[ \t]+"),
    ("NEWLINE", r"\n"),
    ("OTHER", r"."),
]

_MASTER_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC),
    re.DOTALL,
)

_CLASS_FOR_KIND = {
    "COMMENT_LINE": "highlight-comment",
    "COMMENT_BLOCK": "highlight-comment",
    "STRING": "highlight-string",
    "FLOAT": "highlight-number",
    "INT": "highlight-number",
    "OPERATOR": "highlight-operator",
    "PUNCTUATION": "highlight-punctuation",
}


def highlight_code(code: str, language: str | None) -> str:
    lang_key = normalize_language(language)
    keywords = _KEYWORD_SETS.get(lang_key) if lang_key else None

    out = []
    for m in _MASTER_RE.finditer(code):
        kind = m.lastgroup
        text = m.group()

        if kind == "WHITESPACE" or kind == "NEWLINE" or kind == "OTHER":
            out.append(html.escape(text))
            continue

        if kind == "IDENT":
            if keywords and text in keywords:
                out.append(f'<span class="highlight-keyword">{html.escape(text)}</span>')
            else:
                out.append(html.escape(text))
            continue

        css_class = _CLASS_FOR_KIND.get(kind)
        if css_class:
            out.append(f'<span class="{css_class}">{html.escape(text)}</span>')
        else:
            out.append(html.escape(text))

    return "".join(out)
