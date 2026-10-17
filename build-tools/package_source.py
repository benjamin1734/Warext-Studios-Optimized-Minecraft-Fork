#!/usr/bin/env python3
"""Pack the complete patched Warext 26.3 source tree for a GitHub Release.

Run after applyAllPatches and patch_engine_263.py, before or after JAR creation.
Generated source must be included; Gradle caches and compiled build output must not.
"""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "build-tools" / "VERSION").read_text(encoding="utf-8").strip()
UPSTREAM = (ROOT / "build-tools" / "UPSTREAM_REF").read_text(encoding="utf-8").strip()
OUT = ROOT / "artifacts" / f"Warext-Server-Engine-{VERSION}-source.zip"
PREFIX = f"Warext-Server-Engine-{VERSION}-source"

# Derived/compiled files are not source. Excluding caches keeps the release
# portable and avoids bundling machine-specific state and transient credentials.
SKIP_DIRS = {
    ".git", ".gradle", ".idea", ".vscode", "__pycache__", "node_modules",
    "build", "run", "runs", "logs", "cache", "caches",
}
SKIP_FILES = {".DS_Store", "Thumbs.db"}

def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"

def iter_files(root: Path):
    for path, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs
            if d not in SKIP_DIRS and not (Path(path) / d).is_symlink()
        )
        for filename in sorted(files):
            item = Path(path) / filename
            if filename in SKIP_FILES or item.is_symlink() or not item.is_file():
                continue
            yield item

def main() -> None:
    if not (ROOT / "upstream-src").is_dir():
        sys.exit("Cannot package: generated upstream-src tree is missing")
    important = [
        ROOT / "build-tools" / "patch_engine_263.py",
        ROOT / "upstream-src" / "leaf-server" / "src" / "minecraft"
        / "java" / "net" / "minecraft" / "server" / "level" / "ServerLevel.java",
        ROOT / "upstream-src" / "paper-server" / "src" / "main"
        / "java" / "com" / "destroystokyo" / "paper"
        / "entity" / "PaperPathfinder.java",
    ]
    missing = [str(f.relative_to(ROOT)) for f in important if not f.is_file()]
    if missing:
        sys.exit(f"Refusing incomplete source archive; missing: {missing}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    java_count = 0
    uncompressed = 0
    with zipfile.ZipFile(
        OUT, "w", compression=zipfile.ZIP_DEFLATED,
        compresslevel=6, allowZip64=True
    ) as archive:
        for name in ("upstream-src", "build-tools", ".github"):
            for item in iter_files(ROOT / name):
                relative = item.relative_to(ROOT).as_posix()
                archive.write(item, f"{PREFIX}/{relative}")
                file_count += 1
                java_count += relative.endswith(".java")
                uncompressed += item.stat().st_size
        for name in ("README.md", "RELEASE_NOTES.md", "UPSTREAM_COMMIT.txt"):
            item = ROOT / name
            if item.is_file():
                archive.write(item, f"{PREFIX}/{name}")
                file_count += 1
                uncompressed += item.stat().st_size

        manifest = (
            "Warext Server Engine - Complete patched source release\n"
            f"Version: {VERSION}\n"
            f"Fork build commit: {git_sha()}\n"
            f"Pinned Leaf upstream: {UPSTREAM}\n"
            "Contents: patched Leaf/Paper Java sources, Gradle build scripts,\n"
            "Warext performance patch engine, CI workflow and documentation.\n"
            "Excluded: Git history, Gradle caches, generated class/JAR files,\n"
            "temporary test servers and other build artifacts.\n"
        )
        archive.writestr(f"{PREFIX}/SOURCE_MANIFEST.txt", manifest)

    if java_count < 1000:
        OUT.unlink(missing_ok=True)
        sys.exit(f"Refusing suspiciously incomplete source archive: {java_count} Java files")
    with zipfile.ZipFile(OUT, "r") as archive:
        names = set(archive.namelist())
        for required in important:
            expected = f"{PREFIX}/{required.relative_to(ROOT).as_posix()}"
            if expected not in names:
                sys.exit(f"Missing from source archive: {expected}")
        invalid = archive.testzip()
        if invalid is not None:
            sys.exit(f"Corrupt source archive member: {invalid}")

    print(f"Source archive: {OUT}")
    print(f"Files: {file_count} (Java source: {java_count})")
    print(f"Uncompressed bytes: {uncompressed}")
    print(f"ZIP bytes: {OUT.stat().st_size}")

if __name__ == "__main__":
    main()
