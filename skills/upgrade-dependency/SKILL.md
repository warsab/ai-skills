---
name: upgrade-dependency
description: Upgrade a third-party dependency safely by reading the changelog for breaking changes, finding every affected call site, updating the code, and verifying against a known-good baseline. Use when bumping a package version, applying a security or CVE patch, resolving a Dependabot or Renovate pull request, unpinning a version, or when the user mentions upgrading, updating or bumping a library, package, lockfile or requirements file.
license: MIT
metadata:
  author: warsab
  version: "1.0"
---

# Upgrade a dependency

A dependency upgrade fails in one of three ways: it does not install, it installs
but the code no longer compiles, or — the expensive one — it installs, compiles,
passes tests, and behaves differently in production. This procedure is built to
catch the third.

## Before you start

Establish that the build is green **now**. If tests already fail, you cannot tell
what the upgrade broke.

```
<test command>        # must pass before anything changes
```

If the baseline is red, stop and say so. Fixing an unrelated failure first is a
separate piece of work.

Record what you are moving between — the exact installed version, not the range
in the manifest. The manifest may say `^2.1.0` while the lockfile has `2.4.7`.

## Steps

### 1. Size the jump

Read the version numbers as the maintainer intended them:

| Jump | Expectation | Effort |
| --- | --- | --- |
| Patch (`2.4.7` → `2.4.8`) | Bug fixes only | Read the diff if it is a security fix |
| Minor (`2.4.7` → `2.5.0`) | New features, no breaks | Skim the changelog for deprecations |
| Major (`2.4.7` → `3.0.0`) | Breaking changes expected | Read the migration guide in full |

A maintainer who does not follow semver makes all three rows unreliable. Check
the changelog regardless of what the numbers imply.

### 2. Read the changelog, not the release title

Find the actual list of changes — `CHANGELOG.md` in the repository, the GitHub
releases page, or the project's migration guide. Read **every entry between the
installed version and the target**, not just the newest one. A three-version jump
carries three sets of breaking changes.

Write down each breaking change as a concrete question about this codebase:
"they renamed `Client.fetch()` to `Client.request()` — do we call `fetch`?"

### 3. Inventory the actual usage

Do not guess from the changelog which parts matter. Search the codebase for what
it genuinely uses:

- Every import of the package
- Every symbol imported from it
- Configuration files, environment variables and CLI flags the package reads

Cross-reference that inventory against the breaking changes. The intersection is
your real work list; everything else in the changelog is noise for this repo.

### 4. Apply the upgrade

Change the version in the manifest, then regenerate the lockfile with the
ecosystem's own tooling. Never hand-edit a lockfile.

| Ecosystem | Upgrade | Regenerate lock |
| --- | --- | --- |
| npm / pnpm / yarn | `npm install pkg@3.0.0` | automatic |
| pip + requirements | edit `requirements.in` | `pip-compile` |
| Poetry / uv | `poetry add pkg@^3.0.0` / `uv add` | automatic |
| Cargo | `cargo update -p pkg --precise 3.0.0` | automatic |
| Go | `go get pkg@v3.0.0` | `go mod tidy` |

**One dependency per change.** If the upgrade drags in a transitive bump that
breaks something, a single-package diff tells you which one did it. A batch of
twelve does not.

### 5. Fix what broke, at the source

Work through the compiler or test failures. For each one, apply the migration the
changelog prescribes rather than the smallest change that makes the error stop.

If the new version deprecates something without removing it yet, migrate anyway
while the context is loaded. Deprecation warnings become the next upgrade's
breaking changes.

### 6. Verify

In order, stopping at the first failure:

1. It installs from a clean lockfile
2. It builds or type-checks
3. The full test suite passes
4. The application starts and serves a real request
5. Behaviour that the changelog said changed actually behaves as documented

Step 5 is the one that catches silent breakage. If a changelog entry says default
timeouts changed from 30s to 5s, assert the new timeout somewhere — do not assume
the tests cover it.

### 7. Report

State plainly:

- Package, from-version, to-version
- Breaking changes that applied to this codebase, and what you changed for each
- Breaking changes that did **not** apply, and why
- Anything you could not verify locally
- How to roll back

## Do not

- **Force the install.** `--force`, `--legacy-peer-deps` and
  `--ignore-platform-reqs` silence a real incompatibility rather than resolving
  it. If a peer dependency conflicts, resolve the conflict or stop.
- **Widen a version range to make resolution succeed.** Changing `~2.4.0` to
  `>=2.0.0` does not fix anything; it moves the failure to whoever installs next.
- **Upgrade everything at once** because the tool offers to. Batched upgrades are
  unbisectable.
- **Skip the changelog because tests pass.** Tests cover what someone thought to
  test. Changed defaults, altered error types and new network behaviour routinely
  slip through a green suite.
- **Leave a lockfile out of the commit.** The lockfile *is* the upgrade; the
  manifest is only an intention.

## When to stop and ask

- The upgrade requires a runtime bump (Node 18 → 20, Python 3.9 → 3.11) that
  affects deployment
- The package changed licence
- The package is unmaintained or the repository is archived, and the real answer
  is to replace it
- More than a handful of call sites need rewriting — that is a migration with its
  own plan, not a version bump
