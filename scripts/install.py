#!/usr/bin/env python3
"""Install skills from this repository into an agent's skills directory.

Because Agent Skills is a shared format, installing means putting the skill
folder where a given tool looks for it. Nothing is rewritten on the way.

Usage:
    python scripts/install.py --tool claude-code
    python scripts/install.py --tool claude-code --scope project --dest .
    python scripts/install.py --dest ~/some/other/agent/skills
    python scripts/install.py --tool claude-code --skill upgrade-dependency --link

Only Claude Code's paths are built in, because they are the ones this repository
verifies. For any other tool, pass ``--dest`` with the path from that tool's own
documentation — see docs/installing.md.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

#: Destination for each built-in tool and scope.
KNOWN_DESTINATIONS = {
    ("claude-code", "personal"): Path.home() / ".claude" / "skills",
    ("claude-code", "project"): Path(".claude") / "skills",
}


def available_skills() -> list[Path]:
    """Return every skill directory in this repository, sorted by name.

    Returns:
        Directories under ``skills/`` that contain a ``SKILL.md``.
    """
    return sorted(path.parent for path in SKILLS_DIR.glob("*/SKILL.md"))


def resolve_destination(tool: str | None, scope: str, dest: Path | None) -> Path:
    """Work out where skills should be installed.

    Args:
        tool: A built-in tool name, or ``None`` when ``dest`` is given.
        scope: ``"personal"`` or ``"project"``, used with ``tool``.
        dest: An explicit destination, which wins over ``tool``.

    Returns:
        The directory that skill folders should be placed in.

    Raises:
        ValueError: If neither a known tool nor a destination was given.
    """
    if dest is not None:
        base = dest.expanduser()
        # --dest with a tool means "this project root", so keep the tool layout.
        if tool and (tool, scope) in KNOWN_DESTINATIONS:
            relative = KNOWN_DESTINATIONS[(tool, scope)]
            if not relative.is_absolute():
                return base / relative
        return base

    if tool is None:
        raise ValueError("pass either --tool or --dest")

    try:
        resolved = KNOWN_DESTINATIONS[(tool, scope)]
    except KeyError:
        known = ", ".join(sorted({name for name, _ in KNOWN_DESTINATIONS}))
        raise ValueError(
            f"no built-in path for tool {tool!r} with scope {scope!r}. "
            f"Built-in tools: {known}. For anything else pass --dest; "
            "see docs/installing.md"
        ) from None

    if not resolved.is_absolute():
        raise ValueError(
            f"{tool} {scope} skills are relative to a project root; "
            "pass --dest with the project directory"
        )
    return resolved


def install_skill(source: Path, target_dir: Path, link: bool, force: bool) -> str:
    """Install one skill directory.

    Args:
        source: The skill directory in this repository.
        target_dir: The directory to install into.
        link: Create a symlink instead of copying, so edits here take effect
            immediately. Requires developer mode or admin rights on Windows.
        force: Replace an existing installation.

    Returns:
        A short description of what happened, for the caller to print.

    Raises:
        FileExistsError: If the target exists and ``force`` is ``False``.
    """
    target = target_dir / source.name

    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(f"{target} already exists; pass --force to replace it")
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)

    target_dir.mkdir(parents=True, exist_ok=True)

    if link:
        try:
            target.symlink_to(source, target_is_directory=True)
        except OSError as problem:
            raise OSError(
                f"could not create a symlink at {target} ({problem}). "
                "On Windows, enable Developer Mode or drop --link to copy instead"
            ) from problem
        return f"linked  {source.name} -> {target}"

    shutil.copytree(source, target)
    return f"copied  {source.name} -> {target}"


def main(argv: list[str] | None = None) -> int:
    """Install the selected skills.

    Args:
        argv: Command-line arguments, defaulting to :data:`sys.argv`.

    Returns:
        ``0`` on success, ``1`` on a usage or filesystem error.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tool",
        choices=sorted({name for name, _ in KNOWN_DESTINATIONS}),
        help="install into a tool's standard location",
    )
    parser.add_argument(
        "--scope",
        choices=("personal", "project"),
        default="personal",
        help="personal (all your projects) or project (this repo only)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        help="explicit destination, or the project root when used with --scope project",
    )
    parser.add_argument(
        "--skill",
        action="append",
        metavar="NAME",
        help="install only this skill; repeatable (default: all)",
    )
    parser.add_argument(
        "--link",
        action="store_true",
        help="symlink instead of copying, so repo edits apply immediately",
    )
    parser.add_argument(
        "--force", action="store_true", help="replace an existing installation"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would happen, change nothing"
    )
    args = parser.parse_args(argv)

    try:
        target_dir = resolve_destination(args.tool, args.scope, args.dest)
    except ValueError as problem:
        print(f"Error: {problem}", file=sys.stderr)
        return 1

    everything = available_skills()
    if args.skill:
        by_name = {path.name: path for path in everything}
        missing = sorted(set(args.skill) - set(by_name))
        if missing:
            print(
                f"Error: no such skill(s): {', '.join(missing)}.\n"
                f"Available: {', '.join(sorted(by_name))}",
                file=sys.stderr,
            )
            return 1
        selected = [by_name[name] for name in args.skill]
    else:
        selected = everything

    if not selected:
        print("Error: no skills found to install", file=sys.stderr)
        return 1

    print(f"Installing {len(selected)} skill(s) into {target_dir}")

    for source in selected:
        if args.dry_run:
            verb = "would link" if args.link else "would copy"
            print(f"  {verb}  {source.name} -> {target_dir / source.name}")
            continue
        try:
            print(f"  {install_skill(source, target_dir, args.link, args.force)}")
        except (FileExistsError, OSError) as problem:
            print(f"Error: {problem}", file=sys.stderr)
            return 1

    if args.dry_run:
        print("\nDry run: nothing was written.")
    else:
        print("\nDone. Restart your agent if it does not pick up skills live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
