"""White-box tests for Markdown table token parsing helpers."""

import pytest
from markdown_it.token import Token

from csr_gen.errors import MarkdownParseError
from csr_gen.input.markdown_reader import (
    _extract_rows,
    _find_tables,
    _inline_text,
    _token_text,
)


def _token(
    type_: str,
    *,
    tag: str = "",
    nesting: int = 0,
    children: list[Token] | None = None,
    content: str = "",
) -> Token:
    return Token(
        type_,
        tag=tag,
        nesting=nesting,
        children=children or [],
        content=content,
    )


def test_find_tables_rejects_nested_tables() -> None:
    tokens = [
        _token("table_open"),
        _token("table_open"),
        _token("table_close"),
        _token("table_close"),
    ]
    with pytest.raises(MarkdownParseError, match="Nested Markdown tables"):
        _find_tables(tokens)


def test_find_tables_rejects_unmatched_table_close() -> None:
    with pytest.raises(MarkdownParseError, match="Malformed Markdown table token"):
        _find_tables([_token("table_close")])


def test_find_tables_rejects_unclosed_table() -> None:
    with pytest.raises(MarkdownParseError, match="Malformed Markdown table token"):
        _find_tables([_token("table_open")])


def test_extract_rows_rejects_row_without_inline_cell() -> None:
    tokens = [
        _token("tr_open"),
        _token("td_open"),
        _token("text", content="bad"),
        _token("tr_close"),
    ]
    with pytest.raises(MarkdownParseError, match="Malformed Markdown table row"):
        _extract_rows(tokens)


def test_extract_rows_rejects_unmatched_row_close() -> None:
    with pytest.raises(MarkdownParseError, match="Malformed Markdown table row"):
        _extract_rows([_token("tr_close")])


def test_inline_text_rejects_non_inline_token() -> None:
    with pytest.raises(MarkdownParseError, match="Malformed Markdown inline token"):
        _inline_text(_token("text", content="hello"))


def test_token_text_preserves_line_breaks_as_spaces() -> None:
    assert _token_text(_token("softbreak")) == " "
    inline = _token(
        "inline",
        children=[
            _token("text", content="line1"),
            _token("softbreak"),
            _token("text", content="line2"),
        ],
    )
    assert _inline_text(inline) == "line1 line2"
