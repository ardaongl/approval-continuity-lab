# Normative contract index

Application 0.1.0; input/report/database schema 1. Each rule has one owner:

| Document | Owns |
| --- | --- |
| [Binding](contracts/binding.md) | Inputs, immutable envelopes, normalization, review bytes |
| [State/time](contracts/state-time.md) | Transitions, time floor, precedence, replay |
| [Data](contracts/data.md) | SQLite schema, constraints, transactions, limits |
| [Concurrency/recovery](contracts/concurrency-recovery.md) | Process schedules, crash points, linearization |
| [CLI/reporting](contracts/cli-reporting.md) | Commands, schemas, output, exits, faults |
| [Trust](contracts/trust.md) | Guarantees, limitations and demo separation |
| [Acceptance](04-acceptance.md) / [fixtures](05-fixtures.md) | Observable requirements and independent expected data |
| [Test plan](06-test-plan.md) | Required verification methods |

All listed object fields are exact: required unless explicitly optional; no unknown keys, nulls, unsupported versions or implicit defaults. Schemas/pseudocode in docs are specifications, not product implementation.

Planned Python facade: Lab.open(path, clock, observer=None, cancellation=None) returns a context manager. Methods initialize(config,caller), propose(command,caller), review(proposal_id,caller), decide(command,caller), execute(command,caller), revoke(command,caller), inspect(kind,id,caller), admin_update(command,caller) return the same report values as CLI. Lab.open alone never creates a DB. Arguments are validated schema-1 mappings. Caller is {actor_id,context_id}; context_id is null for reviewer/operator. Clock.now_ms() returns int. Observer.reached(point) returns None; optional Cancellation.is_cancelled() returns boolean and defaults false. Methods perform no stdout/stderr IO. Domain/input/storage errors return classified reports; invalid facade construction raises ValueError before IO; observer runtime failure becomes INTERNAL_ERROR with rollback before commit or effect_status committed plus stored result after a known commit, never a domain allow. No framework SDK compatibility promise.

Only init creates absent DB; others require mode=rw. Existing DB init returns STATE_EXISTS, never overwrites. Unsupported input schema → UNSUPPORTED_VERSION; unsupported database → DATABASE_VERSION. No migrations in v0.1.

Invariants: I1 immutable reviewed bytes; I2 fresh trusted context; I3 fixed deadlines/durable nondecreasing floor; I4 at most one effect per approval; I5 consumption/effect/result atomic; I6 target check/update serialized; I7 no grant revival; I8 no external-effect claim; I9 deterministic explicit schedules; I10 neither hash nor opaque ID authenticates.
