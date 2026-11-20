"""Build the packed reference ranks embedded in the Forever addon."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.forever_scoring_checks import find_lua51
from tools.project import ROOT, dataset_json, lua_string

OUTPUT = ROOT / "GuideDataForever.lua"
COMPILER = ROOT / "tools/build_forever_guide.lua"
INPUTS = ("DataForever.lua", "ForeverScoring.lua", "ForeverGearRating.lua", "DataIndex.lua",
          "tools/build_forever_guide.lua", "tools/forever_guide_index.py")
BLOCK = 420
CHUNK = 32768
ROW = re.compile(rb'a\[(\d+)\]="(.*)"\r?\n$')


def number(value: int, width: int) -> bytes:
    return bytes(48 + ((value >> (6 * shift)) & 63) for shift in reversed(range(width)))


def contents_digest() -> str:
    digest = sha256()
    for name in INPUTS:
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def compress(data: bytes) -> bytes:
    """Encode short repeated strings using a bounded back reference."""
    latest = {}
    position = 0
    size = len(data)
    output = bytearray()
    while position + 4 <= size:
        key = data[position:position + 4]
        previous = latest.get(key)
        latest[key] = position
        if previous is None:
            output.append(data[position])
            position += 1
            continue
        length = 4
        distance = position - previous
        while length < 67 and position + length < size and data[position + length] == data[previous + length]:
            length += 1
        if length <= 4:
            output.append(data[position])
            position += 1
            continue
        output.extend(b"~" + number(distance, 2) + number(length - 4, 1))
        for index in range(position + 1, position + length):
            latest[data[index:index + 4]] = index
        position += length
    output.extend(data[position:])
    return bytes(output)


def write_array(out, name: str, values: list[bytes]) -> None:
    payload = b"".join(values)
    starts, position = [number(0, 5)], 0
    for value in values:
        position += len(value)
        starts.append(number(position, 5))
    out.write(f"archive.{name}={{\n".encode())
    for index in range(0, len(payload), CHUNK):
        out.write(lua_string(payload[index:index + CHUNK].decode("ascii")).encode() + b",\n")
    out.write(b"}\n")
    # The offsets themselves can be addressed directly as one string.
    out.write(f"archive.{name}Offsets=".encode() + lua_string(b"".join(starts).decode("ascii")).encode() + b"\n")


def pack_archive(part: Path, packed: Path) -> None:
    values, blocks, indices, lines = [], [], {}, []
    with part.open("rb") as incoming:
        for line in incoming:
            match = ROW.fullmatch(line)
            if not match:
                if not line.startswith((b"(function(a)", b"end)(archive.strings)", b"end\n")):
                    lines.append(line)
                continue
            assert int(match[1]) == len(values) + 1
            value = match[2].replace(b"\\\\", b"\\")
            if len(value) > BLOCK:
                refs = [b"~", number(len(value), 4)]
                for offset in range(0, len(value), BLOCK):
                    block = value[offset:offset + BLOCK]
                    index = indices.get(block)
                    if index is None:
                        blocks.append(compress(block))
                        index = len(blocks)
                        indices[block] = index
                    refs.append(number(index, 4))
                value = b"".join(refs)
            values.append(value)
    with packed.open("wb") as out:
        out.writelines(lines)
        write_array(out, "strings", values)
        write_array(out, "blocks", blocks)
        out.write(b"end\n")


def compile_index(lua: str, *, output: Path = OUTPUT) -> None:
    signature = contents_digest()
    names = sorted({key.split("/")[0] for key in dataset_json("forever", "leveling_rules")["spec_policies"]})
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="forever-guide-", dir=build) as staging:
        staging = Path(staging)
        def compile_part(name: str) -> Path:
            raw = staging / (name + ".lua")
            process = subprocess.run([lua, str(COMPILER), name, str(raw), str(ROOT / "DataForever.lua")],
                                     cwd=ROOT, capture_output=True, check=False)
            if process.returncode:
                raise RuntimeError(process.stderr.decode("utf-8", "replace"))
            if name == "catalog":
                result = raw
            else:
                result = staging / (name + ".packed.lua")
                pack_archive(raw, result)
            print(f"{name} Guide index: {result.stat().st_size:,} bytes", flush=True)
            return result

        with ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 1)) as executor:
            parts = list(executor.map(compile_part, ["catalog", *names]))

        digest = sha256()
        for part in parts:
            digest.update(part.read_bytes())
        body_digest = digest.hexdigest()
        if contents_digest() != signature:
            raise ValueError("Forever Guide inputs changed during generation. Rebuild the index with the current inputs.")
        candidate = staging / OUTPUT.name
        with candidate.open("wb") as bundle:
            bundle.write(f"-- Generated Forever Guide {signature} {body_digest}\n".encode())
            for part in parts:
                bundle.write(part.read_bytes())
        candidate.replace(output)


def check_index() -> bool:
    if not OUTPUT.is_file():
        return False
    with OUTPUT.open("rb") as bundle:
        fields = bundle.readline().strip().split()
        if (len(fields) != 6 or fields[:4] != [b"--", b"Generated", b"Forever", b"Guide"]
                or fields[4].decode() != contents_digest()):
            return False
        digest = sha256()
        for line in bundle:
            digest.update(line[:-2] + b"\n" if line.endswith(b"\r\n") else line)
        return digest.hexdigest() == fields[5].decode()


def verify_index(lua: str) -> bool:
    """Rebuild from the trusted compiler before accepting a data-only patch."""
    if not check_index():
        return False
    (ROOT / "build").mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="forever-guide-verify-", dir=ROOT / "build") as directory:
        rebuilt = Path(directory) / OUTPUT.name
        compile_index(lua, output=rebuilt)
        with OUTPUT.open("rb") as published, rebuilt.open("rb") as fresh:
            for line in fresh:
                if published.readline().replace(b"\r\n", b"\n") != line:
                    return False
            return not published.read(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check", action="store_true")
    checks.add_argument("--verify", action="store_true", help="Rebuild and compare the shipped Guide index.")
    parser.add_argument("--lua")
    args = parser.parse_args()
    if args.check:
        current = check_index()
        print(f"{OUTPUT.name} is {'up to date' if current else 'stale. Run tools/forever_guide_index.py'}.")
        return 0 if current else 1
    lua = find_lua51(args.lua)
    if not lua:
        parser.error("A working Lua 5.1 executable is required")
    if args.verify:
        valid = verify_index(lua)
        print(f"{OUTPUT.name} {'matches' if valid else 'differs from'} the rebuilt Guide index.")
        return 0 if valid else 1
    compile_index(lua)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
