# Approval Continuity Lab — discovery

Research date: 2026-10-19 (Europe/Istanbul). Repo Factory v1.1; phase: discover; profile: showcase.

**Recommendation:** pursue a local, deterministic approval-continuity lab: a small reference mediator and adversarial scenario runner around one simulated deployment operation. Its value is inspectable behavior under mutation, concurrency and recovery, rather than another approval inbox or a claim to invent action-bound authorization.

**Status: DISCOVERY_READY.** The user selected the project/problem. This document recommends its MVP shape; it does not approve that shape on the user's behalf or advance to spec. No product code, Git repository or remote repository was created. All behavior and tests below are proposals, not executed evidence.

## Problem and intended user

A backend engineer adds a human checkpoint to an agent workflow. A reviewer approves deploying artifact A to service S in staging. Before execution, the agent replans, another process updates S, the tool implementation changes, or a retry loads an old approval. A recorded yes answers what was reviewed; it does not by itself establish whether the present execution remains authorized.

The useful question is: **under which explicit, observable conditions may this exact approval still authorize this exact effect?** The lab should let an engineer reproduce a failure, identify the missing binding, and verify a bounded fix without model calls or production credentials.

This is an engineering hypothesis supported by documented controls and research, not customer validation. No interviews, adoption study, revenue estimate or willingness-to-pay evidence were gathered.

## Existing approaches and meaningful substitutes

Sources are primary documentation or author-hosted research. Documentation describes claimed behavior; it is not an independent implementation audit. Reviewed pages are mutable; future integration work must pin versions. An unmentioned feature is unknown, not absent.

| Approach | Documented behavior / relevant substitute | Consequence for this project |
| --- | --- | --- |
| [LangChain HITL](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) | Middleware interrupts tool calls, persists graph state, and supports approval, editing, rejection and response. | Pause/resume and editable arguments are existing features. The proposed lab studies validity across later changes; no claim that LangChain generally executes changed calls. |
| [OpenAI Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/) | Per-call and sticky decisions; durable RunState. Docs require trusted server-side state, reviewer authorization and atomic consumption to prevent duplicate resumes. Sticky scope has tool-specific caveats. | Existing guidance already covers substantial binding and replay concerns. Use per-call behavior as a comparison, not a strawman that all SDK approvals are boolean-only. |
| [HumanLayer SDK](https://pypi.org/project/humanlayer/) | Function decorators require human approval; human-as-tool supports escalation. | Human routing and developer ergonomics are substitutes. This discovery did not establish its complete expiration/revocation semantics. |
| [AgentGate](https://agentgatelabs.com/security/) | Gateway documents fail-closed routing and request-bound one-time approvals that expire and reject replay or changed arguments. Direct upstream access bypasses its boundary. | Expiry + nonce + argument hash is insufficient differentiation. Gateway deployment is a larger product category than this lab. |
| [ActionProxy exact binding](https://actionproxy.com/guides/bind-approval-to-exact-tool-call/) and [approval vs authorization](https://actionproxy.com/guides/ai-agent-approval-vs-authorization/) | Describes normalized input/context bindings, current-state validation before dispatch, and bounded one-use execution authority. | Very close conceptual competition. Do not market use-time validation or approval-versus-authorization as new. |
| [Agent Approval Protocol v1](https://agentapprovalprotocol.io/specification/security) | Requires immutable tool/arguments, expiry and atomic one-time consumption at the adapter boundary. Documents execution bypass limits. | A protocol substitute already specifies much of the core lifecycle. No protocol invention or conformance claim is needed. |
| [Cerbos gateway authorization](https://www.cerbos.dev/blog/fine-grained-authorization-for-ai-gateways) | Documents fresh request-time policy evaluation, principal/delegation context and revocation on subsequent decisions. | Human consent must remain subordinate to current permission. Building a policy engine would duplicate an established category. |
| [Onam governance](https://www.onamsecurity.com/docs/operations/governance) | Documents change-hash binding, expiry and target reread with supersession on drift. Page explicitly says approval centre is early access and customer-cloud execution is on the roadmap. | Even target-drift checking is not a defensible uniqueness claim. Distinguish documented design from delivered execution. |
| [Terraform saved plans](https://developer.hashicorp.com/terraform/cli/commands/plan) and [HCP run modes](https://developer.hashicorp.com/terraform/cloud-docs/workspaces/run/modes-and-options) | Saved executable plans and stale-plan handling are a mature analogue for review/apply separation. | Borrow immutable proposals and freshness checks; do not claim an approved digest observes every live infrastructure change. |
| [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments) | Required reviewers, deployment restrictions and optional prevention of self-review. | Existing workflow gates are often adequate. The lab is useful when evaluating a custom agent-to-tool boundary, not as their replacement. |
| [Macaroons research](https://research.google/pubs/macaroons-cookies-with-contextual-caveats-for-decentralized-authorization-in-the-cloud/) | Contextual caveats attenuate authority across identity, action and time. | Context-bound authority has established foundations. A new token format adds little to this MVP. |

### Direct research overlap

- [Loopjacking](https://arxiv.org/abs/2609.21081), September 2026, distinguishes misleading approval representations from post-approval state substitution. Its abstract reports exact per-call binding in tested OpenAI SDK versions as a negative control. These are author-reported, version-specific findings; no reproductions were run here.
- [Residual Authority Replay](https://arxiv.org/abs/2609.33910), September 2026, studies consent outliving the context that justified it. This directly overlaps the project's motivating problem.
- [Approval Laundering](https://arxiv.org/abs/2609.38983), September 2026, studies binding failures and reports limits of field-bound tokens when behavior diverges below the recorded invocation boundary. A tool-call hash cannot establish arbitrary downstream effects.
- [Transitive Effects Beyond the Approved Invocation](https://arxiv.org/abs/2609.28586), September 2026, introduces an approval-to-action benchmark focused on transitive workflows. A generic adversarial benchmark is therefore also insufficient differentiation.
- [Approve What, Exactly?](https://arxiv.org/abs/2610.21063), October 2026, studies effect binding and trusted rendering. Approval display integrity is existing research territory, not an invented contribution here.

These are recent preprints, not independently reproduced conclusions or ecosystem prevalence estimates. Discovery establishes substantial prior art. It does not establish a novel security primitive, a unique benchmark, or a missing commercial market.

## Candidate directions and scoring

Scores are subjective fit judgments, not empirical validation. Each dimension is 1–5. Total = differentiation ×5 + utility ×4 + technical signal ×4 + feasibility ×4 + demo ×3.

| Candidate | Differentiation | Utility | Technical signal | Feasibility | Demo | Total /100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| General approval gateway / inbox | 1 | 4 | 4 | 2 | 4 | 57 |
| Stateless signed approval-token library | 1 | 3 | 3 | 4 | 3 | 54 |
| Local continuity lab with transaction/race/recovery fixtures | 3 | 4 | 5 | 4 | 5 | 82 |

The gateway needs identity integrations, credential custody, deployment operations and integrations to be credible; it competes directly with existing tools. The token library is smaller but cannot independently guarantee revocation, target freshness, or consumption without state and enforcement.

The lab earns its differentiation score through packaging and focus: a compact, inspectable reference with reproducible ordering of revocation, mutation, consumption and effect, plus honest boundary demonstrations. Existing products or papers may cover these too. The defensible claim is a useful implementation and educational artifact, not exclusivity.

## Recommended showcase MVP

Working positioning: **“Reproduce when a human approval stops applying, and inspect the state transition that blocks execution.”**

One protected operation: `deploy_artifact` updates the artifact digest of a simulated service. Service identity includes tenant, environment and immutable service ID; resource revisions increase monotonically. No shell, provider API or real deployment runs.

Suggested implementation direction, subject to spec: Python library + CLI, one local SQLite database, a deterministic scenario runner, and machine-readable reports with a readable terminal explanation. SQLite is justified by durable state, process races and atomic reference effects. No server, cloud, Redis, LLM, frontend or framework dependency is required. Runtime versions and packaging remain spec/preflight decisions.

The same database holds approval records, current policy/context revisions, resource state and execution outcomes. This deliberately makes the protected simulated effect and grant consumption one transaction. It demonstrates a strong local guarantee without pretending that an external API shares that transaction.

### Proposed approval envelope

An immutable stored proposal binds:

- Request ID, schema version, requester/agent identity and run identity.
- Structured executable plan revision/digest and the selected step ID. The MVP permits one effectful step; it does not authorize a multi-step workflow.
- Tool identity and implementation revision from the mediator's registry, not merely its display name.
- Typed arguments: service ID and explicit immutable artifact digest; reject mutable aliases such as `latest`.
- Trusted tenant/environment/executor context, current policy revision and approver eligibility revision.
- Expected target revision, full normalized review representation, reviewer identity, decision time and fixed expiry.

The mediator derives authoritative identities, context, tool revisions and target versions. Agent-provided descriptions are untrusted explanatory text. Review displays come from the stored proposal, and approval refers to that exact revision. An opaque approval ID is a lookup key, not independent authorization. Hashes detect content mismatch; they do not authenticate a caller or make an untrusted database safe.

Strict equality is the MVP rule for all bound fields. Scope reductions, argument edits, reordered executable steps and unrelated changes to the bound plan all require a new proposal/review. This knowingly sacrifices approval reuse to avoid speculative semantic-equivalence inference. Cosmetic notes outside the executable manifest may change only if clearly excluded from authority and never interpreted by the executor.

### Proposed validity and failure rules

| Concern | Proposed rule | Independently observable result |
| --- | --- | --- |
| Expiration | Pending review has a deadline; an approved grant has a separate fixed expiry. Execution requires `now < expires_at` at the transaction's final authorization check. Retry never extends either deadline. | Exact-boundary fixtures deny; target unchanged. A slow commit after the check does not imply permission was valid at wall-clock commit time. |
| Scope / plan / arguments | Any bound mismatch denies; a changed action requires a new reviewed proposal. No wildcard, session-wide or delegated grant. | Change only environment, artifact, run or plan; original grant cannot authorize the changed effect. |
| Replay | Consumption, effect and result commit together. A repeat may return the previously stored result for the same execution identity but never repeat the effect. | Concurrent callers produce one effect and one resource revision increment. Conflicting reuse is rejected. |
| Revocation | A current revocation or eligibility withdrawal blocks unconsumed approval. Revocation and execution serialize through the same store. | Revocation committed first means no effect; execution committed first means revocation cannot undo it. |
| Target drift | Compare a monotonic expected resource revision while holding the same transaction that applies the effect. | A target changed and restored to identical content still fails through its newer revision (ABA case). |
| Tool/context/policy drift | Current mediator-owned revisions must equal those reviewed; fresh eligibility must hold. | Identical tool name and arguments fail after a registry, executor or permission revision change. |
| Recovery | Failure before transaction commit rolls back effect and consumption; loss of response after commit is reconciled from stored result. | Kill/restart fixtures distinguish rollback from committed execution, without a blind second effect. |
| Unknown state / storage failure | Fail closed; never fall back to a cached yes. | Invalid input or unavailable authoritative state produces no target mutation. |

An expired approval never revives if the local clock moves backwards: proposed implementation should persist a nondecreasing observed time floor and reject regression. This still does not supply a trusted global clock or protect against host/database compromise. Tests use an injected trusted clock. Full time and error precedence rules belong in spec.

Suggested lifecycle: pending → approved/rejected/expired/superseded; approved → consumed/revoked/expired/superseded. A mismatching submitted attempt is denied without silently rewriting the stored approval. Authoritative version drift makes it unusable; a replacement proposal is linked for review. Exact transition/error contracts remain future spec work.

## Planned acceptance evidence

These are test intentions, not tests written or run. Test assertions inspect persisted target state and outcomes independently of the mediator's allow/deny report. Expected envelopes and mutations are authored as fixtures rather than computed using the production digest function.

| ID | Independent scenario and oracle |
| --- | --- |
| D01 | Unchanged reviewed action succeeds; exactly the specified service/artifact changes and grant is consumed. |
| D02 | Single-field mutations of arguments, plan order/revision, step, principal, run, tenant and environment each deny with zero effects. Include new target with the same display name. |
| D03 | Semantically identical allowed JSON key order yields the same normalized proposal; duplicate keys, unknown fields and invalid types reject. No lossy float or implicit-default equivalence. |
| D04 | Clock before, exactly at, and after expiry; pending deadline; backward-clock and restart fixtures. No sleeps as the expiry oracle. |
| D05 | Replayed grant and conflicting execution ID cannot cause a second update; committed retry retrieves recorded outcome. |
| D06 | Two real subprocesses contend for one approval using barriers; observe one durable effect. |
| D07 | Force both orderings of revoke versus execute; verify the specified winner through database state, not timing guesses. |
| D08 | Target edit, edit-and-restore, and substitution between review and execution deny. A competing writer cannot update between final revision check and simulated effect. |
| D09 | Tool revision, executor identity, policy revision or reviewer eligibility changes deny with the same submitted arguments. |
| D10 | Kill a subprocess before commit and after commit/before response; restart and verify rollback versus recorded completion. |
| D11 | Review shows every effectful field from the stored manifest. Forged descriptions and modified client-side proposals cannot substitute the reviewed action. |
| D12 | Missing/corrupt state, database contention beyond a bounded timeout and malformed requests fail closed; reports distinguish rejection from infrastructure failure. |
| D13 | A deliberately naive fixture adapter reuses an approval after drift; the reference adapter blocks it. Label it an educational baseline, never an impersonation of a vendor. |
| D14 | A deliberately uncontrolled downstream-effect fixture changes state outside the mediator boundary. Report “outside guarantee,” demonstrating why passing invocation checks is insufficient. |

D14 is a synthetic limitation demonstration, not a second supported deployment adapter. Shell transitive-effect analysis and external provider execution remain excluded. If CLI authoring is selected at spec, Repo Factory v1.1 requires real closed-descriptor, EPIPE and SIGINT subprocess tests as well.

### Thirty-second demo

1. Show the exact deployment manifest and record a human approval.
2. Change the simulated service revision while keeping the tool arguments identical.
3. Attempt execution: show `TARGET_REVISION_CHANGED`, reviewed/current revisions, and zero effects.
4. Review a fresh proposal, execute once, then replay: show one committed update and the stored outcome.

The extended showcase forces revocation races and crash/restart schedules, then contrasts the controlled adapter with the explicitly unprotected boundary example. A demo success alone is not acceptance evidence.

## Boundaries, feasibility and risks

The host, local operator, mediator, fixture clock and database are trusted. A same-user process that directly edits SQLite or replaces the program can bypass the experiment. CLI reviewer identities are lab personas, not production authentication. This is not a production security boundary, prompt-injection defense, sandbox or compliance certification.

The strongest guarantee applies only to the simulated target updated in the approval transaction. An external target would need its own preconditions, idempotency and outcome reconciliation. A read-then-send gateway cannot eliminate that target's race by hashing arguments. Revocation after dispatch cannot generally undo an external effect, and timeouts must not be mislabeled as failure/no effect. These are reasons to exclude live adapters from the MVP.

The runtime cannot infer whether changed natural-language intent is harmless. It checks the declared executable manifest and trusted revisions. Omitting a relevant dependency from that manifest defeats continuity. Strict invalidation may frustrate users; measure false invalidations later rather than weakening rules by intuition.

Proposed cost boundary: offline local execution, synthetic fixtures, no paid services or credentials. Engineering estimate: roughly 1–2 focused weeks for an experienced implementer, with concurrency/recovery and CLI process behavior the largest uncertainties; not a delivery commitment. Stop scope growth at one operation, one store and one reference adapter. Framework adapters, web approvals, SSO, distributed replication, custom cryptography, delegation, multi-approver quorums, live payments/deployments, autonomous rollback and semantic equivalence are non-goals.

Licensing/IP: do not copy vendor implementations or paper benchmark datasets merely because they are reachable. Before later reuse, inspect actual source/data licenses and attribution requirements. Prefer original synthetic fixtures and paraphrased linked research. No third-party code or dataset was imported in discovery. Product-name availability and trademark clearance were not assessed.

Proposed future milestones: immutable proposal/review → strict execution checks and target revision → transactional replay/revocation → process races and crash recovery → scenario reports/demo → independent adversarial audit and packaging checks. These are planning suggestions, not an authorized build plan or gate results.

## Decision and phase handoff

Proceed as a **showcase engineering lab**, not as a claim to a new approval protocol or production gateway. Its strongest portfolio signal is precise contracts, controlled concurrency, crash consistency, explicit trust boundaries and negative evidence. Its commercial differentiation remains unvalidated.

- PHASE: discover.
- STATUS: DISCOVERY_READY for the user-selected Approval Continuity Lab problem; recommended MVP awaits review before spec.
- FILES_CHANGED: DISCOVERY.md only.
- VERIFICATION: skill/governance/reference reads exited 0. Initial filtered workspace search exited 1 because there were no matching files; directory inspection confirmed an empty workspace. After writing, `wc -l -w DISCOVERY.md`, `rg --files --hidden .`, and `rg -n 'DISCOVERY_READY|PHASE:|STATUS:|FILES_CHANGED:|VERIFICATION:|UNRESOLVED_RISKS:|USER_AUTHORIZATION_REQUIRED:|NEXT_ACTION:|D14|not executed|No product' DISCOVERY.md` each exited 0; inventory contained DISCOVERY.md only. Web research returned the linked sources. These are document/inventory checks, not product verification. No product tests, competitor reproduction, independent audit or hosted checks were executed.
- UNRESOLVED_RISKS: overlapping prior art, unvalidated user demand, strict invalidation usability, bounded synthetic-target guarantees, future licensing review, and runtime/process choices deferred to spec.
- USER_AUTHORIZATION_REQUIRED: explicit authorization to enter spec; build and publication remain outside scope. No additional authorization is needed to complete this discovery.
- NEXT_ACTION: review the recommended lab MVP; if accepted, authorize phase=spec to settle exact schemas, state/error precedence, time semantics, authentication boundary and acceptance commands. No automatic phase advance.

No discovery blocker remains. Production deployment guarantees or research novelty would require a different scope and additional evidence.
