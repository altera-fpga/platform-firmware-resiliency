from pathlib import Path

import yaml

from csr_gen.input.markdown_reader import load_markdown_file

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "docs" / "skills" / "csr-markdown"
SKILL_MD = SKILL_DIR / "SKILL.md"
ASSETS = SKILL_DIR / "assets"


def _load_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _prefix, rest = text.split("---\n", 1)
    assert _prefix == ""
    frontmatter_text, body = rest.split("\n---\n", 1)
    data = yaml.safe_load(frontmatter_text)
    assert isinstance(data, dict)
    return data, body


def test_skill_directory_name_matches_frontmatter() -> None:
    assert SKILL_DIR.is_dir()
    assert SKILL_DIR.name == "csr-markdown"
    data, body = _load_frontmatter(SKILL_MD)
    assert data["name"] == SKILL_DIR.name
    assert data["license"] == "MIT-0"
    description = data["description"]
    assert isinstance(description, str)
    assert 1 <= len(description) <= 1024
    assert "csr-gen" in description.lower()
    metadata = data["metadata"]
    assert isinstance(metadata, dict)
    for key, value in metadata.items():
        assert isinstance(key, str)
        assert isinstance(value, str)
    assert len(SKILL_MD.read_text(encoding="utf-8").splitlines()) < 500
    assert "TABLE_RULES.md" in body
    assert "csr-gen validate" in body


def test_skill_assets_parse_as_csr_gen_markdown() -> None:
    template = load_markdown_file(ASSETS / "template.md", "CSR Registers")
    assert [register.name for register in template.model.registers] == [
        "CTRL",
        "STATUS",
    ]
    example = load_markdown_file(ASSETS / "example-device.md", "CSR Registers")
    assert [register.name for register in example.model.registers] == ["CTRL", "EVENTS"]
    assert example.model.registers[0].fields[0].name == "ENABLE"
