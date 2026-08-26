---
name: review-database-migration
description: Review a database schema migration for locking, data loss, backfill and rollback risk before it runs against a production table. Use when a change adds, alters, renames or drops a column, table, index or constraint, when reviewing an Alembic, Django, Rails, Prisma, Knex, Flyway or Liquibase migration, or when the user mentions a schema change, migration, backfill or ALTER TABLE.
license: MIT
compatibility: Lock behaviour described is PostgreSQL-specific; verify against your engine and version
---

# Review a database migration

A migration that passes review on a laptop with 40 rows can take a production
table offline for twenty minutes. Almost every migration incident comes from one
of four causes: an unexpected lock, an unshipped code path, an unbatched
backfill, or a change that cannot be undone.

Review for those four. Everything else is style.

## The rule that prevents most incidents

**The migration and the deploy are separate events, and you do not control the
order.** During the window between them, old application code runs against the
new schema — and if you roll back, new code runs against the old schema.

So every migration must satisfy: *the currently-deployed code keeps working after
this runs.* A change that cannot satisfy that must be split into stages
(expand → migrate → contract), each shipped separately.

This single rule catches renames, drops and `NOT NULL` additions before they
cause an outage.

## Operation checklist

### Adding a column

- Nullable, no default → safe, metadata-only.
- With a constant default → safe on **PostgreSQL 11+** (stored in the catalogue,
  no table rewrite). On older versions this rewrites the whole table.
- With a **volatile** default (`now()`, `random()`, `uuid_generate_v4()`) → full
  table rewrite, holding an exclusive lock. Add the column nullable, backfill in
  batches, then set the default.
- `NOT NULL` on a table with existing rows → fails outright unless a default is
  supplied. Use the three-step form: add nullable, backfill, add the constraint.

### Dropping a column

Fast at the database level — but it breaks any running code that still selects
it, including an `ORM SELECT *`. Requires the contract stage of expand/contract:
ship code that no longer references the column, confirm it is deployed
everywhere, then drop.

Check for anything the drop takes with it: indexes, constraints, views, triggers,
and downstream consumers such as analytics pipelines or replicas.

### Renaming a column or table

**Never in one migration.** A rename breaks every running instance the instant it
commits. Expand and contract:

1. Add the new column
2. Write to both, read from the old
3. Backfill the new column
4. Read from the new
5. Stop writing to the old
6. Drop the old

Each numbered step is a separate deploy. If the reviewer sees a bare
`RENAME COLUMN`, that is a blocker.

### Adding an index

- `CREATE INDEX` takes an exclusive lock for the duration of the build. On a
  large table this is the outage.
- `CREATE INDEX CONCURRENTLY` avoids it, but **cannot run inside a transaction**,
  and most migration frameworks wrap migrations in one. Alembic, Django and Rails
  each have a specific escape hatch — confirm the migration uses it.
- A failed concurrent build leaves an `INVALID` index behind that must be dropped
  manually before retrying. Check the rollback path accounts for this.

### Changing a column type

Safe widenings (`int` → `bigint` is **not** one of them on PostgreSQL; `varchar(n)`
→ `text` is) avoid a rewrite. Most other changes rewrite the table under an
exclusive lock.

For a large table, the safe form is a new column plus a backfill plus a swap —
the same expand/contract shape as a rename.

### Adding a constraint or foreign key

Validating a constraint scans the whole table while holding a lock. Split it:

```sql
ALTER TABLE orders ADD CONSTRAINT fk_customer
  FOREIGN KEY (customer_id) REFERENCES customers(id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT fk_customer;
```

The first statement is fast and applies to new rows. The second scans without
blocking writes.

## Locking

On PostgreSQL, a blocked `ACCESS EXCLUSIVE` lock does not wait politely — it
queues, and **every query arriving behind it also queues**. A migration waiting
on one slow transaction can stall all traffic to that table.

Look for a lock timeout in the migration:

```sql
SET lock_timeout = '3s';
```

With a timeout, the migration fails fast and is retried. Without one, it waits
indefinitely and takes the table's traffic with it. Its absence on a
high-traffic table is a finding.

## Backfills

A backfill in the same transaction as the schema change is a red flag. A single
`UPDATE` over millions of rows holds locks, bloats the WAL and blocks
replication.

A safe backfill is:

- Batched (a few thousand rows at a time), with a commit between batches
- Idempotent and resumable — it can be re-run after being interrupted
- Run **outside** the schema migration, as a separate script or job
- Throttled, or scheduled off-peak

## Rollback

For every migration, answer: *if this is wrong, how do we undo it?*

- Reversible (add column, add index) → confirm the down migration exists and is
  correct
- **Irreversible** (drop column, drop table, destructive type change) → the data
  is gone; a down migration cannot bring it back. Say so explicitly and confirm a
  backup or an export exists first
- Frameworks that auto-generate a down migration frequently generate a wrong one.
  Read it; do not trust it

## Verdict

Give one of three, with reasons:

- **Blocked** — will cause an outage or lose data as written. Name the operation
  and the safe alternative.
- **Changes needed** — safe in principle, missing a guard such as a lock timeout,
  a batched backfill or a correct down migration.
- **Safe to ship** — state the expected lock, and on roughly what table size that
  holds.

Always state the assumed table size. "Safe" for 10,000 rows and "safe" for 200
million are different claims, and a reviewer who does not say which one they mean
has not really reviewed it.

## Do not

- Approve a bare `RENAME` or `DROP` without a preceding deploy that stopped using
  the old name
- Assume the ORM's generated migration is safe because the framework wrote it
- Let a data backfill share a transaction with a schema change
- Review only the up migration
- Treat `CREATE INDEX CONCURRENTLY` as safe without checking it escapes the
  surrounding transaction
