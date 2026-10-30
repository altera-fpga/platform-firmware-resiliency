import csv
from pathlib import Path

import pytest

from csr_gen.errors import CsrValidationError
from csr_gen.input.csv_reader import CsvParseError, load_csv, load_csv_file

from test_paths import TESTDATA

PQC_IP_CSV = TESTDATA / "pqc_ip.csv"
GOLDEN_CSV_REGS = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "golden"
    / "csv"
    / "example-device"
    / "regs.csv"
)


def test_load_csv_file_uses_filename_stem_by_default() -> None:
    spec = load_csv_file(GOLDEN_CSV_REGS)

    assert spec.section_heading == "regs"
    assert spec.model.registers[0].name == "CTRL"


def test_load_csv_file_accepts_csr_name_override() -> None:
    spec = load_csv_file(GOLDEN_CSV_REGS, csr_name="My CSR")

    assert spec.section_heading == "My CSR"


def test_load_csv_multiline_quoted_description() -> None:
    spec = load_csv(
        """\
Register,Address,Field,Bits,Access,Reset,Description
CTRL,0x00,enable,0,rw,0,"Line one
Line two"
""",
        location="test",
        csr_name="Test",
    )

    assert spec.model.registers[0].fields[0].description == "Line one\nLine two"


def test_load_csv_rejects_empty_reset_when_column_present() -> None:
    with pytest.raises(
        CsrValidationError, match="CSR table row 2: Reset must not be empty"
    ):
        load_csv(
            "Register,Address,Field,Bits,Reset\n" "CTRL,0x00,enable,0,\n",
            location="test",
            csr_name="Test",
        )


def test_load_pqc_ip_csv() -> None:
    """Real-world PQC IP table: multiline cells, continuations, and address range."""
    spec = load_csv_file(PQC_IP_CSV)

    assert spec.section_heading == "pqc_ip"
    model = spec.model
    assert len(model.registers) == 11

    reset = model.registers[0]
    assert reset.name == "HCI_RESET"
    assert reset.address == 0x000
    assert reset.hw_access == "internal"
    assert len(reset.fields) == 1
    assert reset.fields[0].name == "RESET"
    assert reset.fields[0].msb == 0
    assert reset.fields[0].lsb == 0
    assert reset.fields[0].access == "rw"

    status = model.registers[1]
    assert status.name == "HCI_STATUS"
    assert status.fields[0].name == "ACCEL_STATUS"
    assert status.fields[0].msb == 3
    assert status.fields[0].lsb == 0
    assert "0x0: Not Alive" in status.fields[0].description
    assert status.fields[0].description.count("\n") == 7

    irq_status = model.registers[2]
    assert irq_status.name == "HCI_INTERRUPT_STATUS"
    assert len(irq_status.fields) == 3
    assert irq_status.fields[0].name == "TRANSITION_TO_SUCCESS"
    assert irq_status.fields[0].access == "rw1c"

    ip_id = next(r for r in model.registers if r.name == "HCI_ACCELERATOR_IP_ID")
    assert ip_id.address == 0x020
    assert ip_id.fields[0].msb == 31
    assert ip_id.fields[0].lsb == 0
    assert "Xiphera IP" in ip_id.fields[0].description

    param_mem = model.registers[-1]
    assert param_mem.name == "HCI_PARAM_MEM_DATA"
    assert param_mem.address == 0x400
    assert param_mem.address_end == 0x7FF
    assert param_mem.hw_access == "external"
    assert param_mem.fields[0].name == "HCI_PARAM_MEM_DATA"
    assert "Parameter Data register" in param_mem.fields[0].description


def test_load_csv_defaults_reset_when_column_omitted() -> None:
    spec = load_csv(
        "Register,Address,Field,Bits\nCTRL,0x00,enable,0\n",
        location="test",
        csr_name="Test",
    )

    assert spec.model.registers[0].fields[0].reset == 0


def test_load_csv_rejects_hw_access_on_field_row() -> None:
    with pytest.raises(CsrValidationError, match="register definition row"):
        load_csv(
            "Register,Address,Field,Bits,Access,Reset,Description,HW Access\n"
            "CTRL,0x00,,,,,,internal\n"
            ",,enable,0,rw,0,Enable,external\n",
            location="test",
            csr_name="Test",
        )


def test_load_csv_rejects_missing_required_column() -> None:
    with pytest.raises(CsvParseError, match="missing required column"):
        load_csv(
            "Register,Field\nCTRL,enable\n",
            location="test",
            csr_name="Test",
        )


def test_load_csv_rejects_surplus_cells() -> None:
    with pytest.raises(CsvParseError, match="row 2 has 8 cells"):
        load_csv(
            "Register,Address,Field,Bits,Access,Reset,Description\n"
            "CTRL,0x00,enable,0,rw,0,Enable, debug mode\n",
            location="test",
            csr_name="Test",
        )


def test_load_csv_rejects_unterminated_quote() -> None:
    with pytest.raises(CsvParseError, match="malformed CSV"):
        load_csv(
            "Register,Address,Field,Bits,Description\n"
            'CTRL,0x00,enable,0,"unclosed\n'
            "STATUS,0x04,ready,0,Ready\n",
            location="test",
            csr_name="Test",
        )


def test_load_csv_rejects_empty_file() -> None:
    with pytest.raises(CsvParseError, match="is empty"):
        load_csv("", location="empty.csv", csr_name="Test")


def test_load_csv_rejects_malformed_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_csv_error(_stream: object, **_kwargs: object) -> list[list[str]]:
        raise csv.Error("bad row")

    monkeypatch.setattr(csv, "reader", _raise_csv_error)
    with pytest.raises(CsvParseError, match="malformed CSV"):
        load_csv("Register,Field\nCTRL,enable\n", location="bad.csv", csr_name="Test")


def test_load_csv_file_rejects_unreadable_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(CsvParseError, match="Cannot read CSV file"):
        load_csv_file(missing)


def test_load_csv_file_uses_csr_name_when_override_is_whitespace() -> None:
    spec = load_csv_file(GOLDEN_CSV_REGS, csr_name="   ")

    assert spec.section_heading == "regs"


def test_load_csv_skips_blank_body_rows() -> None:
    spec = load_csv(
        "Register,Address,Field,Bits\n" "CTRL,0x00,enable,0\n" ",,,\n" "\n",
        location="test",
        csr_name="Test",
    )

    assert len(spec.model.registers[0].fields) == 1
