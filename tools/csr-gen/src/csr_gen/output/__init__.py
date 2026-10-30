"""Output serializers that render the shared register model to target formats."""

from csr_gen.output.c_header_writer import write_c_header, write_c_header_file
from csr_gen.output.markdown_writer import write_markdown, write_markdown_file
from csr_gen.output.systemverilog_writer import (
    write_systemverilog,
    write_systemverilog_file,
)
from csr_gen.output.yaml_writer import dump_model_yaml

__all__ = [
    "dump_model_yaml",
    "write_c_header",
    "write_c_header_file",
    "write_markdown",
    "write_markdown_file",
    "write_systemverilog",
    "write_systemverilog_file",
]
