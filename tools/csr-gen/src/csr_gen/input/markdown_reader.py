"""Read CSR register models from Markdown tables."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from csr_gen.errors import CsrValidationError, MarkdownParseError
from csr_gen.input.table_reader import (
    EXPECTED_COLUMNS,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    TableParseError,
    parse_csr_table,
    rows_to_register_drafts,
)
from csr_gen.model import (
    RegisterDraft,
    RegisterModel,
    collect_register_draft_errors,
    drafts_to_model,
)

# Re-export for tests and callers that import column sets from markdown_reader.
__all__ = [
    "EXPECTED_COLUMNS",
    "OPTIONAL_COLUMNS",
    "REQUIRED_COLUMNS",
    "MarkdownRegisterSpec",
    "load_markdown",
    "load_markdown_file",
]


@dataclass
class MarkdownRegisterSpec:
    """A register model parsed from a Markdown CSR table."""

    model: RegisterModel
    section_heading: str
    heading_level: int


def load_markdown_file(path: Path, section: str) -> MarkdownRegisterSpec:
    """Read and validate a CSR table from a Markdown file."""
    return load_markdown(path.read_text(encoding="utf-8"), section)


def load_markdown(markdown: str, section: str) -> MarkdownRegisterSpec:
    """Read and validate CSR tables from a Markdown string."""
    tokens = MarkdownIt("commonmark", {"html": False}).enable("table").parse(markdown)
    section_tokens, section_heading, heading_level = _find_section(tokens, section)
    regions = _partition_section_tokens(section_tokens, heading_level)

    all_errors: list[str] = []
    all_drafts: list[RegisterDraft] = []
    table_count = 0

    for region in regions:
        tables = _find_tables(region.tokens)
        if len(tables) > 1:
            raise MarkdownParseError(_multiple_tables_error(section, region.subsection))
        if not tables:
            continue
        table_count += 1
        location = _table_location(section, region.subsection)
        header_cells, body_rows = _extract_table_rows(tables[0], location)
        try:
            normalized, has_reset_column = parse_csr_table(
                header_cells,
                body_rows,
                location=location,
                subsection=region.subsection,
            )
        except TableParseError as error:
            raise MarkdownParseError(str(error)) from error
        table_errors, table_drafts = rows_to_register_drafts(
            normalized,
            has_reset_column=has_reset_column,
            subsection=region.subsection,
        )
        all_errors.extend(table_errors)
        all_drafts.extend(table_drafts)

    if table_count == 0:
        raise MarkdownParseError(
            f"Markdown section {section!r} must contain at least one CSR table."
        )
    all_errors.extend(collect_register_draft_errors(all_drafts))
    if all_errors:
        raise CsrValidationError(all_errors)
    return MarkdownRegisterSpec(
        model=drafts_to_model(all_drafts),
        section_heading=section_heading,
        heading_level=heading_level,
    )


@dataclass
class _SectionRegion:
    """Markdown tokens for the section body or one subsection within it."""

    subsection: str | None
    tokens: list[Token] = field(default_factory=list)


def _multiple_tables_error(section: str, subsection: str | None) -> str:
    if subsection is None:
        return (
            f"Markdown section {section!r} must contain at most one CSR table "
            f"in the section body; found more than one."
        )
    return (
        f"Markdown section {section!r} subsection {subsection!r} must contain "
        f"at most one CSR table; found more than one."
    )


def _table_location(section: str, subsection: str | None) -> str:
    if subsection is None:
        return f"CSR table in section {section!r}"
    return f"CSR table in section {section!r} subsection {subsection!r}"


def _extract_table_rows(
    table_tokens: list[Token], location: str
) -> tuple[list[str], list[list[str]]]:
    rows = _extract_rows(table_tokens)
    if len(rows) < 2:
        raise MarkdownParseError(
            f"{location} must contain a header and at least one row."
        )
    return rows[0], rows[1:]


def _partition_section_tokens(
    tokens: list[Token], section_level: int
) -> list[_SectionRegion]:
    regions: list[_SectionRegion] = []
    current_subsection: str | None = None
    current_tokens: list[Token] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "heading_open" and int(token.tag[1:]) > section_level:
            if current_tokens:
                regions.append(_SectionRegion(current_subsection, list(current_tokens)))
            current_subsection = _inline_text(tokens[index + 1]).strip()
            current_tokens = []
            index += 3
            continue
        current_tokens.append(token)
        index += 1
    if current_tokens:
        regions.append(_SectionRegion(current_subsection, list(current_tokens)))
    return regions


def _find_section(tokens: list[Token], section: str) -> tuple[list[Token], str, int]:
    expected_heading = section.strip().casefold()
    matches: list[tuple[int, int, str]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        source_heading = _inline_text(tokens[index + 1]).strip()
        if source_heading.casefold() == expected_heading:
            matches.append((index, int(token.tag[1:]), source_heading))

    if len(matches) != 1:
        if not matches:
            raise MarkdownParseError(
                f"Markdown file must contain exactly one heading named {section!r}; "
                f"found 0."
            )
        details = ", ".join(f"H{level} {title!r}" for _index, level, title in matches)
        raise MarkdownParseError(
            f"Markdown file must contain exactly one heading named {section!r}; "
            f"found {len(matches)}: {details}. Rename the document title (#) or "
            f"bank section so they do not share the same heading text."
        )

    heading_index, heading_level, section_heading = matches[0]
    start = heading_index + 3
    end = len(tokens)
    for index in range(start, len(tokens)):
        token = tokens[index]
        if token.type == "heading_open" and int(token.tag[1:]) <= heading_level:
            end = index
            break
    return tokens[start:end], section_heading, heading_level


def _find_tables(tokens: list[Token]) -> list[list[Token]]:
    tables: list[list[Token]] = []
    table_start: int | None = None
    for index, token in enumerate(tokens):
        if token.type == "table_open":
            if table_start is not None:
                raise MarkdownParseError("Nested Markdown tables are not supported.")
            table_start = index
        elif token.type == "table_close":
            if table_start is None:
                raise MarkdownParseError("Malformed Markdown table token stream.")
            tables.append(tokens[table_start : index + 1])
            table_start = None
    if table_start is not None:
        raise MarkdownParseError("Malformed Markdown table token stream.")
    return tables


def _extract_rows(tokens: list[Token]) -> list[list[str]]:
    rows: list[list[str]] = []
    current_row: list[str] | None = None
    for index, token in enumerate(tokens):
        if token.type == "tr_open":
            current_row = []
        elif token.type in {"th_open", "td_open"}:
            if current_row is None or tokens[index + 1].type != "inline":
                raise MarkdownParseError("Malformed Markdown table row.")
            current_row.append(_inline_text(tokens[index + 1]).strip())
        elif token.type == "tr_close":
            if current_row is None:
                raise MarkdownParseError("Malformed Markdown table row.")
            rows.append(current_row)
            current_row = None
    return rows


def _inline_text(token: Token) -> str:
    if token.type != "inline":
        raise MarkdownParseError("Malformed Markdown inline token stream.")
    text = "".join(_token_text(child) for child in token.children or [])
    parser = _TextOnlyHtmlParser()
    parser.feed(text)
    parser.close()
    return parser.text


def _token_text(token: Token) -> str:
    if token.type in {"text", "code_inline"}:
        return token.content
    if token.type in {"softbreak", "hardbreak"}:
        return " "
    return "".join(_token_text(child) for child in token.children or [])


class _TextOnlyHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        return "".join(self._parts)

    def handle_data(self, data: str) -> None:
        self._parts.append(data)
