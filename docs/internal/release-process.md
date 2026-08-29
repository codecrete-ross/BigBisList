# Release Process

This is the authoritative playbook for maintainers and automation agents
preparing Big BiS List releases. Other governance documents should link here
instead of copying an independent command list. The playbook stays internal;
`.pkgmeta` excludes `docs` from packaged addon artifacts.

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
3. Review official Blizzard TBC Anniversary content announcements against
   `data/canonical/phases.json`. Record the authoritative URL and exact UTC
   timestamp for a changed schedule, update the epoch from that same instant,
   and cover the boundary immediately before and at launch. Record that the
   review found no change when applicable.
4. Choose the next version using the version policy above.
5. Replace `CHANGELOG.md` with one dated section for the new version containing
   only changes shipped since the prior release tag. Do not append older
   release sections; each tag preserves its own historical changelog.
6. Update release-specific README references and the fallback version in
   `Config.lua`.
7. Regenerate `Data.lua` only when canonical data or generator behavior changed.
   Never hand-edit generated Lua.
8. Commit release prep changes before running the release gate. The gate
   requires a clean worktree; if a failed check requires an edit, commit the fix
   and run the gate again.

Keep `BigBiSList.toc` on the Anniversary interface line unless the release task
explicitly changes the target client. The `## Version` field should stay
`@project-version@` so CurseForge packaging can substitute the tag version.

## Automated Release Gate

Use a dedicated Python 3.10-or-newer virtual environment installed from the
repository's `pyproject.toml` (for example, create the environment and run its
Python with `-m pip install .`). Do not rely on an unrelated global Python whose
installed packages merely happen to satisfy some tests. From the clean release
commit, run:

```powershell
pwsh -File scripts/check-release.ps1 -Version <next-version> -PythonPath <venv-python> -FullData
```

Pass `-PythonPath <path>` when the release interpreter is not available as
`python`, `python3`, or `py`. The script is fail-fast and non-destructive. It
preflights declared Python dependencies and Lua 5.1 tooling, requires a clean
Git state and consistent release metadata, checks README data counts against
canonical validation, and owns the exact unit, compile, generation, scrape,
coverage, corpus, recommendation, suffix, snapshot, and requirements audit set.

Omitting `-FullData` is useful for a quicker local check but is not a release
gate. Do not tag from a partial run.

## Manual Release Evidence

Automated checks do not replace a TBC Anniversary client smoke test. For any
runtime, UI, saved-state, or migration change, record the client build, tester,
date, and outcome. Exercise the affected behavior and, when applicable:

- saved-variable migration from the prior release;
- Endgame/Leveling switching, responsive columns, inspectors, and dropdowns;
- acquisition paths, tooltips, ownership, wishlist, and ignore actions;
- `/bbltest`, `/bbl status`, and `/bbltest perf`.

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

gh release create $version --repo codecrete-ross/BigBisList --title $version --notes-file CHANGELOG.md
```

The release-only `CHANGELOG.md` is the source for both GitHub release notes and
the `.pkgmeta` `manual-changelog` field. That field is CurseForge configuration
terminology; CurseForge automatically reads it from the pushed Git tag through
the repository webhook, builds the release file, and publishes that tag's
changelog. Publishing is complete after the repository commands above; there is
no manual CurseForge follow-up step.

Do not manually upload generated zip files, edit a published CurseForge
changelog, or change release metadata through the CurseForge author UI. If
packaging metadata or release notes need correction, update the repository and
ship the correction through a subsequent normal release.
