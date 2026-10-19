# F1 hardening evidence

Phase: harden. Local hardening PASS; independent re-audit remains pending. The prior audit was BLOCKED (F1/P2/AC-12); its report and reproductions are preserved under `.local-verification/harden/f1/audit-*`. No audit PASS, hosted CI success or publication authorization is claimed.

The defect is missing validation of already-loaded meta values. SQL constraints protect supported writes but do not establish the validity of an already-corrupt row. `Store.check_schema` now requires exactly one meta row, integer singleton1, integer schema_version1 and an integer observed_time_floor_ms in0..9,007,199,254,740,991. This runs after BEGIN IMMEDIATE and before caller/history/time checks for every noninitializing database command. Init retains its existing validation/exclusive-creation/STATE_EXISTS behavior. No integrity sweep, repair, fallback, migration or transaction change was introduced.

Permanent regressions are in `tests.acceptance.test_metadata_integrity` and `tests.distribution.test_installed`. They cover both original corruptions, missing/wrong/extra singleton, stored TEXT/BLOB/REAL types, bounds, valid endpoints, history and error precedence, corruption after connection creation, real processes and CLI65. Full raw snapshots and database-byte hashes establish immutability. Test-only fault connections use ignore_check_constraints; missing-row setup temporarily drops and restores meta_no_delete. Production constraints remain unchanged. BLOB evidence is losslessly encoded as sqlite_blob_hex in the test evidence writer.

Pre-fix original reproduction command: `.venv/bin/python -B scripts/verify.py f1-before -- .venv/bin/python -B -m unittest tests.acceptance.test_metadata_integrity.MetadataIntegrity.test_original_negative_floor_and_wrong_version -v` exited1: both variants incorrectly returned OK/committed. A separate probe using the original audit candidate recorded eight API/CLI new/history cases returning OK; its process exit0 means successful reproduction of the defect, not product acceptance. Before/after raw evidence is under `.local-verification/harden/f1/before-raw` and `after-raw`.

The initial targeted run encountered a test-evidence serialization error for deliberate SQLite BLOB corruption. Production assertions passed; the evidence writer was extended to preserve BLOB bytes as hex. The failed run and corrected run remain in `.local-verification/build/*f1-targeted*`. No failing test was skipped or weakened.

Dependency impact: data meta invariants → store schema validation → all noninitializing mediator transactions, including historical lookup → storage/error/time/replay/CLI and installed distributions. The fix does not change lifecycle, envelopes, canonicalization/Unicode, idempotency, revision/revocation ordering, crash windows, D01–D14, AC-01–18 or any declarative asset. Existing architecture remains appropriate; no contract conflict or full-preflight escalation was found. A separate read-only re-audit must assess the final candidate.

Deferred nonblocking audit findings remain deferred: historical phase prose, transferable documentation paths, explicit CI SQLite capability assertion and direct Factory CI validation. Linux/hosted evidence remains pending. No remote activity occurred.

## Hardening report

PHASE: harden  
PROJECT: Approval Continuity Lab  
HARDENING_STATUS: PASS  
F1_RESOLVED: YES (local correction; independent re-audit pending)  
ROOT_CAUSE: Loaded meta row existence was checked, but values/types/bounds/cardinality were not.

FILES_CHANGED: `src/approval_continuity_lab/store.py`; new `tests/acceptance/test_metadata_integrity.py`; `tests/distribution/test_installed.py`; `tests/support/evidence.py`; directly affected README/PACKAGE-README/status/Factory metadata and this report. Generated bundled documentation and local dist artifacts are refreshed by the build. Normative contracts/acceptance/assets are unchanged.

REGRESSION_TESTS_ADDED: Ten metadata unittest methods with independent subcase matrices, plus one distribution method covering eight installed corruption cases across the direct wheel and sdist-derived wheel. The original70 tests remain; total81. Rejected new and historical operations preserve full raw SQL snapshots and database SHA-256. Deliberate TEXT, BLOB and REAL values exercise actual SQLite storage types; integer-affinity coercion of values such as1.0 is not misrepresented as stored REAL. Wrong singleton and an extra row use CHECK bypass only; missing singleton requires temporary test-only deletion-trigger removal/restoration.

BEFORE_FIX_REPRODUCTIONS: Original two variants both fail the new expected-STATE_CORRUPT test (test-runner exit1). A preserved original-source interpreter separately records eight normal API/CLI new/history cases returning OK in `before-raw/results.json`; reproducer exit0 denotes successful defect reproduction. The immutable original audit remains under the external audit directory, with copies in hardening evidence.

AFTER_FIX_REPRODUCTIONS: Eight equivalent source API/CLI cases return STATE_CORRUPT, CLI65, with unchanged raw rows and database-byte hashes (`after-raw/results.json`). Eight clean-installed CLI cases spanning both distributions, both corruptions and new/history retrieval do the same (`full-snapshots/distribution-corrupt-meta.json`).

METADATA_VALIDATION: Exactly one required row; exact integer singleton1 and schema_version1; exact integer floor in0..9,007,199,254,740,991. Invalid required loaded state is STATE_CORRUPT. PRAGMA/schema-shape version errors retain DATABASE_VERSION precedence. Input validation still precedes state access; schema integrity precedes actor/history/time. Existing init returns STATE_EXISTS without opening or repairing an existing file.

STATE_CORRUPT_CLASSIFICATION: API report STATE_CORRUPT/error/effect none; CLI exit65 and `acl: STATE_CORRUPT` on stderr. No result/observed-time disclosure is fabricated on integrity rejection. Valid committed historical retry still bypasses time sampling after successful integrity validation.

DATABASE_IMMUTABILITY_EVIDENCE: `targeted-corrected-snapshots`, `full-snapshots/metadata`, `after-raw/results.json` and installed-distribution snapshots. Raw all-table before/after equality plus file hashes show no metadata repair, floor advancement, decision modification, consumed transition or execution insertion on refusal. Historical cases retain exactly the one previously committed effect; they do not insert another.

TRANSACTION_INVARIANTS: BEGIN IMMEDIATE, connection scope, final checks, service CAS, execution persistence, consumed transition, rollback/COMMIT and crash points are unchanged. The fix is confined to Store.check_schema. Both real workers paused before BEGIN subsequently reject committed corrupt metadata. No process can use an earlier valid connection check as authority for a later transaction.

ADJACENT_ACCEPTANCE_RESULTS: AC-04/05/06/07/10/12 and metadata tests:34 tests, exit0, zero skips. Exact command below. TOTAL_TESTS:81 in full discovery, exit0, zero skips. ACCEPTANCE_RESULTS:AC-01 through AC-18 all PASS locally; independent audit remains pending.

CONCURRENCY_RESULTS: Both existing execution winner orders, same-ID race, calibrated real SQLITE_BUSY, both revocation and target writer orderings, plus two fresh workers refusing corrupt state, pass. No sleep-based winner oracle or mock transaction substitute was introduced.

CRASH_RECOVERY_RESULTS: Existing real SIGKILL precommit/postcommit recovery, raw reopened state and same-ID reconciliation pass. SQLite write-denial rollback, known COMMIT busy rollback and modeled outcome ambiguity remain covered. This is process-crash evidence, not power-loss certification.

UNICODE_B1_RESULTS: Strict canonicalization, invalid/valid scalar grammar,1024/1025-byte reason limits, canonical non-normalization, immutable retry and deterministic CLI/API serialization all pass in the full suite. No golden regeneration.

CLI_PROCESS_RESULTS: Actual descriptor closure1/2/both, true kernel-calibrated EPIPE, installed console/module faults, pre/postcommit SIGINT and runtime no-application-IO gates pass. No traceback, shutdown120 or DEVNULL substitute.

PACKAGE_AND_OFFLINE_RESULTS: Full suite clean-builds wheel/sdist, rebuilds a wheel from sdist, installs in two new environments, verifies import locations, no runtime dependencies, pinned tools, MIT metadata, all14 scenario resources and normal/fault commands with calibrated Python network blocking. New corruption checks execute through each installed console. Documentation/metadata refresh is followed by a fresh distribution-only run so the final archives include this report/status; logs and final archive hashes are in the ignored final attestation.

DECLARATIVE_ASSET_INTEGRITY:14/14 authored assets and all28 retained approved files match baseline SHA-256 values (`preservation.json`). AC-01–18, D01–D14, lifecycle, bindings, Unicode, time, replay, revocation, target semantics and demonstrations remain unchanged.

Executed verification commands (cwd project root; wrapper preserves actual argv/environment/exit/output/candidate hashes):

- `ACL_TEST_EVIDENCE=.local-verification/harden/f1/targeted-corrected-snapshots .venv/bin/python -B scripts/verify.py f1-targeted-corrected -- .venv/bin/python -B -m unittest tests.acceptance.test_metadata_integrity tests.acceptance.test_d04 tests.acceptance.test_d05 tests.acceptance.test_d06 tests.acceptance.test_d07 tests.acceptance.test_d10 tests.acceptance.test_d12 -v` — exit0;34 tests;8.282s. Record `.local-verification/build/20261019T174001009175Z-f1-targeted-corrected/result.json`.
- `ACL_TEST_EVIDENCE=.local-verification/harden/f1/full-snapshots .venv/bin/python -B scripts/verify.py f1-full-suite -- .venv/bin/python -B -m unittest discover -s tests -t . -v` — exit0;81 tests;52.904s. Record `.local-verification/build/20261019T174101229373Z-f1-full-suite/result.json`. This covers all18 AC modules and the additional metadata/distribution regressions.
- Before and after standalone probe commands use `.local-verification/harden/f1/probe.py --fixtures <project>/docs/fixtures --output <evidence-dir> --expected OK|STATE_CORRUPT`. Exact executable, argv, result interpretation and raw outputs are indexed in the final attestation. The before probe uses the preserved old audit candidate, never a temporary patch to production.

FACTORY_VALIDATION: Local metadata validation and archive link lint outputs/exit statuses are recorded in `.local-verification/harden/f1/final-attestation.json`. Metadata completeness does not establish product correctness or audit approval.

EVIDENCE_UPDATED: Prior M0–M6/build evidence and the original BLOCKED audit are preserved. Factory lifecycle remains LOCAL_READY; audit remains BLOCKED historically with F1 FIXED_LOCALLY_REAUDIT_PENDING; hardening is PASS. Final candidate file hashes, environment, source changes, artifact hashes, preservation checks, raw SQL, child exits and verification commands are recorded under `.local-verification/harden/f1` and the timestamped build wrapper directories. There is no commit SHA or hosted run.

NONBLOCKING_FINDINGS: Deferred historical phase prose outside directly affected status lines; documentation machine paths; explicit CI SQLite capability checks; direct Factory CI verification. No expansion to those follow-ups. Runtime evidence is local macOS arm64, CPython3.12.14/SQLite3.53.1. Current limits remain the trusted host/operator/database/clock, simulated SQLite effect and supported local filesystem. Separate Linux/hosted evidence is pending.

REMAINING_BLOCKERS: No known local F1 blocker after these regressions; separate independent read-only re-audit is still required. No self-approved re-audit was performed.

READY_FOR_INDEPENDENT_REAUDIT: YES  
READY_FOR_INITIAL_PUSH: NO  
HOSTED_CI: PENDING_HOSTED_CI  
REMOTE_CHANGES: NONE  
USER_AUTHORIZATION_REQUIRED: Separate authorization for independent re-audit and any later commit/remote/push/publication/deployment.  
NEXT_ACTION: Stop after local hardening; provide the final candidate and evidence for a separate read-only re-audit.
