from ast_nodes import *
from inline import parse_inline
import html
from typing import Callable
import re

_macro_registry: dict[str, Callable[[Macro], str]] = {}

def register_macro(name: str):
    def deco(fn: Callable[[Macro], str]):
        _macro_registry[name] = fn
        return fn
    return deco


@register_macro("note")
def render_note(node: Macro) -> str:
    inner = parse_inline(node.content)
    return f'<div class="note">{inner}</div>'

@register_macro("center")
def render_center(node: Macro) -> str:
    inner = parse_inline(node.content)
    return f'<div style="text-align:center;">{inner}</div>'

@register_macro("box")
def render_box(node: Macro) -> str:
    cls = html.escape(node.attrs.get("type", ""))
    title = html.escape(node.attrs.get("title", ""))
    title_html = f'<div class="box-title">{title}</div>' if title else ''
    inner = parse_inline(node.content)
    return f'<div class="box {cls}">{title_html}<div class="box-content">{inner}</div></div>'

def render_macro_generic(node: Macro) -> str:
    inner = parse_inline(node.content)
    return f'<div class="{html.escape(node.name)}">{inner}</div>'

def render(node: Node) -> str:
    if isinstance(node, Document):
        title = str(node.meta.get("title", ""))
        author = str(node.meta.get("author", ""))

        style = str(node.meta.get("style", "default")).strip() or "default"

        darkmode = str(node.meta.get("darkmode", "")).lower() in ("true", "1", "yes") # user feedback showed that not everyone agrees on "true"
        mode = "dark" if darkmode else "light"

        stylesheet_path = f"themes/{html.escape(style)}/{mode}.css"

        head = (
            "<!DOCTYPE html>\n<html>\n  <head>\n"
            "    <meta charset='utf-8'>\n"
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"    <title>{title}</title>\n"
            f"    <meta name='author' content='{author}'>\n"
            f"    <link rel='stylesheet' href='{stylesheet_path}'>\n"
            "  </head>"
        )

        body = "\n".join(render(ch) for ch in node.children)
        return f"{head}\n  <body>\n{body}\n  </body>\n</html>"


    if isinstance(node, Heading):
        return f"<h{node.level}>{parse_inline(node.text)}</h{node.level}>"

    if isinstance(node, Paragraph):
        txt = " ".join(line.strip() for line in node.lines)
        return f"<p>{parse_inline(txt)}</p>"

    if isinstance(node, CodeBlock):
        return f"<pre><code>{html.escape(node.code)}</code></pre>"

    if isinstance(node, ListItem):
        inner = parse_inline(node.text)
        children_html = "".join(render(ch) for ch in node.children)
        return f"<li>{inner}{children_html}</li>"


    if isinstance(node, UL):
        items_html = "".join(render(item) for item in node.items)
        return f"<ul>{items_html}</ul>"

    if isinstance(node, OL):
        items_html = "".join(render(item) for item in node.items)
        return f"<ol>{items_html}</ol>"


    if isinstance(node, Table):
        header_html = ""
        rows = node.rows[:]
        if len(rows) >= 2 and all(re.match(r'^:?-+:?$', c.replace(" ", "")) for c in rows[1]):
            header = rows[0]
            header_html = "<thead><tr>" + "".join(f"<th>{parse_inline(c)}</th>" for c in header) + "</tr></thead>"
            body_rows = rows[2:]
        else:
            body_rows = rows
        body_html = "<tbody>" + "".join("<tr>" + "".join(f"<td>{parse_inline(c)}</td>" for c in r) + "</tr>" for r in body_rows) + "</tbody>"
        return f"<table>{header_html}{body_html}</table>"

    if isinstance(node, Macro):
        fn = _macro_registry.get(node.name, render_macro_generic)
        return fn(node)

    if isinstance(node, Comment):
        return ""

    # fallback
    return ""
