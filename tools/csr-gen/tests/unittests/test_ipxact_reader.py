from pathlib import Path

import pytest

from csr_gen.errors import CsrValidationError, IpxactParseError
from csr_gen.input.ipxact_reader import (
    list_ipxact_address_block_names,
    list_ipxact_address_block_names_file,
    load_ipxact,
    load_ipxact_file,
)

from test_paths import TESTDATA

MINIMAL_XML = TESTDATA / "ipxact_minimal.xml"
MULTI_BLOCK_XML = TESTDATA / "ipxact_multi_block.xml"

COMPONENT_PREFIX = """<?xml version="1.0" encoding="utf-8"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014">
  <ipxact:memoryMaps>
    <ipxact:memoryMap>
      <ipxact:name>Test Map</ipxact:name>
"""

COMPONENT_SUFFIX = """    </ipxact:memoryMap>
  </ipxact:memoryMaps>
</ipxact:component>
"""


def test_load_minimal_ipxact_registers() -> None:
    spec = load_ipxact_file(MINIMAL_XML)

    assert spec.section_heading == "Example CSR Map"
    assert spec.memory_map_name == "Example CSR Map"
    assert len(spec.model.registers) == 3

    device_ctrl = spec.model.registers[0]
    assert device_ctrl.name == "DEVICE_CTRL"
    assert device_ctrl.address == 0
    assert device_ctrl.fields[0].access == "rw"

    device_addr = spec.model.registers[1]
    assert device_addr.name == "DEVICE_ADDR"
    assert device_addr.address == 4
    assert device_addr.fields[0].msb == 6
    assert device_addr.fields[0].lsb == 0

    event_status = spec.model.registers[2]
    assert event_status.name == "SLV_EVENT_STATUS"
    assert event_status.address == 0x38
    assert event_status.fields[0].name == "MRL_UPDATED"
    assert event_status.fields[0].access == "rw1c"


def test_rejects_multiple_memory_maps() -> None:
    extra_map = (
        "</ipxact:memoryMap><ipxact:memoryMap>"
        "<ipxact:name>other</ipxact:name></ipxact:memoryMap>"
    )
    xml = MINIMAL_XML.read_text(encoding="utf-8").replace(
        "</ipxact:memoryMap>", extra_map, 1
    )
    with pytest.raises(IpxactParseError, match="exactly one"):
        load_ipxact(xml)


def test_rejects_overlapping_fields(tmp_path) -> None:
    xml = MINIMAL_XML.read_text(encoding="utf-8")
    duplicate_field = """          <ipxact:field>
            <ipxact:name>DUPLICATE</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>2</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
          </ipxact:field>
"""
    needle = (
        "          </ipxact:field>\n        </ipxact:register>\n"
        "        <ipxact:register>\n          <ipxact:name>DEVICE_ADDR"
    )
    replacement = (
        f"          </ipxact:field>\n{duplicate_field}"
        "        </ipxact:register>\n"
        "        <ipxact:register>\n          <ipxact:name>DEVICE_ADDR"
    )
    xml = xml.replace(needle, replacement, 1)
    path = tmp_path / "overlap.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(CsrValidationError):
        load_ipxact_file(path)


def test_rejects_malformed_xml() -> None:
    with pytest.raises(IpxactParseError, match="well-formed"):
        load_ipxact("<not-xml")


def test_rejects_wrong_root_element() -> None:
    ns = "http://www.accellera.org/XMLSchema/IPXACT/1685-2014"
    with pytest.raises(IpxactParseError, match="component"):
        load_ipxact(f"<ipxact:memoryMaps xmlns:ipxact='{ns}'/>")


def test_rejects_missing_memory_maps() -> None:
    xml = """<?xml version="1.0"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014"/>
"""
    with pytest.raises(IpxactParseError, match="memoryMaps"):
        load_ipxact(xml)


def test_rejects_empty_memory_map_list() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014">
  <ipxact:memoryMaps>
  </ipxact:memoryMaps>
</ipxact:component>
"""
    with pytest.raises(IpxactParseError, match="no <memoryMap>"):
        load_ipxact(xml)


def test_rejects_memory_map_without_name() -> None:
    xml = (
        COMPONENT_PREFIX.replace("<ipxact:name>Test Map</ipxact:name>", "")
        + COMPONENT_SUFFIX
    )
    with pytest.raises(IpxactParseError, match="missing <name>"):
        load_ipxact(xml)


def test_rejects_register_without_name(tmp_path) -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="missing <name>"):
        load_ipxact(xml)


def test_rejects_unsupported_access() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>banana</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="unsupported access"):
        load_ipxact(xml)


def test_parse_int_literal_forms() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'d16</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:resets>
              <ipxact:reset>
                <ipxact:value>'b1</ipxact:value>
              </ipxact:reset>
            </ipxact:resets>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    assert spec.model.registers[0].address == 16
    assert spec.model.registers[0].fields[0].reset == 1


def test_rejects_invalid_integer_literal() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>not-a-number</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="integer"):
        load_ipxact(xml)


def test_skips_register_without_fields(tmp_path, caplog) -> None:
    import logging

    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>EMPTY</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
        </ipxact:register>
        <ipxact:register>
          <ipxact:name>GOOD</ipxact:name>
          <ipxact:addressOffset>'h4</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with caplog.at_level(logging.WARNING, logger="csr_gen"):
        spec = load_ipxact(xml)
    assert len(spec.model.registers) == 1
    assert spec.model.registers[0].name == "GOOD"
    assert "EMPTY" in caplog.text


def test_rejects_register_directly_under_memory_map() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:register>
        <ipxact:name>TOP</ipxact:name>
        <ipxact:addressOffset>0x8</ipxact:addressOffset>
        <ipxact:field>
          <ipxact:name>F</ipxact:name>
          <ipxact:bitOffset>0</ipxact:bitOffset>
          <ipxact:bitWidth>1</ipxact:bitWidth>
          <ipxact:access>write-only</ipxact:access>
        </ipxact:field>
      </ipxact:register>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="directly under"):
        load_ipxact(xml)


def test_rejects_multiple_address_blocks_without_selector() -> None:
    with pytest.raises(IpxactParseError, match="ipxact-address-block"):
        load_ipxact_file(MULTI_BLOCK_XML)


def test_loads_named_address_block_with_block_local_offsets() -> None:
    spec = load_ipxact_file(MULTI_BLOCK_XML, address_block_name="alpha_block")

    assert spec.section_heading == "Multi Block Map"
    assert len(spec.model.registers) == 1
    assert spec.model.registers[0].name == "ALPHA_CTRL"
    assert spec.model.registers[0].address == 0

    beta = load_ipxact_file(MULTI_BLOCK_XML, address_block_name="beta_block")
    assert len(beta.model.registers) == 1
    assert beta.model.registers[0].name == "BETA_STAT"
    assert beta.model.registers[0].address == 4


def test_rejects_unknown_address_block_name() -> None:
    with pytest.raises(IpxactParseError, match="no <addressBlock> named"):
        load_ipxact_file(MULTI_BLOCK_XML, address_block_name="missing")


def test_loads_spirit_2009_namespace_component() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<spirit:component xmlns:spirit="http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009">
  <spirit:memoryMaps>
    <spirit:memoryMap>
      <spirit:name>Spirit Map</spirit:name>
      <spirit:addressBlock>
        <spirit:name>spirit_block</spirit:name>
        <spirit:register>
          <spirit:name>R</spirit:name>
          <spirit:addressOffset>0</spirit:addressOffset>
          <spirit:field>
            <spirit:name>F</spirit:name>
            <spirit:bitOffset>0</spirit:bitOffset>
            <spirit:bitWidth>1</spirit:bitWidth>
            <spirit:access>read-only</spirit:access>
          </spirit:field>
        </spirit:register>
      </spirit:addressBlock>
    </spirit:memoryMap>
  </spirit:memoryMaps>
</spirit:component>
"""
    spec = load_ipxact(xml)
    assert spec.memory_map_name == "Spirit Map"
    assert spec.model.registers[0].name == "R"


def test_modified_write_maps_rw1s_and_rw0c() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>S</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
            <ipxact:modifiedWriteValue>oneToSet</ipxact:modifiedWriteValue>
          </ipxact:field>
          <ipxact:field>
            <ipxact:name>C</ipxact:name>
            <ipxact:bitOffset>1</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
            <ipxact:modifiedWriteValue>zeroToClear</ipxact:modifiedWriteValue>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    fields = {field.name: field for field in spec.model.registers[0].fields}
    assert fields["S"].access == "rw1s"
    assert fields["C"].access == "rw0c"


def test_warns_on_unknown_modified_write_and_read_action(
    caplog,
) -> None:
    import logging

    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:access>read-write</ipxact:access>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
            <ipxact:modifiedWriteValue>weird</ipxact:modifiedWriteValue>
            <ipxact:readAction>user</ipxact:readAction>
          </ipxact:field>
          <ipxact:field>
            <ipxact:name>G</ipxact:name>
            <ipxact:bitOffset>1</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:modifiedWriteValue>oneToClear</ipxact:modifiedWriteValue>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with caplog.at_level(logging.WARNING, logger="csr_gen"):
        load_ipxact(xml)
    assert "modifiedWriteValue" in caplog.text
    assert "readAction" in caplog.text


def test_warns_once_per_unknown_element_type(caplog) -> None:
    import logging

    xml = MINIMAL_XML.read_text(encoding="utf-8")
    xml = xml.replace(
        "<ipxact:memoryMaps>",
        "<ipxact:busInterface/><ipxact:busInterface/><ipxact:memoryMaps>",
        1,
    )
    with caplog.at_level(logging.WARNING, logger="csr_gen"):
        load_ipxact(xml)
    bus_warnings = [
        record.message
        for record in caplog.records
        if "unsupported element <busInterface>" in record.message
    ]
    assert len(bus_warnings) == 1


def test_rejects_duplicate_name_child() -> None:
    xml = (
        COMPONENT_PREFIX.replace(
            "<ipxact:name>Test Map</ipxact:name>",
            "<ipxact:name>Test Map</ipxact:name><ipxact:name>dup</ipxact:name>",
        )
        + COMPONENT_SUFFIX
    )
    with pytest.raises(IpxactParseError, match="multiple"):
        load_ipxact(xml)


def test_rejects_memory_map_without_address_blocks() -> None:
    xml = COMPONENT_PREFIX + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="no <addressBlock>"):
        load_ipxact(xml)


def test_rejects_register_without_address_offset() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="addressOffset"):
        load_ipxact(xml)


def test_rejects_field_without_name() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0x0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="field without <name>"):
        load_ipxact(xml)


def test_rejects_field_without_bit_layout() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0x0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="bitOffset"):
        load_ipxact(xml)


def test_rejects_non_positive_bit_width() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0x0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>0</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="bitWidth must be positive"):
        load_ipxact(xml)


def test_rejects_field_without_access() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0x0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="no <access>"):
        load_ipxact(xml)


def test_memory_map_description_becomes_section_heading_for_csr_gen_export() -> None:
    xml = (
        """<?xml version="1.0" encoding="utf-8"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014">
  <ipxact:vendor>csr-gen</ipxact:vendor>
  <ipxact:memoryMaps>
    <ipxact:memoryMap>
      <ipxact:name>test_map</ipxact:name>
      <ipxact:description>Test Map</ipxact:description>
"""
        + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
"""
        + COMPONENT_SUFFIX
    )
    spec = load_ipxact(xml)
    assert spec.section_heading == "Test Map"
    assert spec.memory_map_name == "test_map"


def test_memory_map_description_ignored_for_third_party_import() -> None:
    xml = (
        COMPONENT_PREFIX.replace(
            "<ipxact:name>Test Map</ipxact:name>",
            "<ipxact:name>vendor_map</ipxact:name>"
            "<ipxact:description>Vendor Memory Map Title</ipxact:description>",
        )
        + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
"""
        + COMPONENT_SUFFIX
    )
    spec = load_ipxact(xml)
    assert spec.section_heading == "vendor_map"
    assert spec.memory_map_name == "vendor_map"


def test_reset_defaults_when_resets_element_has_no_value() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:resets>
              <ipxact:reset/>
            </ipxact:resets>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    assert spec.model.registers[0].fields[0].reset == 0


def test_parse_verilog_hex_literals() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>'h10</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:resets>
              <ipxact:reset>
                <ipxact:value>'h1</ipxact:value>
              </ipxact:reset>
            </ipxact:resets>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    assert spec.model.registers[0].address == 0x10
    assert spec.model.registers[0].fields[0].reset == 1


def test_warns_on_unknown_field_child(caplog) -> None:
    import logging

    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>F</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:testable>unconstrained</ipxact:testable>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    with caplog.at_level(logging.WARNING, logger="csr_gen"):
        load_ipxact(xml)
    assert "unsupported element <testable>" in caplog.text


def test_import_register_hw_access_and_address_range() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>MEM</ipxact:name>
          <ipxact:addressOffset>'h20</ipxact:addressOffset>
          <ipxact:dim>4</ipxact:dim>
          <ipxact:dimIncrement>4</ipxact:dimIncrement>
          <ipxact:vendorExtensions>
            <csrgen:hwAccess xmlns:csrgen="http://csr-gen.dev/ipxact/1.0">external</csrgen:hwAccess>
          </ipxact:vendorExtensions>
          <ipxact:field>
            <ipxact:name>WINDOW</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>32</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    register = spec.model.registers[0]
    assert register.name == "MEM"
    assert register.address == 0x20
    assert register.address_end == 0x2F
    assert register.hw_access == "external"


def test_import_field_vendor_access_none_and_r0w1c() -> None:
    xml = COMPONENT_PREFIX + """      <ipxact:addressBlock>
        <ipxact:register>
          <ipxact:name>R</ipxact:name>
          <ipxact:addressOffset>0</ipxact:addressOffset>
          <ipxact:field>
            <ipxact:name>RSVD</ipxact:name>
            <ipxact:bitOffset>1</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-only</ipxact:access>
            <ipxact:vendorExtensions>
              <csrgen:access xmlns:csrgen="http://csr-gen.dev/ipxact/1.0">none</csrgen:access>
            </ipxact:vendorExtensions>
          </ipxact:field>
          <ipxact:field>
            <ipxact:name>FLAG</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>1</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
            <ipxact:vendorExtensions>
              <csrgen:access xmlns:csrgen="http://csr-gen.dev/ipxact/1.0">r0w1c</csrgen:access>
            </ipxact:vendorExtensions>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
""" + COMPONENT_SUFFIX
    spec = load_ipxact(xml)
    fields = {field.name: field for field in spec.model.registers[0].fields}
    assert fields["RSVD"].access == "none"
    assert fields["FLAG"].access == "r0w1c"


def test_list_ipxact_address_block_names_returns_block_names() -> None:
    assert list_ipxact_address_block_names_file(MULTI_BLOCK_XML) == [
        "alpha_block",
        "beta_block",
    ]


def test_list_ipxact_address_block_names_uses_unnamed_placeholder() -> None:
    assert list_ipxact_address_block_names(
        MINIMAL_XML.read_text(encoding="utf-8"),
        MINIMAL_XML.name,
    ) == ["<unnamed>"]


def test_list_ipxact_address_block_names_rejects_malformed_xml() -> None:
    with pytest.raises(IpxactParseError, match="not well-formed XML"):
        list_ipxact_address_block_names("<component>", "broken.xml")


def test_list_ipxact_address_block_names_rejects_wrong_root() -> None:
    with pytest.raises(IpxactParseError, match="root element <component>"):
        list_ipxact_address_block_names("<memoryMap/>", "wrong-root.xml")


def test_list_ipxact_address_block_names_rejects_missing_memory_maps() -> None:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014">
</ipxact:component>
"""
    with pytest.raises(IpxactParseError, match="no <memoryMaps>"):
        list_ipxact_address_block_names(xml, "no-maps.xml")


def test_list_ipxact_address_block_names_rejects_multiple_memory_maps() -> None:
    extra_map = (
        "</ipxact:memoryMap><ipxact:memoryMap>"
        "<ipxact:name>other</ipxact:name></ipxact:memoryMap>"
    )
    xml = MINIMAL_XML.read_text(encoding="utf-8").replace(
        "</ipxact:memoryMap>", extra_map, 1
    )
    with pytest.raises(IpxactParseError, match="exactly one <memoryMap>"):
        list_ipxact_address_block_names(xml, "multi-map.xml")


def test_list_ipxact_address_block_names_rejects_missing_address_blocks() -> None:
    xml = COMPONENT_PREFIX + COMPONENT_SUFFIX
    with pytest.raises(IpxactParseError, match="no <addressBlock>"):
        list_ipxact_address_block_names(xml, "no-blocks.xml")
