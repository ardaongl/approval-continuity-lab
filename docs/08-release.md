# Local, audit and release boundaries

Implementation and local acceptance are complete, F1 hardening is independently re-audited PASS, and initial public GitHub publication to `ardaongl/approval-continuity-lab` on `main` is authorized. Hosted success must still be verified for the exact pushed commit. Separate gates:
1. M0_PASS: independent preflight/environment and contract traceability.
2. LOCAL_READY: every local AC01–18 PASS with real final-candidate evidence and installed artifacts; workflow prepared, hosted pending.
3. AUDIT_PASS: independent adversarial read-only review with new negative cases on exact candidate; no blockers. Code or relevant contract changes invalidate affected evidence and prior audit.
4. Publication authorization: exact owner/repo, visibility and permitted create/push/corrective operations. An existing/conflicting remote is a stop, never overwritten.
5. RELEASE_READY: authorized remote points to intended final SHA; actual required hosted workflow completed successfully with head_sha exactly equal to that SHA.

The explicit publication authorization permits local Git/commits, repository creation, initial push and verified narrow CI corrections. PyPI publication, GitHub Release, deployment and unrelated permission changes remain unauthorized. No package publish is needed to test wheel/sdist.

Prepared CI: supported Python3.12.14 on Ubuntu Linux and macOS, full acceptance/process suite and distribution/clean installs, pinned tool bootstrap, offline runtime tests, archive link checks. Runner action revisions are pinned to commit SHAs. An unsupported platform is not a silent skipped matrix job. Mandatory commands must not use continue-on-error or cache-only offline assumptions.

Use fresh/empty caches to prepare complete pinned tool wheelhouse, then --no-index isolated installs; avoid hidden dependency downloads. Rebuild/recheck archive README links in actual wheel/METADATA and sdist layouts. Factory link linter proves local/archive existence only, not execution, external URLs or publication clearance.

Hosted attestation fields: repository URL, branch, final intended commit SHA, remote branch SHA, workflow/run URL, run head_sha, status completed, conclusion success, mandatory jobs/steps with conclusions, acceptance artifacts, known limitations and authorized actions actually taken. Fetch actual run data; self-reported status metadata is insufficient. Old-SHA green runs do not cover later documentation commits.

Avoid tracked self-referential commit attestations: keep final run evidence in ignored .local-verification/final-attestation.json or an external record. If evidence is committed subsequently, that new commit needs its own verified workflow. Do not fabricate a commit SHA before Git exists. Audit/publication phases must reread factory references10/11.

Archive install/link failures block complete distribution readiness. Host runtime/process assumptions and package compatibility must be documented honestly; no unsupported cross-platform universal guarantees. No release claim until all these conditions are met. See [publication verification](PUBLICATION-VERIFICATION.md) for the current evidence boundary.
