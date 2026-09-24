"""Exercise repository consistency checks against disposable, minimal fixtures."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_repo.py"
SPEC = importlib.util.spec_from_file_location("validate_repo", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def make_repo(repo: Path) -> None:
    for name in validator.SKILL_NAMES:
        skill = repo / "skills" / name
        (skill / "agents").mkdir(parents=True)
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Use when a sample task needs this skill.\n---\n"
            "[Reference](references/guide.md#example)\n", encoding="utf-8",
        )
        (skill / "references" / "guide.md").write_text("# Example\n", encoding="utf-8")
        (skill / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Sample"\n'
            '  short_description: "A useful sample skill description"\n'
            f'  default_prompt: "Use ${name} for a sample task."\n', encoding="utf-8",
        )
    (repo / ".codex-plugin").mkdir()
    (repo / ".codex-plugin" / "plugin.json").write_text(json.dumps({
        "name": "superpowerpoint", "version": "0.1.0", "description": "Sample plugin",
        "skills": "./skills/", "interface": {"displayName": "Superpowerpoint", "shortDescription": "PowerPoint workflows"},
    }), encoding="utf-8")
    (repo / "README.md").write_text("[Skill](skills/superpowerpoint/SKILL.md)\n", encoding="utf-8")


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="superpowerpoint-validate-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "kho tiếng Việt"
        make_repo(self.repo)

    def test_valid_collection_and_unicode_paths_pass(self) -> None:
        self.assertEqual(validator.validate_repo(self.repo), [])

    def test_missing_skill_is_reported(self) -> None:
        (self.repo / "skills" / "editing-powerpoint" / "SKILL.md").unlink()
        self.assertTrue(any("editing-powerpoint/SKILL.md" in error.replace("\\", "/") for error in validator.validate_repo(self.repo)))

    def test_frontmatter_name_must_match_directory(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "SKILL.md"
        path.write_text("---\nname: wrong-name\ndescription: Still a description.\n---\n", encoding="utf-8")
        self.assertTrue(any("name must match" in error for error in validator.validate_repo(self.repo)))

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "SKILL.md"
        path.write_text("---\nname: planning-powerpoint\nname: second\ndescription: Test\n---\n", encoding="utf-8")
        self.assertTrue(any("duplicate key" in error for error in validator.validate_repo(self.repo)))

    def test_non_string_frontmatter_values_are_rejected(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "SKILL.md"
        for value in ("null", "true", "42", "1.5"):
            with self.subTest(value=value):
                path.write_text(f"---\nname: planning-powerpoint\ndescription: {value}\n---\n", encoding="utf-8")
                self.assertTrue(validator.validate_repo(self.repo))

    def test_missing_ui_field_is_reported(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "agents" / "openai.yaml"
        path.write_text("interface:\n  display_name: Sample\n  short_description: Sample description\n", encoding="utf-8")
        self.assertTrue(any("default_prompt" in error for error in validator.validate_repo(self.repo)))

    def test_invalid_nested_metadata_indentation_is_rejected(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "agents" / "openai.yaml"
        path.write_text("interface:\n   display_name: Wrong indentation\n", encoding="utf-8")
        self.assertTrue(any("indentation" in error for error in validator.validate_repo(self.repo)))

    def test_ui_metadata_checks_discovery_constraints(self) -> None:
        path = self.repo / "skills" / "planning-powerpoint" / "agents" / "openai.yaml"
        path.write_text(
            "interface:\n  display_name: Sample\n  short_description: Tiny\n"
            "  default_prompt: Run an unrelated skill.\n", encoding="utf-8",
        )
        errors = validator.validate_repo(self.repo)
        self.assertTrue(any("25–64" in error for error in errors))
        self.assertTrue(any("must name $planning-powerpoint" in error for error in errors))

    def test_broken_inline_and_reference_links_are_reported(self) -> None:
        (self.repo / "README.md").write_text("[Missing](absent.md)\n[Reference][guide]\n[guide]: absent-too.md\n", encoding="utf-8")
        errors = validator.validate_repo(self.repo)
        self.assertEqual(sum("broken local link" in error for error in errors), 2)

    def test_escaping_local_link_is_rejected_even_when_file_exists(self) -> None:
        (self.repo.parent / "outside.md").write_text("outside", encoding="utf-8")
        (self.repo / "README.md").write_text("[Outside](../outside.md)\n", encoding="utf-8")
        self.assertTrue(any("escapes repository" in error for error in validator.validate_repo(self.repo)))

    def test_external_anchor_and_code_examples_are_not_local_files(self) -> None:
        (self.repo / "README.md").write_text(
            "[Web](https://example.com/missing) [Email](mailto:hello@example.com) [Section](#section)\n"
            "```markdown\n[Example](not-created.md)\n```\n`[Inline](not-created-either.md)`\n", encoding="utf-8",
        )
        self.assertEqual(validator.validate_repo(self.repo), [])

    def test_encoded_unicode_and_angle_bracket_links_are_supported(self) -> None:
        (self.repo / "ghi chú.md").write_text("# Notes\n", encoding="utf-8")
        (self.repo / "README.md").write_text("[One](<ghi chú.md>)\n[Two](ghi%20ch%C3%BA.md)\n", encoding="utf-8")
        self.assertEqual(validator.validate_repo(self.repo), [])

    def test_manifest_must_identify_real_skill_collection(self) -> None:
        path = self.repo / ".codex-plugin" / "plugin.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["skills"] = "./missing/"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertTrue(any("skills must point" in error for error in validator.validate_repo(self.repo)))

    def test_malformed_manifest_is_reported(self) -> None:
        (self.repo / ".codex-plugin" / "plugin.json").write_text("{broken", encoding="utf-8")
        self.assertTrue(any("plugin.json" in error for error in validator.validate_repo(self.repo)))

    def test_cli_exit_status_distinguishes_valid_and_invalid_repositories(self) -> None:
        valid = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo)], capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        (self.repo / "README.md").write_text("[Bad](missing.md)\n", encoding="utf-8")
        invalid = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo)], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("broken local link", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
