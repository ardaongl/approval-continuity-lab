# CLI, reporting and process boundary (normative)

## Public commands

Entry points: acl and python -m approval_continuity_lab. Application version 0.1.0. No interactive prompts, progress bars, color, environment configuration, timestamps from wall time or terminal-width-dependent formatting.

Each DB command requires --db PATH --actor ID --now-ms INT and accepts --format json|text (default json). Agent callers also require --context ID; non-agent callers must omit it. CLI Clock returns that same injected value throughout the command. Options may follow the verb in any order; duplicate flags/unknown options rejected. No abbreviations. Integer flag lexemes are decimal digits only, within bounds (unlike JSON integer -0 normalization). --input PATH reads a file; --input - reads stdin. Noninteractive EOF is not approval. No user-supplied output path: stdout is the sole report destination.

| Command | Specific required flags/body | data on OK |
| --- | --- | --- |
| init | --input config.json; actor must name a configured operator; no context | {schema_version:1} |
| propose | --input submission.json; agent | {proposal:P,proposal_digest,review:R,review_digest} |
| review | --proposal-id ID; authorized reader | {review:R,review_digest,description} |
| decide | --input decision.json; designated reviewer | {decision:D,decision_digest} |
| execute | --input execution.json; owning agent | {result:stored_result} |
| revoke | --input revoke.json; reviewer/operator; body {schema_version:1,proposal_id} | {changed:boolean} |
| inspect | --kind proposal|approval|execution --id ID; authorized reader | see below |
| admin-update | --input update.json; operator; body in data contract | {kind,id,reviewer_id,revision} with reviewer_id null except eligibility |
| scenario list | no DB/persona/time/input flags; --format only | {scenarios:[D01..D14 IDs]} |
| scenario run D01..D14|all | no DB/persona/time/input flags; --format only | {scenarios:[scenario_summary,...]} |

Only the listed commands/flags exist. --help and --version are static text to stdout, return 0 without DB/input access; --help takes precedence over other option validation and --version next. They still respect output errors. inspect proposal returns {proposal:P,proposal_digest,review:R,review_digest,description,transitions:[...]} with transitions sorted by sequence. inspect approval returns {proposal_id,decision:D,decision_digest}; inspect execution returns {result:stored_result,request_digest}; no request payload/other-owner disclosure. Top-level status carries selected proposal's lifecycle. No unbounded DB listing.

Python facade mappings are identical: body stays a dict; review/inspect selectors match flags; time comes from Clock, actor/context from Caller. initialize(config,caller) requires an operator present in config. Revoke addresses a proposal and resolves its sole decision, if any, allowing pending-state refusal without inventing an approval ID. Command strings in reports use init, propose, review, decide, execute, revoke, inspect, admin-update, scenario-list, scenario-run.

## Report schema 1

Every normal command response is one canonical JSON object followed by exactly LF. Keys (all required):
- schema_version: 1.
- command: one command string above, or invalid for malformed command line.
- mode: REFERENCE, NAIVE_BASELINE, OUTSIDE_BOUNDARY or SCENARIO.
- outcome: ok, denied, committed, verified, error or interrupted.
- code: one stable code below.
- proposal_id, approval_id, execution_id: ID or null.
- status: pending/approved/rejected/consumed/revoked/expired/superseded or null.
- observed_at_ms: sampled time or null; historical lookup does not sample.
- authorized_at_ms: original execution check time for committed result, otherwise null.
- replayed: boolean.
- effect_status: none, committed, unknown or outside_guarantee.
- details: array of {path,expected,actual}, all strings, sorted by path then expected/actual; maximum 256 entries, each string ≤4096 UTF-8 bytes.
- data: command-specific object above, or null for refusal/error/interruption before commit.

The canonical encoder is [binding](binding.md) C plus terminal LF. Reports exclude machine paths, PIDs, exception messages, durations, host names, runtime versions and random IDs. Evidence files may contain environment details separately. IDs/statuses may be populated only after authorized lookup. observed_at_ms remains null when no valid sample was committed. A committed retry returns the exact stored result as data.result and sets replayed=true; original has false. At a COMMIT failure effect_status=unknown, no speculative result.

Domain lifecycle refusal uses outcome=denied; validation/infrastructure uses error. Success executing uses committed; successful scenario assertions use verified; other success uses ok. Rejected review decision itself is successful ok, status=rejected, not a process failure. Terminal inspect/review is ok. Scenario expected denials do not determine runner exit; the independent assertions do.

Error detail generation is deterministic: validation records the first failing JSON-pointer path with expected a fixed rule label and actual C(value) or "missing"; malformed bytes/syntax use path="/" expected="valid UTF-8 JSON" actual="invalid"; no parser offset or host-dependent text. Binding mismatch reports all differing leaf/container paths in sorted order up to limits; comparison overflow produces INPUT_LIMIT before state access. Current drift reports the first reason and its corresponding path (/context, /tool, /policy, /eligibility, /target) with canonical reviewed/current revision scalar values; a disabled policy/eligibility uses object {revision,enabled}/{revision,allowed} on both sides. For codes without specified details use []. No stack traces.

Text mode: fixed first line "COMMAND: <command> | MODE: <mode>"; second "OUTCOME: <outcome> | CODE: <code>"; third "EXPLANATION: " plus code lowercase with underscores replaced by spaces; fourth "STATUS: <status or none> | EFFECT: <effect_status> | REPLAYED: <true|false>"; fifth "OBSERVED_AT_MS: <integer or none> | AUTHORIZED_AT_MS: <integer or none>". Then each detail is "DETAIL <JSON-escaped path>: expected=<JSON-escaped expected> actual=<JSON-escaped actual>". Then "DATA: " + C(data) + LF. review additionally appends the complete path-based trusted review rendering specified in binding, followed by "UNTRUSTED DESCRIPTION: " + C(description). All text is ASCII escaped where needed. A scenario summary includes a short fixed explanation string defined in the fixture catalog. Text is intentionally plain and stable.

Scenario summary exact fields: {scenario_id,classification,verified,observations,explanation}; classification is REFERENCE except D13 COMPARISON and D14 OUTSIDE_GUARANTEE. observations is ordered by specified logical step, max128 objects {step,code,status,effect_count,service_revision}; status/revision nullable. effect_count counts committed reference or explicitly labeled baseline updates in that scenario's store, never uncontrolled effects. explanation comes from fixtures. D13 observations step prefix reference-/naive- distinguishes stores; D14 outside-file step has effect_count=null and service_revision=null. A coordinator failure sets verified=false and code SCENARIO_FAILED; runner stops at first failed scenario. all runs numeric ID order; reports contain complete passed predecessors plus failed scenario, never mark unrun scenarios verified.

Max report bytes including LF =1,048,576. Serialize completely before emission. Pre-computation bound checks must ensure protected DB operations' maximum result fits. Any unexpected oversize after commit → INTERNAL_ERROR and reconcile existing execution, not rerun. No intentional truncation. At most one stdout report; diagnostics never share stdout.

## Codes and exit classes

| Exit | Codes |
| ---: | --- |
| 0 | OK |
| 2 | INPUT_INVALID, INPUT_LIMIT, UNSUPPORTED_VERSION, LIMIT_EXCEEDED |
| 3 | ROLE_FORBIDDEN, CALLER_MISMATCH, NOT_FOUND, INVALID_STATE, BINDING_MISMATCH, IDEMPOTENCY_CONFLICT, APPROVAL_PENDING, APPROVAL_CONSUMED, APPROVAL_REVOKED, REVIEW_REJECTED, PENDING_EXPIRED, GRANT_EXPIRED, CONTEXT_CHANGED, TOOL_CHANGED, POLICY_CHANGED, REVIEWER_CHANGED, TARGET_REVISION_CHANGED, REPLACED, CLOCK_REGRESSION, REVISION_CONFLICT, TOO_LATE, POLICY_DISABLED, REVIEWER_INELIGIBLE, TARGET_SCOPE_MISMATCH |
| 4 | SCENARIO_FAILED |
| 65 | DATABASE_VERSION, STATE_CORRUPT |
| 66 | INPUT_IO |
| 69 | STATE_EXISTS, STORAGE_ERROR |
| 70 | INTERNAL_ERROR |
| 74 | OUTPUT_IO |
| 75 | STORAGE_BUSY |
| 130 | INTERRUPTED |

Signal termination by SIGKILL is not a graceful exit code. Code STATE_EXISTS intentionally uses storage class; unknown commands use INPUT_INVALID. Every nonzero graceful result attempts one stderr line "acl: CODE\n" after stdout report (if stdout usable); no stderr on success. Missing/broken stderr suppresses that diagnostic and preserves original classification. Never redirect it into stdout. Paths/OS exception details are excluded. API receives the report/code classification but does not exit.

## Runtime and CLI process fault matrix

Application-controlled IO begins only in explicit entrypoints/methods. Pure package import performs no DB/input/file/process/network writes or reads. Python interpreter/site/import startup can create caches or consult user site modules before product code. Supported reproducibility launch is isolated Python (-I) with -B when not using the installed console entrypoint; console entrypoint imports are tested too. No claim prevents every OS/runtime write. Normal reference commands intentionally write DB/journal; scenario runner writes only its temporary synthetic workspace. Input files are never intentionally modified.

CLI startup checks stdout presence, fileno validity and writable access mode without writing a probe byte and without DB/input access. A stdout closed before interpreter startup may be None; handle it explicitly rather than raising AttributeError. Absent/invalid/read-only stdout → exit 74, no product-controlled DB/input access; best-effort stderr OUTPUT_IO. Stderr can be absent without changing product behavior. OS/runtime failures before entrypoint control are outside the product exit guarantee; process tests use supported normal interpreter startup to reach the entrypoint.

| Fault | Required observable behavior |
| --- | --- |
| Normal success | complete LF-terminated canonical report, exit0, empty stderr |
| Domain denial | complete denied report, exit3, one code diagnostic |
| Invalid input | error report exit2; no state mutation; one diagnostic |
| Closed stdout before startup | exit74 before DB/input IO; no traceback |
| Closed stderr before startup | success0 or original domain/input code; correct stdout, no traceback/fallback diagnostic |
| Both closed before startup | exit74, no app DB/input IO, no uncaught exception |
| True EPIPE during write/flush | exit74, no Python shutdown traceback/exit120; no second report; committed effects remain committed |
| Other stdout write/flush error | OUTPUT_IO74; same delivery semantics |
| Input read IO error | INPUT_IO66; report if possible; no state mutation |
| SIGINT before commit | set cancellation flag; check before commit, rollback entire transaction, exit130; no protected effect |
| SIGINT during/after commit | finish/resolve commit, exit130; if committed retain result/consumed/effect, never imply rollback |
| SIGINT during report emission | exit130 unless output fault already requires74; partial output possible; reconcile by identity |
| Lock timeout | STORAGE_BUSY75; no effects or maintenance committed |

Install minimal signal handler setting a cancellation flag; do not raise asynchronously through sqlite3 COMMIT. Handler is active before state operations. Check flag before BEGIN and before COMMIT; once COMMIT starts, finish it and then honor cancellation. If SIGINT arrives while blocking for SQLite lock, cancellation handled after return bounded by busy_timeout plus 1 second on supported host; not an instantaneous OS guarantee. When commit is known complete, INTERRUPTED report may retain data.result, authorized_at_ms, status consumed and effect_status committed. If commit outcome unknown, unknown; otherwise none. Library cancellation uses the optional Cancellation object supplied to Lab.open, with identical transaction semantics and no global signal handler. CLI Observer and signal handler have no effect on validation or authorization conditions.

Stream failures override other process codes with74; otherwise INTERRUPTED overrides the normal result with130. On failure suppress subsequent writes to unusable streams and prevent interpreter shutdown flushing those same broken streams; do not assume catching BrokenPipeError around one buffered write is sufficient. No stdout fallback when stderr fails.

Tests MUST close actual descriptors 1/2 in children before exec, individually and together; DEVNULL is not closure. True EPIPE fixture uses a real pipe, a coordinator-controlled stopped reader and a bounded large report/stream-write test to force write/flush after reader closure. Calibrate to prove EPIPE, not merely preclosed FD or unrelated exception. Verify installed entrypoint and -m startup, process exits, byte output, stderr and raw DB state. Control SIGINT via the same precommit/postcommit observer barriers. Closed-channel tests with malformed input prove output-IO versus input-error precedence; with valid mutation prove no precheck bypass.

## Additional exact classifications

If command-line format cannot be selected due to invalid syntax, use JSON; recognized --format text still applies to other invalid fields. For an unknown/malformed command the command value is invalid. Help/version output is not wrapped in schema1: --version emits exactly "Approval Continuity Lab 0.1.0\n"; --help is static documented usage and may add command descriptions, with no state access. Repeated identical invocation must be byte-stable.

Storage map: SQLITE_BUSY/LOCKED after the configured wait → STORAGE_BUSY; SQLITE_CORRUPT/NOTADB or invalid loaded required row invariants → STATE_CORRUPT; recognized application/version/schema shape mismatch → DATABASE_VERSION; file/path/permission/disk/full/other SQLite IO → STORAGE_ERROR. Failure reading input file/stdin → INPUT_IO. Unsupported CLI/input enum or wrong body shape → INPUT_INVALID. init preexisting file always STATE_EXISTS without opening it as a lab. Unexpected programming exceptions → INTERNAL_ERROR; no catch-all converts exceptions to a successful report. COMMIT failure always effect_status unknown unless rollback/noncommit is established, including for init/admin state; deployment effect_status none is not a promise that no other metadata exists.

No permission bit simulation is sufficient for write-failure tests when host privileges bypass it; calibrate the actual failed write or use a supported SQLite fault harness and verify rollback with raw reads. Every LIMIT_EXCEEDED pre-effect result has no protected deployment; floor/maintenance may advance as specified.

Trusted-review suffix has exact lines "REVIEW <pointer>: <C(value)>\n"; pointer escapes ~ as ~0 and / as ~1. Sorted traversal, array indices numeric order, array length line at <array-pointer>#length before elements. Empty object is emitted as its pointer with {}; empty array as length0. Null is a leaf. Then UNTRUSTED DESCRIPTION line. The [leaf inventory](../fixtures/review-leaves.expected.json) and [suffix golden](../fixtures/review-suffix.golden.txt) pin the base fixture. Error detail actual values exceeding4096 UTF-8 bytes are the fixed string "oversize", never truncated arbitrary data.

Execute uses only the stored, compared P to call the simulated deployment operation. Submitted intent never supplies a replacement callable, SQL, artifact bytes or environment. Trusted tool revision is a configured label; it is not executable-code attestation.

Before authorized object lookup, report IDs/status/times/data are null, replayed=false and effect_status=none. A recognized scenario command uses mode SCENARIO even on input error; all other public command errors use REFERENCE. Malformed unknown command uses command invalid/mode REFERENCE. Internal naive/outside observations keep their explicit labels; they are never selectable public execute modes. Initial validation errors include the recognized command name when that verb was parsed successfully.
