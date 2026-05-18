"""Fill HTML scene templates ({KEY} or {{KEY}} placeholders)."""

from __future__ import annotations


def fill_template(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", value).replace(f"{{{key}}}", value)
    return out
