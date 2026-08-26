# Contributing

## The bar for a new skill

**Would you use this in your job next week?**

A skill costs context at startup for every session, whether or not it is used —
the agent loads every skill's name and description just to know what exists. A
skill that reads impressively but never triggers is a permanent tax with no
return.

Concretely, a skill earns its place when it:

- Encodes a procedure people get wrong under pressure, not one the model already
  performs well
- Captures **judgement** — sequencing, thresholds, hard rules — rather than
  syntax the model already knows
- Has a trigger you can state in one sentence using words a user would actually
  type
- Does one job. If the description needs three "and"s, it is more than one skill

Things that generally do not clear the bar: wrappers around a single shell
command, restatements of a tool's own documentation, and style guides that belong
in a linter.

## Adding one

1. Create `skills/<skill-name>/SKILL.md`. The directory name is the skill name:
   lowercase, hyphens, no underscores.

2. Write the frontmatter. Only these six fields are allowed — anything else
   breaks portability and fails validation:

   ```yaml
   ---
   name: <must match the directory name>
   description: <what it does. Use when <the triggers a user would type>.>
   license: MIT
   ---
   ```

3. Write the body. [docs/writing-skills.md](docs/writing-skills.md) covers what
   works: numbered steps, explicit anti-patterns, a stopping condition, and an
   output template. Keep it under 500 lines and move detail into `references/`.

4. Validate and test:

   ```bash
   pip install -r requirements-dev.txt
   python scripts/validate_skills.py --strict
   pytest
   ```

5. **Actually use it.** Install it, give an agent a real task it should apply to,
   and confirm it activates on its own and changes the outcome. Say in the pull
   request what you tested it against.

## Editing an existing skill

Prefer sharpening what is there to adding sections. If a step was skipped or
misread in practice, that is usually a wording problem, not a missing step.

When you change a `description`, re-check that the triggers still match how
people phrase the request — that line decides whether the skill ever runs.

## Style

- Second person, imperative: "Read the changelog", not "The changelog should be
  read"
- Concrete over general: name the flag, the command, the failure
- No filler. Every line either changes what the agent does or should be cut
- British or American spelling, consistently within a file

## Python code

`scripts/` follows the repository's ruff config: type hints, Google-style
docstrings, 90-column lines.

```bash
ruff check .
ruff format .
```

New behaviour in a script needs a test in `tests/`.

## Pull requests

Include:

- What the skill does and when it triggers
- What you tested it against, and what the agent did differently with it
- For an edit: what went wrong without the change
