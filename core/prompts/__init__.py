"""
Prompt template management for Outur AI agents.

This module provides a simple, file-backed prompt template loader.
Templates are stored as plain ``.txt`` or ``.md`` files under ``core/prompts/templates/``.
Variables are injected using Python's ``str.format_map()`` for zero-dependency rendering.

Usage
-----
::

    from core.prompts import load_prompt

    prompt = load_prompt("scout/company_search", company_name="Acme Corp", industry="SaaS")
"""

from __future__ import annotations

from pathlib import Path

# Root directory for all prompt template files
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_prompt(template_name: str, **variables: str) -> str:
    """
    Load a prompt template by name and render it with the given variables.

    Parameters
    ----------
    template_name:
        Relative path (without extension) under ``core/prompts/templates/``.
        Use forward slashes for subdirectories, e.g. ``"scout/company_search"``.
    **variables:
        Key-value pairs to substitute into the template using ``{key}`` placeholders.

    Returns
    -------
    str
        The rendered prompt string.

    Raises
    ------
    FileNotFoundError
        If no ``.txt`` or ``.md`` file exists for ``template_name``.
    KeyError
        If a required variable placeholder is missing from ``variables``.
    """
    for ext in (".txt", ".md"):
        path = _TEMPLATES_DIR / f"{template_name}{ext}"
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            return raw.format_map(variables)

    raise FileNotFoundError(
        f"Prompt template '{template_name}' not found in {_TEMPLATES_DIR}. "
        f"Expected a .txt or .md file at that path."
    )


def list_templates() -> list[str]:
    """
    Return a sorted list of all available template names (without extensions).

    Useful for debugging and introspection.
    """
    if not _TEMPLATES_DIR.exists():
        return []
    return sorted(
        str(p.relative_to(_TEMPLATES_DIR).with_suffix("")).replace("\\", "/")
        for p in _TEMPLATES_DIR.rglob("*")
        if p.is_file() and p.suffix in {".txt", ".md"}
    )
