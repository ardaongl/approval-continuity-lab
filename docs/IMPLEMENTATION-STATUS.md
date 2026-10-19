# Current publication candidate — independently audited

M0–M6, AC01–18 and F1 hardening are complete locally. The independent post-hardening re-audit passed: source, installed wheel and sdist-derived execution reject both original corruptions without mutation; 81 tests passed with zero skips; 126 independent matrix case executions and four process schedules passed. The saved Factory audit state is reconciled to PASS while the original BLOCKED finding and hardening history are retained.

Public GitHub creation/push to `ardaongl/approval-continuity-lab`, branch `main`, and verified narrow CI corrections are explicitly authorized. Hosted CI must pass for the final intended SHA before RELEASE_READY. Final SHA/run evidence is recorded in ignored local attestation, with Actions as the public source. See [publication verification](PUBLICATION-VERIFICATION.md). Package publication, GitHub Release and deployment remain outside this authorization.

Everything below is historical evidence from before the successful independent re-audit. Statuses and authorization statements below describe their original phase, not current state.

---

# F1 local hardening — PASS; independent re-audit pending

The independent audit found F1 (P2/AC-12): corrupt loaded metadata could permit execution. The narrow fix validates the complete required meta row inside the existing writer transaction, before caller/history/time handling. The original blocked audit is retained; no independent audit PASS is claimed. See [hardening evidence](HARDENING-F1.md). Hosted CI remains PENDING_HOSTED_CI and initial push remains unauthorized.

All81 tests passed with zero skips, including the new metadata regressions and fresh wheel/sdist-derived installed checks. The prior audit remains BLOCKED as history; F1 is fixed locally and awaits separate independent re-audit.

The following build ledger and its original evidence are retained as history.

# Current implementation status — LOCAL_READY

The authorized local build has completed M1–M6. All AC-01–AC-18 local gates pass. The final full-suite commands, exits, count, interpreter/SQLite/OS, source fingerprint, archive hashes and raw SQL/process evidence are recorded under `.local-verification/build/final/`, `.local-verification/build/final-snapshots/` and `.local-verification/build/final-attestation.json`. The ignored evidence is available in the development workspace; it is deliberately excluded from distributions.

The product is an offline stdlib modular monolith: strict schemas/canonicalization, immutable P/R/D, SQLite lifecycle and atomic simulated effect/result/consumption, deterministic reports, fixed adversarial scenarios and POSIX process fault handling. All 14 authored assets and the approved normative contracts remain byte-identical; the preservation gate uses 28 retained pre-build hashes.

M0 is supported by the independent targeted re-preflight and fresh transition checks, not an invented comprehensive transcript. M1–M3 targeted outputs and corrected failed attempts remain indexed below and in Factory metadata. M4–M6 and the final candidate are verified by the full suite, clean wheel/sdist builds, separate offline installations and archive/document link checks. A build-only packaging26.3 transitive pin was needed by wheel0.48.0; the approved pip/setuptools/wheel pins are unchanged and runtime dependencies remain empty.

Independent adversarial product audit: NOT_RUN. Hosted CI: PENDING_HOSTED_CI. Initial push and publication: NOT_AUTHORIZED. No remote operation, release or deployment occurred. There is no claim of RELEASE_READY. Supported Linux behavior still needs the prepared hosted workflow's real evidence; local evidence covers macOS26.5.2 arm64 / CPython3.12.14 / SQLite3.53.1.

See [build verification](BUILD-VERIFICATION.md) for the evidence map and commands. Build work stops at this local gate.

## Historical specification and build ledger (retained)

# Implementation status

Date: 2026-10-19. Project/profile: Approval Continuity Lab / showcase. Phase: SPEC_READY documentation candidate, verified as recorded in [spec evidence](SPEC-VERIFICATION.md).

User authorized phase=spec and approved the discovery MVP. This does not authorize preflight execution beyond specification checks, product implementation, dependency installation, Git initialization or remote work.

| Milestone/gate | Status | Evidence |
| --- | --- | --- |
| Discovery | DISCOVERY_READY; direction accepted by user | [research foundation](../DISCOVERY.md) |
| Specification | SPEC_READY | [contracts](03-contracts.md), [AC map](04-acceptance.md), [verification](SPEC-VERIFICATION.md) |
| M0 independent preflight | NOT_STARTED | none; next authorized phase |
| M1..M6 implementation | NOT_STARTED | no product code |
| AC-01..AC-18 product verification | NOT_RUN | no test modules or product entrypoint yet |
| Independent adversarial audit | NOT_RUN | no implementation candidate |
| Hosted CI | PENDING_HOSTED_CI | no repository, commit or run |
| Publication | NOT_AUTHORIZED | no remote/name/visibility grant |

No claim of LOCAL_READY, AUDIT_PASS or RELEASE_READY. No git commit SHA exists for this workspace. Current spec evidence uses file inventory/fingerprints, never fabricated Git identifiers. Changes after spec verification require affected document/fixture checks refreshed. No product test evidence is implied by valid metadata.

Expected future evidence is stored under ignored .local-verification/ with commands/exits, environment, candidate fingerprint, raw SQLite snapshots, report bytes and coordinator transcripts. This ledger must record real outcomes only. Known residual risks: strict invalidation ergonomics, simulated scope, trusted host/time, prior-art overlap, unvalidated demand. These do not block this bounded specification; capability/contract issues discovered by independent M0 must be reported before coding.

## Authorized build continuation — 2026-10-19

The later goal objective authorizes local M1–M6 implementation, bootstrap, metadata and optional local Git. It supersedes the historical spec-only authorization above. Remote operations remain unauthorized. Independent targeted M0 PASS retained in .local-verification/build/independent-m0/AUDIT-REPORT.md; fresh targeted transition checks in .local-verification/build/m0-transition.json; Factory preflight validator exited 0 after recording M0_PASS. The earlier comprehensive transcript is unavailable and is not claimed rerun.

M1: strict schema/canonicalization, immutable creation/review/decision and pinned environment implemented; 10 targeted tests exited 0. M2: lifecycle, drift, execution transaction and replay implemented; 20 targeted tests exited 0 after two test-fixture corrections (failed runs retained). M3: real processes, both orderings, calibrated SQLITE_BUSY, SIGKILL pre/postcommit and fresh raw-SQL recovery; 10 tests exited 0 after fixing coordinator release and test revision setup. Evidence paths are indexed in Factory metadata. M4–M6 remain outstanding; product ACs stay NOT_RUN until final full-scope checks.
