from csr_gen.input.markdown_reader import load_markdown
from csr_gen.input.yaml_reader import load_yaml
from csr_gen.output.yaml_writer import dump_model_yaml

_HEADER = """\
| Register | Address | Field | Bits | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
"""


def test_dump_model_yaml_round_trips_through_yaml_reader() -> None:
    markdown = f"""\
# Registers

{_HEADER}| CTRL | 0x00 | ENABLE | 0 | rw | 0 | Enable |
"""
    model = load_markdown(markdown, "Registers").model
    yaml_text = dump_model_yaml(model)
    restored = load_yaml(yaml_text)

    assert restored.registers[0].name == "CTRL"
    assert restored.registers[0].hw_access == "internal"
    assert restored.registers[0].address_end is None
    assert restored.registers[0].fields[0].name == "ENABLE"


def test_dump_model_yaml_preserves_hw_access_and_address_end() -> None:
    markdown = """\
# Registers

| Register | Address | Field | Bits | Access | Reset | Description | HW Access |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FIFO | 0x10 | data | 7:0 | rw | 0x0 | FIFO payload | external |
|  |  | level | 15:8 | ro | 0x0 | FIFO fill level | |
| MEM | 0x20-0x2F | window | 31:0 | rw | 0x0 | External memory window | external |
"""
    model = load_markdown(markdown, "Registers").model
    restored = load_yaml(dump_model_yaml(model))

    fifo = restored.registers[0]
    assert fifo.name == "FIFO"
    assert fifo.hw_access == "external"
    assert fifo.address_end is None
    memory = restored.registers[1]
    assert memory.name == "MEM"
    assert memory.hw_access == "external"
    assert memory.address == 0x20
    assert memory.address_end == 0x2F
