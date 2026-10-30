from pathlib import Path

import click

from csr_gen import __version__
from csr_gen import logging
from csr_gen.errors import CsrGenError
from csr_gen.input.ipxact_reader import IpxactRegisterSpec, load_ipxact_file
from csr_gen.input.csv_reader import load_csv_file
from csr_gen.input.markdown_reader import MarkdownRegisterSpec, load_markdown_file
from csr_gen.model import RegisterModel
from csr_gen.output.ipxact_writer import write_ipxact_file
from csr_gen.output.csv_writer import write_csv_file
from csr_gen.output.markdown_writer import write_markdown_file
from csr_gen.output.c_header_writer import CHeaderGenerationError, write_c_header_file
from csr_gen.output.dml_writer import DmlGenerationError, write_dml_file
from csr_gen.input.systemrdl_reader import load_systemrdl_file
from csr_gen.output.systemrdl_writer import (
    SystemRdlGenerationError,
    write_systemrdl_file,
)
from csr_gen.output.systemverilog_writer import (
    RtlGenerationError,
    write_systemverilog_file,
)

INTERFACE_TYPES = ["axi4-lite", "avalon-mm", "axi4", "apb"]
INPUT_FORMATS = ["markdown", "csv", "ip-xact", "systemrdl"]
GENERATE_OUTPUT_FORMATS = [
    "markdown",
    "csv",
    "systemverilog",
    "c-header",
    "dml",
    "ip-xact",
    "systemrdl",
]
OUTPUT_FORMAT_ALIASES = {
    "sv": "systemverilog",
    "c": "c-header",
}
OUTPUT_FORMAT_LABELS = {
    "markdown": "Markdown",
    "csv": "CSV",
    "systemverilog": "SystemVerilog",
    "c-header": "C header",
    "dml": "DML",
    "ip-xact": "IP-XACT",
    "systemrdl": "SystemRDL",
}


def default_rtl_output_path(input_file: Path) -> Path:
    """Return the default SystemVerilog output path for a Markdown input file."""
    return input_file.with_suffix(".sv")


def default_c_header_output_path(input_file: Path) -> Path:
    """Return the default C header output path for a Markdown input file."""
    return input_file.with_suffix(".h")


def _normalize_output_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    return OUTPUT_FORMAT_ALIASES.get(normalized, normalized)


def _output_format_label(output_format: str) -> str:
    return OUTPUT_FORMAT_LABELS.get(output_format, output_format)


def _log_reading_input(input_file: Path, input_format: str) -> None:
    logging.info(f"Reading {input_format} input file {input_file}")


def _log_markdown_section(section_heading: str) -> None:
    logging.info(f"Markdown section {section_heading!r}")


def _log_writing_output(output_format: str, output_file: Path) -> None:
    label = _output_format_label(output_format)
    logging.info(f"Writing {label} output to {output_file}")


def _effective_markdown_section(
    markdown_section: str | None,
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> str | None:
    if markdown_section is not None and markdown_section.strip():
        return markdown_section.strip()
    if markdown_spec is not None:
        return markdown_spec.section_heading
    if ipxact_spec is not None:
        return ipxact_spec.section_heading
    return None


def _markdown_section_heading(
    markdown_section: str | None,
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> str:
    section = _effective_markdown_section(markdown_section, markdown_spec, ipxact_spec)
    if section is not None:
        return section
    raise click.UsageError(
        "--markdown-section is required when reading or generating Markdown "
        "or generating SystemVerilog, C headers, or DML."
    )


def _import_section_heading(
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> str | None:
    if markdown_spec is not None:
        return markdown_spec.section_heading
    if ipxact_spec is not None:
        return ipxact_spec.section_heading
    return None


def _import_heading_level(
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> int | None:
    if markdown_spec is not None:
        return markdown_spec.heading_level
    if ipxact_spec is not None:
        return ipxact_spec.heading_level
    return None


def _load_csv(input_file: Path, csr_name: str | None) -> MarkdownRegisterSpec | None:
    _log_reading_input(input_file, "csv")
    try:
        csv_spec = load_csv_file(input_file, csr_name)
    except CsrGenError as error:
        logging.error(str(error))
        return None
    logging.info(f"CSR name {csv_spec.section_heading!r}")
    return MarkdownRegisterSpec(
        model=csv_spec.model,
        section_heading=csv_spec.section_heading,
        heading_level=csv_spec.heading_level,
    )


def _load_markdown(
    input_file: Path, markdown_section: str
) -> MarkdownRegisterSpec | None:
    _log_reading_input(input_file, "markdown")
    try:
        markdown_spec = load_markdown_file(input_file, markdown_section)
    except CsrGenError as error:
        logging.error(str(error))
        return None
    _log_markdown_section(markdown_spec.section_heading)
    return markdown_spec


def _load_ipxact(
    input_file: Path,
    *,
    address_block_name: str | None = None,
) -> IpxactRegisterSpec | None:
    _log_reading_input(input_file, "ip-xact")
    try:
        ipxact_spec = load_ipxact_file(
            input_file, address_block_name=address_block_name
        )
    except CsrGenError as error:
        logging.error(str(error))
        return None
    _log_markdown_section(ipxact_spec.section_heading)
    return ipxact_spec


def _load_systemrdl(
    input_file: Path,
    *,
    addrmap_instance: str | None = None,
) -> MarkdownRegisterSpec | None:
    _log_reading_input(input_file, "systemrdl")
    try:
        systemrdl_spec = load_systemrdl_file(
            input_file,
            addrmap_instance=addrmap_instance,
        )
    except CsrGenError as error:
        logging.error(str(error))
        return None
    _log_markdown_section(systemrdl_spec.section_heading)
    return MarkdownRegisterSpec(
        model=systemrdl_spec.model,
        section_heading=systemrdl_spec.section_heading,
        heading_level=systemrdl_spec.heading_level,
    )


def _load_model(
    input_file: Path,
    input_format: str,
    markdown_section: str | None,
    *,
    csr_name: str | None = None,
    ipxact_address_block: str | None = None,
    systemrdl_addrmap: str | None = None,
) -> tuple[
    RegisterModel | None,
    MarkdownRegisterSpec | None,
    IpxactRegisterSpec | None,
]:
    if input_format == "markdown":
        if markdown_section is None:
            raise click.UsageError(
                "--markdown-section is required when reading Markdown."
            )
        markdown_spec = _load_markdown(input_file, markdown_section)
        if markdown_spec is None:
            return None, None, None
        return markdown_spec.model, markdown_spec, None
    if input_format == "csv":
        markdown_spec = _load_csv(input_file, csr_name)
        if markdown_spec is None:
            return None, None, None
        return markdown_spec.model, markdown_spec, None
    if input_format == "ip-xact":
        ipxact_spec = _load_ipxact(input_file, address_block_name=ipxact_address_block)
        if ipxact_spec is None:
            return None, None, None
        return ipxact_spec.model, None, ipxact_spec
    if input_format == "systemrdl":
        markdown_spec = _load_systemrdl(
            input_file,
            addrmap_instance=systemrdl_addrmap,
        )
        if markdown_spec is None:
            return None, None, None
        return markdown_spec.model, markdown_spec, None
    _log_reading_input(input_file, input_format)
    logging.error(f"Reading {input_format} input is not implemented yet.")
    return None, None, None


def _write_output(
    model: RegisterModel,
    output_format: str,
    output_file: Path,
    markdown_section: str | None,
    interface_type: str,
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> bool:
    """Write one output artifact. Return False when the format is not implemented."""
    _log_writing_output(output_format, output_file)
    if output_format == "markdown":
        section = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        write_markdown_file(
            output_file,
            model,
            section,
            section_heading=_import_section_heading(markdown_spec, ipxact_spec),
            heading_level=_import_heading_level(markdown_spec, ipxact_spec),
        )
        return True
    if output_format == "csv":
        write_csv_file(output_file, model)
        return True
    if output_format == "systemverilog":
        section_heading = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        try:
            write_systemverilog_file(
                output_file,
                model,
                interface_type,
                section_heading=section_heading,
            )
        except RtlGenerationError as error:
            logging.error(str(error))
            return False
        return True
    if output_format == "c-header":
        section_heading = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        try:
            write_c_header_file(output_file, model, section_heading=section_heading)
        except CHeaderGenerationError as error:
            logging.error(str(error))
            return False
        return True
    if output_format == "dml":
        section_heading = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        try:
            write_dml_file(output_file, model, section_heading=section_heading)
        except DmlGenerationError as error:
            logging.error(str(error))
            return False
        return True
    if output_format == "ip-xact":
        map_name = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        write_ipxact_file(
            output_file,
            model,
            memory_map_name=map_name,
        )
        return True
    if output_format == "systemrdl":
        section_heading = _markdown_section_heading(
            markdown_section, markdown_spec, ipxact_spec
        )
        try:
            write_systemrdl_file(
                output_file,
                model,
                section_heading=section_heading,
            )
        except SystemRdlGenerationError as error:
            logging.error(str(error))
            return False
        return True
    label = _output_format_label(output_format)
    logging.error(f"Writing {label} output is not implemented yet.")
    return False


def _write_outputs(
    model: RegisterModel,
    outputs: list[tuple[str, Path]],
    markdown_section: str | None,
    interface_type: str,
    markdown_spec: MarkdownRegisterSpec | None,
    ipxact_spec: IpxactRegisterSpec | None,
) -> None:
    for output_format, output_file in outputs:
        if not _write_output(
            model,
            output_format,
            output_file,
            markdown_section,
            interface_type,
            markdown_spec,
            ipxact_spec,
        ):
            return


def _paired_outputs(
    output_files: tuple[Path, ...], output_formats: tuple[str, ...]
) -> list[tuple[str, Path]]:
    if len(output_files) != len(output_formats):
        raise click.UsageError(
            "Specify the same number of --output-file and --output-format options."
        )
    return [
        (_normalize_output_format(output_format), output_file)
        for output_format, output_file in zip(output_formats, output_files, strict=True)
    ]


def _validate_input_options(
    input_format: str,
    markdown_section: str | None,
    csr_name: str | None,
    ipxact_address_block: str | None,
    systemrdl_addrmap: str | None,
) -> None:
    if input_format == "markdown" and markdown_section is None:
        raise click.UsageError("--markdown-section is required when reading Markdown.")
    if input_format == "csv" and markdown_section is not None:
        raise click.UsageError(
            "--markdown-section is not used with CSV input; use --csr-name instead."
        )
    if input_format != "csv" and csr_name is not None:
        raise click.UsageError("--csr-name is only valid with --input-format csv.")
    if ipxact_address_block is not None and input_format != "ip-xact":
        raise click.UsageError(
            "--ipxact-address-block is only valid with --input-format ip-xact."
        )
    if systemrdl_addrmap is not None and input_format != "systemrdl":
        raise click.UsageError(
            "--systemrdl-addrmap is only valid with --input-format systemrdl."
        )


def _run_generate(
    input_file: Path,
    input_format: str,
    markdown_section: str | None,
    outputs: list[tuple[str, Path]],
    interface_type: str,
    *,
    csr_name: str | None = None,
    ipxact_address_block: str | None = None,
    systemrdl_addrmap: str | None = None,
) -> None:
    output_formats = [output_format for output_format, _ in outputs]
    _validate_input_options(
        input_format,
        markdown_section,
        csr_name,
        ipxact_address_block,
        systemrdl_addrmap,
    )

    model, markdown_spec, ipxact_spec = _load_model(
        input_file,
        input_format,
        markdown_section,
        csr_name=csr_name,
        ipxact_address_block=ipxact_address_block,
        systemrdl_addrmap=systemrdl_addrmap,
    )
    if model is None:
        return

    needs_section = "markdown" in (input_format, *output_formats) or any(
        fmt in output_formats for fmt in ("systemverilog", "c-header", "dml")
    )
    if (
        needs_section
        and _effective_markdown_section(markdown_section, markdown_spec, ipxact_spec)
        is None
    ):
        raise click.UsageError(
            "--markdown-section is required when reading or generating Markdown "
            "or generating SystemVerilog, C headers, or DML."
        )

    _write_outputs(
        model,
        outputs,
        markdown_section,
        interface_type,
        markdown_spec,
        ipxact_spec,
    )


def _log_deprecated_command(command_name: str) -> None:
    logging.info(
        f"The {command_name} command is deprecated; use 'csr-gen generate' instead."
    )


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="csr-gen")
@click.option(
    "--warnings-as-errors",
    is_flag=True,
    help="Treat warnings as errors and exit with a non-zero status.",
)
def main(warnings_as_errors: bool) -> None:
    """Generate CSR interface artifacts from register definitions."""
    logging.configure(warnings_as_errors=warnings_as_errors)


@main.command("validate")
@click.option(
    "--input-file",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Register description file (Markdown or CSV).",
)
@click.option(
    "--input-format",
    "input_format",
    default="markdown",
    show_default=True,
    type=click.Choice(["markdown", "csv"], case_sensitive=False),
    help="Input register table format.",
)
@click.option(
    "--markdown-section",
    default=None,
    help="Markdown section containing the CSR register table.",
)
@click.option(
    "--csr-name",
    default=None,
    help="CSR block name for CSV input (defaults to the input file stem).",
)
@click.option(
    "--dump-model",
    is_flag=True,
    help="Write the normalized register model as YAML to standard output.",
)
def validate(
    input_file: Path,
    input_format: str,
    markdown_section: str | None,
    csr_name: str | None,
    dump_model: bool,
) -> None:
    """Validate a Markdown or CSV CSR register table."""
    from csr_gen.output.yaml_writer import dump_model_yaml

    _validate_input_options(input_format, markdown_section, csr_name, None, None)
    model, markdown_spec, _ipxact_spec = _load_model(
        input_file, input_format, markdown_section, csr_name=csr_name
    )
    if model is None or markdown_spec is None:
        return
    logging.info(f"Input file {input_file} is valid.")
    if dump_model:
        logging.info("Writing YAML model to standard output.")
        click.echo(dump_model_yaml(model), nl=False)


@main.command("generate")
@click.option(
    "--input-file",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path for the input register description.",
)
@click.option(
    "--input-format",
    "input_format",
    required=True,
    type=click.Choice(INPUT_FORMATS, case_sensitive=False),
    help="Input register description format.",
)
@click.option(
    "--output-file",
    "output_files",
    multiple=True,
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for a generated artifact (repeat per output format).",
)
@click.option(
    "--markdown-section",
    help=(
        "CSR block section heading. Required for Markdown input; optional for "
        "CSV, IP-XACT, and other inputs that supply or default a block name. "
        "Used when generating Markdown, SystemVerilog, C headers, DML, or IP-XACT."
    ),
)
@click.option(
    "--csr-name",
    default=None,
    help="CSR block name for CSV input (defaults to the input file stem).",
)
@click.option(
    "--ipxact-address-block",
    default=None,
    help=(
        "IP-XACT address block to import (exact <name>). Required when the "
        "memory map contains multiple address blocks."
    ),
)
@click.option(
    "--systemrdl-addrmap",
    default=None,
    help=(
        "SystemRDL nested addrmap instance to import (exact instance name). "
        "Required when the top-level addrmap contains multiple nested addrmaps."
    ),
)
@click.option(
    "--output-format",
    "output_formats",
    multiple=True,
    required=True,
    type=click.Choice(
        [*GENERATE_OUTPUT_FORMATS, *OUTPUT_FORMAT_ALIASES.keys()],
        case_sensitive=False,
    ),
    help="Output format (repeat per output file). Aliases: sv, c.",
)
@click.option(
    "--interface-type",
    type=click.Choice(INTERFACE_TYPES, case_sensitive=False),
    default="axi4-lite",
    show_default=True,
    help="CSR bus interface for SystemVerilog RTL outputs.",
)
def generate(
    input_file: Path,
    input_format: str,
    output_files: tuple[Path, ...],
    markdown_section: str | None,
    csr_name: str | None,
    ipxact_address_block: str | None,
    systemrdl_addrmap: str | None,
    output_formats: tuple[str, ...],
    interface_type: str,
) -> None:
    """Generate one or more CSR artifacts from a register description."""
    _run_generate(
        input_file,
        input_format,
        markdown_section,
        _paired_outputs(output_files, output_formats),
        interface_type,
        csr_name=csr_name,
        ipxact_address_block=ipxact_address_block,
        systemrdl_addrmap=systemrdl_addrmap,
    )


@main.command("generate-rtl", hidden=True)
@click.option(
    "--input-file",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Markdown file containing the CSR register table.",
)
@click.option(
    "--markdown-section",
    required=True,
    help="Markdown section containing the CSR register table.",
)
@click.option(
    "--output-file",
    "output_file",
    type=click.Path(dir_okay=False, path_type=Path),
    help=(
        "Path for the generated SystemVerilog RTL. "
        "Defaults to the input Markdown basename with a .sv extension."
    ),
)
@click.option(
    "--interface-type",
    type=click.Choice(INTERFACE_TYPES, case_sensitive=False),
    default="axi4-lite",
    show_default=True,
    help="CSR bus interface generated by the RTL serializer.",
)
def generate_rtl(
    input_file: Path,
    markdown_section: str,
    output_file: Path | None,
    interface_type: str,
) -> None:
    """Deprecated: use generate."""
    _log_deprecated_command("generate-rtl")
    resolved_output = (
        output_file if output_file is not None else default_rtl_output_path(input_file)
    )
    _run_generate(
        input_file,
        "markdown",
        markdown_section,
        [("systemverilog", resolved_output)],
        interface_type,
    )


@main.command("convert", hidden=True)
@click.option(
    "--input-file",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path for the input register description.",
)
@click.option(
    "--input-format",
    "input_format",
    required=True,
    type=click.Choice(INPUT_FORMATS, case_sensitive=False),
    help="Input register description format.",
)
@click.option(
    "--output-file",
    "output_files",
    multiple=True,
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path for a generated register description (repeat per output format).",
)
@click.option(
    "--markdown-section",
    help=(
        "CSR block section heading. Required for Markdown input; optional for "
        "CSV, IP-XACT, and other inputs that supply or default a block name. "
        "Used when generating Markdown, SystemVerilog, C headers, DML, or IP-XACT."
    ),
)
@click.option(
    "--csr-name",
    default=None,
    help="CSR block name for CSV input (defaults to the input file stem).",
)
@click.option(
    "--ipxact-address-block",
    default=None,
    help=(
        "IP-XACT address block to import (exact <name>). Required when the "
        "memory map contains multiple address blocks."
    ),
)
@click.option(
    "--systemrdl-addrmap",
    default=None,
    help=(
        "SystemRDL nested addrmap instance to import (exact instance name). "
        "Required when the top-level addrmap contains multiple nested addrmaps."
    ),
)
@click.option(
    "--output-format",
    "output_formats",
    multiple=True,
    required=True,
    type=click.Choice(
        [*GENERATE_OUTPUT_FORMATS, *OUTPUT_FORMAT_ALIASES.keys()],
        case_sensitive=False,
    ),
    help="Output register description format (repeat per output file).",
)
def convert(
    input_file: Path,
    input_format: str,
    output_files: tuple[Path, ...],
    markdown_section: str | None,
    csr_name: str | None,
    ipxact_address_block: str | None,
    systemrdl_addrmap: str | None,
    output_formats: tuple[str, ...],
) -> None:
    """Deprecated: use generate."""
    _log_deprecated_command("convert")
    _run_generate(
        input_file,
        input_format,
        markdown_section,
        _paired_outputs(output_files, output_formats),
        "axi4-lite",
        csr_name=csr_name,
        ipxact_address_block=ipxact_address_block,
        systemrdl_addrmap=systemrdl_addrmap,
    )
