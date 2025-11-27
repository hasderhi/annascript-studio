from tokenizer import tokenize
from ast_nodes import *
import re

ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]+)"|(\w+)\s*=\s*([^\s]+)')

def parse_attributes(attr_text: str) -> dict:
    if not attr_text:
        return {}
    attrs = {}
    for a1, v1, a2, v2 in ATTR_RE.findall(attr_text):
        if a1:
            attrs[a1] = v1
        else:
            attrs[a2] = v2
    return attrs

def parse_paragraph(tokens, i):
    start_line = tokens[i].lineno
    lines = []
    while i < len(tokens) and tokens[i].type == "TEXT":
        lines.append(tokens[i].value)
        i += 1
    node = Paragraph(lines=lines, start_line=start_line, end_line=tokens[i-1].lineno if lines else start_line)
    node.__end_index__ = i
    return node

def parse_code(tokens, i):
    start_line = tokens[i].lineno
    i += 1
    code_lines = []
    while i < len(tokens) and tokens[i].type != "CODE_END" and tokens[i].type != "EOF":
        val = tokens[i].value if tokens[i].value is not None else ""
        code_lines.append(val)
        i += 1
    if i < len(tokens) and tokens[i].type == "CODE_END":
        i += 1
    code = "\n".join(code_lines)
    node = CodeBlock(code=code, start_line=start_line, end_line=tokens[i-1].lineno if code_lines else start_line)
    node.__end_index__ = i
    return node

def parse_macro(tokens, i):
    start_tok = tokens[i]
    start_line = start_tok.lineno
    m = re.match(r'::(\w+)(.*)$', start_tok.value)
    name = m.group(1)
    attr_text = m.group(2).strip()
    attrs = parse_attributes(attr_text)
    i += 1
    content_lines = []
    while i < len(tokens) and tokens[i].type != "MACRO_END" and tokens[i].type != "EOF":
        if tokens[i].value is not None:
            content_lines.append(tokens[i].value)
        i += 1
    if i < len(tokens) and tokens[i].type == "MACRO_END":
        i += 1
    content = "\n".join(content_lines).strip()
    node = Macro(name=name, attrs=attrs, content=content, start_line=start_line, end_line=tokens[i-1].lineno if content_lines else start_line)
    node.__end_index__ = i
    return node

def parse_list(tokens, i, list_type, base_indent):
    start_line = tokens[i].lineno
    items = []

    while i < len(tokens):
        tok = tokens[i]

        if tok.indent < base_indent:
            break

        if list_type == "UL" and tok.type != "UL_ITEM":
            break
        if list_type == "OL" and tok.type != "OL_ITEM":
            break

        cur_indent = tok.indent
        raw = tok.value.strip()

        if list_type == "UL":
            text = re.sub(r'^\s*-\s+', '', raw)
        else:
            text = re.sub(r'^\s*\d+\.\s+', '', raw)

        item = ListItem(text=text, start_line=tok.lineno)

        i += 1

        while i < len(tokens):
            next_tok = tokens[i]

            if next_tok.indent > cur_indent and next_tok.type in ("UL_ITEM", "OL_ITEM"):
                nested_type = "UL" if next_tok.type == "UL_ITEM" else "OL"
                nested_node, i = parse_list(tokens, i, nested_type, next_tok.indent)
                item.children.append(nested_node)
                continue

            break

        items.append(item)

    if list_type == "UL":
        node = UL(items=items, start_line=start_line, end_line=tokens[i-1].lineno)
    else:
        node = OL(items=items, start_line=start_line, end_line=tokens[i-1].lineno)

    return node, i

def parse_table(tokens, i):
    start_line = tokens[i].lineno
    rows = []
    while i < len(tokens) and tokens[i].type == "TABLE_ROW":
        raw = tokens[i].value.strip()
        cells = [c.strip() for c in raw.strip("|").split("|")]
        rows.append(cells)
        i += 1
    node = Table(rows=rows, start_line=start_line, end_line=tokens[i-1].lineno if rows else start_line)
    node.__end_index__ = i
    return node

def parse(tokens):
    i = 0
    meta = {}
    children = []

    while i < len(tokens) and tokens[i].type == "META":
        line = tokens[i].value
        if ":" in line:
            k, v = line[1:].split(":", 1)
            meta[k.strip()] = v.strip()
        i += 1

    while i < len(tokens) and tokens[i].type != "EOF":
        tok = tokens[i]

        if tok.type == "BLANK" or tok.type == "COMMENT":
            i += 1
            continue

        if tok.type == "HEADING":
            level = len(re.match(r'^(#+)', tok.value).group(1))
            text = tok.value[level:].strip()
            node = Heading(level=level, text=text, start_line=tok.lineno, end_line=tok.lineno)
            node.__end_index__ = i + 1
            children.append(node)
            i += 1
            continue

        if tok.type == "TEXT":
            node = parse_paragraph(tokens, i)
            children.append(node)
            i = node.__end_index__
            continue

        if tok.type == "CODE_START":
            node = parse_code(tokens, i)
            children.append(node)
            i = node.__end_index__
            continue

        if tok.type == "MACRO_START":
            node = parse_macro(tokens, i)
            children.append(node)
            i = node.__end_index__
            continue

        if tok.type == "UL_ITEM":
            node, i = parse_list(tokens, i, "UL", tok.indent)
            children.append(node)
            continue

        if tok.type == "OL_ITEM":
            node, i = parse_list(tokens, i, "OL", tok.indent)
            children.append(node)
            continue


        if tok.type == "TABLE_ROW":
            node = parse_table(tokens, i)
            children.append(node)
            i = node.__end_index__
            continue

        # unknown, skip
        i += 1

    doc = Document(meta=meta, children=children, start_line=1, end_line=tokens[i-1].lineno if i>0 else 1)
    return doc

# parse from text
def parse_text(text: str):
    tokens = tokenize(text)
    return parse(tokens)
