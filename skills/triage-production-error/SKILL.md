---
name: triage-production-error
description: Turn a production failure into a root cause and the smallest safe fix, with a regression test that fails before the fix and passes after. Use when given a stack trace, exception, error log, Sentry or Datadog issue, crash report or on-call alert, or when the user says something is broken, erroring, failing or throwing in production or staging.
license: MIT
---

# Triage a production error

The goal is not to make the error message disappear. It is to find the invariant
that was violated, fix that, and leave behind a test that would have caught it.

## Step 0: is it still bleeding?

Before any investigation, establish whether the failure is **ongoing**.

If it is, mitigation comes before diagnosis. Roll back the deploy, flip the
feature flag off, or scale the broken worker to zero. A correct root cause found
forty minutes into an outage is worth less than a rollback in two.

Say explicitly which you are doing: *"mitigating first, then diagnosing"* or
*"this is not ongoing, going straight to root cause"*.

## Step 1: read the trace properly

Stack traces are read from the bottom, but the useful frame is rarely the last
one.

- The **deepest frame inside a library** tells you what blew up
- The **deepest frame inside this codebase** tells you where to look first
- The **exception type** tells you the category of the violation

`KeyError: 'user_id'` in a JSON parser is not a bug in the parser. It is a
payload arriving without the field your code assumed was always present. The
question is never "why did the library throw" — it is "why did our data reach it
in that shape".

Extract before moving on: exception type, message, the deepest application frame
(file and line), and the full chain of any wrapped or `caused by` exceptions.

## Step 2: pin the blast radius

Answer these from the logs, monitoring or version control — do not guess:

| Question | Why it matters |
| --- | --- |
| When did it start? | Correlates with a deploy, a migration, a config change or a traffic pattern |
| How often? | Once is a bad payload; continuous is a broken code path |
| Which users or requests? | A single tenant points at their data, not your logic |
| Which version or host? | Narrows to a specific release or a bad node |
| Did anything ship near the start time? | The most likely cause is the most recent change |

"It started at 14:02 and a deploy landed at 14:01" is worth more than an hour of
code reading. Check that first.

## Step 3: reproduce it

A bug you cannot reproduce is a bug you cannot prove you fixed.

Write a failing test at the smallest scope that still exhibits the fault —
usually a unit test that feeds the offending input to the function containing the
deepest application frame. Use the real payload from the logs, with any personal
data replaced.

If it will not reproduce, your model of the failure is wrong. Common reasons:

- It depends on state left behind by an earlier request
- It only appears under concurrency
- It depends on the environment — timezone, locale, filesystem, clock
- It only happens with production-scale data

Each of those is a clue about the root cause, not an obstacle to it.

## Step 4: find the cause, not the symptom

Trace the bad value backwards to where it was created, not where it exploded.

For each step ask: *should this value have been possible here?* Keep going until
you reach the point where an invariant was actually broken — the place where
something was allowed to exist that should never have existed.

That is the root cause. It is usually several frames upstream of the traceback.

## Step 5: the smallest safe fix

Fix the broken invariant at the point it was broken.

Prefer, in order:

1. Prevent the bad state from being created (validate at the boundary)
2. Handle the legitimate case that was overlooked (the field really is optional —
   so treat it as optional everywhere)
3. Fail loudly and early with a message naming the offending value

Keep the fix and any refactoring in separate commits. A reviewer paged at 2am
should be able to read the fix in isolation.

## Step 6: prove it

The regression test from step 3 must now pass. Verify in this order:

1. Run the new test against the **unfixed** code — it must fail
2. Apply the fix — it must pass
3. Run the full suite — nothing else may break

A test that passes before the fix is testing something else.

## Step 7: look for siblings

The same mistake is rarely made once. Search the codebase for the same pattern:
the same unchecked access, the same assumption about the same payload, the same
missing timeout. Report what you find even if you do not fix it here.

## Do not

- **Wrap it in a catch to make it stop.** `try/except: pass` around the symptom
  converts a loud failure into silent data corruption.
- **Catch broadly.** `except Exception` / `catch (e)` around the failing call
  hides the next, different bug too.
- **Add a null check without knowing why it is null.** If you cannot say what
  produced the null, the guard is a guess and the real fault is still live.
- **Fix it in the trace's last frame** just because that is where the line number
  points.
- **Widen a type or loosen a schema** to accommodate bad data, unless you have
  established the data is genuinely valid.
- **Claim it is fixed without a failing-then-passing test.**

## Report format

```
Symptom     : <exception type and message, where it surfaced>
Started     : <time, and what changed near it>
Impact      : <frequency, users or requests affected>
Root cause  : <the invariant that was violated, and where>
Fix         : <what changed, and why at that layer>
Test        : <the regression test, confirmed failing before the fix>
Siblings    : <same pattern found elsewhere, or "none found">
Follow-up   : <anything deliberately left undone>
```

## When to stop and ask

- The root cause is data corruption that has already been written and needs a
  backfill decision
- The fix requires a schema change or a migration
- The correct behaviour is genuinely ambiguous — a product decision, not a bug
- The trace points into a third-party service you cannot see into
