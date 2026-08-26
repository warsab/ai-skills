"""Tests for the install script."""

from __future__ import annotations

from pathlib import Path

import pytest

from install import available_skills, install_skill, main, resolve_destination


class TestAvailableSkills:
    def test_finds_the_repository_skills(self) -> None:
        names = [path.name for path in available_skills()]
        assert "upgrade-dependency" in names
        assert all((path / "SKILL.md").is_file() for path in available_skills())


class TestResolveDestination:
    def test_claude_code_personal_is_under_the_home_directory(self) -> None:
        resolved = resolve_destination("claude-code", "personal", None)
        assert resolved == Path.home() / ".claude" / "skills"

    def test_project_scope_needs_a_destination(self) -> None:
        with pytest.raises(ValueError, match="project root"):
            resolve_destination("claude-code", "project", None)

    def test_project_scope_appends_the_tool_layout(self, tmp_path: Path) -> None:
        resolved = resolve_destination("claude-code", "project", tmp_path)
        assert resolved == tmp_path / ".claude" / "skills"

    def test_an_explicit_destination_without_a_tool_is_used_as_is(
        self, tmp_path: Path
    ) -> None:
        assert resolve_destination(None, "personal", tmp_path) == tmp_path

    def test_neither_tool_nor_destination_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="--tool or --dest"):
            resolve_destination(None, "personal", None)

    def test_an_unknown_tool_names_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="claude-code"):
            resolve_destination("some-other-agent", "personal", None)


class TestInstallSkill:
    @pytest.fixture
    def source(self, tmp_path: Path) -> Path:
        skill = tmp_path / "src" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: demo-skill\n---\nBody\n", "utf-8")
        (skill / "references").mkdir()
        (skill / "references" / "REFERENCE.md").write_text("Detail", "utf-8")
        return skill

    def test_copies_the_whole_skill_directory(self, source: Path, tmp_path: Path) -> None:
        target_dir = tmp_path / "dest"
        install_skill(source, target_dir, link=False, force=False)

        installed = target_dir / "demo-skill"
        assert (installed / "SKILL.md").is_file()
        assert (installed / "references" / "REFERENCE.md").read_text("utf-8") == "Detail"

    def test_creates_the_destination_directory(
        self, source: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "deep" / "nested" / "dest"
        install_skill(source, target_dir, link=False, force=False)
        assert (target_dir / "demo-skill" / "SKILL.md").is_file()

    def test_refuses_to_overwrite_without_force(
        self, source: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "dest"
        install_skill(source, target_dir, link=False, force=False)
        with pytest.raises(FileExistsError, match="--force"):
            install_skill(source, target_dir, link=False, force=False)

    def test_force_replaces_an_existing_installation(
        self, source: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "dest"
        install_skill(source, target_dir, link=False, force=False)
        stale = target_dir / "demo-skill" / "stale.md"
        stale.write_text("old", encoding="utf-8")

        install_skill(source, target_dir, link=False, force=True)
        assert not stale.exists()
        assert (target_dir / "demo-skill" / "SKILL.md").is_file()


class TestMain:
    def test_dry_run_writes_nothing(self, tmp_path: Path, capsys) -> None:
        assert main(["--dest", str(tmp_path), "--dry-run"]) == 0
        assert not list(tmp_path.iterdir())
        assert "nothing was written" in capsys.readouterr().out

    def test_installs_every_skill(self, tmp_path: Path) -> None:
        assert main(["--dest", str(tmp_path)]) == 0
        installed = {path.name for path in tmp_path.iterdir()}
        assert installed == {path.name for path in available_skills()}

    def test_installs_a_single_named_skill(self, tmp_path: Path) -> None:
        assert main(["--dest", str(tmp_path), "--skill", "upgrade-dependency"]) == 0
        assert [path.name for path in tmp_path.iterdir()] == ["upgrade-dependency"]

    def test_an_unknown_skill_lists_what_is_available(
        self, tmp_path: Path, capsys
    ) -> None:
        assert main(["--dest", str(tmp_path), "--skill", "does-not-exist"]) == 1
        error = capsys.readouterr().err
        assert "no such skill" in error
        assert "upgrade-dependency" in error

    def test_reinstalling_without_force_fails_clearly(
        self, tmp_path: Path, capsys
    ) -> None:
        main(["--dest", str(tmp_path)])
        assert main(["--dest", str(tmp_path)]) == 1
        assert "--force" in capsys.readouterr().err

    def test_missing_target_arguments_are_reported(self, tmp_path: Path, capsys) -> None:
        assert main([]) == 1
        assert "--tool or --dest" in capsys.readouterr().err
