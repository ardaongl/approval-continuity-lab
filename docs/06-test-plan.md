# Test strategy and runtime/distribution gates

Use standard-library unittest and subprocess/multiprocessing; no runtime or test framework dependency required. tests is a package so the exact module commands in acceptance resolve. Unit tests cover strict parser/canonical vectors, state functions, report bytes; integration tests use disk SQLite. AC mapping and expected states are in [acceptance](04-acceptance.md), fixture sources in [fixtures](05-fixtures.md).

Future test layout:
- tests/acceptance/test_d01.py through test_d14.py.
- tests/process/test_fault_matrix.py, test_runtime_boundary.py.
- tests/interface/test_reports.py.
- tests/distribution/test_installed.py.
- tests/support holds process coordination, **independent** raw SQL readers and literal expected data; never production approval or digest helpers as expected oracles.

Critical invariants I1–I10 require explicit negative cases, not a numerical coverage waiver. No mandatory 100% or coverage dependency. Record test counts and no unsupported skipped mandatory cases. A supported-platform capability missing (SIGKILL, locks, descriptors) blocks M0/local gate rather than weakening the test. Optional future coverage metrics are informational.

## Runtime Boundary Audit

M0 records actual interpreter/version/SQLite/OS, interpreter startup/site behavior, console wrapper/import code paths, intentional IO, allowed cache writes and stream/sys.stdout=None behavior. Unsupported Python is a preflight environment blocker, not a product bug. Test both installed console command and python -m; -B suppresses import-cache writes when chosen before startup, -I excludes user site/environment effects in isolated probes. Console-wrapper startup cannot promise to prevent every interpreter write.

Pure import must not open database/input/config or create temp paths. Help/version must not. Invalid input cannot touch DB. Use a calibrated observer/audit-hook or IO wrapper that demonstrably catches an intentional control write/read and compare a filesystem inventory; explicitly record what C/runtime activity instrumentation does not intercept. No unsupported universal no-write assertion.

## Real process matrix

Every AC-15 row is mandatory on macOS/Linux. Launch actual subprocesses, close descriptors1/2 before exec, verify None streams, and check no Python shutdown exit120/traceback. DEVNULL is a writable descriptor and fails the test requirement. True EPIPE uses a valid open write FD with no reader by output time; it must pass fstat precheck and reach write/flush, unlike preclosed stdout. A small write with zero readers also forces EPIPE; large bounded flush cases exercise buffering. Record calibration proving underlying EPIPE.

SIGINT uses ready/release barriers at precommit and postcommit; never sleep and hope the process is in the right place. Coordinator kills/reaps on timeout, all child FDs closed, failure cannot turn into a skipped case. Validate DB as well as exit130. Crash SIGKILL tests are separate from graceful cancellation. Include lock-contention timeout and midtransaction SQLite failure.

## Adversarial fixtures and negative controls

Baseline proves the drift fixture is capable of causing an unsafe change; reference refuses identical changed target. D14 proves absence of coverage without external infrastructure. Canonical expected data are frozen before implementation; changes require a semantic justification/ADR and affected acceptance review, never golden refresh simply to get green.

New independent audit must challenge ambiguous paths beyond existing tests: combined errors/precedence, response loss and historical ownership, replacement links, duplicate decisions, overflow, malicious annotations, cold package data, closed descriptors and crash windows. Read-only audit may generate ignored repro files but may not fix product source. New failures block AUDIT_PASS until hardening and fresh review.

## Decision-reason Unicode boundaries

B1 remediation follows the user-approved detailed reason grammar: valid Unicode scalars, 1..1024 UTF-8 bytes, no NUL, no decoded surrogate code points, no normalization/coercion. This is a specification regression plan, not executed product tests. AC-03 owns parsing/scalar/canonical checks, AC-11 owns decision persistence/retry/authority checks, and AC-18 owns deterministic API/CLI serialization. Existing test module names and all 18 AC numbers remain unchanged.

For each case use an otherwise valid decision command derived from the unchanged decision-input asset, changing only reason, with a fresh pending fixture unless testing retries. The canonical fragments below are literal ASCII bytes for C({reason:value}), without BOM or LF; they are hand-derived from C's escaping rules, not future production output. Complete decision expectations preserve the authored expected D's other fields, with only its reason member replaced; independently calculate the decision-domain hash over those expected bytes with hashlib. Report JSON alone adds terminal LF. Existing golden assets are not rewritten.

| Case | Reason value / construction | Independent expected result |
| --- | --- | --- |
| ASCII | `Reviewed` | Accept; 8 UTF-8 bytes; `{"reason":"Reviewed"}` |
| Non-ASCII Latin | U+00E9 (`é`) | Accept; 2 UTF-8 bytes; `{"reason":"\u00e9"}` |
| Turkish | U+0130 followed by `zin` (`İzin`) | Accept; 5 UTF-8 bytes; `{"reason":"\u0130zin"}`; no case folding |
| Supplementary scalar | U+1F600 | Accept; 4 UTF-8 bytes; `{"reason":"\ud83d\ude00"}`; raw UTF-8 and a valid JSON escaped pair yield identical C |
| Non-normalization | U+0065 U+0301 versus U+00E9 | Both accept; respectively 3 and 2 UTF-8 bytes; `{"reason":"e\u0301"}` differs from `{"reason":"\u00e9"}` |
| NUL | JSON reason escape `\u0000`, alone or embedded | INPUT_INVALID / exit2; no decision or other DB mutation; no canonical valid reason |
| Invalid surrogate | JSON escapes `\ud800`, `\udc00`, reversed pair `\udc00\ud800`, or `\ud800A`; API strings containing either surrogate code point | INPUT_INVALID / exit2; reject invalid decoded sequences; no DB mutation; malformed UTF-8 surrogate encodings also reject |
| Empty/lower bound | Empty string; one ASCII `a` | Empty rejects INPUT_INVALID / exit2; one byte accepts |
| ASCII byte boundaries | `a` repeated 1023, 1024, 1025 times | First two accept, 1025 rejects INPUT_INVALID / exit2; expected C is literal prefix `{"reason":"`, that many `a` bytes, then `"}` |
| Multibyte boundaries | U+00E9 repeated 511 times plus `a`; U+00E9 repeated 512 times; latter plus `a` | 1023/1024 bytes accept, 1025 rejects INPUT_INVALID / exit2; accepted C repeats the literal six ASCII bytes `\u00e9`, preserving any final `a` |
| Supplementary byte boundaries | U+1F600 repeated 256 times; same plus `a` | 1024 bytes accepts, 1025 rejects INPUT_INVALID / exit2; accepted C repeats literal `\ud83d\ude00` 256 times |
| Existing control escaping | `A`, then U+000A, then `B`; U+001B alone | Accept; canonical fragments `{"reason":"A\nB"}` and `{"reason":"\u001b"}`; no raw terminal control interpretation |

Raw unescaped JSON control bytes remain syntax errors; allowing a decoded non-NUL control does not relax JSON syntax. Byte counts refer to decoded scalar strings encoded as UTF-8, not the longer ASCII escape representation. Failed validation must precede store access. Successful decisions preserve P/R, reviewer/time/expiry semantics and create no deployment or execution; verify raw canonical_decision/submission_json plus independent digest bytes. For valid exact retries compare original stored bytes and expiry; for changed reason reuse assert conflict and unchanged rows. A persuasive reason with an invalid reviewer or review digest must still fail the existing authorization checks. Product tests must not import production validation/rendering/canonical helpers to construct their expected values.

## Packaging and installation contract

Distribution name approval-continuity-lab, version0.1.0, requires-python ==3.12.*, tested reference patch3.12.14; no claim for other patches until tests. Platform support POSIX macOS/Linux despite pure-Python wheel tag. Standard src layout, setuptools84.0.0 / wheel0.48.0 PEP517 backend, pip26.2.1 bootstrap; no unpinned installer downloads in tests. Build configuration and locks are implementation deliverables, not installed in spec.

Planned build invocation after lock/bootstrap: `.venv/bin/python -B -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .`; sdist via pinned backend's build_sdist through the distribution test harness. Build wheel from both original tree and sdist in clean dirs. Build/bootstrap may use an explicitly prepared local wheelhouse; runtime acceptance and isolated --no-index install require no network. Cold-cache CI must prepare all pinned tools before disabling network for install/runtime tests; a warm developer cache is not evidence.

Package README, DISCOVERY, AGENTS, GOAL and every linked docs/*.md/docs/contracts/docs/fixtures asset in wheel under approval_continuity_lab/documentation preserving their relative layout (root README etc at documentation root); sdist includes source-root equivalents. Runtime scenarios/goldens load via importlib.resources under that package, never cwd/source checkout. Include original MIT LICENSE and license metadata. No tests, caches, DBs, logs or secrets in wheel; sdist includes tests and necessary fixture assets.

Long-description README is a self-contained distribution README with no filesystem-relative Markdown links: links to bundled docs are described as installed resources until a verified repository URL exists. It must retain limits and specification/implementation status truthfully. Source README relative links remain valid in packaged documentation root. Archive checks inspect METADATA/README and bundled docs at actual roots, not assume source layout.

Exact installed smoke: create two fresh virtualenvs outside tree, install wheel with --no-index --no-deps, run `acl --version`, `acl scenario run all --format json`, text D08 and module entrypoint; also install wheel rebuilt from sdist. Verify imported path belongs to environment. Archive link lint: `python3 "$REPO_FACTORY_ROOT/scripts/check_package_links.py" dist/approval_continuity_lab-0.1.0-py3-none-any.whl` and corresponding .tar.gz; set REPO_FACTORY_ROOT to the installed Repo Factory skill directory. Check its --help at execution. This is archive-relative link existence lint only; tests separately check anchors, asset coverage, clean execution and README claims. Never claim remote-link validity from lint.

Evidence: archive member lists/hashes, tool versions, exact install/run exits, stdout/stderr, resource loads, offline proof and link-lint results. No package publish or hosted CI occurs in local tests.
