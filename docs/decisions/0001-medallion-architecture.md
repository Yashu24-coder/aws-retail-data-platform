# 0001 - Three layers instead of one

**Status:** accepted

## Context

The source exports are dirty in predictable ways: two date formats, eleven
status spellings, duplicate rows, blank join keys. Analysts need a clean,
stable model. Two forces conflict - cleaning must be reproducible, and the raw
truth must remain available when a cleaning rule turns out to be wrong.

## Decision

Keep three physical layers:

- **Bronze** - exactly what arrived, all `VARCHAR`, plus `_ingest_ts`.
- **Silver** - typed, de-duplicated, one row per entity, no business logic.
- **Gold** - star schema and marts, business logic only.

## Consequences

Rebuilding gold never re-reads the source, so a logic change costs minutes.
When a cleaning rule is wrong, bronze still holds the original bytes, so silver
can be replayed without asking the source team for a re-export. The cost is
storage: bronze keeps data at full fidelity, which is why the raw bucket expires
objects after 400 days instead of forever.
