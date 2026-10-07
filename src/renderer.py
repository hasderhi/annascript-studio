from ast_nodes import *
from inline import parse_inline
from evaluator import normalize_expr, safe_eval, ExpressionError
from highlighter import highlight_code
import html
from typing import Callable
import re
import math

# helpers go here
def _parse_point(s):
    x, y = s.split(',')
    return float(x), float(y)
 
def _parse_points(s):
    return [_parse_point(p) for p in s.split(';') if p.strip()]

def marker_for(node, cursor_line):
    global _marker_used

    if _marker_used:
        return ""

    if cursor_line is None:
        return ""

    if node.start_line <= cursor_line <= node.end_line:
        _marker_used = True
        return '<div id="scroll-destination"></div>'

    return ""

_marker_used = False

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
        pixel_per_unit = size / (2 * half_range)
 
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
        GEOMETRY_COLORS = {
            "segment": "#008080",
            "line": "#2e8b57",
            "ray": "#ff8c00",
            "circle": "#8b008b",
            "ellipse": "#4682b4",
            "polygon": "#a0522d",
            "angle": "#222222",
        }
 
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
 
            elif typ == "segment":
                (x1, y1), (x2, y2) = _parse_points(value)[:2]
                px1, py1 = map_x(x1), map_y(y1)
                px2, py2 = map_x(x2), map_y(y2)
                color = GEOMETRY_COLORS["segment"]
                elements.append(f'''
                    <line x1="{px1}" y1="{py1}" x2="{px2}" y2="{py2}" stroke="{color}" stroke-width="2"/>
                    <text class="figure-label" x="{(px1+px2)/2 + 5}" y="{(py1+py2)/2 - 5}" font-size="12">{name}</text>
                ''')
 
            elif typ in ("line", "ray"):
                (x1, y1), (x2, y2) = _parse_points(value)[:2]
                px1, py1 = map_x(x1), map_y(y1)
                px2, py2 = map_x(x2), map_y(y2)
                dx, dy = px2 - px1, py2 - py1
                length = math.hypot(dx, dy)
                if length == 0:
                    continue
                ux, uy = dx / length, dy / length
                FAR = 10_000
                end_x, end_y = px2 + ux * FAR, py2 + uy * FAR
                if typ == "line":
                    start_x, start_y = px1 - ux * FAR, py1 - uy * FAR
                else:
                    start_x, start_y = px1, py1
                color = GEOMETRY_COLORS[typ]
                dash = ' stroke-dasharray="6,4"' if typ == "line" else ''
                elements.append(f'''
                    <line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}"
                          stroke="{color}" stroke-width="2"{dash}/>
                    <text class="figure-label" x="{px2 + 5}" y="{py2 - 5}" font-size="12">{name}</text>
                ''')
 
            elif typ == "circle":
                cx, cy, r = map(float, value.split(','))
                pcx, pcy = map_x(cx), map_y(cy)
                pr = r * pixel_per_unit
                color = GEOMETRY_COLORS["circle"]
                elements.append(f'''
                    <circle cx="{pcx}" cy="{pcy}" r="{pr}" stroke="{color}" stroke-width="2" fill="none"/>
                    <text class="figure-label" x="{pcx + pr + 5}" y="{pcy}" font-size="12">{name}</text>
                ''')
 
            elif typ == "ellipse":
                cx, cy, rx, ry = map(float, value.split(','))
                pcx, pcy = map_x(cx), map_y(cy)
                prx, pry = rx * pixel_per_unit, ry * pixel_per_unit
                color = GEOMETRY_COLORS["ellipse"]
                elements.append(f'''
                    <ellipse cx="{pcx}" cy="{pcy}" rx="{prx}" ry="{pry}" stroke="{color}" stroke-width="2" fill="none"/>
                    <text class="figure-label" x="{pcx + prx + 5}" y="{pcy}" font-size="12">{name}</text>
                ''')
 
            elif typ == "polygon":
                pts = _parse_points(value)
                if len(pts) < 3:
                    continue
                pixel_pts = [(map_x(x), map_y(y)) for x, y in pts]
                points_attr = " ".join(f"{px},{py}" for px, py in pixel_pts)
                color = GEOMETRY_COLORS["polygon"]
                lx, ly = pixel_pts[0]
                elements.append(f'''
                    <polygon points="{points_attr}" stroke="{color}" stroke-width="2"
                             fill="{color}" fill-opacity="0.15"/>
                    <text class="figure-label" x="{lx + 5}" y="{ly - 5}" font-size="12">{name}</text>
                ''')
 
            elif typ == "angle":
                pts = _parse_points(value)
                if len(pts) < 3:
                    continue
                (ax, ay), (vx, vy), (bx, by) = pts[:3]
                pvx, pvy = map_x(vx), map_y(vy)
                pax, pay = map_x(ax), map_y(ay)
                pbx, pby = map_x(bx), map_y(by)
 
                angle_a = math.atan2(pay - pvy, pax - pvx)
                angle_b = math.atan2(pby - pvy, pbx - pvx)
                diff = angle_b - angle_a
                while diff <= -math.pi:
                    diff += 2 * math.pi
                while diff > math.pi:
                    diff -= 2 * math.pi
 
                arc_r = 20
                arc_start = (pvx + arc_r * math.cos(angle_a), pvy + arc_r * math.sin(angle_a))
                arc_end = (pvx + arc_r * math.cos(angle_a + diff), pvy + arc_r * math.sin(angle_a + diff))
                large_arc_flag = 1 if abs(diff) > math.pi else 0
                sweep_flag = 1 if diff > 0 else 0
                color = GEOMETRY_COLORS["angle"]
 
                degrees = abs(math.degrees(diff))
                mid_angle = angle_a + diff / 2
                label_x = pvx + (arc_r + 12) * math.cos(mid_angle)
                label_y = pvy + (arc_r + 12) * math.sin(mid_angle)
 
                elements.append(f'''
                    <path d="M {arc_start[0]} {arc_start[1]} A {arc_r} {arc_r} 0 {large_arc_flag} {sweep_flag} {arc_end[0]} {arc_end[1]}"
                          stroke="{color}" stroke-width="1.5" fill="none"/>
                    <text class="figure-label" x="{label_x}" y="{label_y}" font-size="12">{name} ({degrees:.1f}&#176;)</text>
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
                    path_segments = [[]]
                    for x in x_vals:
                        try:
                            y = safe_eval(func, x)
                        except SyntaxError:
                            return '<div>Error rendering coordinate system, check syntax/expressions!</div>'
                        except ExpressionError:
                            # nope, no funny eval code injection
                            return '<div>Error rendering coordinate system, disallowed character(s) in expression!</div>'
                        except (ValueError, ZeroDivisionError, OverflowError):
                            if path_segments[-1]:
                                path_segments.append([])
                            continue
 
                        if not math.isfinite(y) or not (-1e6 < y < 1e6):
                            if path_segments[-1]:
                                path_segments.append([])
                            continue
 
                        path_segments[-1].append((map_x(x), map_y(y)))
 
                    last_x = last_y = None
                    for seg in path_segments:
                        if len(seg) < 2:
                            continue
                        path_d = "M " + " L ".join(f"{px},{py}" for px, py in seg)
                        elements.append(f'<path d="{path_d}" stroke="{color}" fill="none"/>')
                        last_x, last_y = seg[-1]
                    if last_x is not None:
                        elements.append(f'<text class="figure-label" x="{last_x + 5}" y="{last_y - 5}" font-size="12">{name}</text>')
 
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

def generate_page_number_css(meta):
    raw_pagenum = str(meta.get("pagenum", "")).strip()

    if not raw_pagenum:
        return ""

    parts = raw_pagenum.split("-")

    if len(parts) != 4:
        return ""

    vertical, horizontal, numbering, format_type = parts

    if vertical not in ("top", "bottom"):
        return ""

    if horizontal not in ("left", "right"):
        return ""

    margin_box = f"@{vertical}-{horizontal}"

    counter_styles = {
        "arabic": "decimal",
        "roman_upper": "upper-roman",
        "roman_lower": "lower-roman",
    }

    counter_style = counter_styles.get(numbering)

    if counter_style is None:
        return ""

    if format_type not in ("numeric", "labeled", "fractional"):
        return ""

    page_counter = f"counter(page, {counter_style})"
    pages_counter = f"counter(pages, {counter_style})"

    if format_type == "numeric":
        content = page_counter

    elif format_type == "labeled":
        content = f'"Page " {page_counter}'

    else:
        content = (
            f'"Page " {page_counter} '
            f'" of " {pages_counter}'
        )

    return (
        "@page {\n"
        "   margin: 2.5cm;\n"
        f"  {margin_box} {{\n"
        f"      content: {content};\n"
        "       font-size: 10pt;\n"
        "       font-family: var(--font-stack);"
        "       vertical-align: middle;"
        "   }\n"
        "}\n"
    )

def render(node: Node, cursor_line=None) -> str:
    if isinstance(node, Document):
        title = str(node.meta.get("title", ""))
        author = str(node.meta.get("author", ""))

        style = str(node.meta.get("style", "default")).strip() or "default"

        darkmode = str(node.meta.get("darkmode", "")).lower() in ("true", "1", "yes") # user feedback showed that not everyone agrees on "true"
        mode = "dark" if darkmode else "light"

        page_number_css = generate_page_number_css(node.meta)

        stylesheet_path = f"themes/{html.escape(style)}/{mode}.css"

        head = (
            "<!-- Generated by annaScript, https://tk-dev-software.com/annascript/ -->\n"
            "<!DOCTYPE html>\n<html>\n  <head>\n"
            "    <meta charset='utf-8'>\n"
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"   <title>{title}</title>\n"
            f"   <meta name='author' content='{author}'>\n"
            f"   <link rel='stylesheet' href='{stylesheet_path}'>\n"
            f"   <style>\n{page_number_css}</style>\n"
            "  </head>"
        )

        js_auto_scroll = (
            '<!-- Auto scroll to cursor pos -->\n'
            '<script>\n'
            'window.onload = () => {\n'
            '    const el = document.getElementById("scroll-destination");\n'
            '    if (el) {\n'
            '        el.scrollIntoView({\n'
            '            block: "center",\n'
            '            behavior: "instant"\n'
            '        });\n'
            '    }\n'
            '};\n'
            '</script>\n\n'
        )


        body = "\n".join(render(ch, cursor_line) for ch in node.children)
        return f"{head}\n  <body>\n{body}\n\n{js_auto_scroll}\n  </body>\n</html>"

    global _marker_used
    _marker_used = False

    if isinstance(node, Heading):
        return marker_for(node, cursor_line) + f"<h{node.level}>{parse_inline(node.text)}</h{node.level}>"

    if isinstance(node, Paragraph):
        txt = " ".join(line.strip() for line in node.lines)
        return marker_for(node, cursor_line) + f"<p>{parse_inline(txt)}</p>"

    if isinstance(node, CodeBlock):
        highlighted = highlight_code(node.code, node.lang)
        lang_class = f" language-{html.escape(node.lang)}" if node.lang else ""
        if node.inline:
            return marker_for(node, cursor_line) + (
                f'<pre class="code-inline{lang_class}"><code>{highlighted}</code></pre>'
            )
        return marker_for(node, cursor_line) + f'<pre class="code-block{lang_class}"><code>{highlighted}</code></pre>'

    if isinstance(node, ListItem):
        inner = parse_inline(node.text)
        children_html = "".join(render(ch) for ch in node.children)
        return f"<li>{inner}{children_html}</li>"


    if isinstance(node, UL):
        items_html = "".join(render(item) for item in node.items)
        return marker_for(node, cursor_line) + f"<ul>{items_html}</ul>"

    if isinstance(node, OL):
        items_html = "".join(render(item) for item in node.items)
        return marker_for(node, cursor_line) + f"<ol>{items_html}</ol>"


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
        return marker_for(node, cursor_line) + f"<table>{header_html}{body_html}</table>"

    if isinstance(node, Macro):
        fn = _macro_registry.get(node.name, render_macro_generic)
        return marker_for(node, cursor_line) + fn(node)

    if isinstance(node, Marker):
        escaped_name = html.escape(node.name)
        escaped_color = html.escape(node.color.lower())

        icon = "✕" if escaped_color == "fail" else "✓"

        return marker_for(node, cursor_line) + (
            f'<span class="marker marker-{escaped_color}">'
            f'<span class="marker-icon">{icon}</span> '
            f'{escaped_name}'
            f'</span><br>'
        )
    
    if isinstance(node, ToDo):
        checked_attr = "checked" if node.checked else ""
        completed_class = " completed" if node.checked else ""
        escaped_name = html.escape(node.name)

        return marker_for(node, cursor_line) + (
            f'<label class="todo-item{completed_class}">'
            f'<input type="checkbox" class="todo-checkbox" {checked_attr}> '
            f'{escaped_name}'
            f'</label><br>' # break so multiple boxes create a list
        )
    
    if isinstance(node, Comment):
        return ""

    # fallback
    return ""
