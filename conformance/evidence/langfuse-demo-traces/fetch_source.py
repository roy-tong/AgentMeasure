#!/usr/bin/env python3
"""Fetch the pinned source traces for this evidence case.

Downloads the three files from the pinned langfuse/langfuse commit.
The raw URLs below are commit-pinned and immutable.

We do not redistribute these files (multi-part upstream license); see
PROVENANCE.md. Files land in ./source/ — created if needed.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

PIN = "ea3c905cd535"
BASE = (
    "https://raw.githubusercontent.com/langfuse/langfuse/"
    f"{PIN}/packages/shared/scripts/seeder/utils/framework-traces/"
)
FILES = [
    "langgraph-2025-08-22.json",
    "openai-agents-2025-09-30.json",
    "pydantic-ai-tools-2025-12-04.json",
]


def main() -> int:
    here = Path(__file__).parent
    src = here / "source"
    src.mkdir(exist_ok=True)
    for name in FILES:
        url = BASE + name
        dest = src / name
        if dest.exists():
            print(f"have  {name}")
            continue
        print(f"fetch {url}")
        urllib.request.urlretrieve(url, dest)  # noqa: S310 (pinned https URL)
        print(f"  -> {dest.relative_to(here)} ({dest.stat().st_size} bytes)")
    print("done. Pinned commit:", PIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
