"""Syntax highlighting for read-only GUI code preview panes."""

from __future__ import annotations

import re
from enum import Enum, auto

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class PreviewLanguage(Enum):
    """Preview pane language selector."""

    PLAIN = auto()
    SYSTEMVERILOG = auto()
    C_LIKE = auto()
    SYSTEMRDL = auto()
    XML = auto()


_COLORS = {
    "comment": "#6a737d",
    "keyword": "#0550ae",
    "preprocessor": "#8250df",
    "string": "#0a3069",
    "number": "#116329",
    "type": "#953800",
}

_C_KEYWORDS = frozenset(
    {
        "auto",
        "break",
        "case",
        "const",
        "continue",
        "default",
        "do",
        "else",
        "enum",
        "extern",
        "for",
        "if",
        "return",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "void",
        "while",
    }
)

_DML_KEYWORDS = frozenset(
    {
        "at",
        "bank",
        "device",
        "dml",
        "field",
        "import",
        "is",
        "param",
        "read",
        "register",
        "reserved",
        "size",
        "write",
        "write_1_clears",
    }
)

_C_TYPES = frozenset(
    {
        "char",
        "double",
        "float",
        "int",
        "long",
        "short",
        "signed",
        "size_t",
        "uint16_t",
        "uint32_t",
        "uint64_t",
        "uint8_t",
        "unsigned",
    }
)

_SV_KEYWORDS = frozenset(
    {
        "always",
        "always_comb",
        "always_ff",
        "assign",
        "begin",
        "case",
        "default",
        "else",
        "end",
        "endcase",
        "endgenerate",
        "endmodule",
        "generate",
        "if",
        "input",
        "inout",
        "int",
        "localparam",
        "logic",
        "module",
        "output",
        "parameter",
        "reg",
        "unsigned",
        "wire",
    }
)

_SYSTEMRDL_KEYWORDS = frozenset(
    {
        "addrmap",
        "component",
        "csr_gen_access",
        "default",
        "desc",
        "enum",
        "external",
        "field",
        "hw",
        "onread",
        "onwrite",
        "property",
        "reg",
        "regfile",
        "regwidth",
        "r",
        "rw",
        "rclr",
        "rset",
        "string",
        "sw",
        "type",
        "w",
        "woclr",
        "woset",
        "woc",
        "wos",
    }
)


def _format(
    *,
    color: str | None = None,
    bold: bool = False,
    italic: bool = False,
) -> QTextCharFormat:
    text_format = QTextCharFormat()
    if color is not None:
        text_format.setForeground(QColor(color))
    if bold:
        text_format.setFontWeight(QFont.Weight.Bold)
    if italic:
        text_format.setFontItalic(True)
    return text_format


def _keyword_pattern(keywords: frozenset[str]) -> re.Pattern[str]:
    ordered = sorted(keywords, key=len, reverse=True)
    body = "|".join(re.escape(keyword) for keyword in ordered)
    return re.compile(rf"\b(?:{body})\b")


def _type_pattern(types: frozenset[str]) -> re.Pattern[str]:
    ordered = sorted(types, key=len, reverse=True)
    body = "|".join(re.escape(type_name) for type_name in ordered)
    return re.compile(rf"\b(?:{body})\b")


class _RegexHighlighter(QSyntaxHighlighter):
    _IN_MULTILINE_COMMENT = 1

    def __init__(
        self,
        document,
        *,
        keyword_pattern: re.Pattern[str],
        line_rules: tuple[tuple[re.Pattern[str], QTextCharFormat], ...],
        type_pattern: re.Pattern[str] | None = None,
    ) -> None:
        super().__init__(document)
        self._keyword_pattern = keyword_pattern
        self._line_rules = line_rules
        self._type_pattern = type_pattern
        self._comment_format = _format(color=_COLORS["comment"], italic=True)
        self._keyword_format = _format(color=_COLORS["keyword"], bold=True)
        self._type_format = _format(color=_COLORS["type"])

    def highlightBlock(self, text: str) -> None:
        covered = [False] * len(text)

        def mark(start: int, length: int, text_format: QTextCharFormat) -> None:
            if length <= 0:
                return
            self.setFormat(start, length, text_format)
            end = min(start + length, len(text))
            for index in range(start, end):
                covered[index] = True

        def is_covered(start: int, end: int) -> bool:
            return any(covered[start:end])

        start_index = 0
        if self.previousBlockState() == self._IN_MULTILINE_COMMENT:
            end_index = text.find("*/")
            if end_index == -1:
                mark(0, len(text), self._comment_format)
                self.setCurrentBlockState(self._IN_MULTILINE_COMMENT)
                return
            mark(0, end_index + 2, self._comment_format)
            start_index = end_index + 2

        while start_index < len(text):
            start = text.find("/*", start_index)
            if start == -1:
                break
            end = text.find("*/", start + 2)
            if end == -1:
                mark(start, len(text) - start, self._comment_format)
                self.setCurrentBlockState(self._IN_MULTILINE_COMMENT)
                break
            mark(start, end - start + 2, self._comment_format)
            start_index = end + 2

        if self.currentBlockState() != self._IN_MULTILINE_COMMENT:
            self.setCurrentBlockState(0)

        for pattern, text_format in self._line_rules:
            for match in pattern.finditer(text):
                if is_covered(match.start(), match.end()):
                    continue
                mark(match.start(), match.end() - match.start(), text_format)

        if self._type_pattern is not None:
            for match in self._type_pattern.finditer(text):
                if is_covered(match.start(), match.end()):
                    continue
                mark(match.start(), match.end() - match.start(), self._type_format)

        for match in self._keyword_pattern.finditer(text):
            if is_covered(match.start(), match.end()):
                continue
            mark(match.start(), match.end() - match.start(), self._keyword_format)


def _clike_line_rules() -> tuple[tuple[re.Pattern[str], QTextCharFormat], ...]:
    return (
        (
            re.compile(r"//.*$"),
            _format(color=_COLORS["comment"], italic=True),
        ),
        (
            re.compile(
                r"#\s*(?:define|include|ifndef|ifdef|endif|else|elif|undef|pragma)\b[^\n]*"
            ),
            _format(color=_COLORS["preprocessor"]),
        ),
        (
            re.compile(r'"(?:\\.|[^"\\])*"'),
            _format(color=_COLORS["string"]),
        ),
        (
            re.compile(r"0x[0-9a-fA-F]+(?:u|ul|ll|ULL)?"),
            _format(color=_COLORS["number"]),
        ),
        (
            re.compile(r"\b\d+\b"),
            _format(color=_COLORS["number"]),
        ),
    )


def _systemverilog_line_rules() -> tuple[tuple[re.Pattern[str], QTextCharFormat], ...]:
    return (
        (
            re.compile(r"//.*$"),
            _format(color=_COLORS["comment"], italic=True),
        ),
        (
            re.compile(r"`\w+"),
            _format(color=_COLORS["preprocessor"]),
        ),
        (
            re.compile(r'"(?:\\.|[^"\\])*"'),
            _format(color=_COLORS["string"]),
        ),
        (
            re.compile(r"\d+'[bhBHdD][0-9a-fA-F_xXzZ?]+"),
            _format(color=_COLORS["number"]),
        ),
        (
            re.compile(r"0x[0-9a-fA-F]+(?:u|ul|ll|ULL)?"),
            _format(color=_COLORS["number"]),
        ),
        (
            re.compile(r"\b\d+\b"),
            _format(color=_COLORS["number"]),
        ),
    )


class CLikeHighlighter(_RegexHighlighter):
    """Shared C header and Simics DML preview highlighting."""

    def __init__(self, document) -> None:
        super().__init__(
            document,
            keyword_pattern=_keyword_pattern(_C_KEYWORDS | _DML_KEYWORDS),
            line_rules=_clike_line_rules(),
            type_pattern=_type_pattern(_C_TYPES),
        )


class SystemVerilogHighlighter(_RegexHighlighter):
    """SystemVerilog preview highlighting."""

    def __init__(self, document) -> None:
        super().__init__(
            document,
            keyword_pattern=_keyword_pattern(_SV_KEYWORDS),
            line_rules=_systemverilog_line_rules(),
            type_pattern=_type_pattern(
                frozenset({"logic", "wire", "reg", "int", "unsigned"})
            ),
        )


def _systemrdl_line_rules() -> tuple[tuple[re.Pattern[str], QTextCharFormat], ...]:
    return (
        (
            re.compile(r"//.*$"),
            _format(color=_COLORS["comment"], italic=True),
        ),
        (
            re.compile(r'"(?:\\.|[^"\\])*"'),
            _format(color=_COLORS["string"]),
        ),
        (
            re.compile(r"\[\d+:\d+\]"),
            _format(color=_COLORS["type"]),
        ),
        (
            re.compile(r"0x[0-9a-fA-F]+"),
            _format(color=_COLORS["number"]),
        ),
        (
            re.compile(r"\b\d+\b"),
            _format(color=_COLORS["number"]),
        ),
    )


class SystemRdlHighlighter(_RegexHighlighter):
    """SystemRDL preview highlighting."""

    def __init__(self, document) -> None:
        super().__init__(
            document,
            keyword_pattern=_keyword_pattern(_SYSTEMRDL_KEYWORDS),
            line_rules=_systemrdl_line_rules(),
        )


class XmlHighlighter(QSyntaxHighlighter):
    """XML preview highlighting for IP-XACT and similar markup."""

    _IN_XML_COMMENT = 1

    def __init__(self, document) -> None:
        super().__init__(document)
        self._comment_format = _format(color=_COLORS["comment"], italic=True)
        self._tag_format = _format(color=_COLORS["keyword"], bold=True)
        self._attribute_format = _format(color=_COLORS["type"])
        self._string_format = _format(color=_COLORS["string"])
        self._number_format = _format(color=_COLORS["number"])
        self._declaration_format = _format(color=_COLORS["preprocessor"])
        self._line_rules = (
            (
                re.compile(r"<\?xml.*?\?>"),
                self._declaration_format,
            ),
            (
                re.compile(r'"(?:\\.|[^"\\])*"'),
                self._string_format,
            ),
            (
                re.compile(r"'h[0-9a-fA-F]+"),
                self._number_format,
            ),
            (
                re.compile(r"</?(?:\w+:)?[\w-]+"),
                self._tag_format,
            ),
            (
                re.compile(r"(?<=\s)[\w:-]+(?==)"),
                self._attribute_format,
            ),
        )

    def highlightBlock(self, text: str) -> None:
        covered = [False] * len(text)

        def mark(start: int, length: int, text_format: QTextCharFormat) -> None:
            if length <= 0:
                return
            self.setFormat(start, length, text_format)
            end = min(start + length, len(text))
            for index in range(start, end):
                covered[index] = True

        def is_covered(start: int, end: int) -> bool:
            return any(covered[start:end])

        start_index = 0
        if self.previousBlockState() == self._IN_XML_COMMENT:
            end_index = text.find("-->")
            if end_index == -1:
                mark(0, len(text), self._comment_format)
                self.setCurrentBlockState(self._IN_XML_COMMENT)
                return
            mark(0, end_index + 3, self._comment_format)
            start_index = end_index + 3

        while start_index < len(text):
            start = text.find("<!--", start_index)
            if start == -1:
                break
            end = text.find("-->", start + 4)
            if end == -1:
                mark(start, len(text) - start, self._comment_format)
                self.setCurrentBlockState(self._IN_XML_COMMENT)
                break
            mark(start, end - start + 3, self._comment_format)
            start_index = end + 3

        if self.currentBlockState() != self._IN_XML_COMMENT:
            self.setCurrentBlockState(0)

        for pattern, text_format in self._line_rules:
            for match in pattern.finditer(text):
                if is_covered(match.start(), match.end()):
                    continue
                mark(match.start(), match.end() - match.start(), text_format)


def attach_preview_highlighter(document, language: PreviewLanguage):
    """Attach a language highlighter to a preview document, if supported."""
    if language is PreviewLanguage.SYSTEMVERILOG:
        return SystemVerilogHighlighter(document)
    if language is PreviewLanguage.C_LIKE:
        return CLikeHighlighter(document)
    if language is PreviewLanguage.SYSTEMRDL:
        return SystemRdlHighlighter(document)
    if language is PreviewLanguage.XML:
        return XmlHighlighter(document)
    return None
