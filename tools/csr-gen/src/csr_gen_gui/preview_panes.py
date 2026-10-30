"""Preview pane metadata shared by the GUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewPaneSpec:
    """One read-only artifact preview tab."""

    pane_id: str
    menu_label: str
    tab_label: str
    uses_interface_type: bool = False


PREVIEW_PANE_SPECS: tuple[PreviewPaneSpec, ...] = (
    PreviewPaneSpec(
        "systemverilog",
        "&SystemVerilog",
        "SystemVerilog",
        uses_interface_type=True,
    ),
    PreviewPaneSpec("c_header", "&C Header", "C header"),
    PreviewPaneSpec("dml", "&DML", "DML"),
    PreviewPaneSpec("systemrdl", "&SystemRDL", "SystemRDL"),
    PreviewPaneSpec("ipxact", "IP-XACT", "IP-XACT"),
)


def default_preview_pane_visibility() -> dict[str, bool]:
    """Return the default visibility map (all preview panes shown)."""
    return {spec.pane_id: True for spec in PREVIEW_PANE_SPECS}
