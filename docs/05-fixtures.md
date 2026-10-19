# Fixture and golden plan

The committed [fixtures directory](fixtures/) contains declarative input/expected assets only, not product or test implementation. These were authored during spec before a product exists. Expected state tables below are the oracle; build must not replace them with snapshots of its own output.

## Base literals and command sequence

[base-config.json](fixtures/base-config.json) seeds op(operator), req_a/req_b(agent), rev_a(reviewer); c1/c2/c3 contexts; one tool; enabled t1 policy; allowed reviewer; svc1 and svc2 share display name api in staging, svc3 in prod. All revisions1. A is sha256 plus64 a digits, B uses b, C uses c. These are immutable synthetic identifiers, not claims about fetched artifact bytes.

Planned primitive sequence (all --format json unless testing text):
1. acl init --db lab.sqlite --actor op --now-ms 1000 --input docs/fixtures/base-config.json
2. acl propose --db lab.sqlite --actor req_a --context c1 --now-ms 1000 --input docs/fixtures/submission.json
3. acl review --db lab.sqlite --actor rev_a --now-ms 1400 --proposal-id p1
4. acl decide --db lab.sqlite --actor rev_a --now-ms 1500 --input docs/fixtures/decision-input.json
5. acl execute --db lab.sqlite --actor req_a --context c1 --now-ms 1600 --input docs/fixtures/execution-input.json

All commands above are planned, not executed product evidence. Review step is optional in programmatic fixtures; approval still requires exact digest. [proposal.expected.json](fixtures/proposal.expected.json), [review.expected.json](fixtures/review.expected.json), [decision.expected.json](fixtures/decision.expected.json) pin immutable content. Decision1500 + grant period1000 = expiry2500. [D01 golden](fixtures/d01-report.golden.json) is complete canonical command output including LF. D08's [golden](fixtures/d08-report.golden.json) is the execute refusal after svc1 update at1550 to C/rev2, with expected1/current2.

## Catalog of required independent variants

| ID | Fixture cases | Fixed summary explanation |
| --- | --- | --- |
| D01 | approved exact intent; unrelated services unchanged | exact reviewed deployment committed once |
| D02 | typed bound-field mutations; caller substitution; extra step; correct retry after denial | changed submitted bindings do not consume approval |
| D03 | canonical vectors, duplicates nested/root, null/missing/extra/type/size/depth/Unicode/overflow | strict input bytes have explicit canonical meaning |
| D04 | pending1999/2000/2001, grant2499/2500/2501, floor2400→2399/restart, delayed commit | validity uses final authorization time and durable floor |
| D05 | equal retry, conflicting key, another ID, old history after drift/time | committed retry retrieves history without another effect |
| D06 | A-first/B-first, same-ID variants with pipe barriers | serialized competing executions commit one effect |
| D07 | revoke-first/execute-first and repeated revoke | revocation cannot undo a committed deployment |
| D08 | update, ABA, substitution/same-name target, both writer orderings, fresh replacement | target revision drift requires a fresh review |
| D09 | each current revision/disable/withdrawal, combined precedence, restoration | current trusted revisions must still match review |
| D10 | real SIGKILL precommit and postcommit/pre-response, restart and retry | crash recovery distinguishes rollback from committed history |
| D11 | full review pointers, misleading controls/Unicode, forged digest, wrong reviewer | trusted review renders stored executable bindings |
| D12 | missing/corrupt/version/busy/write failure/input and bounds | missing authoritative state never implies approval |
| D13 | independent identical stores: reference refuses, naive changes C/rev2→B/rev3 | unsafe educational baseline reuses approval after drift |
| D14 | reference commit plus separate sentinel A→C | uncontrolled downstream file is outside guarantee |

Shipped scenario runner executes the illustrative named case(s) per catalog with positive assertions; test modules additionally exercise every edge variant from acceptance. D04 includes equality/backward restart, D06 both orderings, D07 both orderings, D08 update/ABA and race orderings, D10 both kills, D13 both adapters, D14 both scopes. D02 and D03 include all enumerated families. Runner uses the same report schema/limits and fixed explanation strings here. No dynamic assertion loading or arbitrary fixture scripts from user paths.

Canonical vectors in [canonical-vectors.json](fixtures/canonical-vectors.json) pin key order, -0, non-normalized accent and surrogate-pair serialization. [duplicate input](fixtures/duplicate-key.input.txt) is intentionally invalid JSON *for this contract* despite generic parsers accepting it. Add raw invalid UTF-8/surrogate inputs during build as binary literals in tests, not silently normalized valid JSON.

[digests.expected.json](fixtures/digests.expected.json) pins domain-separated independent hashlib calculations over authored expected bytes; no production code was imported. The [review leaf inventory](fixtures/review-leaves.expected.json) and [text suffix golden](fixtures/review-suffix.golden.txt) must agree with the authored review object and include container lengths. New negative fixtures must record input, expected primary code/exit, state delta and independent rationale before implementation changes.

## Persistent oracle summary

| Case | Final status | svc1 | executions | extra invariant |
| --- | --- | --- | ---: | --- |
| exact execute | consumed | B/2 | 1 | expiry2500 unchanged |
| submitted mutation | approved | A/1 | 0 | stored manifest unchanged |
| grant equality2500 | expired | A/1 | 0 | reason GRANT_EXPIRED |
| target drift update | superseded | C/2 | 0 | reason TARGET_REVISION_CHANGED |
| ABA | superseded | A/3 | 0 | content equality cannot reset revision |
| revoke-first | revoked | A/1 | 0 | no consumed transition |
| execute-first/revoke | consumed | B/2 | 1 | revoke TOO_LATE |
| crash A, before retry | approved | A/1 | 0 | floor1500 |
| crash B, after retry | consumed | B/2 | 1 | stored original result returned |
| naive after drift | approved | B/3 | 0 | unsafe effect count1 outside reference rules |
| D14 | consumed | B/2 | 1 | sentinel C not in result |

The naive execution count0 is intentional: unsafe demo never pretends to create a valid reference execution/consumption. Its effect count is asserted from the service revision delta attributable to that fixed naive operation. All reference counts derive from executions rows. No oracle uses the report's claimed verified/allow as proof of target state.
