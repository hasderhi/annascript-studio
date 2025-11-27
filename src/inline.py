import re
import html

def parse_inline(text: str) -> str:
    if not text:
        return ""

    code_spans = {}

    def repl_code(m):
        key = f"__CODE_{len(code_spans)}__"
        code_spans[key] = f"<code>{html.escape(m.group(1))}</code>"
        return key

    text = re.sub(r'`([^`]+?)`', repl_code, text)

    MATH_SYMBOLS = {
        "<->": "↔",
        "->": "→",
        "=>": "⇒",
        "<=": "≤",
        ">=": "≥",
        "!=": "≠",
        "+-": "±",
        "<*>": "×",
        "--": "–",
    }

    for k, v in MATH_SYMBOLS.items():
        text = text.replace(k, v)

    GREEK = {
        r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
        r"\delta": "δ", r"\epsilon": "ε", r"\zeta": "ζ",
        r"\eta": "η", r"\theta": "θ", r"\iota": "ι",
        r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ",
        r"\nu": "ν", r"\xi": "ξ", r"\omicron": "ο",
        r"\pi": "π", r"\rho": "ρ", r"\sigma": "σ",
        r"\tau": "τ", r"\upsilon": "υ", r"\phi": "φ",
        r"\chi": "χ", r"\psi": "ψ", r"\omega": "ω",
    }

    for k, v in GREEK.items():
        text = text.replace(k, v)

    text = html.escape(text)

    for placeholder, html_code in code_spans.items():
        text = text.replace(placeholder, html_code)

    text = re.sub(r'\*\*\*(.+?)\*\*\*',
                  lambda m: f"<strong><em>{_inline_parse(m.group(1))}</em></strong>",
                  text, flags=re.S)

    text = re.sub(r'\*\*(.+?)\*\*',
                  lambda m: f"<strong>{_inline_parse(m.group(1))}</strong>",
                  text, flags=re.S)

    text = re.sub(r'\*(.+?)\*',
                  lambda m: f"<em>{_inline_parse(m.group(1))}</em>",
                  text, flags=re.S)

    text = re.sub(r'==(.+?)==',
                  lambda m: f"<mark>{_inline_parse(m.group(1))}</mark>",
                  text, flags=re.S)

    text = re.sub(r'\^\^(.+?)\^\^',
                  lambda m: f"<sup>{_inline_parse(m.group(1))}</sup>",
                  text, flags=re.S)

    text = re.sub(r',,(.+?),,',
                  lambda m: f"<sub>{_inline_parse(m.group(1))}</sub>",
                  text, flags=re.S)

    def repl_link(m):
        label = _inline_parse(m.group(1))
        href = html.escape(m.group(2))
        if href.strip().lower().startswith("javascript:"):
            href = "#"
        return f'<a href="{href}">{label}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_link, text)

    return text

def _inline_parse(s: str) -> str:
    
    s = re.sub(r'\*\*\*(.+?)\*\*\*',
               lambda m: f"<strong><em>{m.group(1)}</em></strong>",
               s, flags=re.S)

    s = re.sub(r'\*\*(.+?)\*\*',
               lambda m: f"<strong>{m.group(1)}</strong>",
               s, flags=re.S)

    s = re.sub(r'\*(.+?)\*',
               lambda m: f"<em>{m.group(1)}</em>",
               s, flags=re.S)

    s = re.sub(r'==(.+?)==',
               lambda m: f"<mark>{m.group(1)}</mark>",
               s, flags=re.S)

    s = re.sub(r'\^\^(.+?)\^\^',
               lambda m: f"<sup>{m.group(1)}</sup>",
               s, flags=re.S)

    s = re.sub(r',,(.+?),,',
               lambda m: f"<sub>{m.group(1)}</sub>",
               s, flags=re.S)

    return s
