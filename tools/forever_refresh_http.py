"""Bounded public HTTP collection and durable responses for the Forever refresh."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.parser import BytesHeaderParser
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from tools.project import load_json, write_text


MAX_REQUESTS = 80
COLLECTION_SECONDS = 300
EXACT_REQUEST_RESERVE = 20
EXACT_SECONDS_RESERVE = 60
EVERLOOT_HOURLY_LIMIT = 30
MAX_BODY_BYTES = 64 * 1024 * 1024
REDIRECTS = {301, 302, 303, 307, 308}
WINDOWS_TLS_HOSTS = {"api.github.com", "raw.githubusercontent.com", "www.raidbots.com", "storage.googleapis.com",
                     "ahledger.com", "everloot.app", "eternadex.com", "zephras.com", "nether.wowhead.com", "edge.forgecdn.net"}


def windows_https(executable: Path, url: str, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    args = [str(executable), "--disable", "--silent", "--show-error", "--proto", "=https",
            "--suppress-connect-headers", "--dump-header", "-", "--max-time", f"{timeout:.2f}",
            "--max-filesize", str(MAX_BODY_BYTES)]
    for name, value in headers.items():
        if "\r" in value or "\n" in value:
            raise ValueError("Invalid public HTTP request header")
        args.extend(("--header", f"{name}: {value}"))
    response = subprocess.run([*args, "--", url], capture_output=True, timeout=timeout + 1, check=False)
    if response.returncode:
        raise OSError(response.stderr.decode("utf-8", errors="replace").strip() or f"curl exited {response.returncode}")
    data = response.stdout
    while data.startswith(b"HTTP/"):
        block, separator, body = data.partition(b"\r\n\r\n")
        if not separator or b"\r\n" not in block:
            break
        line, fields = block.split(b"\r\n", 1)
        status = int(line.split()[1])
        if status >= 200:
            return status, BytesHeaderParser().parsebytes(fields), body
        data = body
    raise ValueError("Missing public HTTP response headers")


def timestamp(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed
    return datetime.min.replace(tzinfo=timezone.utc)


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


@contextmanager
def workspace_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "refresh.lock").open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another Forever refresh is running in this directory") from exc
        yield


class Unavailable(Exception):
    def __init__(self, message: str, *, status: int | None = None, retry_at: str | None = None):
        super().__init__(message)
        self.status = status
        self.retry_at = retry_at


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RefreshHTTP:
    def __init__(self, directory: Path, *, online: bool, user_agent: str,
                 opener=None, now=None, monotonic=None, sleep=None):
        self.directory = directory
        self.path = directory / "state.json"
        self.state = load_json(self.path) if self.path.is_file() else {
            "version": 1, "requests": {}, "attempts": [], "cooldown": {},
            "collections": {}, "snapshots": {}, "exact": {},
        }
        if self.state.get("version") != 1:
            raise ValueError("Unsupported Forever refresh checkpoint version")
        self.online = online
        self.user_agent = user_agent
        self.open = opener or build_opener(NoRedirect()).open
        system_curl = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "curl.exe"
        self.curl = system_curl if os.name == "nt" and opener is None and system_curl.is_file() else None
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic or time.monotonic
        self.sleep = sleep or time.sleep
        self.deadline = self.monotonic() + COLLECTION_SECONDS
        self.request_limit = MAX_REQUESTS
        self.started_at = self.now().isoformat()
        self.attempts_before = len(self.state["attempts"])
        self.request_count = 0
        self.last_request = {}
        self.seen = set()

    def checkpoint(self) -> None:
        write_json(self.path, self.state)

    @contextmanager
    def bulk_budget(self, *, reserve_exact: bool):
        deadline, limit = self.deadline, self.request_limit
        if reserve_exact:
            self.deadline -= EXACT_SECONDS_RESERVE
            self.request_limit -= EXACT_REQUEST_RESERVE
        try:
            yield
        finally:
            self.deadline, self.request_limit = deadline, limit

    def _cached(self, receipt: dict) -> bytes:
        content = (self.directory / "responses" / receipt["source_content_digest"]).read_bytes()
        if sha256(content).hexdigest() != receipt["source_content_digest"]:
            raise ValueError(f"Corrupt cached response for {receipt['source_url']}")
        return content

    def _store(self, raw: bytes) -> str:
        checksum = sha256(raw).hexdigest()
        path = self.directory / "responses" / checksum
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
            try:
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        return checksum

    def _check_budget(self, host: str) -> None:
        current = self.now()
        if self.request_count >= min(self.request_limit, MAX_REQUESTS) or self.monotonic() >= self.deadline:
            raise Unavailable("Live collection budget reached")
        blocked_until = self.state["cooldown"].get(host)
        if timestamp(blocked_until) > current:
            raise Unavailable(f"{host} is in cooldown", retry_at=blocked_until)
        if host == "everloot.app":
            cutoff = current - timedelta(hours=1)
            window = sorted(timestamp(row["attempted_at"]) for row in self.state["attempts"]
                            if row["host"] == host and timestamp(row["attempted_at"]) > cutoff)
            if len(window) >= EVERLOOT_HOURLY_LIMIT:
                raise Unavailable("Everloot's hourly request allowance reached",
                                  retry_at=(window[0] + timedelta(hours=1)).isoformat())
        # Pace a host without waiting through a provider cooldown.
        wait = max(0, self.last_request[host] + 0.75 - self.monotonic()) if host in self.last_request else 0
        if self.monotonic() + wait >= self.deadline:
            raise Unavailable("Live collection budget reached")
        if wait:
            self.sleep(wait)

    def _request(self, url: str, headers: dict) -> tuple[int, dict, bytes, dict]:
        host = urlsplit(url).hostname
        self._check_budget(host)
        self.request_count += 1
        self.last_request[host] = self.monotonic()
        attempt = {"source_url": url, "host": host, "attempted_at": self.now().isoformat(), "status": "started"}
        self.state["attempts"].append(attempt)
        self.checkpoint()
        try:
            timeout = min(12, max(0.01, self.deadline - self.monotonic()))
            if self.curl and host in WINDOWS_TLS_HOSTS:
                status, fields, raw = windows_https(self.curl, url, headers, timeout)
                if status == 200 and not raw:
                    raise ValueError("Empty public response")
                return status, fields, raw, attempt
            with self.open(Request(url, headers=headers), timeout=timeout) as response:
                if int(response.status) != 200:
                    raise ValueError(f"Unexpected HTTP {response.status}")
                chunks = bytearray()
                while self.monotonic() < self.deadline:
                    block = response.read1(65536)
                    if not block:
                        break
                    chunks.extend(block)
                    if len(chunks) > MAX_BODY_BYTES:
                        raise ValueError("Public response exceeds the size limit")
                else:
                    raise ValueError("Live collection deadline reached while reading the response")
                if not chunks:
                    raise ValueError("Empty public response")
                size = response.headers.get("Content-Length", "")
                if size.isdecimal() and len(chunks) != int(size):
                    raise ValueError("Truncated public response body")
                return 200, response.headers, bytes(chunks), attempt
        except HTTPError as exc:
            exc.close()
            return exc.code, exc.headers or {}, b"", attempt
        except (OSError, URLError, ValueError, subprocess.TimeoutExpired) as exc:
            attempt.update(status="error", error=str(exc))
            self.checkpoint()
            raise Unavailable(str(exc)) from exc

    def get(self, url: str, *, cycle: str | None = None, immutable: bool = False,
            project_cache: Path | None = None) -> tuple[bytes, dict]:
        original = url
        origin = urlsplit(original)
        if origin.scheme != "https" or not origin.hostname or origin.username or origin.password or origin.port:
            raise ValueError("Expected a public HTTPS source URL")
        saved = self.state["requests"].get(original)
        if saved and (immutable or original in self.seen or (cycle and saved.get("cycle") == cycle)
                      or (not self.online and not cycle)):
            return self._cached(saved), saved
        if not self.online:
            if project_cache and project_cache.is_file():
                raw = project_cache.read_bytes()
                collected_at = datetime.fromtimestamp(project_cache.stat().st_mtime, timezone.utc).isoformat()
                return raw, {"source_url": original, "collected_at": collected_at,
                             "source_content_digest": sha256(raw).hexdigest(), "status": "project_cache"}
            raise Unavailable("No cached response")

        headers = {"User-Agent": self.user_agent}
        if saved and saved.get("etag"):
            headers["If-None-Match"] = saved["etag"]
        if saved and saved.get("last_modified"):
            headers["If-Modified-Since"] = saved["last_modified"]
        for _ in range(4):
            status, response_headers, raw, attempt = self._request(url, headers)
            attempt["status"] = status
            if status in REDIRECTS:
                self.checkpoint()
                target = urlsplit(urljoin(url, response_headers.get("Location", "")))
                if target.scheme != "https" or target.netloc != origin.netloc or target.geturl() == url:
                    raise Unavailable("Unsupported public redirect", status=status)
                url = target.geturl()
                continue
            if status == 200 or (status == 304 and saved):
                if status == 304:
                    raw = self._cached(saved)
                validators = saved if status == 304 else {}
                receipt = {"source_url": original, "response_url": url, "status": status,
                           "collected_at": saved["collected_at"] if status == 304 else self.now().isoformat(),
                           "source_content_digest": self._store(raw), "bytes": len(raw), "cycle": cycle,
                           "etag": response_headers.get("ETag") or validators.get("etag"),
                           "last_modified": response_headers.get("Last-Modified") or validators.get("last_modified")}
                attempt["source_content_digest"] = receipt["source_content_digest"]
                self.state["requests"][original] = receipt
                self.seen.add(original)
                self.checkpoint()
                return raw, receipt
            retry_at = None
            if status in {403, 429, 503}:
                now = self.now()
                retry_after = response_headers.get("Retry-After", "")
                if retry_after.isdecimal():
                    until = now + timedelta(seconds=int(retry_after))
                else:
                    try:
                        until = parsedate_to_datetime(retry_after)
                        if until.tzinfo is None:
                            until = until.replace(tzinfo=timezone.utc)
                    except (TypeError, ValueError):
                        until = now + timedelta(hours={403: 24, 429: 1, 503: 1}[status])
                retry_at = max(now, until).isoformat()
                self.state["cooldown"][origin.hostname] = retry_at
                attempt["retry_at"] = retry_at
            self.checkpoint()
            raise Unavailable(f"HTTP {status}", status=status, retry_at=retry_at)
        raise Unavailable("Too many public redirects")
