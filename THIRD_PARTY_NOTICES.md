# Third-Party Notices

Big BiS List is a distinct addon with its own folder, saved variables, globals,
and release packaging.

## Reference Addon

This repository includes `vendor/reference/BIS-TBC-1.15` as a local reference
for parity checks and provenance review.

Reference project:

- `BIS-TBC-Anniversary`
- CurseForge: https://www.curseforge.com/wow/addons/bis-tbc-anniversary
- Credited names from project metadata: Hellixoid, Dweem, csm_sudo

The reference addon is identified in project documentation as MIT licensed.
Big BiS List preserves attribution to that project while publishing Big BiS
List itself under the All Rights Reserved license in `LICENSE`.

## Embedded Libraries

Big BiS List bundles lightweight WoW addon libraries under `lib/` for
DataBroker launcher and minimap-button integration:

- `LibStub`
- `CallbackHandler-1.0`
- `LibDataBroker-1.1`
- `LibDBIcon-1.0`

Library source headers are preserved in the bundled files.

## Data Sources

Generated release data is derived from audited local snapshots of Wowhead TBC
guide and item/spell pages, plus explicit curated overrides where source data
needed normalization.

Wowhead and World of Warcraft names, item data, spell data, game terminology,
and related trademarks belong to their respective owners.
