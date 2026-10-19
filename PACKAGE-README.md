# Approval Continuity Lab

Offline Python lab for observing when a reviewed approval stops authorizing a
simulated deployment. Python 3.12.14, SQLite 3.35 or later, macOS/Linux POSIX.
Standard-library runtime; no network, credentials, cloud deployments or models.

The package includes documentation and authored fixture assets under
`approval_continuity_lab/documentation`, accessible through `importlib.resources`.

The reference effect, one-time consumption and durable result share one SQLite
transaction. CLI personas are trusted lab assertions, not production authentication.
The guarantee covers the simulated database service only. Direct database edits,
external effects, global time and arbitrary power loss are outside its guarantee.

Local implementation passes all18 acceptance criteria and clean offline distribution
gates (81 tests, zero skips). The independent post-hardening audit passed, including
F1 metadata-corruption checks. Hosted CI must verify the exact repository commit;
package publication and production security certification are not claimed.
