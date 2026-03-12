from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


FRONTMATTER_DELIMITER = "---"
DESCRIPTION_KEY = "description"
COMMAND_FALLBACK_CHARS = 30


@dataclass(frozen=True)
class MarkdownDescription:
    description: str
    source: str


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _extract_frontmatter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_DELIMITER:
            frontmatter = "\n".join(lines[1:index])
            rest = "\n".join(lines[index + 1 :])
            return frontmatter, rest
    return None, text


def _parse_description_from_frontmatter(frontmatter: str) -> str | None:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith(f"{DESCRIPTION_KEY}:"):
            continue
        raw_value = stripped[len(f"{DESCRIPTION_KEY}:") :].strip()
        if raw_value in {"|", ">"}:
            return _parse_block_scalar(lines[index + 1 :])
        return _strip_wrapping_quotes(raw_value) or None
    return None


def _parse_block_scalar(lines: list[str]) -> str | None:
    collected: list[str] = []
    for line in lines:
        if not line.startswith((" ", "\t")):
            break
        collected.append(line.lstrip())
    value = "\n".join(collected).strip()
    return value or None


def _normalize_single_line(text: str) -> str:
    return " ".join(text.split())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_description_from_markdown(path: Path) -> MarkdownDescription | None:
    if not path.exists():
        return None
    text = _read_text(path)
    frontmatter, rest = _extract_frontmatter(text)
    if frontmatter:
        description = _parse_description_from_frontmatter(frontmatter)
        if description:
            return MarkdownDescription(description=_normalize_single_line(description), source="frontmatter")
    return _build_fallback_description(rest, COMMAND_FALLBACK_CHARS)


def read_description_from_skill_folder(folder: Path) -> MarkdownDescription | None:
    if not folder.exists():
        return None
    if folder.is_file():
        return read_description_from_markdown(folder)
    return read_description_from_markdown(folder / "SKILL.md")


def _build_fallback_description(text: str, max_chars: int) -> MarkdownDescription | None:
    normalized = _normalize_single_line(text)
    if not normalized:
        return None
    return MarkdownDescription(description=normalized[:max_chars], source="content")
