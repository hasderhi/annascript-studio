from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class Node:
    start_line: int = 0
    end_line: int = 0

@dataclass
class Document(Node):
    meta: dict = field(default_factory=dict)
    children: List[Node] = field(default_factory=list)

@dataclass
class Heading(Node):
    level: int = 1
    text: str = ""

@dataclass
class Paragraph(Node):
    lines: List[str] = field(default_factory=list)

@dataclass
class CodeBlock(Node):
    code: str = ""

@dataclass
class Macro(Node):
    name: str = ""
    attrs: dict = field(default_factory=dict)
    content: str = ""

@dataclass
class ListItem(Node):
    text: str = ""
    children: List[Node] = field(default_factory=list)

@dataclass
class UL(Node):
    items: List[ListItem] = field(default_factory=list)

@dataclass
class OL(Node):
    items: List[ListItem] = field(default_factory=list)

@dataclass
class Table(Node):
    rows: List[List[str]] = field(default_factory=list)

@dataclass
class Comment(Node):
    raw: str = ""
