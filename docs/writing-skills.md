# Writing a skill

The [Agent Skills specification](https://agentskills.io/specification) defines
the format. This page covers the format briefly, then the part the spec does not
cover: what makes a skill actually change an agent's behaviour.

## The format

```
skills/my-skill/
├── SKILL.md          # required: frontmatter + instructions
├── scripts/          # optional: executable helpers
├── references/       # optional: detail loaded only when needed
└── assets/           # optional: templates, schemas, examples
```

### Frontmatter

Six fields, and **only** these six. Anything else is rejected outright when a
skill is packaged or uploaded, which is what would break portability across
tools:

| Field | Required | Constraints |
| --- | --- | --- |
| `name` | Yes | ≤64 chars, lowercase letters, digits and single hyphens. No leading, trailing or doubled hyphens. **Must match the directory name.** |
| `description` | Yes | ≤1024 chars. What it does *and* when to use it. |
| `license` | No | Licence name, or the name of a bundled licence file. |
| `compatibility` | No | ≤500 chars. Environment requirements. Most skills do not need it. |
| `metadata` | No | Map of string keys to string values. Quote version numbers. |
| `allowed-tools` | No | Space-separated string, not a list. Experimental. |

Run `python scripts/validate_skills.py` to check all of this.

## The description is the most important line

An agent loads only `name` and `description` at startup. That single sentence is
the entire basis on which it decides whether to read the rest. A perfect skill
body with a vague description never runs.

Write the description to match **what a user would actually type**, not what the
skill is called internally.

```yaml
# Poor — never matches anything
description: Helps with dependencies.

# Good — states the job, then the trigger vocabulary
description: Upgrade a third-party dependency safely by reading the changelog for
  breaking changes, finding every affected call site, updating the code, and
  verifying. Use when bumping a package version, applying a security or CVE patch,
  resolving a Dependabot or Renovate pull request, or when the user mentions
  upgrading, updating or bumping a library, package, lockfile or requirements file.
```

The pattern that works: **what it does**, then *"Use when..."* followed by the
concrete words, tools and file names that signal the situation.

## Writing the body

The body loads only once the skill activates, so it can be substantial — but
every line competes for the agent's attention with the actual task.

**Write procedures, not descriptions.** "Read the changelog between the installed
and target versions" is actionable. "Changelogs are an important source of
information" is not.

**Order the steps.** An agent follows a numbered sequence far more reliably than
it infers one from prose.

**Say what not to do.** Anti-patterns are often more valuable than instructions,
because they name the shortcut the agent would otherwise take. `--force` to make
an install succeed, `try/except: pass` to make an error stop, a null check
without knowing why the value is null — those are the failures worth naming.

**Give a stopping condition.** Say when the agent should stop and ask rather than
guess. Without it, an agent presses on through an ambiguity it should have raised.

**Provide the output shape.** A report template makes results consistent enough
to compare across runs.

**Encode judgement, not syntax.** The model already knows `git` and `npm`
commands. What it lacks is your team's sequencing, thresholds and hard rules —
"the migration and the deploy are separate events" is knowledge; `ALTER TABLE`
syntax is not.

## Keep it short

Target under 500 lines. When a skill grows past that, move detail into
`references/` and link to it — the agent loads those files only when the task
needs them, which is the point of progressive disclosure.

```markdown
For engine-specific lock behaviour see [references/locking.md](references/locking.md).
```

Keep references one level deep. Chains of files that reference further files
tend not to get followed.

## Scope

One skill, one job. A skill named `code-stuff` that reviews, refactors, tests and
deploys will be loaded for all four and be mediocre at each, because its
description cannot describe a clear trigger.

If you cannot write the description without using "and" three times, it is more
than one skill.

## Before opening a pull request

```bash
python scripts/validate_skills.py --strict
pytest
```

Then actually use it. Install the skill, give the agent a real task it should
apply to, and check that it (a) activates without being told to and (b) changes
what the agent does. A skill that never triggers, or that produces the same
result as no skill at all, is not finished.
