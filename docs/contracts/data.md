# SQLite data and durability (normative)

## Initialization and versioning

Single local SQLite file, application_id=0x41434C31, user_version=1. Use SQLite ≥3.35.0, journal_mode=DELETE, synchronous=FULL, foreign_keys=ON, busy_timeout=2000 ms and cache_spill=OFF on every connection; isolation_level=None and explicit BEGIN IMMEDIATE. Reject another application_id, version, missing required tables/columns or inconsistent loaded records as DATABASE_VERSION/STATE_CORRUPT. No automatic migration, recovery by deletion or recreation. init validates config fully before creating; use exclusive file creation to avoid races, initialize schema/config in one transaction; proven precommit/rolled-back init failure removes only the file this invocation created, never an existing file. After a known commit or an uncertain COMMIT outcome, preserve the database/journal for inspection/recovery even if response delivery fails. An empty existing file is STATE_EXISTS. Path parent must exist; resolve once, reject symlink DB path, do not create parents. Runtime may use standard SQLite journal sidecars.

Config schema: {schema_version:1,actors:[...],contexts:[...],tools:[...],policies:[...],eligibility:[...],services:[...]}. Exact row fields match the table definitions below except metadata/derived keys. No duplicate IDs/keys, invalid FK/roles or missing tool/policy dependencies; eligibility entries must refer to existing tenant policy/reviewer but need not exist for every reviewer/context until nominated. Initial revisions are positive supplied integers; no implicit seed/default data. Exactly one tool row deploy_artifact is required. No proposals/decisions/executions can be seeded. All tables initially within limits. init uses CLI now_ms as initial time floor. Config canonical values are trusted operator assertions.

## Table contract

Notation: ID = bounded ASCII identifier, INT = bounded safe integer, REV = positive INT, JSON = exact canonical JSON TEXT. All fields NOT NULL unless "nullable". FK references enforced; roles and application invariants checked before writes and on loaded rows. Keys are global within their table, not caller-defined namespaces. No automatic SQL row ID exposed publicly. ID/text/JSON/digest columns use SQLite TEXT with typeof checks; INT/REV/booleans use INTEGER with typeof, bounds and 0/1 checks. Status reasons allow only the state/time codes. ON DELETE RESTRICT applies to all FKs. No extra application tables or columns in schema1. All SQL values are parameterized; table identifiers are fixed by code. Init maps JSON booleans to INTEGER0/1 only after strict boolean type validation.

| Table | Fields and keys |
| --- | --- |
| meta | singleton=1 primary key; schema_version=1; observed_time_floor_ms INT |
| actors | actor_id ID primary key; role enum operator/agent/reviewer |
| contexts | context_id ID primary key; requester_id FK actors(agent); agent_id ID; run_id ID; tenant ID; environment ID; executor_id ID; revision REV |
| tools | tool_id primary key fixed deploy_artifact; revision REV |
| policies | tenant ID primary key; revision REV; enabled integer 0/1 |
| eligibility | (tenant,reviewer_id FK actors(reviewer)) composite primary key; revision REV; allowed integer 0/1 |
| services | service_id ID primary key; tenant ID; environment ID; display_name text; artifact_digest text; revision REV |
| proposals | proposal_id ID primary key; request_id ID UNIQUE; context_id FK; reviewer_id FK; target_service_id FK; canonical_proposal JSON; proposal_digest hex; canonical_review JSON; review_digest hex; submission_json JSON; description text; status enum; status_reason enum/null; replacement_id FK proposals nullable; status_at_ms INT |
| decisions | approval_id ID primary key; proposal_id FK UNIQUE; canonical_decision JSON; decision_digest hex; submission_json JSON; reviewer_id FK; decided_at_ms INT; expires_at_ms INT nullable |
| executions | execution_id ID primary key; approval_id FK decisions UNIQUE; proposal_id FK; requester_id FK; context_id FK; request_json JSON; request_digest hex; result_json JSON; authorized_at_ms INT; before_revision REV; after_revision REV |
| transitions | (proposal_id FK,sequence REV) composite primary key; from_status nullable; to_status enum; reason enum/null; at_ms INT |

Decision outcome is stored in canonical_decision and checked against null expiry. Denormalized columns must equal canonical contents. Decision rows and canonical proposal/review/submission/description are immutable. Context identity and service IDs/tenant/environment never mutate or delete in v1; admin updates can change only specified fields below. All history is retained. No delete/prune command.

Store must enforce at least uniqueness, enum values, nonnegative time, positive revisions, FK and immutable proposal/decision/execution contents through SQL constraints/triggers; JSON shape/digest/cross-table invariants are also mediator/store validation. Consumed requires exactly one approve decision and execution; execution must reference that proposal/approval, after_revision=before_revision+1 and fixed result values. During execute the temporary in-transaction order may be update service → insert execution → update proposal; validate all invariants before commit. No other connection can observe this intermediate state. status transitions append one transition row, including initial null→pending; sequence is per-proposal previous sequence+1 within transaction. No AUTOINCREMENT identity or nondeterministic SQL time.

## Admin mutation surface

operator-only admin-update body is one of:
- {schema_version:1,kind:"service",id,expected_revision,changes:{artifact_digest}}
- {schema_version:1,kind:"context",id,expected_revision,changes:{executor_id}}
- {schema_version:1,kind:"tool",id:"deploy_artifact",expected_revision,changes:{}} (explicit implementation-revision bump).
- {schema_version:1,kind:"policy",id:tenant,expected_revision,changes:{enabled:boolean}}
- {schema_version:1,kind:"eligibility",id:tenant,reviewer_id,expected_revision,changes:{allowed:boolean}}.

Each increments its revision by one even if content restored/unchanged. Expected mismatch → REVISION_CONFLICT; missing row → NOT_FOUND. No arbitrary SQL, deletes, identity edits, extra change keys, display-name edits, revision resets or upserts. Context identity changes are modeled by another preseeded context, not mutating IDs. Mutations do not eagerly scan proposals; affected live proposals reconcile lazily. Duplicate admin invocations with old expected_revision conflict, not apply twice.

## Transactions and denial durability

All DB commands acquire BEGIN IMMEDIATE, validate loaded state, resolve caller, perform command rules, snapshot the report data and COMMIT. Input validation/stream checks happen first; errors opening/acquiring/checking schema cannot modify protected state. Domain denials after valid time observation may commit time-floor advance and lazy expiry/supersession, but never consumption/deployment/execution rows. Infrastructure errors roll back the entire transaction.

New execution: load submitted approval/proposal → identity/replay handling → observe clock → expiry/drift/state/binding checks → compare service expected_revision → conditional service update (affected rows must be 1) → insert result/execution → mark consumed/transition → consistency checks → COMMIT. No commits, separate connection or callback-driven writes between check and effect. This is the proof obligation: all three effects have one SQLite transaction commit record; crash-before-commit rolls all back; commit exposes all three together. Independent raw-SQL oracles and crash tests must establish this in implementation, not merely code comments.

Read commands may commit floor/lifecycle maintenance, as stated in [state/time](state-time.md). There is no read-only "current status" command that pretends stale stored status is fresh. Historical execution lookup never reauthorizes effects.

## Resource bounds and recovery

Limits: input 65,536 bytes; depth 16; 256 rows each actors/contexts/policies/eligibility/services, exactly one tool; 1,000 proposals/decisions/executions each; 8 transitions per proposal; report ≤1,048,576 bytes; pending/grant periods ≤86,400,000 ms; revisions/times ≤9,007,199,254,740,991. Reject additions/increments exceeding limits with LIMIT_EXCEEDED before any protected mutation. No unbounded list output (only scenario catalog, max 14); inspect is by ID. No maximum DB file-byte or universal memory/CPU promise; page cache and Python runtime excluded. No unbounded retries.

Crash recovery uses normal SQLite rollback-journal recovery on open. Never delete a hot journal. After restart load durable status/result/floor, validate invariants, then reconcile only the selected live proposal at command time. Power loss, malicious file edits, unsupported locks and hardware corruption are outside guarantee. A database error/corrupt loaded record is STATE_CORRUPT or STORAGE_ERROR; no cached approve path.
