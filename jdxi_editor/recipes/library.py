"""Saved recipes: one JSON file each, in the user's folder (~/.jdxi_editor/recipes)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from jdxi_editor.recipes.model import Recipe


def folder() -> Path:
    custom = os.environ.get("JDXI_RECIPES_DIR")
    if custom:
        path = Path(custom)
    else:
        from jdxi_editor.project import __data_name__, __package_name__

        path = Path.home() / f".{__data_name__}" / "recipes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def slug(title: str) -> str:
    text = re.sub(r"[^\w\- ]+", "", title.strip(), flags=re.UNICODE).strip().replace(" ", "_")
    return text[:60] or "ricetta"


def saved() -> list[tuple[str, Path]]:
    """(title, path) of every saved recipe, by title."""
    out = []
    for path in folder().glob("*.json"):
        try:
            out.append((Recipe.from_json(path.read_text(encoding="utf-8")).title or path.stem, path))
        except (OSError, ValueError, TypeError):
            continue
    return sorted(out, key=lambda item: item[0].lower())


def save(recipe: Recipe, path: Path | None = None) -> Path:
    if path is None:
        base = folder() / slug(recipe.title)
        path = base.with_suffix(".json")
        n = 2
        while path.exists():
            path = Path(f"{base}_{n}.json")
            n += 1
    path.write_text(recipe.to_json(), encoding="utf-8")
    return path


def load(path: Path) -> Recipe:
    return Recipe.from_json(Path(path).read_text(encoding="utf-8"))


def delete(path: Path) -> None:
    Path(path).unlink(missing_ok=True)
