"""In-memory CSR document model for the GUI."""

from __future__ import annotations

from pathlib import Path

from csr_gen.errors import CsrGenError
from csr_gen.model import collect_model_errors, validate_model
from csr_gen.output.c_header_writer import write_c_header
from csr_gen.output.dml_writer import write_dml
from csr_gen.output.ipxact_writer import write_ipxact
from csr_gen.output.systemrdl_writer import write_systemrdl
from csr_gen.output.systemverilog_writer import write_systemverilog

from csr_gen_gui.markdown_document import load_document_file, save_document_file
from csr_gen_gui.models import Bank, Document, PreviewArtifacts

DEFAULT_INTERFACE_TYPE = "axi4-lite"

__all__ = [
    "Bank",
    "DEFAULT_INTERFACE_TYPE",
    "Document",
    "DocumentController",
    "PreviewArtifacts",
]


class DocumentController:
    """Headless document operations shared by the GUI and tests."""

    def __init__(self, document: Document | None = None) -> None:
        self.document = document or Document()

    @property
    def active_bank(self) -> Bank:
        return self.document.banks[self.document.active_bank_index]

    def new_document(self, *, document_title: str | None = None) -> None:
        """Replace the current document with an empty one."""
        self.document = Document(document_title=document_title)

    def add_bank(self, section_heading: str, *, heading_level: int = 2) -> int:
        """Append a bank and make it active. Returns the new bank index."""
        title = section_heading.strip()
        if not title:
            raise ValueError("section heading must not be empty")
        bank = Bank(section_heading=title, heading_level=heading_level)
        self.document.banks.append(bank)
        self.document.active_bank_index = len(self.document.banks) - 1
        return self.document.active_bank_index

    def import_bank(self, bank: Bank) -> int:
        """Replace the document with one imported bank and clear the saved path."""
        self.document = Document(banks=[bank], active_bank_index=0, source_path=None)
        return 0

    def remove_bank(self, index: int) -> None:
        """Remove a bank and clamp the active index."""
        if index < 0 or index >= len(self.document.banks):
            raise IndexError(f"bank index out of range: {index}")
        del self.document.banks[index]
        if not self.document.banks:
            self.document.active_bank_index = 0
        elif self.document.active_bank_index >= len(self.document.banks):
            self.document.active_bank_index = len(self.document.banks) - 1

    def rename_bank(self, index: int, section_heading: str) -> None:
        """Rename a bank section heading."""
        title = section_heading.strip()
        if not title:
            raise ValueError("section heading must not be empty")
        self.document.banks[index].section_heading = title

    def set_active_bank(self, index: int) -> None:
        """Select the bank shown in the editor and preview panes."""
        if index < 0 or index >= len(self.document.banks):
            raise IndexError(f"bank index out of range: {index}")
        self.document.active_bank_index = index

    def validate_bank(self, index: int) -> list[str]:
        """Return validation errors for a bank (empty when legal)."""
        return collect_model_errors(self.document.banks[index].model)

    def validate_active_bank(self) -> list[str]:
        """Return validation errors for the active bank."""
        return self.validate_bank(self.document.active_bank_index)

    def generate_previews(
        self,
        index: int | None = None,
        *,
        interface_type: str = DEFAULT_INTERFACE_TYPE,
    ) -> PreviewArtifacts:
        """Render SV, C, DML, SystemRDL, and IP-XACT previews for a legal bank."""
        bank_index = self.document.active_bank_index if index is None else index
        errors = self.validate_bank(bank_index)
        if errors:
            return PreviewArtifacts(errors=list(errors))

        bank = self.document.banks[bank_index]
        try:
            return PreviewArtifacts(
                systemverilog=write_systemverilog(
                    bank.model,
                    interface_type,
                    section_heading=bank.section_heading,
                ),
                c_header=write_c_header(
                    bank.model,
                    section_heading=bank.section_heading,
                ),
                dml=write_dml(
                    bank.model,
                    section_heading=bank.section_heading,
                ),
                systemrdl=write_systemrdl(
                    bank.model,
                    section_heading=bank.section_heading,
                ),
                ipxact=write_ipxact(
                    bank.model,
                    memory_map_name=bank.section_heading,
                ),
            )
        except CsrGenError as error:
            return PreviewArtifacts(errors=[str(error)])

    def load(self, path: Path, *, bank_heading_level: int = 2) -> None:
        """Load CSR banks from a Markdown file."""
        self.document = load_document_file(path, bank_heading_level=bank_heading_level)

    def save(self, path: Path | None = None) -> Path:
        """Write the document to disk, preserving unmanaged prose when loaded."""
        target = path or self.document.source_path
        if target is None:
            raise ValueError("save path is required for a new document")
        for bank in self.document.banks:
            validate_model(bank.model)
        save_document_file(self.document, target)
        self.document.source_path = target
        return target
