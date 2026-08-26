# Installing skills

A skill is a folder containing `SKILL.md`. Installing one means putting that
folder where your agent looks for skills. Nothing is converted on the way — the
same folder works in every tool that supports the format.

## With the install script

```bash
# Everything, for all your projects (Claude Code)
python scripts/install.py --tool claude-code

# Into one project only
python scripts/install.py --tool claude-code --scope project --dest /path/to/project

# One skill, symlinked so edits in this repo apply immediately
python scripts/install.py --tool claude-code --skill upgrade-dependency --link

# Any other agent: give the path from its own documentation
python scripts/install.py --dest ~/.config/some-agent/skills
```

Useful flags: `--dry-run` to preview, `--force` to replace an existing
installation, `--link` to symlink instead of copy.

`--link` is the better choice while you are still editing a skill — the agent
reads your working copy, so there is no reinstall step. On Windows it needs
Developer Mode enabled; without it, drop the flag and copy.

## By hand

Copy the skill folder into the target directory:

```bash
cp -r skills/upgrade-dependency ~/.claude/skills/
```

## Where each tool looks

Only the Claude Code paths below are verified by this repository and built into
the install script. For every other tool, follow its own documentation and pass
the path with `--dest` — vendors move these, and a stale path in a README is
worse than no path.

| Tool | Documentation |
| --- | --- |
| Claude Code | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) |
| Claude (claude.ai, API) | [platform.claude.com](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| ChatGPT / Codex | [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills/) |
| Gemini CLI | [geminicli.com/docs/cli/skills](https://geminicli.com/docs/cli/skills/) |
| Cursor | [cursor.com/docs/context/skills](https://cursor.com/docs/context/skills) |
| GitHub Copilot | [docs.github.com](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |
| VS Code | [code.visualstudio.com](https://code.visualstudio.com/docs/copilot/customization/agent-skills) |
| OpenCode | [opencode.ai/docs/skills](https://opencode.ai/docs/skills/) |
| Amp | [ampcode.com/manual](https://ampcode.com/manual#agent-skills) |
| Goose | [block.github.io/goose](https://block.github.io/goose/docs/guides/context-engineering/using-skills/) |

The [full client list](https://agentskills.io/clients) is longer and still
growing.

### Claude Code paths

| Scope | Path | Applies to |
| --- | --- | --- |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<skill-name>/SKILL.md` | That repository only |

Claude Code watches these directories, so a skill added or edited mid-session is
picked up without a restart.

Commit project skills to the repository when the whole team should have them —
that is also what makes them available to cloud sessions, which do not read your
personal `~/.claude/skills/`.

## Checking it worked

Ask the agent to list its available skills, or invoke one directly by name — in
Claude Code, `/upgrade-dependency`.

If the skill does not appear:

1. Confirm the path is `<skills-dir>/<skill-name>/SKILL.md` — the file must sit
   inside a folder named after the skill, not loose in the skills directory
2. Confirm the `name` in the frontmatter matches that folder name
3. Run `python scripts/validate_skills.py` against the installed copy
4. Restart the agent
