#!/usr/bin/env python3
"""Lightweight local secret scanner for pre-commit.

Scans staged/all-file inputs from pre-commit for high-signal secret patterns.
This avoids pre-commit virtualenv bootstrapping issues on some Windows/Python
combinations while still providing useful local secret guardrails.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# High-signal patterns only to keep false positives manageable.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "AWS Secret Access Key assignment",
        re.compile(r"(?i)aws(.{0,20})?(secret|access)?.{0,20}[:=].{0,4}[A-Za-z0-9/+=]{40}"),
    ),
    (
        "GitHub token",
        re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    ),
    (
        "Private key header",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----"),
    ),
]

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".pyd",
    ".so",
    ".a",
    ".o",
    ".bin",
}


def should_scan(path: pathlib.Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    return path.suffix.lower() not in SKIP_EXTENSIONS


def scan_file(path: pathlib.Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        findings.append(f"{path}: read_error: {exc}")
        return findings

    for label, pattern in PATTERNS:
        if pattern.search(text):
            findings.append(f"{path}: possible_secret: {label}")
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)

    findings: list[str] = []
    for name in args.files:
        path = pathlib.Path(name)
        if should_scan(path):
            findings.extend(scan_file(path))

    if findings:
        print("Secret scan failed. Potential secrets detected:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
