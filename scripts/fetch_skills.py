#!/usr/bin/env python3
"""
Fetch private skills from a remote bundle URL into .claude/skills/

Used to keep the public repo free of proprietary skill content while still
loading the real skill at deploy time.

Usage:
    python scripts/fetch_skills.py

Environment:
    SKILLS_BUNDLE_URL    - URL to a tar.gz containing skill folders.
                           If unset, this script does nothing (placeholder skill stays active).
    SKILLS_BUNDLE_TOKEN  - Optional bearer token for private URLs (e.g. private GitHub releases).

Bundle format:
    The tar.gz must extract to a directory containing one or more skill folders, e.g.:

        skills-bundle.tar.gz
          └── forensic-price-chart/
              ├── SKILL.md
              ├── references/
              └── assets/
          └── another-skill/
              └── SKILL.md

    Each top-level folder becomes a skill in .claude/skills/

How to host your private bundle (pick one):

    1. Cloudflare R2 / AWS S3 with a signed URL (recommended)
       - Upload skills-bundle.tar.gz
       - Generate a signed URL valid for 7 days
       - Set SKILLS_BUNDLE_URL to that signed URL
       - Refresh quarterly or whenever you update the skill

    2. Private GitHub release asset
       - Make a private repo with a release containing the tar.gz
       - SKILLS_BUNDLE_URL = the asset's API URL (api.github.com/...)
       - SKILLS_BUNDLE_TOKEN = a fine-grained PAT with read access

    3. Self-hosted file server
       - Just need an HTTPS endpoint that returns the tar.gz
       - Optional bearer token for protection

This script runs idempotently — it's safe to run on every deploy.
If SKILLS_BUNDLE_URL is unset, it's a no-op (good for forks/contributors who
don't have access to the private bundle).
"""

import os
import sys
import tarfile
import io
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.absolute()
SKILLS_DIR = BASE_DIR / ".claude" / "skills"


def main():
    url = os.getenv("SKILLS_BUNDLE_URL", "").strip()
    token = os.getenv("SKILLS_BUNDLE_TOKEN", "").strip()

    if not url:
        print("ℹ SKILLS_BUNDLE_URL not set — skipping fetch (placeholder skill remains active)")
        return 0

    print(f"⤓ Fetching skills bundle from: {url[:60]}...")

    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        # GitHub release assets need this content type
        req.add_header("Accept", "application/octet-stream")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"✗ Failed to download bundle: {e}")
        print("  Continuing with placeholder skill")
        return 1

    print(f"✓ Downloaded {len(data) / 1024:.1f} KB")

    # Extract
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            # Safety: validate paths before extracting
            for member in tar.getmembers():
                # Reject absolute paths and ../ traversal
                if member.name.startswith("/") or ".." in Path(member.name).parts:
                    print(f"✗ Refusing to extract suspicious path: {member.name}")
                    return 1
            tar.extractall(SKILLS_DIR)
    except Exception as e:
        print(f"✗ Failed to extract bundle: {e}")
        return 1

    # Report what got extracted
    skills = [d for d in SKILLS_DIR.iterdir() if d.is_dir()]
    print(f"✓ Skills now installed in {SKILLS_DIR}:")
    for s in sorted(skills):
        size = sum(f.stat().st_size for f in s.rglob("*") if f.is_file())
        print(f"    · {s.name} ({size / 1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
