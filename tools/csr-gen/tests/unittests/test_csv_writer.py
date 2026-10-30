from pathlib import Path

from csr_gen.input.csv_reader import load_csv, load_csv_file
from csr_gen.input.markdown_reader import load_markdown_file
from csr_gen.output.csv_writer import write_csv

from test_paths import TESTDATA

GOLDEN_CSV_REGS = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "golden"
    / "csv"
    / "example-device"
    / "regs.csv"
)


def test_csv_round_trip_matches_golden_regs_model() -> None:
    source = load_csv_file(GOLDEN_CSV_REGS, csr_name="CSR Registers")
    csv_text = write_csv(source.model)
    restored = load_csv(csv_text, location="round-trip", csr_name="CSR Registers")

    assert restored.model.registers[0].name == source.model.registers[0].name
    assert len(restored.model.registers) == len(source.model.registers)
    assert restored.model.registers[0].fields[1].access == "rw"
    assert restored.model.registers[0].fields[1].reset == 1


def test_write_csv_formats_address_ranges() -> None:
    external_case = (
        Path(__file__).resolve().parents[2] / "specs" / "golden" / "external-device"
    )
    section = (external_case / "section.txt").read_text(encoding="utf-8").strip()
    model = load_markdown_file(external_case / "regs.md", section).model
    text = write_csv(model)

    assert "0x20-0x2f" in text
    assert "MEM" in text


def test_write_csv_includes_canonical_columns() -> None:
    spec = load_csv_file(TESTDATA / "example_device.csv")
    text = write_csv(spec.model)

    header = text.splitlines()[0]
    assert header == ("Register,Address,Field,Bits,Access,Reset,HW Access,Description")
