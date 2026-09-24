#!/usr/bin/env python3
"""Validate this repository's skill metadata, local Markdown links, and plugin manifest.

This checks package consistency, not agent behavior, slide quality, or visual output.
The metadata reader deliberately supports scalar YAML mappings only; no YAML dependency
is required. Quoted strings and nested mappings cover the files maintained here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


SKILL_NAMES = (
    "superpowerpoint", "planning-powerpoint", "designing-powerpoint",
    "building-powerpoint", "editing-powerpoint", "reviewing-powerpoint",
)
IGNORED_PARTS = {".git", ".build", ".venv", "venv", "node_modules", "__pycache__"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read_mapping(text: str) -> dict:
    """Read our small YAML mapping subset, rejecting duplicate or ambiguous keys."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-2, root)]
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[:len(line) - len(line.lstrip())]:
            raise ValueError(f"line {number}: tabs are not allowed for indentation")
        match = re.fullmatch(r"( *)([A-Za-z_][A-Za-z0-9_-]*):(?: +(.*))?", line.rstrip())
        if not match:
            raise ValueError(f"line {number}: expected a scalar YAML mapping")
        indent, key, raw = len(match[1]), match[2], match[3]
        while stack[-1][0] >= indent:
            stack.pop()
        if indent != stack[-1][0] + 2:
            raise ValueError(f"line {number}: expected two-space mapping indentation")
        mapping = stack[-1][1]
        if key in mapping:
            raise ValueError(f"line {number}: duplicate key {key!r}")
        if raw is None or raw == "":
            mapping[key] = {}
            stack.append((indent, mapping[key]))
            continue
        if raw.startswith('"'):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {number}: invalid quoted string") from exc
            if not isinstance(value, str):
                raise ValueError(f"line {number}: expected a string")
        elif raw.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", raw):
                raise ValueError(f"line {number}: invalid single-quoted string")
            value = raw[1:-1].replace("''", "'")
        elif raw[0] in "|>[{&*!" or ": " in raw:
            raise ValueError(f"line {number}: use a quoted single-line string")
        else:
            value = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
            if value.lower() in {"null", "~", "true", "false"} or re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value):
                raise ValueError(f"line {number}: metadata values must be strings; quote scalar values")
        mapping[key] = value
    return root


def frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    return read_mapping("\n".join(lines[1:end]))


def _required_strings(mapping: dict, keys: tuple[str, ...], label: str, errors: list[str]) -> None:
    for key in keys:
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: {key} must be a nonempty string")


def markdown_targets(text: str) -> list[str]:
    # Documentation examples are not live links. Ignore fenced and inline code.
    prose = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    inline = re.findall(r"!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))(?:\s+[\"'][^\n]*?[\"'])?\s*\)", prose)
    references = re.findall(r"(?m)^\s{0,3}\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))", prose)
    return [angle or plain for angle, plain in inline + references]


def _local_target(root: Path, origin: Path, target: str, errors: list[str]) -> None:
    if target.startswith("#") or target.startswith("//"):
        return
    parsed = urlsplit(target)
    if parsed.scheme:
        # Absolute machine paths cannot be portable repository references.
        if len(parsed.scheme) == 1 or parsed.scheme == "file":
            errors.append(f"{origin.relative_to(root)}: nonportable local link {target!r}")
        return
    path_text = unquote(parsed.path)
    if not path_text:
        return
    resolved = (origin.parent / path_text).resolve()
    if not resolved.is_relative_to(root):
        errors.append(f"{origin.relative_to(root)}: local link escapes repository: {target!r}")
    elif not resolved.exists():
        errors.append(f"{origin.relative_to(root)}: broken local link: {target!r}")


def validate_repo(repo: Path) -> list[str]:
    root = repo.resolve()
    errors: list[str] = []
    for name in SKILL_NAMES:
        skill_path = root / "skills" / name / "SKILL.md"
        try:
            meta = frontmatter(skill_path.read_text(encoding="utf-8-sig"))
            _required_strings(meta, ("name", "description"), str(skill_path.relative_to(root)), errors)
            if meta.get("name") != name or not NAME_PATTERN.fullmatch(str(meta.get("name", ""))):
                errors.append(f"{skill_path.relative_to(root)}: name must match directory {name!r}")
            if isinstance(meta.get("description"), str) and len(meta["description"]) > 1024:
                errors.append(f"{skill_path.relative_to(root)}: description exceeds 1024 characters")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{skill_path.relative_to(root)}: {exc}")
        ui_path = skill_path.parent / "agents" / "openai.yaml"
        try:
            ui = read_mapping(ui_path.read_text(encoding="utf-8-sig"))
            interface = ui.get("interface")
            if not isinstance(interface, dict):
                errors.append(f"{ui_path.relative_to(root)}: interface must be a mapping")
            else:
                _required_strings(interface, ("display_name", "short_description", "default_prompt"), str(ui_path.relative_to(root)), errors)
                short = interface.get("short_description")
                if isinstance(short, str) and not 25 <= len(short) <= 64:
                    errors.append(f"{ui_path.relative_to(root)}: short_description must contain 25–64 characters")
                prompt = interface.get("default_prompt")
                if isinstance(prompt, str) and f"${name}" not in prompt:
                    errors.append(f"{ui_path.relative_to(root)}: default_prompt must name ${name}")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{ui_path.relative_to(root)}: {exc}")

    manifest_path = root / ".codex-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
        _required_strings(manifest, ("name", "version", "description", "skills"), ".codex-plugin/plugin.json", errors)
        if manifest.get("name") != "superpowerpoint":
            errors.append(".codex-plugin/plugin.json: name must be 'superpowerpoint'")
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", str(manifest.get("version", ""))):
            errors.append(".codex-plugin/plugin.json: version must be a semantic version")
        skills = manifest.get("skills")
        if not isinstance(skills, str) or (root / skills).resolve() != root / "skills":
            errors.append(".codex-plugin/plugin.json: skills must point to ./skills/")
        interface = manifest.get("interface")
        if not isinstance(interface, dict):
            errors.append(".codex-plugin/plugin.json: interface must be an object")
        else:
            _required_strings(interface, ("displayName", "shortDescription"), ".codex-plugin/plugin.json interface", errors)
            for field in ("composerIcon", "logo"):
                if field in interface:
                    if not isinstance(interface[field], str):
                        errors.append(f".codex-plugin/plugin.json: {field} must be a path string")
                    else:
                        _local_target(root, root / "plugin.json", interface[field], errors)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f".codex-plugin/plugin.json: {exc}")

    for md_path in sorted(root.rglob("*.md")):
        if any(part in IGNORED_PARTS for part in md_path.relative_to(root).parts):
            continue
        try:
            for target in markdown_targets(md_path.read_text(encoding="utf-8-sig")):
                _local_target(root, md_path, target, errors)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{md_path.relative_to(root)}: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root to validate")
    args = parser.parse_args(argv)
    errors = validate_repo(args.repo)
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository validation passed: six skills, UI metadata, plugin manifest, and local Markdown file links.")
    print("Scope: package consistency only; no agent behavior, factual, or visual quality claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
