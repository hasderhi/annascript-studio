from ast_nodes import *
from inline import parse_inline
from evaluator import safe_eval, normalize_expr
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

@register_macro("coordinates")
def render_coordinate_system(node: Macro) -> str:
    try:
        title = html.escape(node.attrs.get("title", ""))
        scale = float(node.attrs.get("scale", 20))
        if scale >= 2000:
            return '<div>The selected scale is too large (max. 1999)! The coordinate system is not rendered to avoid application instability.</div>'
        size = 400
        half_range = scale

        def map_x(x):
            return (x + half_range) * (size / (2 * half_range))
        def map_y(y):
            return size - (y + half_range) * (size / (2 * half_range))

        title_html = f'<div class="coord-title">{title}</div>' if title else ''
        elements = []


        rows = []
        for line in node.content.split('\n'):
            line = line.strip()
            if line.startswith('|') and '|' in line[1:]:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 3:
                    rows.append(cells)

        defs = """
        <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L6,3 Z" fill="blue"/>
            </marker>
        </defs>
        """
        elements.append(defs)

        axes = f"""
        <line class="coord-axis" x1="0" y1="{map_y(0)}" x2="{size}" y2="{map_y(0)}"/>
        <line class="coord-axis" x1="{map_x(0)}" y1="0" x2="{map_x(0)}" y2="{size}"/>
        """
        elements.append(axes)

        if scale <= 20:
            step = 1
        elif scale <= 200:
            step = 10
        else:
            step = 100

        min_label_spacing = 20
        last_label_x = last_label_y = -float('inf')
        ticks = []
        for i in range(int(-half_range), int(half_range)+1):
            if i % step != 0 or i % 2 != 0:
                continue

            x = map_x(i)
            y = map_y(i)

            if i != 0:
                ticks.append(f'<line class="coord-grid" x1="{x}" y1="0" x2="{x}" y2="{size}"/>')
                ticks.append(f'<line class="coord-grid" x1="0" y1="{y}" x2="{size}" y2="{y}"/>')

            if i == 0:
                continue

            if abs(x - last_label_x) >= min_label_spacing:
                ticks.append(f'''
                    <line class="coord-axis" x1="{x}" y1="{map_y(0)-5}" x2="{x}" y2="{map_y(0)+5}"/>
                    <text class="coord-label" x="{x}" y="{map_y(0)+15}" font-size="10" text-anchor="middle">{i}</text>
                ''')
                last_label_x = x

            if abs(y - last_label_y) >= min_label_spacing:
                ticks.append(f'''
                    <line class="coord-axis" x1="{map_x(0)-5}" y1="{y}" x2="{map_x(0)+5}" y2="{y}"/>
                    <text class="coord-label" x="{map_x(0)-10}" y="{y+3}" font-size="10" text-anchor="end">{i}</text>
                ''')
                last_label_y = y

        elements.append("".join(ticks))

        # I hope these work, it's difficult to find colours that work both on light and dark bgs
        FUNC_COLORS = ["#e6194b", "#3cb44b", "#726722", "#4363d8", "#f58231",
                       "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe"]
        func_index = 0

        for row in rows:
            name, typ, value = row[:3]
            domain_min, domain_max = -half_range, half_range
            if len(row) >= 4 and row[3].startswith("domain="):
                d = row[3][7:]
                domain_min, domain_max = map(float, d.split(":"))

            name = html.escape(name)

            if typ == "point":
                x, y = map(float, value.split(','))
                cx, cy = map_x(x), map_y(y)
                elements.append(f'''
                    <circle cx="{cx}" cy="{cy}" r="4" fill="red"/>
                    <text class="figure-label" x="{cx + 5}" y="{cy - 5}" font-size="12">{name}</text>
                ''')

            elif typ == "vector":
                dx, dy = map(float, value.split(','))
                x2, y2 = map_x(dx), map_y(dy)
                elements.append(f'''
                    <line x1="{map_x(0)}" y1="{map_y(0)}"
                          x2="{x2}" y2="{y2}"
                          stroke="blue" stroke-width="2"
                          marker-end="url(#arrow)"/>
                    <text class="figure-label" x="{x2 + 5}" y="{y2 - 5}" font-size="12">{name}</text>
                ''')

            elif typ == "function":
                color = FUNC_COLORS[func_index % len(FUNC_COLORS)]
                func_index += 1
                func = normalize_expr(value.replace(" ", ""))

                match = re.match(r'^([+-]?\d*\.?\d*)\*?x([+-]\d+\.?\d*)?$', func)
                if match:
                    a = match.group(1)
                    b = match.group(2)
                    a = float(a) if a not in ("", "+", "-") else float(f"{a}1" if a else 1)
                    b = float(b) if b else 0
                    x1, x2 = max(domain_min, -half_range), min(domain_max, half_range)
                    y1, y2 = a*x1+b, a*x2+b
                    elements.append(f'''
                        <line x1="{map_x(x1)}" y1="{map_y(y1)}"
                              x2="{map_x(x2)}" y2="{map_y(y2)}"
                              stroke="{color}" stroke-width="2"/>
                        <text class="figure-label" x="{map_x(x2)+5}" y="{map_y(y2)-5}" font-size="12">{name}</text>
                    ''')
                else:
                    samples_per_unit = 5
                    x_vals = [domain_min + i/samples_per_unit for i in range(int((domain_max - domain_min)*samples_per_unit)+1)]
                    path_points = []
                    for x in x_vals:
                        try:
                            y = safe_eval(func, x) # nope, no funny eval code injection
                            px, py = map_x(x), map_y(y)
                            if -1e6 < y < 1e6:
                                path_points.append((px, py))
                        except SyntaxError:
                            return '<div>Error rendering coordinate system, check syntax/expressions!</div>'
                        except ValueError:
                            return '<div>Error rendering coordinate system, disallowed character(s) in expression!</div>'
                    if path_points:
                        path_d = "M " + " L ".join(f"{px},{py}" for px, py in path_points)
                        last_x, last_y = path_points[-1]
                        elements.append(f'''
                            <path d="{path_d}" stroke="{color}" fill="none"/>
                            <text class="figure-label" x="{last_x + 5}" y="{last_y - 5}" font-size="12">{name}</text>
                        ''')

        svg = f'''
        <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
            {''.join(elements)}
        </svg>
        '''

        return f'<div class="coordinates">{title_html}{svg}</div>'

    except Exception:
        return '<div>Error rendering coordinate system, check syntax/expressions!</div>'

@register_macro("chart")
def render_chart(node: Macro) -> str:
    try:
        chart_type = html.escape(node.attrs.get("type", ""))
        title = html.escape(node.attrs.get("title", ""))
        title_html = f'<div class="chart-title">{title}</div>' if title else ''

        rows = []
        for line in node.content.split('\n'):
            line = line.strip()
            if line.startswith('|') and '|' in line[1:]:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 2:
                    rows.append(cells)

        if chart_type == "pie":
            chart_html = render_pie_chart(rows)
        elif chart_type == "bar":
            chart_html = render_bar_chart(rows)
        else:
            chart_html = "<div class='chart-error'>Unsupported chart type</div>"
        return f'<div class="chart {chart_type}">{title_html}{chart_html}</div>'
    except Exception:
        f'<div>Error creating chart, check syntax!</div>'
    

def render_pie_chart(rows):
    try:
        if rows == []:
            return f'<div>No data provided.</div>'
        colors = ["#ff6b6b", "#4ecdc4", "#ffe66d", "#a55eea", "#feca57", "#ff9ff3"]
        total = sum(float(row[1]) for row in rows)
        gradient_stops = []
        legend_items = []
        cumulative_percentage = 0

        for i, (label, value) in enumerate(rows):
            percentage = (float(value) / total) * 100
            gradient_stops.append(f"{colors[i % len(colors)]} {cumulative_percentage}% {cumulative_percentage + percentage}%")
            legend_items.append(f'<div class="legend-item"><div class="legend-color" style="background: {colors[i % len(colors)]};"></div>{label} ({percentage:.2f}%)</div>')
            cumulative_percentage += percentage

        gradient = "conic-gradient(" + ", ".join(gradient_stops) + ")"
        pie_chart = f'<div class="pie-chart" style="background: {gradient};"></div>'
        legend = '<div class="legend">' + "".join(legend_items) + "</div>"

        return pie_chart + legend
    except Exception as e:
        return f'<div>Error creating chart, check table data!</div>'

def render_bar_chart(rows):
    try:
        if rows == []:
            return f'<div>No data provided.</div>'
        colors = ["#4ecdc4", "#ff6b6b", "#ffe66d", "#a55eea", "#feca57", "#ff9ff3"]
        max_value = max(float(row[1]) for row in rows)
        bars = []

        for i, (label, value) in enumerate(rows):
            bar_height = (float(value) / max_value) * 100
            bars.append(f'''
                <div class="bar-container">
                    <div class="bar" style="height: {bar_height}%; background: {colors[i % len(colors)]};"></div>
                    <div class="bar-label">{label}</div>
                </div>
            ''')

        bar_chart = f'''
            <div class="bar-chart">
                {"".join(bars)}
            </div>
        '''
        return bar_chart
    except Exception as e:
        return f'<div>Error creating chart, check table data!</div>'

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
            f"<!-- Generated by annaScript, https://tk-dev-software.com/annascript/ -->\n"
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
