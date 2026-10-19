# Architecture

Python modular monolith: package approval_continuity_lab, installed command acl, equivalent python -m approval_continuity_lab. Imports perform no application-controlled file/database/process/clock/network IO.

| Planned module | Owns | Dependency boundary |
| --- | --- | --- |
| validation | Bounded strict JSON and types | stdlib; no state |
| canonical | Canonical bytes and digests | validated values; no IO |
| models | Command/result records and enums | no IO/global mutable state |
| review | Stored proposal → trusted review object/text | never agent description as authority |
| store | Connections, schema, SQL and transactions | sole SQL issuer |
| mediator | Identity, lifecycle, time, replay | injected Clock/Observer; store/review/canonical |
| deployment | Target precondition and simulated update | caller transaction; no independent commit |
| report | Pure JSON/text serialization | immutable snapshot; no database reads |
| cli / __main__ | Parsing, input, streams, signals, exits | dispatch only; no duplicate approval rules |
| scenarios / scenario_worker | Fixed D01–D14 schedules and subprocess barriers | same mediator/connections as CLI |
| naive | Explicit unsafe D13 experiment | scenario-only; unreachable through execute |

Flow: bounded input → validated command → mediator/authoritative transaction → immutable report snapshot → commit → output. No progress output inside transactions. Output failure after commit does not mean rollback.

SQLite owns roles, contexts, tool/policy/eligibility revisions, target identity/revision, proposals, decisions, grants and committed executions. Caller IDs select records; they do not authenticate. --actor/--context are trusted local assertions.

Fresh connection per command; no inherited fork connections or pool. Local filesystem with POSIX locks only. Journal DELETE, synchronous FULL, foreign_keys ON, busy_timeout 2000 ms, cache_spill OFF; explicit BEGIN IMMEDIATE. Even inspection may reconcile lifecycle and therefore uses a writer transaction. See [data](contracts/data.md).

Clock sampled once after lock acquisition for new operations; final authorization, version comparisons and effect happen within that lock. Default observer is a no-op. Fixed observer points allow external crash/barrier tests without replacing checks; see [recovery](contracts/concurrency-recovery.md).

Rejected: stateless token-only control cannot enforce revocation/consumption itself; live targets break local atomicity; HTTP gateways add deployment/authentication scope. No distributed infrastructure.

Scenario IDs, logical times and participant ordering are explicit. Reports exclude PIDs, temp paths, durations, random IDs and observed scheduler order. Stress tests may vary winners but assert invariants. No external scenario code is executed.
