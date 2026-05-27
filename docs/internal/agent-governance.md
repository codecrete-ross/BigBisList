# Internal Agent Governance

This playbook expands the root `AGENTS.md` guidance. It is for maintainers and
automation agents, not addon users.

## Repo Map

- Root Lua files are the packaged addon runtime. Keep the root layout because
  CurseForge packaging reads `BigBiSList.toc` from the repository root.
- `Data.lua` is generated runtime data. It should only change as the result of
  canonical data changes and `tools/generate_lua.py`.
- `Config.lua`, `Core.lua`, `DataIndex.lua`, `Widgets.lua`, `UI.lua`,
  `Tooltip.lua`, and `Minimap.lua` divide runtime behavior by responsibility.
- `data/canonical` contains the committed canonical data model used to generate
  runtime data.
- `data/raw/wowhead` contains normalized source snapshots and audit inputs.
- `data/schema` documents expected JSON shapes for key canonical files.
- `tools` contains scrapers, importers, validation, generation, source
  derivation, manifest coverage, reference counts, and parity reporting.
- `tests` contains Python static/runtime-adjacent checks for data, tooling, and
  addon Lua structure.
- `vendor/reference/BIS-TBC-1.15` is a reference addon kept for parity and
  provenance review.

## Change Decisions

- For UI/runtime behavior, edit the smallest responsible Lua module and add or
  adjust static tests when behavior can be asserted without a WoW client.
- For data correctness, prefer source snapshots and importer changes over
  hand-editing large canonical files. Use overrides only for reviewed
  exceptions.
- For generated data, never patch `Data.lua` directly. Change canonical data or
  tooling, then regenerate.
- For release packaging, update `.pkgmeta`, `.toc`, and release docs only when
  the task is explicitly about packaging or release preparation.
- For internal governance, use `AGENTS.md` for concise rules and
  `docs/internal` for deeper policy. Keep `CLAUDE.md` as a pointer only.

## Worktree Discipline

- Start by checking `git status --short --branch`.
- Treat existing modifications as user or prior-agent work. Do not revert them.
- If a required edit touches a dirty file, inspect the current diff first and
  make a narrow additive change that preserves existing work.
- Avoid broad formatting passes unless formatting is the requested task.
- Keep generated files and their source inputs together in one logical change.

## Review Checklist

- The change preserves TBC Anniversary targeting and root addon packaging.
- User-facing docs, addon text, slash commands, saved variables, and globals are
  unchanged unless explicitly requested.
- Data lineage remains traceable through manifest entries, snapshots,
  canonical JSON, overrides, and generated Lua.
- Manual data corrections have an override record with id, target, reason,
  reviewer, reviewed date, and source URL.
- `Data.lua` is current if canonical data changed.
- `.pkgmeta` excludes internal-only docs and development-only directories.
- Relevant tests and validation commands were run, or any skipped command is
  called out with the reason.

## Agent-Authored Work

Agent decisions that matter after the chat ends should be recorded in durable
repo artifacts: commit messages, PR descriptions, review notes, or internal
docs. Chat history is not a substitute for provenance when a future maintainer
needs to understand why a policy, source, override, or generated artifact
changed.
