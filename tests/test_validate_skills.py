"""Tests for the skill validator.

The repository's own skills are validated here too, so a spec violation in a new
skill fails the suite rather than being discovered at upload time.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from validate_skills import (
    find_skills,
    main,
    split_frontmatter,
    validate_skill,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID_FRONTMATTER = """\
---
name: {name}
description: A skill that does a specific thing, used when a user asks for that
  specific thing by name or describes the problem it solves.
---

# Heading

Body content.
"""


def write_skill(root: Path, name: str, content: str | None = None) -> Path:
    """Create a skill directory containing a SKILL.md.

    Args:
        root: Directory to create the skill inside.
        name: Skill directory name.
        content: File contents; a valid skill is written when omitted.

    Returns:
        The skill directory.
    """
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    body = content if content is not None else VALID_FRONTMATTER.format(name=name)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return skill_dir


def errors_of(skill_dir: Path) -> list[str]:
    """Return the error messages for a skill, ignoring warnings."""
    return [p.message for p in validate_skill(skill_dir) if p.is_error]


def warnings_of(skill_dir: Path) -> list[str]:
    """Return the warning messages for a skill, ignoring errors."""
    return [p.message for p in validate_skill(skill_dir) if not p.is_error]


class TestSplitFrontmatter:
    def test_splits_frontmatter_from_body(self) -> None:
        assert split_frontmatter("---\nname: x\n---\nBody") == ("name: x", "Body")

    def test_body_may_contain_further_delimiters(self) -> None:
        _, body = split_frontmatter("---\nname: x\n---\nBefore\n---\nAfter")
        assert body == "Before\n---\nAfter"

    def test_rejects_a_file_with_no_frontmatter(self) -> None:
        with pytest.raises(ValueError, match="must start with"):
            split_frontmatter("# Just markdown")

    def test_rejects_unclosed_frontmatter(self) -> None:
        with pytest.raises(ValueError, match="never closed"):
            split_frontmatter("---\nname: x\nstill going")


class TestValidSkill:
    def test_a_well_formed_skill_has_no_findings(self, tmp_path: Path) -> None:
        assert validate_skill(write_skill(tmp_path, "good-skill")) == []

    def test_all_optional_spec_fields_are_accepted(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            ---
            name: full-skill
            description: Does a specific thing, and says clearly when it should be used.
            license: MIT
            compatibility: Requires git and network access
            allowed-tools: Read Grep
            metadata:
              author: warsab
              version: "1.0"
            ---

            Body.
            """)
        assert errors_of(write_skill(tmp_path, "full-skill", content)) == []


class TestSpecViolations:
    def test_missing_skill_file(self, tmp_path: Path) -> None:
        (tmp_path / "empty-skill").mkdir()
        assert "no SKILL.md" in errors_of(tmp_path / "empty-skill")[0]

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        skill = write_skill(tmp_path, "bare", "---\nlicense: MIT\n---\n\nBody.\n")
        messages = " ".join(errors_of(skill))
        assert "'name'" in messages
        assert "'description'" in messages

    @pytest.mark.parametrize(
        "name", ["Upper-Case", "-leading", "trailing-", "double--hyphen", "under_score"]
    )
    def test_invalid_name_characters(self, tmp_path: Path, name: str) -> None:
        content = VALID_FRONTMATTER.format(name=name)
        skill = write_skill(tmp_path, name.lower().replace("_", "-"), content)
        assert any("lowercase letters" in message for message in errors_of(skill))

    def test_name_must_match_the_directory(self, tmp_path: Path) -> None:
        content = VALID_FRONTMATTER.format(name="something-else")
        skill = write_skill(tmp_path, "actual-directory", content)
        assert any("must match its directory" in m for m in errors_of(skill))

    def test_name_over_64_characters(self, tmp_path: Path) -> None:
        name = "a" * 65
        skill = write_skill(tmp_path, name, VALID_FRONTMATTER.format(name=name))
        assert any("1-64 characters" in message for message in errors_of(skill))

    def test_description_over_1024_characters(self, tmp_path: Path) -> None:
        content = f"---\nname: wordy\ndescription: {'x' * 1025}\n---\n\nBody.\n"
        skill = write_skill(tmp_path, "wordy", content)
        assert any("at most 1024" in message for message in errors_of(skill))

    def test_empty_description(self, tmp_path: Path) -> None:
        content = '---\nname: blank\ndescription: ""\n---\n\nBody.\n'
        skill = write_skill(tmp_path, "blank", content)
        assert any("must not be empty" in message for message in errors_of(skill))

    def test_compatibility_over_500_characters(self, tmp_path: Path) -> None:
        content = (
            "---\nname: picky\ndescription: A skill that does a thing, used when "
            f"someone asks for that thing.\ncompatibility: {'x' * 501}\n---\n\nBody.\n"
        )
        skill = write_skill(tmp_path, "picky", content)
        assert any("at most 500" in message for message in errors_of(skill))

    def test_allowed_tools_must_be_a_string_not_a_list(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            ---
            name: listy
            description: A skill that does a thing, used when someone asks for it.
            allowed-tools:
              - Read
              - Grep
            ---

            Body.
            """)
        skill = write_skill(tmp_path, "listy", content)
        assert any("space-separated string" in m for m in errors_of(skill))

    def test_metadata_values_must_be_strings(self, tmp_path: Path) -> None:
        # An unquoted version number parses as a float and breaks packaging.
        content = (
            "---\nname: metaskill\ndescription: A skill that does a thing, used when "
            "someone asks for that thing.\nmetadata:\n  version: 1.0\n---\n\nBody.\n"
        )
        skill = write_skill(tmp_path, "metaskill", content)
        assert any("must map a string to a string" in m for m in errors_of(skill))

    def test_body_must_not_be_empty(self, tmp_path: Path) -> None:
        content = (
            "---\nname: hollow\ndescription: A skill that does a thing, used when "
            "someone asks for that thing.\n---\n"
        )
        skill = write_skill(tmp_path, "hollow", content)
        assert any("no body" in message for message in errors_of(skill))

    def test_malformed_yaml_is_reported(self, tmp_path: Path) -> None:
        skill = write_skill(tmp_path, "broken", "---\nname: [unclosed\n---\n\nBody.\n")
        assert any("not valid YAML" in message for message in errors_of(skill))


class TestPortability:
    def test_a_vendor_extension_field_is_an_error(self, tmp_path: Path) -> None:
        # argument-hint is valid in Claude Code but rejected when packaged.
        content = (
            "---\nname: extended\ndescription: A skill that does a thing, used when "
            "someone asks for that thing.\nargument-hint: [file]\n---\n\nBody.\n"
        )
        skill = write_skill(tmp_path, "extended", content)
        messages = " ".join(errors_of(skill))
        assert "argument-hint" in messages
        assert "portable" in messages

    def test_it_names_every_offending_field(self, tmp_path: Path) -> None:
        content = (
            "---\nname: extended\ndescription: A skill that does a thing, used when "
            "someone asks for that thing.\nargument-hint: [f]\n"
            "disable-model-invocation: true\n---\n\nBody.\n"
        )
        skill = write_skill(tmp_path, "extended", content)
        messages = " ".join(errors_of(skill))
        assert "argument-hint" in messages
        assert "disable-model-invocation" in messages


class TestStyleWarnings:
    def test_a_terse_description_warns_without_erroring(self, tmp_path: Path) -> None:
        content = "---\nname: terse\ndescription: Helps with PDFs.\n---\n\nBody.\n"
        skill = write_skill(tmp_path, "terse", content)
        assert errors_of(skill) == []
        assert any("when to use it" in message for message in warnings_of(skill))

    def test_a_long_body_warns_without_erroring(self, tmp_path: Path) -> None:
        body = "\n".join(f"Line {n}." for n in range(600))
        content = (
            "---\nname: sprawling\ndescription: A skill that does a thing, used when "
            f"someone asks for that thing.\n---\n\n{body}\n"
        )
        skill = write_skill(tmp_path, "sprawling", content)
        assert errors_of(skill) == []
        assert any("references/" in message for message in warnings_of(skill))


class TestDiscovery:
    def test_finds_every_skill_in_a_directory(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "one")
        write_skill(tmp_path, "two")
        (tmp_path / "not-a-skill").mkdir()
        assert [path.name for path in find_skills(tmp_path)] == ["one", "two"]

    def test_accepts_a_single_skill_directory(self, tmp_path: Path) -> None:
        skill = write_skill(tmp_path, "solo")
        assert find_skills(skill) == [skill]


class TestMain:
    def test_passes_on_valid_skills(self, tmp_path: Path, capsys) -> None:
        write_skill(tmp_path, "fine")
        assert main([str(tmp_path)]) == 0
        assert "all valid" in capsys.readouterr().out

    def test_fails_on_an_invalid_skill(self, tmp_path: Path, capsys) -> None:
        write_skill(tmp_path, "bad", "---\nname: bad\n---\n\nBody.\n")
        assert main([str(tmp_path)]) == 1
        assert "ERROR" in capsys.readouterr().out

    def test_warnings_pass_by_default(self, tmp_path: Path) -> None:
        write_skill(
            tmp_path, "terse", "---\nname: terse\ndescription: Short.\n---\n\nB.\n"
        )
        assert main([str(tmp_path)]) == 0

    def test_strict_turns_warnings_into_failures(self, tmp_path: Path) -> None:
        write_skill(
            tmp_path, "terse", "---\nname: terse\ndescription: Short.\n---\n\nB.\n"
        )
        assert main([str(tmp_path), "--strict"]) == 1

    def test_a_missing_path_is_reported(self, tmp_path: Path, capsys) -> None:
        assert main([str(tmp_path / "nope")]) == 1
        assert "no such path" in capsys.readouterr().out

    def test_an_empty_directory_is_reported(self, tmp_path: Path, capsys) -> None:
        assert main([str(tmp_path)]) == 1
        assert "no skills found" in capsys.readouterr().out


class TestThisRepository:
    def test_every_shipped_skill_is_spec_compliant(self) -> None:
        skills = find_skills(REPO_ROOT / "skills")
        assert skills, "the repository should ship at least one skill"

        problems = [
            problem.format() for skill in skills for problem in validate_skill(skill)
        ]
        assert not problems, "\n" + "\n".join(problems)
