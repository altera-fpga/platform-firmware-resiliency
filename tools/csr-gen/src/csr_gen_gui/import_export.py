"""Headless import and export helpers for the CSR GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from csr_gen.errors import CsrGenError, CsrValidationError, ModelValidationError
from csr_gen.input.csv_reader import load_csv_file
from csr_gen.input.ipxact_reader import (
    load_ipxact_file,
    list_ipxact_address_block_names_file,
)
from csr_gen.input.systemrdl_reader import (
    load_systemrdl_file,
    list_systemrdl_addrmap_instances_file,
)
from csr_gen.model import RegisterModel, validate_model
from csr_gen.output.c_header_writer import write_c_header_file
from csr_gen.output.csv_writer import write_csv_file
from csr_gen.output.dml_writer import write_dml_file
from csr_gen.output.ipxact_writer import write_ipxact_file
from csr_gen.output.systemrdl_writer import write_systemrdl_file
from csr_gen.output.systemverilog_writer import (
    RtlGenerationError,
    module_name_from_section,
    write_systemverilog_file,
)

from csr_gen_gui.models import Bank


class ExportFormat(str, Enum):
    """Supported GUI export formats for the active bank."""

    SYSTEMVERILOG = "systemverilog"
    C_HEADER = "c-header"
    DML = "dml"
    IPXACT = "ip-xact"
    SYSTEMRDL = "systemrdl"
    CSV = "csv"


@dataclass(frozen=True)
class ExportDialogOptions:
    """QFileDialog filter and default suffix for one export format."""

    title: str
    filter: str
    suffix: str


EXPORT_DIALOG_OPTIONS: dict[ExportFormat, ExportDialogOptions] = {
    ExportFormat.SYSTEMVERILOG: ExportDialogOptions(
        title="Export SystemVerilog",
        filter="SystemVerilog (*.sv)",
        suffix=".sv",
    ),
    ExportFormat.C_HEADER: ExportDialogOptions(
        title="Export C Header",
        filter="C header (*.h)",
        suffix=".h",
    ),
    ExportFormat.DML: ExportDialogOptions(
        title="Export Simics DML",
        filter="Simics DML (*.dml)",
        suffix=".dml",
    ),
    ExportFormat.IPXACT: ExportDialogOptions(
        title="Export IP-XACT",
        filter="IP-XACT XML (*.xml)",
        suffix=".xml",
    ),
    ExportFormat.SYSTEMRDL: ExportDialogOptions(
        title="Export SystemRDL",
        filter="SystemRDL (*.rdl)",
        suffix=".rdl",
    ),
    ExportFormat.CSV: ExportDialogOptions(
        title="Export CSV",
        filter="CSV (*.csv)",
        suffix=".csv",
    ),
}


def default_export_filename(section_heading: str, export_format: ExportFormat) -> str:
    """Return a suggested export filename for one bank."""
    stem = module_name_from_section(section_heading)
    return f"{stem}{EXPORT_DIALOG_OPTIONS[export_format].suffix}"


def ipxact_import_selector_names(path: Path) -> list[str] | None:
    """Return address-block names when the user must pick one before import."""
    names = list_ipxact_address_block_names_file(path)
    if len(names) <= 1:
        return None
    return names


def systemrdl_import_selector_names(path: Path) -> list[str] | None:
    """Return addrmap instance names when the user must pick one before import."""
    names = list_systemrdl_addrmap_instances_file(path)
    if not names:
        return None
    return names


def import_bank_from_ipxact(
    path: Path,
    *,
    address_block_name: str | None = None,
) -> Bank:
    """Parse one IP-XACT file into a GUI bank."""
    spec = load_ipxact_file(path, address_block_name=address_block_name)
    return Bank(
        section_heading=spec.section_heading,
        heading_level=spec.heading_level,
        model=spec.model,
    )


def import_bank_from_systemrdl(
    path: Path,
    *,
    addrmap_instance: str | None = None,
) -> Bank:
    """Parse one SystemRDL file into a GUI bank."""
    spec = load_systemrdl_file(path, addrmap_instance=addrmap_instance)
    return Bank(
        section_heading=spec.section_heading,
        heading_level=spec.heading_level,
        model=spec.model,
    )


def import_bank_from_csv(path: Path, *, section_heading: str) -> Bank:
    """Parse one CSV file into a GUI bank."""
    title = section_heading.strip()
    if not title:
        raise ValueError("section heading must not be empty")
    spec = load_csv_file(path, csr_name=title)
    return Bank(
        section_heading=spec.section_heading,
        heading_level=spec.heading_level,
        model=spec.model,
    )


def export_bank_file(
    bank: Bank,
    path: Path,
    export_format: ExportFormat,
    *,
    interface_type: str,
) -> None:
    """Write one export artifact for a validated bank."""
    validate_model(bank.model)
    try:
        if export_format == ExportFormat.SYSTEMVERILOG:
            write_systemverilog_file(
                path,
                bank.model,
                interface_type,
                section_heading=bank.section_heading,
            )
        elif export_format == ExportFormat.C_HEADER:
            write_c_header_file(
                path,
                bank.model,
                section_heading=bank.section_heading,
            )
        elif export_format == ExportFormat.DML:
            write_dml_file(path, bank.model, section_heading=bank.section_heading)
        elif export_format == ExportFormat.IPXACT:
            write_ipxact_file(
                path,
                bank.model,
                memory_map_name=bank.section_heading,
            )
        elif export_format == ExportFormat.SYSTEMRDL:
            write_systemrdl_file(
                path,
                bank.model,
                section_heading=bank.section_heading,
            )
        elif export_format == ExportFormat.CSV:
            write_csv_file(path, bank.model)
        else:
            raise ValueError(f"unsupported export format: {export_format}")
    except (CsrGenError, RtlGenerationError) as error:
        raise CsrValidationError([str(error)]) from error


def validate_bank_for_export(model: RegisterModel) -> list[str]:
    """Return validation errors that block export."""
    from csr_gen.model import collect_model_errors

    return collect_model_errors(model)
