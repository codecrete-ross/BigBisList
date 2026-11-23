"""Verify the Git objects behind an isolated Forever data-only release."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from tools import forever
from tools.generate_release_notes import parse_changelog
from tools.project import ROOT


VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
CONFIG_VERSION = re.compile(r'^([ \t]*version[ \t]*=[ \t]*")(\d+\.\d+\.\d+)("[ \t]*\r?$)', re.M)
PAYLOAD = "DataForever.lua"
GUIDE_PAYLOAD = "GuideDataForever.lua"
PAYLOADS = {PAYLOAD, GUIDE_PAYLOAD, "GuideRanksForever.lua"}
CANONICAL = "data/canonical/forever/"
LIVE_ACCEPTANCE = CANONICAL + "live_acceptance.json"
DATA_PREFIXES = (CANONICAL, "data/raw/forever/", "data/raw/wowhead/forever/")
METADATA = {"CHANGELOG.md", "Config.lua", "README.md", "RELEASE_NOTES.md"}
POLICY = {CANONICAL + name + ".json" for name in (
    "classes", "phases", "leveling_rules", "leveling_scoring_profiles", "racial_modifiers",
    "scoring_model", "scoring_profiles", "reviewed_builds", "effect_benchmarks",
    "stat_weight_review", "runtime_compatibility",
)} | {LIVE_ACCEPTANCE}


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def commit_id(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()


def tag_commit(root: Path, tag: str) -> str:
    if not VERSION.fullmatch(tag):
        raise ValueError("Expected a numeric release tag")
    return commit_id(root, "refs/tags/" + tag)


def blob(root: Path, commit: str, path: str) -> bytes:
    return git(root, "cat-file", "blob", f"{commit}:{path}")


def artifact_digest(root: Path, commit: str) -> str:
    paths = git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--", "assets")
    assets = [name.decode() for name in paths.split(b"\0") if name]
    return forever.artifact_digest(lambda path: blob(root, commit, path), assets)


def changed_paths(root: Path, before: str, after: str, *paths: str) -> set[str]:
    output = git(root, "diff", "--name-only", "--no-renames", "-z", before, after, "--", *paths)
    return {name.decode("utf-8") for name in output.split(b"\0") if name}


def is_ancestor(root: Path, ancestor: str, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, commit],
                          capture_output=True, check=False).returncode == 0


def config_version(text: str) -> str:
    match, *others = list(CONFIG_VERSION.finditer(text)) or [None]
    if match is None or others:
        raise ValueError("Expected one numeric fallback version in Config.lua")
    return match[2]


def with_config_version(text: str, version: str) -> str:
    config_version(text)
    return CONFIG_VERSION.sub(lambda match: match[1] + version + match[3], text)


def with_readme_version(text: str, previous: str, version: str) -> str:
    return re.sub(rf"(?<=-Version ){re.escape(previous)}(?![\d.])", version,
                  text.replace(f"\x60{previous}\x60", f"\x60{version}\x60"))


def patch_version(previous: str) -> str:
    if not VERSION.fullmatch(previous):
        raise ValueError("Expected a numeric previous release")
    major, minor, patch = previous.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def allowed_data(path: str) -> bool:
    return (path not in POLICY and path.endswith(".json") and path.startswith(DATA_PREFIXES)
            and all(part and not part.startswith(".") and ":" not in part and "\\" not in part
                    for part in path.split("/")))


def verify_patch(root: Path, before: str, after: str, previous: str, version: str) -> set[str]:
    """Check the entire PR or tag delta, including modes and exact metadata edits."""
    before, after = commit_id(root, before), commit_id(root, after)
    if not is_ancestor(root, before, after) or version != patch_version(previous):
        raise ValueError("A Forever data patch must extend its base by one patch version")
    changes = changed_paths(root, before, after)
    forbidden = changes - METADATA - PAYLOADS
    forbidden = sorted(path for path in forbidden if not allowed_data(path))
    if forbidden:
        raise ValueError(f"Changes outside the Forever data release scope: {', '.join(forbidden[:5])}")
    if not (PAYLOADS & changes) or not {"CHANGELOG.md", "RELEASE_NOTES.md"} <= changes:
        raise ValueError("The patch needs changed player data and its release notes")
    entries = git(root, "ls-tree", "-r", "-z", after, "--", *sorted(changes))
    modes = {}
    for entry in filter(None, entries.split(b"\0")):
        metadata, path = entry.split(b"\t", 1)
        modes[path.decode("utf-8")] = metadata.split(b" ", 1)[0]
    if any(modes.get(path) != b"100644" for path in changes):
        raise ValueError("A data patch only adds or updates regular non-executable files")

    old_config = blob(root, before, "Config.lua").decode()
    new_config = blob(root, after, "Config.lua").decode()
    if config_version(old_config) != previous or new_config != with_config_version(old_config, version):
        raise ValueError("Config.lua may change only its fallback version")
    old_readme = blob(root, before, "README.md").decode()
    if blob(root, after, "README.md").decode() != with_readme_version(old_readme, previous, version):
        raise ValueError("README.md may change only release version references")
    old_history = blob(root, before, "CHANGELOG.md").decode().replace("\r\n", "\n")
    new_history = blob(root, after, "CHANGELOG.md").decode().replace("\r\n", "\n")
    if (not old_history.startswith("# Changelog\n\n") or not new_history.startswith("# Changelog\n\n")
            or not new_history.endswith("\n\n" + old_history.removeprefix("# Changelog\n\n"))):
        raise ValueError("A data patch must preserve published changelog text")
    old_notes, new_notes = parse_changelog(old_history), parse_changelog(new_history)
    if old_notes[0].version != previous or new_notes[0].version != version or new_notes[1:] != old_notes:
        raise ValueError("A data patch must prepend exactly one version to the changelog")
    return changes


def baseline_acceptance(tag: str, *, root: Path = ROOT, revision: str = "HEAD") -> dict:
    """Reuse a genuine live test only for the same runtime and reviewed build."""
    result = {"ok": False, "status": "baseline_required", "baseline_tag": tag, "errors": []}
    try:
        baseline = tag_commit(root, tag)
        candidate = commit_id(root, revision)
        if not is_ancestor(root, baseline, candidate):
            raise ValueError("The live-tested tag must be an ancestor of the candidate")
        document = json.loads(blob(root, baseline, LIVE_ACCEPTANCE))
        errors = forever.live_acceptance_errors(
            document, artifact_digest(root, baseline))
        if errors:
            return {**result, "errors": errors}
        rules = json.loads(blob(root, candidate, CANONICAL + "leveling_rules.json"))
        builds = json.loads(blob(root, candidate, CANONICAL + "reviewed_builds.json"))
        if builds["target_client"] != document["client_build"]:
            raise ValueError("The target client build requires a fresh live baseline")
        if rules["review"]["client_build"] != builds["leveling_sources"] or any(
            json.loads(blob(root, candidate, CANONICAL + name + ".json"))["client_build"] != builds["guide_sources"]
            for name in ("guide_equipment", "scoring_model", "effect_benchmarks")
        ):
            raise ValueError("The source build pins changed since live acceptance")
        paths = forever.release_manifest_files(blob(root, baseline, forever.FOREVER_MANIFEST).decode())
        protected = (set(paths) - (PAYLOADS | {"Config.lua"})) | POLICY | {"assets", "lib", ".pkgmeta"}
        changes = changed_paths(root, baseline, candidate, *sorted(protected))
        if changes:
            raise ValueError(f"The live-tested runtime or policy changed: {', '.join(sorted(changes)[:5])}")
        old, new = (blob(root, parent, "Config.lua").decode() for parent in (baseline, candidate))
        if with_config_version(old, "0.0.0") != with_config_version(new, "0.0.0"):
            raise ValueError("Config.lua changed beyond the fallback version")
        return {**result, "ok": True, "status": "scripted_data_only", "baseline_commit": baseline,
                "client_build": document["client_build"], "commit": candidate,
                "artifact_digest": artifact_digest(root, candidate)}
    except (ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        result["errors"].append(str(exc))
        return result
