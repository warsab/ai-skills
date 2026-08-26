# ai-skills

[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-5A67D8.svg)](https://agentskills.io)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-53%20passing-brightgreen.svg)](tests)

Reusable skills for AI coding agents, written to the
[Agent Skills](https://agentskills.io) open standard.

A skill is a folder with a `SKILL.md` inside: instructions an agent loads on
demand when a task matches. These ones encode the procedures that are easy to
get wrong under pressure — upgrading a dependency, triaging a production error,
reviewing a database migration — so the agent follows a checklist instead of
improvising.

Every skill here is plain markdown with no dependencies, and works in Claude
Code, ChatGPT/Codex, Gemini CLI, Cursor, Copilot and
[every other client](https://agentskills.io/clients) that supports the standard.

---

## The skills

| Skill | What it does | Reach for it when |
| --- | --- | --- |
| [`upgrade-dependency`](skills/upgrade-dependency/SKILL.md) | Establishes a green baseline, reads every changelog entry between the two versions, maps breaking changes onto the code's actual usage, then verifies behaviour — not just that it compiles. | Bumping a version, patching a CVE, working a Dependabot PR |
| [`triage-production-error`](skills/triage-production-error/SKILL.md) | Mitigates first if the bleeding is ongoing, traces the bad value back to the invariant that was broken, and requires a regression test that fails *before* the fix. | A stack trace, a Sentry issue, an on-call page |
| [`review-database-migration`](skills/review-database-migration/SKILL.md) | Checks locking, unshipped code paths, unbatched backfills and rollback for each operation type, and gives a blocked / changes-needed / safe verdict. | Any schema change heading for a production table |

Each one is deliberately about **judgement, not syntax**. An agent already knows
how to write `npm install` or `ALTER TABLE`. What it lacks is the sequencing that
stops those commands causing an incident.

## Quick start

```bash
git clone https://github.com/warsab/ai-skills.git
cd ai-skills

# Install everything into Claude Code, for all your projects
python scripts/install.py --tool claude-code

# Or preview first
python scripts/install.py --tool claude-code --dry-run
```

Then just work. The agent loads a skill when the task matches its description,
or you can invoke one by name — `/upgrade-dependency` in Claude Code.

Using a different agent? Pass its skills directory:

```bash
python scripts/install.py --dest ~/.config/some-agent/skills
```

See [docs/installing.md](docs/installing.md) for each tool's path.

## Why there are no per-provider folders

The obvious layout for a repository like this is one folder per vendor —
`anthropic/`, `openai/`, `gemini/`. It is the wrong one.

Agent Skills is a **cross-vendor open standard**, originally built by Anthropic
and released openly. The same `SKILL.md` is read by Claude Code, ChatGPT/Codex,
Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode, Amp, Goose and dozens of
others. Splitting by provider would mean three copies of identical content, which
would drift apart within a month.

What genuinely differs between providers is only two things, and neither needs a
folder:

1. **Where the folder is installed.** That is documentation —
   [docs/installing.md](docs/installing.md).
2. **Which frontmatter fields are legal.** Only six are portable: `name`,
   `description`, `license`, `compatibility`, `metadata`, `allowed-tools`.
   Vendor extensions such as Claude Code's `argument-hint` are not ignored
   elsewhere — they are a hard error:

   ```
   Unexpected key(s) in SKILL.md frontmatter: argument-hint.
   ```

So skills live once, in `skills/`, restricted to the portable six fields — and
`scripts/validate_skills.py` fails the build if anyone adds a seventh. The spec's
own `compatibility` field covers the rare genuinely tool-specific skill.

## Repository layout

```
ai-skills/
├── skills/                       # the skills themselves, one folder each
│   ├── upgrade-dependency/SKILL.md
│   ├── triage-production-error/SKILL.md
│   └── review-database-migration/SKILL.md
├── scripts/
│   ├── validate_skills.py        # enforce the spec + the portable subset
│   └── install.py                # copy or symlink into an agent's directory
├── docs/
│   ├── installing.md             # per-tool paths and troubleshooting
│   └── writing-skills.md         # the format, and what makes a skill work
├── tests/                        # 53 tests, including every shipped skill
└── requirements-dev.txt
```

## Contributing

New skills are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/writing-skills.md](docs/writing-skills.md).

The bar is one question: **would you actually use this in your job next week?**
A skill that reads well but never activates is worse than no skill, because it
costs context at startup for nothing.

```bash
pip install -r requirements-dev.txt
python scripts/validate_skills.py --strict
pytest
```

The test suite validates every shipped skill, so a spec violation fails CI rather
than surfacing when someone tries to upload it.

## License

[MIT](LICENSE). The skills are yours to copy, edit and fold into your own
toolkit.
