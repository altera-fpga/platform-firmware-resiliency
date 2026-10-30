import logging
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from csr_gen.cli import (
    _effective_markdown_section,
    _import_heading_level,
    _import_section_heading,
    _load_csv,
    _load_ipxact,
    _load_markdown,
    _load_model,
    _markdown_section_heading,
    _run_generate,
    _validate_input_options,
    _write_output,
    _write_outputs,
    default_c_header_output_path,
    default_rtl_output_path,
    main,
)
from csr_gen import logging as csr_logging
from test_paths import TESTDATA

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = REPO_ROOT / "specs" / "golden"
from csr_gen.input.markdown_reader import load_markdown, load_markdown_file
from csr_gen.model import Field, Register, RegisterModel
from csr_gen.output.c_header_writer import CHeaderGenerationError
from csr_gen.output.dml_writer import DmlGenerationError
from csr_gen.output.systemrdl_writer import SystemRdlGenerationError

RUNNER = CliRunner()


def invoke_cli(*args, **kwargs):
    return RUNNER.invoke(*args, **kwargs)


REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_REGS = REPO_ROOT / "specs" / "golden" / "example-device" / "regs.md"

VALID_MARKDOWN = """\
# Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | ENABLE | 0 | rw | 0 | Enable |
"""


def test_help_lists_initial_commands() -> None:
    result = invoke_cli(main, ["--help"])

    assert result.exit_code == 0
    assert "--warnings-as-errors" in result.output
    assert "generate" in result.output
    assert "validate" in result.output
    assert "import-md" not in result.output
    assert "export" not in result.output


def test_version_option() -> None:
    result = invoke_cli(main, ["--version"])

    assert result.exit_code == 0
    assert "csr-gen, version 1.0.0" in result.output


def test_validate_succeeds_for_valid_markdown(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "validate",
                "--input-file",
                str(source),
                "--markdown-section",
                "Registers",
            ],
        )

    assert result.exit_code == 0
    assert f"Reading markdown input file {source}" in caplog.text
    assert "Markdown section 'Registers'" in caplog.text
    assert f"Input file {source} is valid." in caplog.text


def test_validate_dump_model_writes_yaml(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "validate",
                "--input-file",
                str(source),
                "--markdown-section",
                "Registers",
                "--dump-model",
            ],
        )

    assert result.exit_code == 0
    assert f"Input file {source} is valid." in caplog.text
    assert "Writing YAML model to standard output." in caplog.text
    assert "registers:" in result.output
    assert "CTRL" in result.output
    assert "ENABLE" in result.output


def test_validate_reports_multiple_errors(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(
        """\
# Registers

| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| CTRL | 0x00 | A | 3:0 | rw | 0 | |
|  |  | B | 2:1 | rw | 0 | overlap |
| OTHER | bad | C | 0 | rw | 0 | bad address |
""",
        encoding="utf-8",
    )

    result = invoke_cli(
        main,
        [
            "validate",
            "--input-file",
            str(source),
            "--markdown-section",
            "Registers",
        ],
    )

    assert result.exit_code == 1
    assert "CSR specification errors:" in result.output
    assert "row 2" in result.output
    assert "row 3" in result.output


def test_generate_systemverilog_writes_axi4lite_rtl(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = source.with_suffix(".sv")

    with caplog.at_level("INFO"):
        result = invoke_cli(
            main,
            [
                "generate",
                "--input-file",
                str(source),
                "--input-format",
                "markdown",
                "--markdown-section",
                "Registers",
                "--output-file",
                str(output),
                "--output-format",
                "systemverilog",
            ],
        )

    assert result.exit_code == 0
    assert f"Writing SystemVerilog output to {output}" in caplog.text
    rtl = output.read_text(encoding="utf-8")
    assert "module registers" in rtl
    assert "`timescale 1 ps / 1 ps" in rtl
    assert "ctrl_enable_q" in rtl


def test_generate_accepts_interface_type_and_sv_alias(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(source.with_suffix(".sv")),
            "--output-format",
            "sv",
            "--interface-type",
            "apb",
        ],
    )

    assert result.exit_code == 1
    assert "SystemVerilog RTL generation for apb" in result.output


def test_generate_help_lists_interface_default() -> None:
    result = invoke_cli(main, ["generate", "--help"])

    assert result.exit_code == 0
    assert "--interface-type [axi4-lite|avalon-mm|axi4|apb]" in result.output
    assert "[default: axi4-lite]" in result.output


def test_generate_validates_markdown_input(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n", encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(tmp_path / "out.md"),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 1
    assert "must contain at least one CSR table" in result.output


def test_generate_reads_systemrdl(tmp_path) -> None:
    source = GOLDEN_ROOT / "example-device" / "expected.rdl"
    output = tmp_path / "regs.md"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "systemrdl",
            "--output-file",
            str(output),
            "--output-format",
            "markdown",
            "--markdown-section",
            "CSR Registers",
        ],
    )

    assert result.exit_code == 0
    assert "CTRL" in output.read_text(encoding="utf-8")


def test_generate_writes_multiple_outputs_in_one_run(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    markdown_out = tmp_path / "normalized.md"
    markdown_copy = tmp_path / "copy.md"

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "generate",
                "--input-file",
                str(source),
                "--input-format",
                "markdown",
                "--markdown-section",
                "Registers",
                "--output-file",
                str(markdown_out),
                "--output-format",
                "markdown",
                "--output-file",
                str(markdown_copy),
                "--output-format",
                "markdown",
            ],
        )

    assert result.exit_code == 0
    assert f"Reading markdown input file {source}" in caplog.text
    assert f"Writing Markdown output to {markdown_out}" in caplog.text
    assert f"Writing Markdown output to {markdown_copy}" in caplog.text
    assert markdown_out.read_text(encoding="utf-8") == markdown_copy.read_text(
        encoding="utf-8"
    )


def test_generate_requires_matching_output_option_counts(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(tmp_path / "a.md"),
            "--output-format",
            "markdown",
            "--output-format",
            "ip-xact",
        ],
    )

    assert result.exit_code == 2
    assert "same number of --output-file and --output-format" in result.output


def test_generate_markdown_round_trip(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "normalized.md"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(output),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    output_text = output.read_text(encoding="utf-8")
    assert output_text.startswith("# Registers")
    assert "| CTRL | 0x0 |  |  |  |  | internal | Enable |" in output_text
    assert "|  |  | ENABLE | 0 | rw | 0x0 |  | Enable |" in output_text


def test_generate_markdown_preserves_source_section_heading(tmp_path, caplog) -> None:
    output = tmp_path / "k.md"

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "generate",
                "--input-file",
                str(GOLDEN_REGS),
                "--input-format",
                "markdown",
                "--markdown-section",
                "cSR Registers",
                "--output-file",
                str(output),
                "--output-format",
                "markdown",
            ],
        )

    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8").splitlines()[0] == "## CSR Registers"
    assert "Markdown section 'CSR Registers'" in caplog.text


def test_generate_ipxact_output(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "regs.xml"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(output),
            "--output-format",
            "ip-xact",
        ],
    )

    assert result.exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "memoryMap" in text
    assert "CTRL" in text


def test_generate_ipxact_input_defaults_section(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    markdown_output = tmp_path / "regs.md"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--output-file",
            str(markdown_output),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    assert markdown_output.read_text(encoding="utf-8").startswith("## Example CSR Map")


def test_generate_ipxact_address_block_filter(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_multi_block.xml"
    markdown_output = tmp_path / "beta.md"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--ipxact-address-block",
            "beta_block",
            "--output-file",
            str(markdown_output),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    text = markdown_output.read_text(encoding="utf-8")
    assert "BETA_STAT" in text
    assert "ALPHA_CTRL" not in text


def test_generate_rejects_ipxact_address_block_for_markdown(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "CSR Registers",
            "--ipxact-address-block",
            "unused",
            "--output-file",
            str(tmp_path / "out.md"),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code != 0
    assert "ipxact-address-block" in result.output


def test_generate_systemrdl_addrmap_filter(tmp_path) -> None:
    rdl_source = TESTDATA / "systemrdl" / "hierarchical_multi_peripheral.rdl"
    markdown_output = tmp_path / "uart.md"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(rdl_source),
            "--input-format",
            "systemrdl",
            "--systemrdl-addrmap",
            "uart_inst",
            "--output-file",
            str(markdown_output),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    text = markdown_output.read_text(encoding="utf-8")
    assert "UART_TX" in text
    assert "SPI_DATA" not in text


def test_generate_rejects_systemrdl_addrmap_for_markdown(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "CSR Registers",
            "--systemrdl-addrmap",
            "unused",
            "--output-file",
            str(tmp_path / "out.md"),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code != 0
    assert "systemrdl-addrmap" in result.output


def test_generate_c_header_output(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "regs.h"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(output),
            "--output-format",
            "c-header",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert "#ifndef REGISTERS_H" in text
    assert "REGISTERS_BASE_ADDR" in text


def test_generate_c_header_requires_markdown_section(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--output-file",
            str(tmp_path / "regs.h"),
            "--output-format",
            "c-header",
        ],
    )

    assert result.exit_code == 2
    assert "--markdown-section is required" in result.output


def test_generate_dml_output(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "device.dml"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(output),
            "--output-format",
            "dml",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert "dml 1.4;" in text
    assert "device registers;" in text
    assert "bank registers {" in text
    assert "field ENABLE @ [0] is (read, write)" in text


def test_generate_dml_requires_markdown_section(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--output-file",
            str(tmp_path / "device.dml"),
            "--output-format",
            "dml",
        ],
    )

    assert result.exit_code == 2
    assert "--markdown-section is required" in result.output


def test_generate_ipxact_to_dml_without_explicit_section(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    output = tmp_path / "example.dml"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--output-file",
            str(output),
            "--output-format",
            "dml",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    assert "device example_csr_map;" in output.read_text(encoding="utf-8")


def test_generate_ipxact_to_c_header_without_explicit_section(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    output = tmp_path / "example.h"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--output-file",
            str(output),
            "--output-format",
            "c-header",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert "#ifndef EXAMPLE_CSR_MAP_H" in text
    assert "EXAMPLE_CSR_MAP_CTRL_ADDR" in text


def test_generate_ipxact_to_c_header_with_section_override(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    output = tmp_path / "custom.h"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--markdown-section",
            "Custom Block",
            "--output-file",
            str(output),
            "--output-format",
            "c-header",
        ],
    )

    assert result.exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert "#ifndef CUSTOM_BLOCK_H" in text
    assert "CUSTOM_BLOCK_CTRL_ADDR" in text


def test_generate_csv_to_c_header_and_dml(tmp_path) -> None:
    csv_source = TESTDATA / "example_device.csv"
    header_output = tmp_path / "example.h"
    dml_output = tmp_path / "example.dml"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(csv_source),
            "--input-format",
            "csv",
            "--output-file",
            str(header_output),
            "--output-format",
            "c-header",
            "--output-file",
            str(dml_output),
            "--output-format",
            "dml",
        ],
    )

    assert result.exit_code == 0
    assert header_output.is_file()
    assert dml_output.is_file()
    assert "device example_device;" in dml_output.read_text(encoding="utf-8")
    assert "EXAMPLE_DEVICE_" in header_output.read_text(encoding="utf-8")


def test_generate_markdown_and_dml_in_one_run(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    markdown_out = tmp_path / "normalized.md"
    dml_out = tmp_path / "device.dml"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(markdown_out),
            "--output-format",
            "markdown",
            "--output-file",
            str(dml_out),
            "--output-format",
            "dml",
        ],
    )

    assert result.exit_code == 0
    assert markdown_out.is_file()
    assert dml_out.is_file()
    assert "dml 1.4;" in dml_out.read_text(encoding="utf-8")


def test_default_rtl_output_path_uses_markdown_basename() -> None:
    assert default_rtl_output_path(Path("/path/to/regs.md")) == Path("/path/to/regs.sv")


def test_default_c_header_output_path_uses_markdown_basename() -> None:
    assert default_c_header_output_path(Path("/path/to/regs.md")) == Path(
        "/path/to/regs.h"
    )


def test_generate_requires_input_option() -> None:
    result = invoke_cli(
        main,
        ["generate", "--markdown-section", "Registers"],
    )

    assert result.exit_code == 2
    assert "Missing option '--input-file'." in result.output


def test_generate_requires_markdown_section(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--output-file",
            str(tmp_path / "regs.out.md"),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 2
    assert "--markdown-section is required" in result.output


def test_generate_systemverilog_requires_markdown_section(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--output-file",
            str(tmp_path / "regs.sv"),
            "--output-format",
            "systemverilog",
        ],
    )

    assert result.exit_code == 2
    assert "--markdown-section is required" in result.output


def test_deprecated_generate_rtl_forwards_to_generate(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "generate-rtl",
                "--input-file",
                str(source),
                "--markdown-section",
                "Registers",
            ],
        )

    assert result.exit_code == 0
    assert "generate-rtl command is deprecated" in caplog.text
    assert (tmp_path / "regs.sv").is_file()
    assert "module registers" in (tmp_path / "regs.sv").read_text(encoding="utf-8")


def test_deprecated_convert_forwards_to_generate(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "normalized.md"

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "convert",
                "--input-file",
                str(source),
                "--input-format",
                "markdown",
                "--markdown-section",
                "Registers",
                "--output-file",
                str(output),
                "--output-format",
                "markdown",
            ],
        )

    assert result.exit_code == 0
    assert "convert command is deprecated" in caplog.text
    assert output.read_text(encoding="utf-8").startswith("# Registers")


def test_cli_helpers_resolve_section_from_loaded_specs() -> None:
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    from csr_gen.input.ipxact_reader import load_ipxact_file

    ipxact_spec = load_ipxact_file(ipxact_source)

    assert (
        _effective_markdown_section("  ", markdown_spec, None)
        == markdown_spec.section_heading
    )
    assert (
        _effective_markdown_section(None, None, ipxact_spec)
        == ipxact_spec.section_heading
    )
    assert _import_section_heading(markdown_spec, None) == "Registers"
    assert _import_heading_level(markdown_spec, None) == 1
    assert _import_section_heading(None, None) is None
    assert _import_heading_level(None, None) is None


def test_markdown_section_heading_raises_when_unresolved() -> None:
    with pytest.raises(click.UsageError, match="--markdown-section is required"):
        _markdown_section_heading(None, None, None)


def test_load_model_requires_markdown_section(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")

    with pytest.raises(click.UsageError, match="--markdown-section is required"):
        _load_model(source, "markdown", None)


def test_validate_returns_early_on_invalid_markdown(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n\nNo table.\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "validate",
                "--input-file",
                str(source),
                "--markdown-section",
                "Registers",
            ],
        )

    assert result.exit_code == 1
    assert "at least one CSR table" in result.output


def test_generate_returns_early_on_invalid_markdown(tmp_path, caplog) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n\nNo table.\n", encoding="utf-8")
    output = tmp_path / "out.md"

    with caplog.at_level(logging.ERROR, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "generate",
                "--input-file",
                str(source),
                "--input-format",
                "markdown",
                "--markdown-section",
                "Registers",
                "--output-file",
                str(output),
                "--output-format",
                "markdown",
            ],
        )

    assert result.exit_code == 1
    assert not output.exists()


def test_generate_returns_early_on_invalid_ipxact(tmp_path, caplog) -> None:
    source = tmp_path / "bad.xml"
    source.write_text("<not-xml", encoding="utf-8")
    output = tmp_path / "out.md"

    with caplog.at_level(logging.ERROR, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "generate",
                "--input-file",
                str(source),
                "--input-format",
                "ip-xact",
                "--output-file",
                str(output),
                "--output-format",
                "markdown",
            ],
        )

    assert result.exit_code == 1
    assert not output.exists()


def test_generate_ipxact_to_systemverilog_without_explicit_section(tmp_path) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    output = tmp_path / "example.sv"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(ipxact_source),
            "--input-format",
            "ip-xact",
            "--output-file",
            str(output),
            "--output-format",
            "systemverilog",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    assert "module example_csr_map" in output.read_text(encoding="utf-8")


def test_generate_systemrdl_output(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    output = tmp_path / "out.rdl"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(output),
            "--output-format",
            "systemrdl",
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    assert "addrmap registers" in output.read_text(encoding="utf-8")


def test_generate_aborts_remaining_outputs_after_failure(tmp_path) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    markdown_out = tmp_path / "normalized.md"
    sv_out = tmp_path / "out.sv"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "markdown",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(markdown_out),
            "--output-format",
            "markdown",
            "--output-file",
            str(sv_out),
            "--output-format",
            "systemverilog",
            "--interface-type",
            "avalon-mm",
        ],
    )

    assert result.exit_code == 1
    assert markdown_out.is_file()
    assert not sv_out.exists()


def test_run_generate_requires_resolved_section(monkeypatch, tmp_path) -> None:
    source = tmp_path / "regs.xml"
    source.write_text("<ipxact:component/>", encoding="utf-8")
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )

    monkeypatch.setattr(
        "csr_gen.cli._load_model",
        lambda *_args, **_kwargs: (model, None, None),
    )

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "ip-xact",
            "--output-file",
            str(tmp_path / "out.md"),
            "--output-format",
            "markdown",
        ],
    )

    assert result.exit_code == 2
    assert "--markdown-section is required" in result.output


def test_write_output_raises_on_rtl_generation_error(tmp_path) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    with pytest.raises(
        click.ClickException, match="SystemVerilog RTL generation for apb"
    ):
        _write_output(
            model,
            "systemverilog",
            tmp_path / "regs.sv",
            "Registers",
            "apb",
            markdown_spec,
            None,
        )


def test_write_output_raises_on_c_header_generation_error(
    monkeypatch, tmp_path
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    def _raise_c_header_error(*_args, **_kwargs) -> None:
        raise CHeaderGenerationError("C header generation failed.")

    monkeypatch.setattr("csr_gen.cli.write_c_header_file", _raise_c_header_error)

    with pytest.raises(click.ClickException, match="C header generation failed."):
        _write_output(
            model,
            "c-header",
            tmp_path / "regs.h",
            "Registers",
            "axi4-lite",
            markdown_spec,
            None,
        )


def test_main_warnings_as_errors_fails_on_ipxact_warning(tmp_path, caplog) -> None:
    ipxact_source = TESTDATA / "ipxact_minimal.xml"
    xml = ipxact_source.read_text(encoding="utf-8").replace(
        "<ipxact:memoryMaps>",
        "<ipxact:busInterface/><ipxact:memoryMaps>",
        1,
    )
    warning_source = tmp_path / "warning.xml"
    warning_source.write_text(xml, encoding="utf-8")
    output = tmp_path / "out.md"

    try:
        with caplog.at_level(logging.ERROR, logger="csr_gen"):
            result = invoke_cli(
                main,
                [
                    "--warnings-as-errors",
                    "generate",
                    "--input-file",
                    str(warning_source),
                    "--input-format",
                    "ip-xact",
                    "--output-file",
                    str(output),
                    "--output-format",
                    "markdown",
                ],
            )

        assert result.exit_code != 0
        assert not output.exists()
    finally:
        csr_logging.configure(warnings_as_errors=False)


def test_validate_csv_input(tmp_path, caplog) -> None:
    source = tmp_path / "regs.csv"
    source.write_text(
        "Register,Address,Field,Bits,Access,Reset,Description\n"
        "CTRL,0x00,ENABLE,0,rw,0,Enable\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "validate",
                "--input-file",
                str(source),
                "--input-format",
                "csv",
            ],
        )

    assert result.exit_code == 0
    assert "Reading csv input file" in caplog.text
    assert "CSR name 'regs'" in caplog.text


def test_generate_csv_round_trip(tmp_path) -> None:
    source = tmp_path / "regs.csv"
    source.write_text(
        "Register,Address,Field,Bits,Access,Reset,Description\n"
        "CTRL,0x00,ENABLE,0,rw,0,Enable\n",
        encoding="utf-8",
    )
    output = tmp_path / "out.csv"

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "csv",
            "--csr-name",
            "Device CSR",
            "--output-file",
            str(output),
            "--output-format",
            "csv",
        ],
    )

    assert result.exit_code == 0
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("Register,Address,Field,Bits")
    assert "CTRL" in lines[1]


def test_generate_rejects_markdown_section_with_csv_input(tmp_path) -> None:
    source = tmp_path / "regs.csv"
    source.write_text(
        "Register,Address,Field,Bits\nCTRL,0x00,EN,0\n",
        encoding="utf-8",
    )

    result = invoke_cli(
        main,
        [
            "generate",
            "--input-file",
            str(source),
            "--input-format",
            "csv",
            "--markdown-section",
            "Registers",
            "--output-file",
            str(tmp_path / "out.csv"),
            "--output-format",
            "csv",
        ],
    )

    assert result.exit_code != 0
    assert "markdown-section is not used with CSV" in result.output


@pytest.fixture
def log_errors_without_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let CLI loaders return None instead of raising via logging.error."""

    def _log_only(message: str) -> None:
        logging.getLogger("csr_gen").error(message)

    monkeypatch.setattr("csr_gen.logging.error", _log_only)


def test_load_csv_returns_none_on_parse_error(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "regs.csv"
    source.write_text("Register,Field\nCTRL,enable\n", encoding="utf-8")

    assert _load_csv(source, csr_name=None) is None


def test_load_markdown_returns_none_on_parse_error(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n\nNo table.\n", encoding="utf-8")

    assert _load_markdown(source, "Registers") is None


def test_load_ipxact_returns_none_on_parse_error(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "bad.xml"
    source.write_text("<not-xml", encoding="utf-8")

    assert _load_ipxact(source) is None


def test_load_model_returns_none_when_loaders_fail(
    tmp_path, log_errors_without_exit
) -> None:
    markdown = tmp_path / "regs.md"
    markdown.write_text("# Registers\n\nNo table.\n", encoding="utf-8")
    csv_path = tmp_path / "regs.csv"
    csv_path.write_text("Register,Field\nCTRL,enable\n", encoding="utf-8")
    xml_path = tmp_path / "bad.xml"
    xml_path.write_text("<not-xml", encoding="utf-8")
    rdl_path = tmp_path / "regs.rdl"
    rdl_path.write_text("addrmap top {};\n", encoding="utf-8")

    assert _load_model(markdown, "markdown", "Registers") == (None, None, None)
    assert _load_model(csv_path, "csv", None) == (None, None, None)
    assert _load_model(xml_path, "ip-xact", None) == (None, None, None)
    assert _load_model(rdl_path, "systemrdl", None) == (None, None, None)


def test_load_model_returns_none_for_unimplemented_input_format(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n", encoding="utf-8")

    assert _load_model(source, "svd", None) == (None, None, None)


def test_write_output_returns_false_on_rtl_error(
    tmp_path, log_errors_without_exit
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    assert (
        _write_output(
            model,
            "systemverilog",
            tmp_path / "regs.sv",
            "Registers",
            "apb",
            markdown_spec,
            None,
        )
        is False
    )


def test_write_output_returns_false_on_c_header_error(
    monkeypatch, tmp_path, log_errors_without_exit
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    def _raise_c_header_error(*_args, **_kwargs) -> None:
        raise CHeaderGenerationError("C header generation failed.")

    monkeypatch.setattr("csr_gen.cli.write_c_header_file", _raise_c_header_error)

    assert (
        _write_output(
            model,
            "c-header",
            tmp_path / "regs.h",
            "Registers",
            "axi4-lite",
            markdown_spec,
            None,
        )
        is False
    )


def test_write_output_returns_false_on_dml_error(
    monkeypatch, tmp_path, log_errors_without_exit
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    def _raise_dml_error(*_args, **_kwargs) -> None:
        raise DmlGenerationError("DML generation failed.")

    monkeypatch.setattr("csr_gen.cli.write_dml_file", _raise_dml_error)

    assert (
        _write_output(
            model,
            "dml",
            tmp_path / "device.dml",
            "Registers",
            "axi4-lite",
            markdown_spec,
            None,
        )
        is False
    )


def test_write_output_returns_false_on_systemrdl_error(
    monkeypatch, tmp_path, log_errors_without_exit
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    def _raise_systemrdl_error(*_args, **_kwargs) -> None:
        raise SystemRdlGenerationError("SystemRDL generation failed.")

    monkeypatch.setattr("csr_gen.cli.write_systemrdl_file", _raise_systemrdl_error)

    assert (
        _write_output(
            model,
            "systemrdl",
            tmp_path / "regs.rdl",
            "Registers",
            "axi4-lite",
            markdown_spec,
            None,
        )
        is False
    )


def test_write_output_raises_on_dml_generation_error(monkeypatch, tmp_path) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )
    markdown_spec = load_markdown(VALID_MARKDOWN, "Registers")

    def _raise_dml_error(*_args, **_kwargs) -> None:
        raise DmlGenerationError("DML generation failed.")

    monkeypatch.setattr("csr_gen.cli.write_dml_file", _raise_dml_error)

    with pytest.raises(click.ClickException, match="DML generation failed."):
        _write_output(
            model,
            "dml",
            tmp_path / "device.dml",
            "Registers",
            "axi4-lite",
            markdown_spec,
            None,
        )


def test_write_output_returns_false_on_unimplemented_format(
    tmp_path, log_errors_without_exit
) -> None:
    model = RegisterModel(
        registers=[
            Register(name="CTRL", address=0, fields=[Field("EN", 0, 0, "rw", 0)])
        ]
    )

    assert (
        _write_output(
            model,
            "not-a-format",
            tmp_path / "out.rdl",
            "Registers",
            "axi4-lite",
            None,
            None,
        )
        is False
    )


def test_write_outputs_stops_after_first_failure(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    markdown_spec = load_markdown_file(source, "Registers")
    model = markdown_spec.model
    markdown_out = tmp_path / "normalized.md"
    sv_out = tmp_path / "out.sv"

    _write_outputs(
        model,
        [("markdown", markdown_out), ("systemverilog", sv_out)],
        "Registers",
        "avalon-mm",
        markdown_spec,
        None,
    )

    assert markdown_out.is_file()
    assert not sv_out.exists()


def test_validate_input_options_rejects_csr_name_with_markdown() -> None:
    with pytest.raises(click.UsageError, match="--csr-name is only valid"):
        _validate_input_options("markdown", "Registers", "My CSR", None, None)


def test_validate_input_options_rejects_systemrdl_addrmap_for_markdown() -> None:
    with pytest.raises(click.UsageError, match="systemrdl-addrmap"):
        _validate_input_options("markdown", "Registers", None, None, "uart_inst")


def test_run_generate_returns_when_model_load_fails(
    tmp_path, log_errors_without_exit
) -> None:
    source = tmp_path / "regs.md"
    source.write_text("# Registers\n\nNo table.\n", encoding="utf-8")
    output = tmp_path / "out.md"

    _run_generate(
        source,
        "markdown",
        "Registers",
        [("markdown", output)],
        "axi4-lite",
    )

    assert not output.exists()


def test_validate_returns_when_markdown_spec_missing(
    monkeypatch, tmp_path, log_errors_without_exit, caplog
) -> None:
    source = tmp_path / "regs.md"
    source.write_text(VALID_MARKDOWN, encoding="utf-8")
    model = load_markdown(VALID_MARKDOWN, "Registers").model

    monkeypatch.setattr(
        "csr_gen.cli._load_model",
        lambda *_args, **_kwargs: (model, None, None),
    )

    with caplog.at_level(logging.INFO, logger="csr_gen"):
        result = invoke_cli(
            main,
            [
                "validate",
                "--input-file",
                str(source),
                "--markdown-section",
                "Registers",
            ],
        )

    assert result.exit_code == 0
    assert "is valid" not in caplog.text
