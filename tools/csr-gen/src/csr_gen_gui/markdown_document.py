"""Load and save multi-bank CSR Markdown documents for the GUI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from csr_gen.errors import CsrGenError, CsrValidationError, MarkdownParseError
from csr_gen.input.markdown_reader import load_markdown
from csr_gen.output.markdown_writer import write_markdown

from csr_gen_gui.models import Bank, Document

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PROSE_ONLY_SECTION = "must contain at least one CSR table"


class DocumentLoadError(CsrGenError):
    """Raised when one or more CSR bank sections cannot be loaded."""


@dataclass(frozen=True)
class _Heading:
    level: int
    title: str
    line_index: int


def load_document_file(path: Path, *, bank_heading_level: int = 2) -> Document:
    """Discover CSR banks under headings at ``bank_heading_level``.

    Prose-only bank-level headings (no tables) are skipped. Any bank-level
    heading that contains a table but fails to parse as a CSR bank raises
    :class:`DocumentLoadError` with the collected messages.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    headings = _scan_headings(lines)

    banks: list[Bank] = []
    managed_spans: list[tuple[int, int]] = []
    document_title: str | None = None
    load_errors: list[str] = []

    for index, heading in enumerate(headings):
        if heading.level == 1 and document_title is None:
            document_title = heading.title
        if heading.level != bank_heading_level:
            continue
        try:
            spec = load_markdown(text, heading.title)
        except MarkdownParseError as error:
            message = str(error)
            if _PROSE_ONLY_SECTION in message:
                continue
            load_errors.append(f"Section {heading.title!r}: {message}")
            continue
        except CsrValidationError as error:
            detail = "; ".join(error.messages)
            load_errors.append(f"Section {heading.title!r}: {detail}")
            continue
        banks.append(
            Bank(
                section_heading=spec.section_heading,
                heading_level=spec.heading_level,
                model=spec.model,
            )
        )
        managed_spans.append(_section_line_span(headings, index, len(lines)))

    if load_errors:
        raise DocumentLoadError(
            "Failed to load CSR bank section(s):\n" + "\n".join(load_errors)
        )

    if not banks:
        return Document(
            source_path=path,
            document_title=document_title,
            preamble_lines=list(lines),
        )

    first_start = managed_spans[0][0]
    last_end = managed_spans[-1][1]
    return Document(
        banks=banks,
        document_title=document_title,
        preamble_lines=lines[:first_start],
        suffix_lines=lines[last_end:],
        source_path=path,
    )


def save_document_file(document: Document, path: Path) -> None:
    """Write managed bank sections and preserve preamble/suffix prose."""
    if not document.banks:
        raise ValueError("document must contain at least one bank to save")

    _ensure_preamble_title(document)

    chunks: list[str] = []
    chunks.extend(document.preamble_lines)

    for index, bank in enumerate(document.banks):
        if index > 0 and chunks and not chunks[-1].endswith("\n"):
            chunks.append("\n")
        if chunks and chunks[-1].strip() and not chunks[-1].endswith("\n\n"):
            chunks.append("\n")
        chunks.append(
            write_markdown(
                bank.model,
                bank.section_heading,
                section_heading=bank.section_heading,
                heading_level=bank.heading_level,
            )
        )

    if document.suffix_lines:
        if not chunks[-1].endswith("\n"):
            chunks.append("\n")
        chunks.extend(document.suffix_lines)

    path.write_text("".join(chunks), encoding="utf-8")


def _scan_headings(lines: list[str]) -> list[_Heading]:
    headings: list[_Heading] = []
    for line_index, line in enumerate(lines):
        match = _HEADING_RE.match(line.rstrip("\n"))
        if match is None:
            continue
        headings.append(
            _Heading(
                level=len(match.group(1)),
                title=match.group(2).strip(),
                line_index=line_index,
            )
        )
    return headings


def _section_line_span(
    headings: list[_Heading],
    heading_index: int,
    line_count: int,
) -> tuple[int, int]:
    heading = headings[heading_index]
    for candidate in headings[heading_index + 1 :]:
        if candidate.level <= heading.level:
            return heading.line_index, candidate.line_index
    return heading.line_index, line_count


def _ensure_preamble_title(document: Document) -> None:
    """Insert or update the optional document H1 in preamble lines."""
    if not document.document_title:
        return
    line = f"# {document.document_title}\n"
    if document.preamble_lines and document.preamble_lines[0].lstrip().startswith("#"):
        document.preamble_lines[0] = line
    else:
        document.preamble_lines = [line, "\n", *document.preamble_lines]
