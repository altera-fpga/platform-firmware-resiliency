"""Shared datatypes for the CSR GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from csr_gen.model import RegisterModel


@dataclass
class Bank:
    """One named Markdown section and its register map."""

    section_heading: str
    heading_level: int = 2
    model: RegisterModel = field(default_factory=RegisterModel)


@dataclass
class Document:
    """One Markdown file containing one or more CSR banks."""

    banks: list[Bank] = field(default_factory=list)
    document_title: str | None = None
    preamble_lines: list[str] = field(default_factory=list)
    suffix_lines: list[str] = field(default_factory=list)
    source_path: Path | None = None
    active_bank_index: int = 0


@dataclass
class PreviewArtifacts:
    """Generated preview text for the active bank."""

    systemverilog: str | None = None
    c_header: str | None = None
    dml: str | None = None
    systemrdl: str | None = None
    ipxact: str | None = None
    errors: list[str] = field(default_factory=list)
