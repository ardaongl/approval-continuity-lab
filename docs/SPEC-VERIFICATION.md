# Historical specification verification record

Public rendering: private workstation paths in historical commands are replaced with `$REPO_FACTORY_ROOT`, `$PYTHON312` and `.`. These substitutions are not claims that those portable forms were originally executed. Exact original records are retained in ignored local evidence; original exits/results are unchanged. This document describes the specification phase only.

Date: 2026-10-19 (Europe/Istanbul). Scope: specification/documents/declarative goldens only. No product acceptance, runtime process behavior, package execution, independent M0 or independent adversarial audit is claimed.

## Executed preparation

- Read DISCOVERY.md in full across bounded reads; retained unchanged. Skill/governance/spec/build/handoff/runtime/targeted-repreflight/distribution/hosted-attestation references read; command exits0.
- Factory scaffold command: `python3 -B $REPO_FACTORY_ROOT/scripts/scaffold.py --project-dir . --slug approval-continuity-lab --title 'Approval Continuity Lab' --profile showcase`; exit0. It created starter docs only; all starter placeholders replaced.
- Initial environment probe printed system Python3.9.6/SQLite3.51.0 then exited1 on an importlib.metadata API unavailable in that runtime. Corrected stdlib version probe exited0; no dependency installation. A combined locator command contained an unsupported zsh command flag; its later successful Python command made the shell exit0, so that locator is not treated as successful evidence.
- Bundled runtime probe exited0: CPython3.12.14, SQLite3.53.1, macOS26.5.2-arm64, pip26.2.1, setuptools84.0.0, wheel0.48.0. Runtime is the spec target, not an M0 capability PASS.
- Authored declarative base config/submission, expected proposal/review/decision, execute request, golden reports/canonical vectors and independent domain-separated hash values using stdlib. No product existed/imported, no acceptance scenario executed.
- A patch-editor attempt was rejected before changing files; subsequent document writes succeeded. This was an editing issue, not a product gate.

## Final checks

Executed specification checks:

| Command | Exit | Observation |
| --- | ---: | --- |
| `python3 -B $REPO_FACTORY_ROOT/scripts/validate.py --project-dir . --phase spec` | 0 | metadata_check PASS; explicit metadata-only warning, no errors |
| `$PYTHON312 -B .local-verification/check_spec.py` | 0 | documentation/asset consistency PASS:21 Markdown files,63 relative links on initial and final runs,18 ACs,14 discovery scenarios,14 declarative assets; no product-code files or local .git |
| `rg --files --hidden -g '!**/.git/**' .` | 0 | reviewed specification/config/fixture inventory; no source/tests/build manifest/venv/dist |
| `rg -n 'TODO|\[FILL\]|\{\{|\? To|approval_id\}|initialize\(config\)|cache_spill|initialize|NO|NOT_RUN' docs/contracts AGENTS.md GOAL.md` | 0 | reviewed matches for signatures, lock settings and truthful status; no unresolved starter markers |

The stdlib checker is saved only under ignored `.local-verification/`; it is documentation-verification tooling, not product code. It checks paths, all AC mappings, NOT_RUN metadata, envelope fields, canonical bytes, digest domains, proposal/review/decision/execution coherence, expiry arithmetic, D01/D08 golden reports, Unicode vectors, duplicate-key negative input, review pointer/text asset agreement, schema/table inventory and absence of implementation directories. It imports no product, runs no proposed test or scenario, and writes an ignored SHA-256 manifest of the specification files. Final rerun refreshes that manifest after this record is saved.

Manual consistency review resolved: immutable proposal versus future decision time; pending revoke addressability; valid historical result lookup versus fresh authorization; submitted mismatch versus authoritative supersession; precommit raw reader versus SQLite cache spill; cancellation/COMMIT ambiguity; real contention calibration versus uncontrolled scheduling. These refinements preserve approved discovery scope/limits. M0 must independently challenge the result.

Official SQLite transaction, locking and cache_spill documentation was consulted to verify the specific design assumptions; links are in the concurrency contract. This is source verification, not an executed SQLite behavior test. Product tests remain NOT_RUN throughout. Metadata PASS proves required files/status fields only; manual contract review and independent asset checks are separate evidence. Hosted evidence is unavailable, not success.

## Review rationale

One immutable proposal plus later immutable decision resolves decision-time binding. Lazy persisted expiry/drift never authorizes unchecked execution. Historical exact-result lookup is deliberately distinct from new authorization. Multi-process and crash tests use real independent connections and SIGKILL, not mocked atomicity. Target/consumption/result share a transaction. Spec limits do not promise authentication, external effects or global time.

Mandatory review dimensions: document links,18 ACs including all14 discovery IDs, module/data ownership, transition/action matrix, byte/digest/golden agreement, error/time precedence, resource bounds, process faults, artifact layout, milestones, truthful NOT_RUN statuses, and absence of implementation/remote mutations.

One intermediate consistency-check rerun exited1 because this historical verification record quotes the placeholder-search pattern itself. Placeholder detection was scoped to contract/specification content, excluding this nonbinding command log; link and asset checks still include it. No product rule or acceptance was weakened. Final reruns below returned0.

Final classification review also pinned creation/replacement lookup errors, pending revoke semantics, rejected-decision/null-expiry tests, report fields before authorized lookup, and preservation of init files after uncertain commit/delivery. These were documentation-only refinements, with no implementation or external operation.

## B1 targeted specification remediation — 2026-10-19

The independent read-only M0 report in this chat returned BLOCKED on B1: binding's general Unicode whitelist excluded decision.reason while its detailed reason rule allowed Unicode scalar strings. That historical finding is retained; this remediation is not an M0 pass. The user explicitly approved valid non-ASCII scalar reasons and authorized only the narrow specification/evidence correction.

Changed binding lines7/34 to include decision.reason under the existing Unicode grammar: 1..1024 decoded UTF-8 bytes, no NUL or decoded surrogate code points, no normalization/coercion, unchanged C serialization. Valid escaped surrogate pairs represent supplementary scalars. Non-NUL controls remain escaped, not interpreted. Reason remains explanatory but is retained in immutable D/digest and exact decision-retry equality; it cannot independently grant authority. Identifiers and other restricted grammars are unchanged.

AC-03/11/18 now reference the added decision-reason boundary plan in the existing test strategy. Independent literal cases cover ASCII, Latin, Turkish, supplementary scalars, NUL, invalid surrogates, UTF-8 length boundaries, canonical escapes, distinct composed/decomposed bytes, and existing control escaping. These are planned product regressions, not product tests executed. No existing fixture or golden was regenerated.

Verification commands executed in this remediation:

| Command | Exit | Observation |
| --- | ---: | --- |
| `python3 -B $REPO_FACTORY_ROOT/scripts/validate.py --project-dir . --phase spec` | 0 | Metadata PASS only |
| `python3 -B $REPO_FACTORY_ROOT/scripts/validate.py --project-dir . --phase preflight` | 2 | Sole error: SPEC_READY cannot satisfy M0_PASS; workflow state prerequisite, not a specification defect |
| `$PYTHON312 -I -B .local-verification/check_spec.py` | 0 | Existing document/assets check PASS:21 Markdown files,66 relative links,18 ACs,14 assets |
| `python3 -B $REPO_FACTORY_ROOT/scripts/check_package_links.py .` | 0 | Source README14 relative targets exist; no archive/runtime proof |
| `$PYTHON312 -I -B .local-verification/check_b1.py` | 0 | Focused grammar/literal arithmetic/full-decision-byte/hash/AC preservation and asset checks PASS |

The initial new focused-checker run exited1 because its section parser included the following coverage heading in AC-18. Corrected that verification-only parser; subsequent runs exited0 without changing product rules or assets. Seven authored canonical literals,10 length cases,4 invalid escaped-surrogate cases,2 NUL cases and invalid UTF-8 surrogate encodings were checked using stdlib only. Full expected decision bytes were derived by replacing the reason member in the unchanged authored D bytes; independent decision-domain hashes were cross-checked without production imports.

Baseline/environment evidence is `.local-verification/b1-before.json`; the focused checker is `.local-verification/check_b1.py`; command outputs/exits and final candidate fingerprint are recorded in `.local-verification/b1-verification.json`. The existing `.local-verification/spec-artifacts.sha256.json` is refreshed for this candidate. CPython3.12.14 (Clang22.1.3), SQLite3.53.1, macOS26.5.2-arm64 were observed in the pinned interpreter command context. Python launched with -B before startup; no dependencies were installed.

Preservation uses baseline hashes for every unchanged specification file and all14 declarative assets. Only binding's two paragraphs changed; original AC text remains with additive coverage under03/11/18; original test-plan content is retained. Discovery, seven-state lifecycle, SQLite atomicity, replay/idempotency, clock/expiry, revocation ordering, recovery, trust boundaries, D01–D14 intent, all18 AC numbers and M0–M6 structure are unchanged. Factory metadata/ledger remain unchanged and product acceptance remains NOT_RUN. B1 is resolved for targeted independent re-preflight; no implementation, Git, remote operation or M0_PASS is claimed.
