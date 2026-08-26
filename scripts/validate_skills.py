#!/usr/bin/env python3
"""Validate skills against the Agent Skills specification.

The specification (https://agentskills.io/specification) allows exactly six
frontmatter fields. Tools that package or upload skills — claude.ai, the Skills
API, ``package_skill.py`` — reject any other key with a hard error rather than
ignoring it, so a skill carrying a vendor extension stops being portable.

This script enforces the portable subset, which is the whole point of keeping
one canonical copy of each skill rather than one per vendor.

Usage:
    python scripts/validate_skills.py [PATH ...] [--strict]

Exits ``0`` when every skill passes, ``1`` when any error is found. Warnings are
style recommendations and do not fail the run unless ``--strict`` is passed.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without the dependency
    sys.exit(
        "PyYAML is required to validate skills.\n"
        "Install it with:  pip install -r requirements-dev.txt"
    )

#: The complete set of fields the Agent Skills spec permits.
SPEC_FIELDS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)
REQUIRED_FIELDS = frozenset({"name", "description"})

#: Lowercase alphanumerics and single hyphens, not leading or trailing.
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
COMPATIBILITY_MAX_LENGTH = 500

#: The spec recommends keeping SKILL.md short so activation stays cheap.
RECOMMENDED_MAX_BODY_LINES = 500
#: A description this short almost never says when to use the skill.
RECOMMENDED_MIN_DESCRIPTION_LENGTH = 60

FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True)
class Problem:
    """One validation finding.

    Attributes:
        skill: Name of the skill directory the finding belongs to.
        message: What is wrong, phrased so it can be fixed without the spec open.
        is_error: ``True`` for a spec violation, ``False`` for a style warning.
    """

    skill: str
    message: str
    is_error: bool = True

    def format(self) -> str:
        """Return the finding as one printable line."""
        label = "ERROR" if self.is_error else "warn "
        return f"  {label}  {self.skill}: {self.message}"


def split_frontmatter(text: str) -> tuple[str, str]:
    r"""Split a SKILL.md into its YAML frontmatter and markdown body.

    Args:
        text: The full file contents.

    Returns:
        A ``(frontmatter, body)`` pair, both unparsed.

    Raises:
        ValueError: If the file does not open with a delimited frontmatter block.

    Example:
        >>> split_frontmatter("---\nname: x\n---\nBody")
        ('name: x', 'Body')
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        raise ValueError("file must start with a '---' frontmatter delimiter")

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIMITER:
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :]).strip()

    raise ValueError("frontmatter is never closed with a second '---'")


def _check_name(name: Any, directory: str) -> list[str]:
    """Return every problem with the ``name`` field.

    Args:
        name: The parsed value of the field.
        directory: The skill's directory name, which the field must match.

    Returns:
        Human-readable problem descriptions; empty when the name is valid.
    """
    if not isinstance(name, str):
        return [f"name must be a string, got {type(name).__name__}"]

    problems = []
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        problems.append(f"name must be 1-{NAME_MAX_LENGTH} characters, got {len(name)}")
    if not NAME_PATTERN.match(name):
        problems.append(
            f"name {name!r} must be lowercase letters, numbers and single hyphens, "
            "and must not start or end with a hyphen"
        )
    if name != directory:
        problems.append(f"name {name!r} must match its directory name {directory!r}")
    return problems


def _check_description(description: Any) -> list[Problem]:
    """Return every problem with the ``description`` field.

    Args:
        description: The parsed value of the field.

    Returns:
        Findings, which may include a style warning about vague descriptions.
    """
    if not isinstance(description, str):
        return [
            Problem("", f"description must be a string, got {type(description).__name__}")
        ]

    problems = []
    if not description.strip():
        problems.append(Problem("", "description must not be empty"))
    elif len(description) > DESCRIPTION_MAX_LENGTH:
        problems.append(
            Problem(
                "",
                f"description must be at most {DESCRIPTION_MAX_LENGTH} characters, "
                f"got {len(description)}",
            )
        )
    elif len(description) < RECOMMENDED_MIN_DESCRIPTION_LENGTH:
        problems.append(
            Problem(
                "",
                "description is very short; it should say what the skill does AND "
                "when to use it, including the words a user would actually type",
                is_error=False,
            )
        )
    return problems


def validate_skill(skill_dir: Path) -> list[Problem]:
    """Validate one skill directory.

    Args:
        skill_dir: A directory expected to contain ``SKILL.md``.

    Returns:
        Every finding for this skill, errors and warnings together.
    """
    name = skill_dir.name
    problems: list[Problem] = []

    def error(message: str) -> None:
        problems.append(Problem(name, message))

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [Problem(name, "no SKILL.md found in the skill directory")]

    text = skill_file.read_text(encoding="utf-8")

    try:
        frontmatter_text, body = split_frontmatter(text)
    except ValueError as problem:
        return [Problem(name, str(problem))]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as problem:
        return [Problem(name, f"frontmatter is not valid YAML: {problem}")]

    if not isinstance(frontmatter, dict):
        return [Problem(name, "frontmatter must be a mapping of fields")]

    unexpected = sorted(set(frontmatter) - SPEC_FIELDS)
    if unexpected:
        error(
            f"frontmatter has non-spec field(s) {', '.join(unexpected)}. Only "
            f"{', '.join(sorted(SPEC_FIELDS))} are portable; anything else is "
            "rejected when the skill is packaged or uploaded"
        )

    for field in sorted(REQUIRED_FIELDS - set(frontmatter)):
        error(f"frontmatter is missing the required field '{field}'")

    if "name" in frontmatter:
        for message in _check_name(frontmatter["name"], name):
            error(message)

    if "description" in frontmatter:
        for problem in _check_description(frontmatter["description"]):
            problems.append(Problem(name, problem.message, problem.is_error))

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            error("compatibility must be a string")
        elif len(compatibility) > COMPATIBILITY_MAX_LENGTH:
            error(
                f"compatibility must be at most {COMPATIBILITY_MAX_LENGTH} "
                f"characters, got {len(compatibility)}"
            )

    if "license" in frontmatter and not isinstance(frontmatter["license"], str):
        error("license must be a string")

    if "allowed-tools" in frontmatter and not isinstance(
        frontmatter["allowed-tools"], str
    ):
        error("allowed-tools must be a space-separated string, not a list")

    metadata = frontmatter.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            error("metadata must be a mapping of string keys to string values")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    error(
                        f"metadata entry {key!r} must map a string to a string; "
                        "quote values like version numbers"
                    )

    if not body.strip():
        error("SKILL.md has no body; frontmatter alone gives the agent nothing to do")

    body_lines = len(body.splitlines())
    if body_lines > RECOMMENDED_MAX_BODY_LINES:
        problems.append(
            Problem(
                name,
                f"body is {body_lines} lines; the spec recommends under "
                f"{RECOMMENDED_MAX_BODY_LINES}. Move detail into references/",
                is_error=False,
            )
        )

    return problems


def find_skills(root: Path) -> list[Path]:
    """Find every skill directory beneath a path.

    A directory counts as a skill when it directly contains ``SKILL.md``.

    Args:
        root: A skills directory, or a single skill directory.

    Returns:
        Skill directories, sorted by name.
    """
    if (root / "SKILL.md").is_file():
        return [root]
    return sorted(path.parent for path in root.glob("*/SKILL.md"))


def main(argv: list[str] | None = None) -> int:
    """Validate the given paths and print a report.

    Args:
        argv: Command-line arguments, defaulting to :data:`sys.argv`.

    Returns:
        ``0`` if everything passed, ``1`` if any error (or, with ``--strict``,
        any warning) was found.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("skills")],
        help="skills directory or individual skill directories (default: skills)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat style warnings as failures"
    )
    args = parser.parse_args(argv)

    skills: list[Path] = []
    for path in args.paths:
        if not path.exists():
            print(f"ERROR  no such path: {path}")
            return 1
        skills.extend(find_skills(path))

    if not skills:
        print("ERROR  no skills found; expected directories containing SKILL.md")
        return 1

    problems = [problem for skill in skills for problem in validate_skill(skill)]
    errors = [problem for problem in problems if problem.is_error]
    warnings = [problem for problem in problems if not problem.is_error]

    for problem in problems:
        print(problem.format())

    checked = f"Checked {len(skills)} skill(s)"
    if errors:
        print(f"\n{checked}: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    if warnings:
        print(f"\n{checked}: no errors, {len(warnings)} warning(s).")
        return 1 if args.strict else 0

    print(f"\n{checked}: all valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
