"""Validate the behavior changelog and generate the current minor's release notes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import subprocess
import sys

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.project import ROOT, write_text


VERSION_PATTERN = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
HEADING = re.compile(rf"## (?P<version>{VERSION_PATTERN}) - (?P<date>\d{{4}}-\d{{2}}-\d{{2}})")
NO_BEHAVIOR_CHANGES = "- No addon behavior changes."
# A guard for common mistakes, not a substitute for reviewing player impact.
DEVELOPMENT_TOPICS = re.compile(
    r"\b(?:GitHub|CurseForge|CI|governance|documentation|docs|tooling|packaging)\b"
    r"|\brepositor(?:y|ies)\b|\brefactor(?:ed|ing|s)?\b"
    r"|\b(?:unit|integration|static|release) tests?\b|\btest suite\b"
    r"|\brelease (?:automation|gate|process|workflow)\b|\bcontributor workflows?\b",
    re.IGNORECASE,
)


def version_key(version: str) -> tuple[int, ...]:
    if not re.fullmatch(VERSION_PATTERN, version):
        raise ValueError(f"Invalid plain numeric release version: {version}")
    return tuple(map(int, version.split(".")))


@dataclass(frozen=True)
class Release:
    version: str
    released: date
    body: str

    def markdown(self) -> str:
        return f"## {self.version} - {self.released.isoformat()}\n\n{self.body}"


def assert_behavior_only(text: str) -> None:
    match = DEVELOPMENT_TOPICS.search(text)
    if match:
        raise ValueError(
            "Public notes must describe addon behavior only. "
            f"Move development-only '{match.group()}' details to internal release evidence."
        )


def parse_changelog(text: str) -> list[Release]:
    text = text.replace("\r\n", "\n").strip()
    lines = text.splitlines()
    if not lines or lines[0] != "# Changelog":
        raise ValueError("CHANGELOG.md must start with '# Changelog'.")
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not headings or any(line.strip() for line in lines[1:headings[0]]):
        raise ValueError("CHANGELOG.md must contain dated release sections after its title.")

    releases = []
    seen = set()
    for index, start in enumerate(headings):
        match = HEADING.fullmatch(lines[start])
        if not match:
            raise ValueError(f"Malformed release heading: {lines[start]}")
        version = match["version"]
        if version in seen:
            raise ValueError(f"Duplicate changelog version: {version}")
        seen.add(version)
        end = headings[index + 1] if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start + 1:end]).strip()
        # Headings, blank bullets, or comments alone are not release notes.
        visible_body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        if not re.search(r"(?m)^- [^\s#].*\S|^- [^\s#]$", visible_body):
            raise ValueError(f"Release {version} must have non-empty bullet notes.")
        if re.search(r"(?m)^#{1,2}(?!#)", body):
            raise ValueError(f"Malformed heading inside release {version}.")
        if NO_BEHAVIOR_CHANGES in body and body != NO_BEHAVIOR_CHANGES:
            raise ValueError(f"Release {version} mixes the no-behavior note with other content.")
        assert_behavior_only(body)
        releases.append(Release(version, date.fromisoformat(match["date"]), body))

    keys = [version_key(release.version) for release in releases]
    if keys != sorted(keys, reverse=True):
        raise ValueError("Changelog releases must be in descending numeric version order.")
    return releases


def render_release_notes(releases: list[Release], version: str) -> str:
    current = version_key(version)
    if not releases or releases[0].version != version:
        raise ValueError(f"The newest changelog entry must be {version}; future or missing entries are invalid.")
    selected = [release for release in releases if version_key(release.version)[:2] == current[:2]]
    if f"{current[0]}.{current[1]}.0" not in {release.version for release in selected}:
        raise ValueError("The current minor line is missing its initial .0 release.")
    preamble = (
        f"# Big BiS List {version}\n\n"
        f"Addon behavior changes in the {current[0]}.{current[1]}.x releases, "
        "newest first. Each section describes changes introduced in that version."
    )
    rendered = preamble + "\n\n" + "\n\n".join(release.markdown() for release in selected) + "\n"
    assert_behavior_only(rendered)
    return rendered


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout.strip()


def validate_history(root: Path, releases: list[Release], version: str) -> None:
    if git_output(root, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("Full Git history and tags are required; fetch with depth 0 before the release gate.")
    tags = {
        tag for tag in git_output(root, "tag", "--merged", "HEAD", "--list").splitlines()
        if re.fullmatch(VERSION_PATTERN, tag)
    }
    recorded = {release.version for release in releases}
    missing = tags - recorded
    extra = recorded - tags - {version}
    if missing:
        raise ValueError(f"Missing changelog entries for reachable release tags: {', '.join(sorted(missing, key=version_key))}")
    if extra:
        raise ValueError(f"Changelog versions have no reachable release tag: {', '.join(sorted(extra, key=version_key))}")

    earlier = [tag for tag in tags if version_key(tag) < version_key(version)]
    if not earlier:
        return
    previous = max(earlier, key=version_key)
    # 0.12.3 establishes the restored history. Earlier tags retain their original files.
    if version_key(previous) < (0, 12, 3):
        return
    historical = parse_changelog(git_output(root, "show", f"{previous}:CHANGELOG.md"))
    by_version = {release.version: release for release in releases}
    for release in historical:
        if by_version.get(release.version) != release:
            raise ValueError(f"Published changelog entry {release.version} differs from {previous}.")


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Must match Config.lua; defaults to its fallback version.")
    parser.add_argument("--check", action="store_true", help="Validate without writing; fail on missing or stale release notes.")
    args = parser.parse_args(argv)
    try:
        config = (root / "Config.lua").read_text(encoding="utf-8")
        matches = re.findall(rf'^\s*version\s*=\s*"({VERSION_PATTERN})"\s*$', config, re.MULTILINE)
        if len(matches) != 1:
            raise ValueError("Config.lua must have one plain numeric fallback version.")
        version = args.version or matches[0]
        if version != matches[0]:
            raise ValueError(f"Requested version {version} does not match Config.lua {matches[0]}.")
        releases = parse_changelog((root / "CHANGELOG.md").read_text(encoding="utf-8"))
        rendered = render_release_notes(releases, version)
        validate_history(root, releases, version)
        output = root / "RELEASE_NOTES.md"
        if args.check:
            if not output.is_file():
                raise ValueError("RELEASE_NOTES.md is missing; run tools/generate_release_notes.py.")
            existing = output.read_text(encoding="utf-8").replace("\r\n", "\n")
            assert_behavior_only(existing)
            if existing != rendered:
                raise ValueError("RELEASE_NOTES.md is stale; run tools/generate_release_notes.py.")
            print(f"Release notes and changelog history are valid for {version}.")
        else:
            write_text(output, rendered)
            print(f"Wrote {output}")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Release notes error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
