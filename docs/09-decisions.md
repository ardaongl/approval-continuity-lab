# Decision records

All decisions below refine the user-approved discovery direction at spec time; no new production guarantee is introduced.

## ADR-001 — one local atomic effect
Accepted: SQLite store plus simulated service in the same transaction, modular monolith. Reject external deployment adapters/gateway infrastructure. Rationale: independently testable consumption/effect/result atomicity without a distributed exactly-once claim.

## ADR-002 — immutable proposal plus immutable decision
Accepted: P/R fixed at creation; approval D later binds review digests, reviewer/time/expiry. Lifecycle mutable separately. Resolves the impossibility of including a future decision time inside an already-reviewed immutable hash. No circular/self-referential digest.

## ADR-003 — strict executable equality
Accepted: one effectful step, no semantic equivalence, no alias artifacts, no plan-reuse inference. Bound revision/content changes require new proposal. Cosmetic annotation is untrusted/excluded and never executable. Extra-step reorder cases are rejected on cardinality; they are not silently removed from D02.

## ADR-004 — trusted injected clock and durable floor
Accepted: explicit logical --now-ms, no system-clock default; durable floor advances only on committed observation; clock regression denies new operations. Final-check validity while writer lock held, not wall time at commit. Lost uncommitted observations and dishonest clocks are outside the guarantee.

## ADR-005 — historical idempotent retrieval
Accepted: own identical committed execution retrieves stored result before current authorization/clock checks; identity/integrity/equality still checked. Historical receipt is not renewed authority. Distinguish submitted mismatch (keep live grant) from authoritative drift (supersede).

## ADR-006 — rollback journal and observable process faults
Accepted: BEGIN IMMEDIATE, DELETE journal/FULL sync, no side connections around effect, no-op observer seam. Fixed barrier notifications permit real SIGKILL/SIGINT tests. CLI has no failpoint switch; workers use same mediator. No test-only fast path changes semantics.

## ADR-007 — schema and toolchain scope
Accepted: CPython3.12.14 observed in bundled runtime, SQLite≥3.35, macOS/Linux POSIX, stdlib runtime/tests. Default shell3.9.6 is not the implementation target. Future pinned build tools use observed pip26.2.1/setuptools84.0.0/wheel0.48.0. Preflight must verify availability without assumptions or unapproved installation.

## ADR-008 — documentation and educational modes
Accepted: preserve discovery unchanged; spec assets are original declarative fixtures/goldens, not product code. Naive and outside examples are fixed scenario-only experiments, not vendor claims or supported live adapters. Package a self-contained metadata README plus bundled documentation with preserved links.

## ADR-009 — safety of delivery versus validity
Accepted: stdout precheck avoids obvious preclosed-channel mutations; true output failure can still occur after commit and must require identity reconciliation. SIGINT cancellation flag is checked before COMMIT; a signal during COMMIT cannot imply rollback. Do not rerun effects with a new identity after unknown delivery/outcome.
