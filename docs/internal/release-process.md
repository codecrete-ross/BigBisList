# Release Process

This is the authoritative playbook for maintainers and automation agents
preparing Big BiS List releases. Other governance documents should link here
instead of copying an independent command list. The playbook stays internal;
`.pkgmeta` excludes `docs` from packaged addon artifacts.

## Client Scope

Prepare releases for Forever by default. Anniversary work resumes only at the
user's explicit direction. That direction is required for Anniversary data
review, refreshes, validation, generation, coverage audits, schedule checks,
and live client verification. Keep existing Anniversary compatibility checks
available for work in that scope.

## Version Policy

Use plain numeric Git tags such as `0.6.0`; do not prefix tags with `v`.

- Major release: use for an intentional compatibility break, addon identity
  change, target-client change, saved-variable reset, or another change that
  existing users or packaging automation must handle manually.
- Minor release: use for user-visible features, behavior changes, settings or
  migration changes, data-family expansions, release-process changes, or any
  change that should be announced as more than a correction.
- Patch or point release: use only for compatible fixes, data corrections,
  validation hardening, packaging metadata fixes, or documentation corrections
  that do not introduce new user-facing behavior.

While the addon is still below `1.0.0`, keep the same decision rules. Do not use
`0.x` as permission to hide breaking changes; call out compatibility impact in
the changelog and choose the smallest version that honestly describes the
release.

When multiple changes are included, choose the highest required bump. For
example, a bug fix plus a new filter is a minor release.

## Release Preparation

1. Inspect the worktree with `git status --short --branch` and preserve unrelated
   dirty changes.
2. Review `git log <last-tag>..HEAD` and `git diff --stat <last-tag>..HEAD`.
3. If the user includes Anniversary in the release scope, review official
   Blizzard TBC Anniversary content announcements against
   `data/canonical/phases.json`. Record the authoritative URL and exact UTC
   timestamp for a changed schedule, update the epoch from that same instant,
   and cover the boundary immediately before and at launch. Record that the
   review found no change when applicable.
4. Choose the next version using the version policy above.
5. Prepend one `## VERSION - YYYY-MM-DD` section to the complete `CHANGELOG.md`,
   retaining all earlier releases in descending numeric version order. Describe
   only player-observable addon behavior shipped since the prior release tag.
   Appropriate notes cover UI, commands, settings, compatibility, runtime fixes,
   and addon data or recommendation changes. Never include governance,
   documentation, tests, CI, tooling, refactors, packaging metadata, release
   automation, or contributor workflow changes. Record those development details
   in commits, pull requests, and the internal release evidence. If there are no
   addon behavior changes, use the exact note `- No addon behavior changes.`
   Published entries are preserved; record later behavior changes under the new
   version. Every reachable numeric tag must have a dated entry with bullet notes.
6. Update release-specific README references and the fallback version in
   `Config.lua`.
7. Regenerate the affected client payload when canonical data or generator
   behavior changes. Pass the client explicitly with `--flavor`.
8. Run the release environment's Python with `tools/generate_release_notes.py`.
   Commit the generated `RELEASE_NOTES.md`: it contains all sections sharing the
   current version's exact `MAJOR.MINOR`, including its initial `.0`, newest
   first. Each section remains an incremental account of that version. A new
   minor or major starts a fresh view. Never edit the generated file by hand.
9. Commit release prep changes before running the release gate. The gate
   requires a clean worktree; if a failed check requires an edit, commit the fix
   and run the gate again.

Keep `BigBiSList.toc` on the Anniversary interface line unless the release task
explicitly changes the target client. The `## Version` field should stay
`@project-version@` so CurseForge packaging can substitute the tag version.

## Automated Release Gate

Forever is the default release gate scope. Select `-Flavor anniversary` explicitly for an
authorized Anniversary release. The authoritative gate runs on the final
clean release commit.

Use a dedicated Python 3.10-or-newer virtual environment installed from the
repository's `pyproject.toml` (for example, create the environment and run its
Python with `-m pip install .`). Do not rely on an unrelated global Python whose
installed packages merely happen to satisfy some tests. From the clean release
commit, run:

```powershell
pwsh -File scripts/check-release.ps1 -Version <next-version> -Flavor forever -PythonPath <venv-python> -FullData
```

Pass `-PythonPath <path>` when the release interpreter is not available as
`python`, `python3`, or `py`. The script is fail-fast and non-destructive. It
preflights declared Python dependencies and Lua 5.1 tooling, requires a clean
Git state and consistent release metadata, checks README data counts against
canonical validation, and owns the exact unit, compile, generation, scrape,
coverage, corpus, recommendation, suffix, snapshot, and requirements audit set.
It also runs `tools/generate_release_notes.py --version <next-version> --check`,
which validates the full changelog and compares the generated notes without
writing files. Use a full checkout with all tags; CI uses `fetch-depth: 0`.
The behavior-topic guard catches common development notes, but release review
must still assess whether each entry describes an actual player-visible impact.

The 0.12.3 migration restores earlier history from tags, reconstructs missing
0.3.0/0.4.0 notes, and removes development details. From that baseline onward,
the gate also compares published entries with the prior tag to prevent history
from being silently rewritten. Existing remote tags and release pages are not
changed by the migration.

Omitting `-FullData` is useful for a quicker local check but is not a release
gate. Do not tag from a partial run.

## Manual Release Evidence

Run smoke tests on each client in the release scope. For any
runtime, UI, saved-state, or migration change, record the client build, tester,
date, and outcome. Exercise the affected behavior and, when applicable:

- saved-variable migration from the prior release;
- Endgame/Leveling switching, responsive columns, inspectors, and dropdowns;
- acquisition paths, tooltips, ownership, wishlist, and ignore actions;
- `/bbltest`, `/bbl status`, and `/bbltest perf`.

For the first Forever release, record the
[pilot checks](forever-pilot.md), including quest progress, waypoint behavior,
and the Forever package load list. After automated ingestion, verify that
CurseForge recognizes the Forever package.

Forever source review and live acceptance are separate gates. Reviewed profile
documents may use `source_reviewed` before the user's gameplay session. Standard
local deployment requires both strict data families (`leveling` and `bis_lists`).
The explicit local Forever prerelease command
`scripts/deploy.ps1 -Flavor forever -Prerelease -NoClean` permits uncovered
leveling combinations. It checks leveling for validation errors, requires strict
pre-raid coverage, and verifies generated and installed files. Both Forever
deployment paths also require all 56 talent-aware contexts to pass the
[scoring audit](forever-scoring.md#verification-and-rollout). Public publishing
requires both strict audits and
`data/canonical/forever/live_acceptance.json` to pass
`python tools/scrape_wowhead.py live-acceptance-audit --flavor forever`;
the authoritative `-FullData` gate runs that audit itself.

Record `status: accepted`, the tester, date, client build, supporting evidence
URL, reason, and `artifact_digest`. Obtain the digest from
`tools.forever.release_artifact_digest()` after generation; it covers the
Forever manifest and its listed runtime files. All keys in
`tools.forever.LIVE_ACCEPTANCE_CHECKS` must be true, and `performance` must
include measured `startup_ms` and `first_open_ms`. A later runtime or data
change invalidates that artifact-specific acceptance. Leave this document
pending until the user supplies the actual gameplay results. The weekly
data-only path uses the baseline described below and records its own
scripted verification receipt.

Record the automated gate result, content-schedule review, and in-game result in
the release PR or handoff. A skipped applicable check must include its reason,
risk, owner, and follow-up. Treat an undocumented skip as a failed gate; the
release owner must explicitly accept a documented exception before publishing.

## Publish

After all gates pass, push the release commit, tag it, push the tag, and create
the GitHub release:

```powershell
$version = "<next-version>"
git push origin HEAD:main
git tag $version
git push origin $version

gh release create $version --repo codecrete-ross/BigBisList --title $version --notes-file RELEASE_NOTES.md
```

The generated, player-facing `RELEASE_NOTES.md` is the source for both GitHub
release notes and the `.pkgmeta` `manual-changelog` field. `CHANGELOG.md` remains
the complete source history and is excluded from the installable package.
Public release notes must describe addon behavior only; internal development
work belongs in release
evidence and repository history. The `manual-changelog` field is CurseForge
configuration terminology; CurseForge automatically reads it from the pushed
Git tag through the repository webhook, builds the release file, and publishes
that tag's changelog. Publishing is complete after the repository commands
above; there is no manual CurseForge follow-up step.

Do not manually upload generated zip files, edit a published CurseForge
changelog, or change release metadata through the CurseForge author UI. If
packaging metadata or release notes need correction, update the repository and
ship the correction through a subsequent normal release.

Verify that the GitHub body matches `RELEASE_NOTES.md`, that the tag points at
the validated commit, and that the hosted release gate succeeds. A read-only
check of the automatically published CurseForge file should show the current
minor line's sections and no older minor line; report ingestion as unverified
if the new file is not yet available. This check does not introduce a manual
publishing or correction step.

## Weekly Forever data releases

The **Forever weekly data** workflow runs Wednesdays at 9:25 a.m. Pacific
on `main`. Use its manual dry run to collect and verify from the current
remote `main` without opening a PR or publishing. `compare_build` stages a
different client's evidence separately. Request checkpoints and verified
snapshots are restored from a prior run and retained for 30 days.

The job creates a disposable worktree from `origin/main`. It applies only
complete evidence that passes the existing review rules, then imports and
generates the Forever payload there. Conflicts and stale or missing approvals
stay in the report. Each applicable patch goes through a data-only PR with the
existing required GitHub checks. After merge the job checks the entire diff
since the previous published tag and reruns `-FullData` on the exact clean
commit before publishing. A tag that already points at that commit can resume
the GitHub release. The `release_commit` dispatch input accepts the merged
PR's full SHA for recovery.

Merge the workflow separately from data PRs. The first Forever release uses
artifact-specific gameplay acceptance and both strict audits. After publishing
that release, configure the following repository settings:

- `FOREVER_LIVE_BASELINE_TAG` names the published tag with genuine live
  acceptance for the current client build.
- `FOREVER_RELEASE_APP_CLIENT_ID` and `FOREVER_RELEASE_BOT_LOGIN` identify
  the GitHub App and its bot. Install the App only in this repository with
  Contents and Pull requests write permissions. Store its private key in
  `FOREVER_RELEASE_APP_PRIVATE_KEY`.
- Enable GitHub auto-merge and require the release check on data PRs. Set
  `FOREVER_DATA_AUTO_RELEASE` to `true` after a successful workflow dry run.

The same live-tested baseline covers data-only patches for the same client
build, manifest, runtime, assets, eligibility rules, and scoring configuration.
Records of live tests stay with the baseline tag. The `-BaselineTag` gate
verifies each changed data artifact and records scripted acceptance separately.
Record a fresh live baseline when the client build, runtime, or rules change.

## Convention References

- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
  [Common Changelog](https://common-changelog.org/) inform the durable,
  version-by-version history. Current-minor release notes are this project's
  presentation choice for players installing the latest patch.
- [CurseForge PackageMeta](https://support.curseforge.com/support/solutions/articles/9000197952-preparing-the-packagemeta-file)
  consumes the entire configured changelog file; it does not select a version.
