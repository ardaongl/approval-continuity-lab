# Approval Continuity Lab

An offline engineering lab for observing when a reviewed approval stops authorizing a simulated deployment. All18 local acceptance criteria and clean distribution gates pass. The independent post-hardening audit passed, including F1 metadata-corruption checks. Hosted CI is a separate gate for each commit; see the [publication verification record](docs/PUBLICATION-VERIFICATION.md).

Approve a stored manifest, change its target revision, and observe execution refused. Review a fresh proposal, execute once, and retry without another update. Extended scenarios force revocation orderings, competing execution and process crashes. A labeled naive adapter shows approval reuse after drift; a separate synthetic experiment shows an uncontrolled effect outside the guarantee.

Installed quickstart:

```sh
acl scenario list --format json
acl scenario run D08 --format text
acl scenario run all --format json
```

Scenarios use temporary synthetic state, fixed times and explicit schedules. Exit 0 means expected assertions hold, including expected denials. Temporary state is removed. No network or paid service is used. Required runtime: CPython 3.12.14, SQLite 3.35 or later, macOS/Linux POSIX. Windows is unsupported. Install the built wheel into a virtual environment with `python -m pip install --no-index --no-deps dist/approval_continuity_lab-0.1.0-py3-none-any.whl`.

For development, select CPython 3.12.14, create `.venv`, prepare a local wheelhouse with the hashes in `requirements-build.lock`, then install those pinned tools with `--no-index --no-deps --require-hashes`. Install the project with `.venv/bin/python -B -m pip install --no-index --no-deps --no-build-isolation -e .` and run `.venv/bin/python -B scripts/sync_documentation.py`. The additional build-only `packaging==26.3` pin satisfies wheel's declared dependency; the product has no runtime dependencies beyond the standard library.

Run all local checks with `.venv/bin/python -B -m unittest discover -s tests -t . -v`. Distribution tests expect the prepared wheelhouse at `.local-verification/build/wheelhouse`, or the absolute `ACL_WHEELHOUSE` test-harness setting. They build in a clean temporary source tree, install wheel and sdist-built wheel into separate environments, block Python network access and exercise installed commands. See the test strategy for individual gate commands.

Public database commands require `--db`, `--actor`, `--now-ms` and agent `--context`; input commands require `--input PATH` (or `-` for stdin). Only `init` creates a database. `propose` creates an immutable manifest, `review` renders stored bindings, `decide` records a designated reviewer decision, and `execute` checks current authority in the effect transaction. `inspect` retrieves a selected proposal, approval or execution. `revoke` and operator-only `admin-update` expose the documented lifecycle and revision changes. `acl --help` lists exact syntax. Time is explicitly injected; there is no system-clock default.

After an unknown commit outcome, interrupted response or output failure, reconcile with the same execution identity. Do not retry with a new execution ID. D13 is labeled NAIVE_BASELINE/UNSAFE_EDUCATIONAL; D14's outside-file observation demonstrates OUTSIDE_BOUNDARY/OUTSIDE_GUARANTEE. Neither is an alternate public executor. Keep sensitive data out of descriptions and reasons: this synthetic lab provides no secret-redaction promise.

Guarantees cover the simulated service in the consumption transaction. CLI personas are lab identities; database edits bypass the mediator. Hashes cannot prove intent or arbitrary downstream effects. This is not a production gateway or certification. Existing products/research cover binding, expiry and replay; no novelty or market-demand claim is made. See [discovery](DISCOVERY.md).

Specification: [goal](GOAL.md), [working agreement](AGENTS.md), [product](docs/01-product-brief.md), [architecture](docs/02-architecture.md), [contracts](docs/03-contracts.md), [acceptance](docs/04-acceptance.md), [fixtures](docs/05-fixtures.md), [tests](docs/06-test-plan.md), [milestones](docs/07-build-plan.md), [release](docs/08-release.md), [decisions](docs/09-decisions.md), [status](docs/IMPLEMENTATION-STATUS.md), [verification](docs/SPEC-VERIFICATION.md).

Local verification and limitations: [build evidence map](docs/BUILD-VERIFICATION.md). GitHub publication to ardaongl/approval-continuity-lab is authorized; PyPI publication, GitHub Releases and deployment require separate authorization.
