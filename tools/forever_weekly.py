"""Prepare and publish approved Forever data patches from a disposable worktree."""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from tools import forever_release as release
from tools.forever import FOREVER_MANIFEST
from tools.project import ROOT, load_json, write_text


MAIN = "refs/remotes/origin/main"
ORIGIN_MAIN = "refs/heads/main"
DATA_BRANCH = "codex/forever-data-"
BUNDLE_REF = "refs/weekly/verified"
SHA = re.compile(r"[0-9a-f]{40}")
BOT = ("-c", "user.name=Big BiS List data", "-c", "user.email=bigbislist-data@users.noreply.github.com")
GIT_AUTH = ("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential")


def command(root: Path, *args: str, log: Path | None = None) -> bytes:
    environment = os.environ.copy()
    if args[0] != "gh":
        environment.pop("GH_TOKEN", None)
        environment.pop("GITHUB_TOKEN", None)
    if log is None:
        return subprocess.check_output(args, cwd=root, env=environment, stderr=subprocess.PIPE)
    with log.open("ab") as handle:
        subprocess.run(args, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT, check=True)
    return b""


def json_file(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def git_text(root: Path, *args: str) -> str:
    return release.git(root, *args).decode().strip()


def fetch_main(root: Path) -> str:
    auth = GIT_AUTH if os.environ.get("GH_TOKEN") else ()
    release.git(root, *auth, "fetch", "--tags", "origin", f"+{ORIGIN_MAIN}:{MAIN}")
    return release.commit_id(root, MAIN)


def checkout(root: Path, directory: Path, commit: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="worktree-", dir=directory))
    release.git(root, "-c", "core.longpaths=true", "worktree", "add", "--detach", str(path), commit)
    return path


def newest_tag(root: Path, commit: str) -> str | None:
    tags = git_text(root, "tag", "--merged", commit, "--list").splitlines()
    return max((tag for tag in tags if release.VERSION.fullmatch(tag)),
               key=lambda tag: tuple(map(int, tag.split("."))), default=None)


def preceding_version(version: str) -> str:
    if not release.VERSION.fullmatch(version):
        raise ValueError("Expected a numeric patch version")
    major, minor, patch = version.split(".")
    if int(patch) == 0:
        raise ValueError("The first minor release needs its own live acceptance")
    return f"{major}.{minor}.{int(patch) - 1}"


def validate_candidate(root: Path, commit: str, baseline: str) -> dict:
    version = release.config_version(release.blob(root, commit, "Config.lua").decode())
    previous = preceding_version(version)
    release.verify_patch(root, release.tag_commit(root, previous), commit, previous, version)
    acceptance = release.baseline_acceptance(baseline, root=root, revision=commit)
    if not acceptance["ok"]:
        raise ValueError("; ".join(acceptance["errors"]))
    return {**acceptance, "version": version, "previous": previous}


def run_gate(worktree: Path, version: str, baseline: str, log: Path) -> None:
    command(worktree, "pwsh", "-NoProfile", "-File", "scripts/check-release.ps1",
            "-Version", version, "-Flavor", "forever", "-FullData", "-BaselineTag", baseline,
            "-PythonPath", sys.executable, log=log)


def review_blocked(report: dict) -> bool:
    exception = report.get("release_exception", {})
    accepted = (exception.get("ok") is True and exception.get("uncovered") == report.get("uncovered_combinations")
                and exception.get("pending_items") == len(report.get("unresolved", [])))
    return bool(report.get("audit_errors") or report.get("conflicts") or any(report.get("review_issues", {}).values())
                or report.get("unclassified_discoveries") or report.get("disappeared_item_ids")
                or ((report.get("uncovered_combinations") or report.get("unresolved")) and not accepted))


def evaluate_leveling(report: dict, worktree: Path, base: str) -> dict:
    from tools import forever_prerelease

    if "gap_rows" in report and report.get("leveling_summary"):
        version = release.config_version(release.blob(worktree, base, "Config.lua").decode())
        exception = forever_prerelease.evaluate(version, report["gap_rows"], report["unresolved"],
                                               report["leveling_summary"], previous=base, root=worktree)
        return {**report, "release_exception": exception}
    return report


def regenerate(worktree: Path, log: Path) -> None:
    command(worktree, sys.executable, "-B", "-m", "tools.forever_guide_routes", "--write", log=log)
    command(worktree, sys.executable, "-B", "-m", "tools.generate_lua", "--flavor", "forever", log=log)


def apply_snapshots(report: dict, state: Path, build: str, *, equipment_only: bool = False) -> int:
    """Promote validated receipts without creating item, route, or ranking approvals."""
    from tools import forever, forever_review_carry as carry, forever_sources as sources
    from tools.project import FOREVER_CANONICAL_DIR, FOREVER_RAW_DIR, dataset_json
    from tools.scrape_wowhead import snapshot_name

    manifest_path = FOREVER_CANONICAL_DIR / "scrape_manifest.json"
    reviews_path = FOREVER_CANONICAL_DIR / "leveling_reviews.json"
    original_manifest, reviews = load_json(manifest_path), load_json(reviews_path)
    manifest = {**original_manifest, "sources": list(original_manifest["sources"])}
    rules = dataset_json("forever", "leveling_rules")
    if build != rules["review"]["client_build"]:
        raise ValueError("Integration requires the exact reviewed Forever build")
    guide_build = dataset_json("forever", "guide_equipment")["client_build"]
    equipment = report.get("equipment", {})
    if equipment and (equipment["build"] != guide_build or equipment["fidelity_errors"]):
        raise ValueError("The equipment batch needs the current Guide build and a passing fidelity audit")
    original = forever.read_snapshots(FOREVER_RAW_DIR)
    registered = forever.registered_urls()
    current = dict(original)
    pending = []
    availability_changed = False
    for entry in report["staged_snapshots"]:
        url = entry["url"]
        address = (state / entry["file"]).resolve()
        if not address.is_relative_to(state / "snapshots"):
            raise ValueError("Staged snapshot path escaped its evidence directory")
        snapshot = load_json(address)
        guide = snapshot.get("page_type") in sources.GUIDE_EVIDENCE_TYPES
        if equipment_only and not guide:
            continue
        if guide and not equipment:
            raise ValueError("Guide evidence requires its equipment audit receipt")
        provider = sources.source_provider(url)
        if (snapshot.get("url") != url or snapshot.get("flavor") != "forever" or not provider
                or snapshot.get("provider", provider) != provider or snapshot.get("client_build") not in (None, guide_build if guide else build)
                or sources.content_digest(snapshot) != entry["digest"]):
            raise ValueError("Staged snapshot did not match its evidence receipt")
        location = FOREVER_RAW_DIR if sources.entity_key(url) else sources.PROVIDER_RAW_DIR / provider
        target = (location / snapshot_name(url)).resolve()
        path = target.relative_to(ROOT).as_posix()
        if path != entry["target"] or not release.allowed_data(path):
            raise ValueError("Staged snapshot did not match its Forever destination")
        current[url] = snapshot
        availability_changed |= not guide
        if url not in registered:
            manifest["sources"].append({"url": url, "provider": provider, "status": "pending_live_review",
                                        "data_family": "item_corpus" if snapshot.get("page_type") == "equipment_facts"
                                        else "acquisition" if guide or sources.entity_key(url) else "leveling_evidence"})
            registered.add(url)
        pending.append((target, snapshot))

    if availability_changed:
        scoped = carry.scoped_reviews(reviews, original, rules)
        updated = carry.carry_additive_catalogs(scoped, original, current)
        if updated != reviews:
            json_file(reviews_path, updated)
    if manifest != original_manifest:
        json_file(manifest_path, manifest)
    for target, snapshot in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        json_file(target, snapshot)
    return len(pending)


def prepare_evidence_patch(worktree: Path, state: Path, cache: Path, report: dict, log: Path, *, equipment_only: bool) -> dict:
    if release.git(worktree, "status", "--porcelain").strip():
        raise ValueError("An evidence patch needs a clean checkout")
    count = apply_snapshots(report, cache, report["build"], equipment_only=equipment_only)
    if not count:
        return {}
    command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", "import", "--flavor", "forever", log=log)
    regenerate(worktree, log)
    command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", "coverage", "--flavor", "forever",
            "--family", "item_corpus", "--summary", "--strict", log=log)
    if not equipment_only:
        version = release.config_version((worktree / "Config.lua").read_text(encoding="utf-8"))
        for family in ("bis_lists", "leveling"):
            args = ["--release-version", version] if family == "leveling" else []
            command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", "coverage", "--flavor", "forever",
                    "--family", family, "--summary", "--strict", *args, log=log)
        command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", "scoring-audit", "--flavor", "forever",
                "--strict", log=log)
    patch = state / ("equipment.patch" if equipment_only else "verified.patch")
    with tempfile.TemporaryDirectory(dir=state) as directory:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(directory) / "index")}
        subprocess.run(["git", "read-tree", "HEAD"], cwd=worktree, env=env, check=True)
        subprocess.run(["git", "add", "-A", "--", "."], cwd=worktree, env=env, check=True)
        changed = subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z", "HEAD"],
                                          cwd=worktree, env=env).decode().split("\0")
        if any(path and path not in release.PAYLOADS and not release.allowed_data(path) for path in changed):
            raise ValueError("The evidence patch contains changes outside approved Forever data")
        candidate = Path(directory) / patch.name
        with candidate.open("wb") as output:
            subprocess.run(["git", "diff", "--cached", "--binary", "HEAD"], cwd=worktree, env=env, stdout=output, check=True)
        candidate.replace(patch)
    return {"equipment_patch": patch.name, "equipment_snapshots": count} if equipment_only else {"verified_patch": patch.name, "verified_snapshots": count}


def prepare_patch(worktree: Path, state: Path, report: dict, baseline: str, previous: str, today: str, log: Path) -> dict:
    from tools.forever_refresh_http import write_json

    write_json(state / "integration.json", report)
    command(worktree, sys.executable, "-B", "-m", "tools.forever_weekly", "apply",
            "--state-dir", str(state), log=log)
    command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", "import", "--flavor", "forever", log=log)
    regenerate(worktree, log)
    if not release.git(worktree, "diff", "--name-only", "HEAD", "--", *sorted(release.PAYLOADS)).strip():
        return {"status": "unchanged", "reason": "Generated player data is unchanged"}

    version = release.patch_version(previous)
    config = worktree / "Config.lua"
    readme = worktree / "README.md"
    changelog = worktree / "CHANGELOG.md"
    write_text(config, release.with_config_version(config.read_text(encoding="utf-8"), version))
    write_text(readme, release.with_readme_version(readme.read_text(encoding="utf-8"), previous, version))
    history = changelog.read_text(encoding="utf-8")
    entry = f"## {version} - {today}\n\n- Updated WoW Forever gearing data.\n\n"
    write_text(changelog, "# Changelog\n\n" + entry + history.removeprefix("# Changelog\n\n"))
    command(worktree, sys.executable, "-B", "-m", "tools.generate_release_notes", "--version", version, log=log)
    base = release.commit_id(worktree, "HEAD")
    # This worktree was checked out detached at origin/main and is owned by this
    # run. Verify the finished commit before letting it reach the writer.
    release.git(worktree, "add", "-A", "--", ".")
    release.git(worktree, *BOT, "commit", "-m", f"Refresh Forever gear data for {version}")
    commit = release.commit_id(worktree, "HEAD")
    release.verify_patch(worktree, base, commit, previous, version)
    receipt = validate_candidate(worktree, commit, baseline)
    run_gate(worktree, version, baseline, log)
    tree = git_text(worktree, "rev-parse", f"{commit}^{{tree}}")
    return {**receipt, "status": "ready", "base": base, "tree": tree}


def prepare(root: Path, state: Path, baseline: str, today: str, *, online: bool, comparison: str | None) -> dict:
    log = state / "prepare.log"
    if comparison and not re.fullmatch(r"1\.60\.\d+\.\d+", comparison):
        raise ValueError("Expected a Forever comparison build such as 1.60.1.70959")
    base = fetch_main(root)
    worktree = checkout(root, state, base)
    cache = state / "cache"
    if not (worktree / FOREVER_MANIFEST).is_file():
        return {"base": base, "status": "blocked", "reason": "The reviewed Forever port must reach main before intake"}
    report_dir = cache / "compare" / comparison if comparison else cache
    args = ["refresh-availability", "--flavor", "forever", "--state-dir", str(cache)]
    if online:
        args.append("--online")
    if comparison:
        args.extend(("--compare-build", comparison))
    command(worktree, sys.executable, "-B", "-m", "tools.scrape_wowhead", *args, log=log)
    report = load_json(report_dir / "report.json")
    summary = {"base": base, "build": report["build"], "attempts": report["http_attempts"],
               "new_snapshots": report["new_snapshot_count"], "uncovered": report["uncovered_combinations"],
               "stage_seconds": report.get("stage_seconds", {}), "state_path": str(report_dir)}
    if comparison:
        return {**summary, "status": "comparison", "comparison": report["build_comparison"]["status"]}
    report = evaluate_leveling(report, worktree, base)
    summary["release_exception"] = report.get("release_exception")
    if review_blocked(report):
        equipment_patch = {}
        if report.get("equipment") and not report["equipment"]["fidelity_errors"]:
            # Use the checkout's paths even if this prepare call came from a
            # different clone. Never update the source checkout.
            try:
                output = command(worktree, sys.executable, "-B", "-m", "tools.forever_weekly", "apply",
                                 "--equipment-only", "--write-patch", str(state), "--state-dir", str(report_dir))
                equipment_patch = json.loads(output)
            except (ValueError, subprocess.CalledProcessError) as exc:
                equipment_patch = {"equipment_error": str(exc)[:420]}
        return {**summary, "status": "blocked", "reason": "Evidence, approvals, or coverage need review",
                **equipment_patch,
                "review_groups": [{"fact": row["missing_fact"], "item_ids": row["item_ids"][:5]}
                                  for row in report.get("review_groups", [])[:5]]}
    if not report["staged_snapshots"]:
        return {**summary, "status": "unchanged", "reason": "No changed evidence"}
    previous = newest_tag(root, base)
    if not (baseline and previous and release.baseline_acceptance(baseline, root=root, revision=base)["ok"]):
        output = command(worktree, sys.executable, "-B", "-m", "tools.forever_weekly", "apply",
                         "--write-patch", str(state), "--state-dir", str(report_dir))
        return {**summary, "status": "review", "reason": "Verified evidence for the first live-tested release",
                **json.loads(output)}
    if release.config_version(release.blob(root, base, "Config.lua").decode()) != previous:
        return {**summary, "status": "blocked", "reason": "Main contains an unpublished release candidate"}
    try:
        return {**summary, **prepare_patch(worktree, cache, report, baseline, previous, today, log)}
    except (ValueError, subprocess.CalledProcessError) as exc:
        return {**summary, "status": "blocked", "reason": f"Production checks need review. See {log.name}.",
                "detail": str(exc)[:420]}


def gh_json(root: Path, *args: str):
    return json.loads(command(root, "gh", *args))


def published(root: Path, tag: str) -> dict | None:
    result = subprocess.run(["gh", "release", "view", tag, "--json", "tagName,isDraft,body"],
                            cwd=root, capture_output=True, check=False)
    if result.returncode == 0:
        return json.loads(result.stdout)
    if b"release not found" in result.stderr.lower() or b"http 404" in result.stderr.lower():
        return None
    raise subprocess.CalledProcessError(result.returncode, result.args, stderr=result.stderr)


def author_login(login: str) -> str:
    # gh pr list reports GitHub App authors as app/slug. REST uses slug[bot].
    return login[4:] + "[bot]" if login.startswith("app/") else login


def transfer_candidate(root: Path, state: Path, *, restore: bool) -> None:
    receipt = load_json(state / "weekly.json")
    if receipt["status"] != "ready":
        raise ValueError("A checked data candidate is required for transfer")
    sha, base = checked_sha(receipt["commit"]), checked_sha(receipt["base"])
    bundle = str(state / "candidate.bundle")
    if restore:
        release.git(root, "fetch", bundle, BUNDLE_REF)
        if release.commit_id(root, "FETCH_HEAD") != sha:
            raise ValueError("The bundle does not contain the checked commit")
    if git_text(root, "rev-parse", sha + "^") != base or git_text(root, "rev-parse", sha + "^{tree}") != receipt["tree"]:
        raise ValueError("The candidate differs from its verification receipt")
    if not restore:
        release.git(root, "update-ref", BUNDLE_REF, sha)
        release.git(root, "bundle", "create", bundle, BUNDLE_REF, "^" + base)


def submit(root: Path, state: Path, baseline: str, today: str, author: str) -> dict:
    receipt_path = state / "weekly.json"
    result = load_json(receipt_path)
    if result["status"] != "ready":
        return result
    main = fetch_main(root)
    if main != result["base"]:
        # Reuse collected responses. A changed main must never acquire another
        # worktree's files or continue under the old release receipt.
        result = prepare(root, state, baseline, today, online=False, comparison=None)
        json_file(receipt_path, result)
        main = fetch_main(root)
        if result["status"] != "ready" or main != result["base"]:
            return {**result, "status": "blocked", "reason": "Main advanced during data integration"}
    commit = checked_sha(result["commit"])
    version, previous = result["version"], result["previous"]
    release.verify_patch(root, main, commit, previous, version)
    validate_candidate(root, commit, baseline)
    last = published(root, previous)
    live = published(root, baseline)
    if not last or last["isDraft"] or not live or live["isDraft"] or newest_tag(root, main) != previous:
        raise ValueError("The preceding release must be published and current")
    tree = git_text(root, "rev-parse", f"{commit}^{{tree}}")
    branch = DATA_BRANCH + version + "-" + tree[:12]
    if not author:
        raise ValueError("The weekly PR needs the authenticated workspace account")
    pulls = gh_json(root, "pr", "list", "--base", "main", "--state", "open", "--limit", "100",
                    "--json", "number,url,headRefOid,headRefName,author,isCrossRepository")
    existing = [row for row in pulls if row["headRefName"] == branch and not row["isCrossRepository"]]
    if existing:
        pr = existing[0]
        if author_login(pr["author"]["login"]) != author:
            raise ValueError("The existing release PR belongs to another author")
        remote = checked_sha(pr["headRefOid"])
        release.git(root, *GIT_AUTH, "fetch", "origin", f"refs/heads/{branch}")
        if (git_text(root, "rev-parse", f"{remote}^{{tree}}") != tree
                or git_text(root, "rev-parse", f"{remote}^") != main):
            raise ValueError("An existing data branch does not match the verified candidate")
        commit = remote
    else:
        remote_ref = f"refs/heads/{branch}"
        if git_text(root, *GIT_AUTH, "ls-remote", "--heads", "origin", remote_ref):
            release.git(root, *GIT_AUTH, "fetch", "origin", remote_ref)
            remote = release.commit_id(root, "FETCH_HEAD")
            if git_text(root, "rev-parse", f"{remote}^{{tree}}") != tree or git_text(root, "rev-parse", f"{remote}^") != main:
                raise ValueError("The existing data branch differs from the verified patch")
            commit = remote
        else:
            release.git(root, *GIT_AUTH, "push", "origin", f"{commit}:{remote_ref}")
        body = state / "pr.md"
        write_text(body, f"Scripted Forever data refresh for {version}.\n\nVerified from {main} against live-tested {baseline}.\n")
        command(root, "gh", "pr", "create", "--base", "main", "--head", branch, "--title",
                f"Refresh Forever gear data for {version}", "--body-file", str(body))
        pr = gh_json(root, "pr", "view", branch, "--json", "number,url,headRefOid")
    if pr["headRefOid"] != commit:
        raise ValueError("The PR head changed after verification")
    for row in pulls:
        if (row["number"] != pr["number"] and not row["isCrossRepository"]
                and author_login(row["author"]["login"]) == author and row["headRefName"].startswith(DATA_BRANCH + version + "-")):
            command(root, "gh", "pr", "close", str(row["number"]))
    command(root, "gh", "pr", "merge", str(pr["number"]), "--auto", "--squash", "--match-head-commit", commit)
    return {**result, "status": "submitted", "commit": commit, "pr": pr["url"], "number": pr["number"]}


def checked_sha(value: str) -> str:
    if not SHA.fullmatch(value):
        raise ValueError("Expected an exact Git commit SHA")
    return value


def associated_pr(root: Path, repository: str, commit: str, author: str, number: int | None) -> dict | None:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not author:
        raise ValueError("The repository and authenticated workspace account are required")
    pulls = ([gh_json(root, "api", f"repos/{repository}/pulls/{number}")] if number
             else gh_json(root, "api", f"repos/{repository}/commits/{commit}/pulls"))
    for pull in pulls:
        if (pull.get("merged_at") and pull.get("merge_commit_sha") == commit
                and pull["base"]["ref"] == "main" and pull["head"]["ref"].startswith(DATA_BRANCH)
                and (pull["head"].get("repo") or {}).get("full_name") == repository
                and pull["user"]["login"] == author):
            return pull
    return None


def verify_merge(root: Path, state: Path, commit: str, baseline: str, repository: str, author: str,
                 number: int | None = None) -> dict:
    commit = checked_sha(commit)
    main = fetch_main(root)
    if not release.is_ancestor(root, commit, main):
        raise ValueError("The publishing commit must be on origin/main")
    pull = associated_pr(root, repository, commit, author, number)
    if not pull:
        return {"status": "ignored", "commit": commit}
    result = validate_candidate(root, commit, baseline)
    if newest_tag(root, main) not in {result["previous"], result["version"]}:
        raise ValueError("A different release superseded this patch")
    worktree = checkout(root, state, commit)
    run_gate(worktree, result["version"], baseline, state / "publish.log")
    return {**result, "status": "verified", "pr": pull["number"]}


def publish(root: Path, state: Path, baseline: str) -> dict:
    receipt = load_json(state / "publish.json")
    if receipt["status"] != "verified":
        raise ValueError("Publishing requires a clean-commit full verification receipt")
    sha = checked_sha(receipt["commit"])
    main = fetch_main(root)
    result = validate_candidate(root, sha, baseline)
    version, previous = result["version"], result["previous"]
    if (not release.is_ancestor(root, sha, main) or receipt != {**result, "status": "verified", "pr": receipt["pr"]}
            or newest_tag(root, main) not in {previous, version}):
        raise ValueError("The release receipt no longer matches main and its tag history")
    last = published(root, previous)
    live = published(root, baseline)
    if not last or last["isDraft"] or not live or live["isDraft"]:
        raise ValueError("The preceding release must be published")
    ref = f"refs/tags/{version}"
    if git_text(root, *GIT_AUTH, "ls-remote", "--tags", "origin", ref):
        if release.tag_commit(root, version) != sha:
            raise ValueError("The release tag names a different commit")
    else:
        # Push an exact commit with a normal, non-forced tag update. A competing
        # tag cannot be replaced, even if it arrives after the remote check.
        try:
            local = release.tag_commit(root, version)
        except subprocess.CalledProcessError:
            release.git(root, *BOT, "tag", "-a", version, sha, "-m", f"Big BiS List {version}")
        else:
            if local != sha:
                raise ValueError("A local release tag names a different commit")
        release.git(root, *GIT_AUTH, "push", "origin", f"{ref}:{ref}")
    notes = release.blob(root, sha, "RELEASE_NOTES.md").decode()
    existing = published(root, version)
    if existing is None:
        note_path = state / "release-notes.md"
        write_text(note_path, notes)
        command(root, "gh", "release", "create", version, "--verify-tag", "--title", version,
                "--notes-file", str(note_path))
        existing = published(root, version)
    if not existing or existing["isDraft"] or existing["tagName"] != version or existing["body"].strip() != notes.strip():
        raise ValueError("GitHub release notes do not match the verified tag")
    return {**receipt, "status": "published"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "apply", "bundle", "restore", "submit", "eligible", "verify-merge", "publish"))
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--baseline-tag", default="")
    parser.add_argument("--compare-build")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--equipment-only", action="store_true", help="Apply verified Guide evidence independently of leveling approvals.")
    parser.add_argument("--write-patch", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "codecrete-ross/BigBisList"))
    parser.add_argument("--pr-number", type=int)
    args = parser.parse_args(argv)
    try:
        if args.action == "eligible":
            print(json.dumps(validate_candidate(ROOT, release.commit_id(ROOT, args.commit), args.baseline_tag)))
            return 0
        if not args.state_dir:
            raise ValueError("--state-dir is required")
        state = args.state_dir.resolve()
        state.mkdir(parents=True, exist_ok=True)
        today = (args.date or date.today()).isoformat()
        if args.action in ("bundle", "restore"):
            transfer_candidate(ROOT, state, restore=args.action == "restore")
            return 0
        if args.action == "apply":
            report = load_json(state / ("report.json" if args.write_patch or args.equipment_only else "integration.json"))
            if not args.equipment_only:
                report = evaluate_leveling(report, ROOT, release.commit_id(ROOT, "HEAD"))
            if report.get("build_comparison") or (not args.equipment_only and review_blocked(report)):
                raise ValueError("Only complete reviewed-build batches can be integrated")
            if args.write_patch:
                out = args.write_patch.resolve()
                result = prepare_evidence_patch(ROOT, out, state, report, out / "prepare.log", equipment_only=args.equipment_only)
                print(json.dumps(result, sort_keys=True))
            else:
                print(json.dumps({"applied": apply_snapshots(report, state, report["build"], equipment_only=args.equipment_only)}))
            return 0
        if args.action in {"submit", "verify-merge"}:
            author = command(ROOT, "gh", "api", "user", "--jq", ".login").decode().strip()
        if args.action == "prepare":
            result = prepare(ROOT, state, args.baseline_tag, today, online=args.online, comparison=args.compare_build)
        elif args.action == "submit":
            result = submit(ROOT, state, args.baseline_tag, today, author)
        elif args.action == "verify-merge":
            result = verify_merge(ROOT, state, args.commit, args.baseline_tag, args.repository, author,
                                  args.pr_number)
            json_file(state / "publish.json", result)
        else:
            result = publish(ROOT, state, args.baseline_tag)
            json_file(state / "released.json", result)
        if args.action == "prepare":
            json_file(state / "weekly.json", result)
        elif args.action == "submit":
            json_file(state / "submitted.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"Forever weekly release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
