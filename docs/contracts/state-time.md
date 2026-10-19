# State, time, errors and idempotency (normative)

## Identity and immutable history

Actors have immutable seeded roles. Owning agent means Caller.actor_id=P.requester_id, Caller.context_id=P.context_id, and that context's requester matches the actor. Reviewer means exact P.reviewer_id and reviewer role. Operator means operator role and null context. Agent-only propose/execute; reviewer-only decide; approved revocation by designated reviewer or operator. review/inspect permit owning agent, designated reviewer or operator for the selected object. Context_id must be null for non-agent actors. --actor is a lab assertion, not authentication.

A different valid agent/context cannot inspect, mutate, consume or retrieve another context's result merely by ID. Caller identity is checked before revealing history. Current *revision* or eligibility drift does not block an authorized historical result lookup; identity checks still apply.

## Persisted states

status on proposals is the lifecycle source of truth, with transitions persisted transactionally. Decision envelope is immutable history, not current permission. Expiry/drift reconciliation is lazy, subject-specific and persisted when a command examines a live proposal. A raw DB row may remain approved past expiry until reconciliation; it never authorizes an effect without fresh checks. After restart load durable state and floor, then reconcile before a new decision/execution/review/inspect/revoke. No background timer or automatic startup sweep.

| From | Legal next states / trigger |
| --- | --- |
| absent | pending: valid creation |
| pending | approved: approve decision; rejected: reject decision; expired: pending deadline reached; superseded: authoritative drift or explicit replacement |
| approved | consumed: atomic successful execution; revoked: valid revoke; expired: grant expiry reached; superseded: authoritative drift or replacement |
| rejected / consumed / revoked / expired / superseded | no new lifecycle transition |

Exact idempotent retrieval and repeated revoke are no-op operations, not transitions. Pending cannot be revoked (APPROVAL_PENDING); no consumed/rejected/expired grant can be revoked retroactively. Each transition appends one history row with observed logical time. status_reason is null for pending/approved/consumed/revoked, REVIEW_REJECTED for rejected, PENDING_EXPIRED or GRANT_EXPIRED for expired, and a drift code or REPLACED for superseded. Once terminal, it never revives, even if revisions/content/time are restored. Replaced superseded proposal may acquire replacement_id only once, without status transition.

Approved expiry derives from decision time, not creation time; it may extend beyond the former pending deadline. Only pending uses that deadline. Reviewer rejection consumes no grant and creates no execution. A different decision after any decision exists is INVALID_STATE.

## Trusted logical time

CLI requires --now-ms for every DB command (including init/inspect); there is no wall-clock default or environment override. Lab API accepts injected Clock.now_ms(). One integer sample is taken after BEGIN IMMEDIATE, caller/record checks and historical-retry detection, immediately before lifecycle/authorization comparisons. All compared current records are held under that writer lock; comparisons/effect are synchronous with no other clock read or released lock. This is the final authorization-check time, not a promise about wall time at COMMIT.

On a new command, if sampled time < persisted meta.observed_time_floor_ms: CLOCK_REGRESSION, rollback, no expiry/drift/status/effect/floor updates. Equality is allowed. Otherwise advance floor to sample in the same transaction; domain denials may commit this floor/maintenance, infrastructure failures roll it back. If a process dies before commit, that uncommitted observation is not durable. Guarantee is monotonic **durably committed** observations, not knowledge of all clock readings before crashes.

Pending expires at now >= pending_deadline_ms. Approved expires at now >= expires_at_ms. Equality denies. All times and additions obey safe integer bounds. Large forward jumps can permanently expire a grant; no time-reset command. Restart preserves the floor. Trusted operator/clock can lie; no global/fault-resistant time claim. After the authorization check a transaction may commit when wall time is later than expiry; validity is defined at that check while the lock is held. Tests explicitly demonstrate this distinction.

Historical exact retry of propose/decide/execute and inspection of execution may retrieve stored history without sampling the clock, changing floor, expiry or any binding. Report observed_at_ms is null, replayed=true for retries, status=null for propose/decide historical retrieval and consumed for execution. This retrieval grants no new authority and is allowed despite later expiry, revocation attempt, policy/eligibility/context/target drift or backward time. Actor/ownership checks, strict input equality, schema/integrity and output limits still apply.

## Reconciliation order and execution denial

For a nonterminal selected proposal, after valid time: expire first; else supersede on first authoritative mismatch in this order:
1. context revision or any bound current context identity (CONTEXT_CHANGED);
2. tool revision (TOOL_CHANGED);
3. tenant policy revision or enabled=false (POLICY_CHANGED);
4. reviewer eligibility revision or allowed=false (REVIEWER_CHANGED);
5. service immutable scope/ID or expected revision/prior artifact (TARGET_REVISION_CHANGED).

Missing required authoritative rows mean STATE_CORRUPT, not a normal revision change. Service substitution in submitted intent is BINDING_MISMATCH; a persisted target's higher revision is TARGET_REVISION_CHANGED. A live proposal is superseded even if a submitted attempt also has mismatching fields; this is authoritative drift, not approval mutation by the caller.

Submitted BINDING_MISMATCH alone leaves status approved and records no execution/transition; only floor may advance. Correct subsequent intent can still execute before expiry. Pending execution → APPROVAL_PENDING; consumed with another execution ID → APPROVAL_CONSUMED; revoked → APPROVAL_REVOKED; rejected → REVIEW_REJECTED; expired → persisted expiry reason; superseded → persisted drift/replacement reason. Repeated revoke of revoked returns OK/no transition after time observation; consumed revoke → TOO_LATE; other terminal revoke → INVALID_STATE. inspect/review return OK with reconciled lifecycle rather than returning a refusal solely for terminal status. decide/revoke/execute enforce their action's state.

## Total precedence

A command returns exactly one primary code. No best-effort operation after a failure. Order:
1. Minimal launch handling: --help/--version; otherwise required stdout availability check (OUTPUT_IO outranks product validation). CLI syntax/limits/strict JSON/version/type failures are INPUT_INVALID, INPUT_LIMIT or UNSUPPORTED_VERSION, in sorted canonical JSON-pointer path order. Type/shape failures precede semantic cross-field failures.
2. Open/init path and schema/integrity errors; acquire lock within bound (STORAGE_BUSY on timeout). IO exceptions mapped by classification, never to allow. Integrity checking is for loaded records/required schema, not a whole-file per-command cryptographic proof.
3. Actor role and caller context validity (ROLE_FORBIDDEN / CALLER_MISMATCH); selected record existence (NOT_FOUND); object ownership (CALLER_MISMATCH). Invalid/unknown actor → ROLE_FORBIDDEN.
4. Existing idempotency key: compare canonical full submitted request and original identity. Equal → historical response; unequal → IDEMPOTENCY_CONFLICT. For an unclaimed execution ID and already-consumed grant → APPROVAL_CONSUMED after time check, below. Wrong review_digest on a *new* decision → BINDING_MISMATCH after lifecycle reconciliation.
5. Sample/validate clock (CLOCK_REGRESSION or INPUT_INVALID for invalid injected type; overflow LIMIT_EXCEEDED).
6. Reconcile expiry then authoritative drift in order above; evaluate legal action/state. New propose validates enabled policy/eligible reviewer/target scope under this step (POLICY_DISABLED, REVIEWER_INELIGIBLE, TARGET_SCOPE_MISMATCH).
7. Compare submitted digest/review/intent fields (BINDING_MISMATCH); validate replacement-state and target expected revision; enforce row/integer limits (LIMIT_EXCEEDED). For admin stale expected revision use REVISION_CONFLICT.
8. Apply effect and consistency checks; commit; format/output. Any infrastructure error rolls back if not committed; failure during COMMIT returns STORAGE_ERROR with effect_status=unknown, and same execution identity must be reconciled. No new ID retry.
9. Output failure after computation overrides process exit with OUTPUT_IO, but does not rewrite the committed report/result. SIGINT handling in process contract overrides normal exit; a pending signal never creates extra effects.

STATE_EXISTS, DATABASE_VERSION, STATE_CORRUPT, STORAGE_ERROR are storage-class errors. Unexpected application exceptions → INTERNAL_ERROR (no raw traceback); observer failure → INTERNAL_ERROR with rollback unless after commit. Details for an error expose at most the selected authorized object's mismatches; no secret/other-owner data or SQLite exception/path strings.

## Idempotency and stored results

propose: unique request_id and proposal_id. Store C(submission) and caller identity. An exact existing request/proposal pair returns stored P/R; either ID reused inconsistently → IDEMPOTENCY_CONFLICT. A new proposal has new IDs; never rewrite an old one.

decide: unique approval_id and one decision per proposal. Exact request/identity returns original D with original expiry. Different approval_id for decided proposal → INVALID_STATE; same approval_id for different data → IDEMPOTENCY_CONFLICT.

execute: execution_id globally unique; approval_id unique in executions. C(full execution request including original caller IDs) must match on retry, not only hash. A committed identical retry returns stored result_json, authorized_at_ms and before/after revisions, code OK, outcome committed, replayed=true. Never compare current eligibility/expiry/target before this historical retrieval. Different payload under the same execution_id → IDEMPOTENCY_CONFLICT. Different execution_id with consumed approval → APPROVAL_CONSUMED. Denied attempts do not reserve execution IDs. Full operation response differs only in replayed/observed_at_ms between original and retry; data.result is byte-identical canonical stored content.

Committed result is exactly {approval_id,execution_id,proposal_id,service_id,tenant,environment,artifact_digest,before_revision,after_revision,authorized_at_ms}, all from the reviewed intent/current transaction. Result does not include delivery time or later status. No global exactly-once execution claim: at-most-one committed simulated effect per approval, with repeatable retrieval of its committed result.

revoke has no separate request ID; revoked is idempotent, consumed is TOO_LATE. admin-update is revision-CAS only; failed old revision retries never apply twice. No generalized workflow idempotency layer.

## Action-specific state outcomes

The following applies after schema/identity/idempotency/time precedence. A newly requested decision for a proposal that already has a decision returns INVALID_STATE at key/uniqueness handling before time; exact same approval key remains historical retrieval.

| Action | pending | approved | rejected | consumed | revoked | expired | superseded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| new decide approve/reject | corresponding transition | INVALID_STATE | INVALID_STATE | INVALID_STATE | INVALID_STATE | persisted expiry code | persisted supersession code |
| new execute ID | APPROVAL_PENDING | validate binding and commit | REVIEW_REJECTED | APPROVAL_CONSUMED | APPROVAL_REVOKED | persisted expiry code | persisted supersession code |
| revoke by proposal ID | APPROVAL_PENDING | revoked/OK | INVALID_STATE | TOO_LATE | OK/changed=false | INVALID_STATE | INVALID_STATE |
| review/inspect | OK with reconciled current state in all columns | OK | OK | OK | OK | OK | OK |
| explicit replacement | superseded + create pending | superseded + create pending | INVALID_STATE | INVALID_STATE | INVALID_STATE | INVALID_STATE | create pending/link only if no replacement_id |

New execute with missing approval_id returns NOT_FOUND before lifecycle lookup; to observe APPROVAL_PENDING use inspect or revoke (a pending proposal has no approval decision). A structurally valid approve decision is the only way to create an executable grant. This distinction prevents inventing an approval ID for pending state. Pending-execution denial is a library state-machine test; no nonexistent decision is accepted in the public DB API. Tests must assert NOT_FOUND for an arbitrary pending approval ID and APPROVAL_PENDING for revoke of pending proposal.

New propose returns pending only after all creation bindings/eligibility/scope/deadline/replacement checks pass atomically. Replacement target must share context, have no replacement already, and not introduce cycles; new IDs cannot be old IDs and new node has no descendants. Otherwise INVALID_STATE, CALLER_MISMATCH (replacement target not owned in the selected context), or IDEMPOTENCY_CONFLICT (ID reuse), according to preceding rules. Replacement lookup/ownership is evaluated with the other selected-record checks before key/time handling.

Approve/reject for a live proposal that reconciles to expired/superseded returns that new persisted reason with no decision. Existing terminal rejection/consumption/revocation with a valid decision has earlier uniqueness handling. Live state changes caused by authoritative reconciliation are committed even when the submitted intent also mismatches. Input/ownership/clock failures before reconciliation cannot cause them.

Creation edge classification: unknown caller context or body/context mismatch is CALLER_MISMATCH; unknown requested service or replacement proposal is NOT_FOUND; an existing service in another tenant/environment is TARGET_SCOPE_MISMATCH; unknown/non-reviewer nominated reviewer or missing/disallowed nominated eligibility is REVIEWER_INELIGIBLE. Init requires context policies and the sole tool, but eligibility entries are optional until a reviewer is nominated. A missing policy/tool for an already seeded context or missing bound eligibility for an existing proposal is STATE_CORRUPT. A new pending deadline not strictly after creation time or more than one day later is INPUT_INVALID. Expected-revision overflow on admin or approval-expiry arithmetic overflow is LIMIT_EXCEEDED. Body cross-field shape/selected-step/cardinality errors are INPUT_INVALID before store access; mismatches inside a typed submitted execution binding remain BINDING_MISMATCH.
