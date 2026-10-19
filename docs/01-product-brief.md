# Product brief

Profile: showcase. User: backend/agent engineer investigating a custom approval boundary. The user approved the recommended direction from [discovery](../DISCOVERY.md) on 2026-10-19. Prior art remains research evidence, not binding product behavior or market validation.

Workflow: operator seeds synthetic actors/context/services; agent persona proposes one deployment step; designated reviewer sees the stored manifest and approves its digest; execution commits one local effect or explains refusal. Bound changes require a new proposal. Scenario runner reproduces this with independent expected outcomes.

Deliverables: mediator, simulated deploy operation, SQLite, scenario runner, deterministic JSON/text, tests, installable Python package. Policy is a versioned enabled/disabled tenant record, not a rule engine. No provider execution, identity provider, inbox, UI, service or integrations.

Success means another engineer can reproduce expiry, mutation, replay, revocation, drift and crash outcomes, inspect persistent state independently, and explain the guarantee's limits. Determinism means equal validated inputs, initial state, clock values and explicit operation order yield equal report bytes. Uncontrolled concurrent winners need not be deterministic; shipped demos force order.

Scope budget: one operation/store/reference executor, built-in scenarios, no arbitrary user scripts. Discovery's 1–2 focused weeks is an estimate with concurrency/recovery uncertainty, not a commitment. No service fees or credentials.

Commercial demand, name clearance and exclusivity remain unvalidated. Use original synthetic fixtures. Inspect licenses before any later third-party code/data reuse; none is required. Original code distribution is planned as MIT; create the license text during build.
