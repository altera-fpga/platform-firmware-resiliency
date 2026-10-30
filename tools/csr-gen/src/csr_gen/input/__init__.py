"""Input parsers that load CSR definitions into the shared register model."""

from csr_gen.input.markdown_reader import (
    MarkdownRegisterSpec,
    load_markdown,
    load_markdown_file,
)
from csr_gen.input.yaml_reader import load_yaml, load_yaml_file

__all__ = [
    "MarkdownRegisterSpec",
    "load_markdown",
    "load_markdown_file",
    "load_yaml",
    "load_yaml_file",
]
