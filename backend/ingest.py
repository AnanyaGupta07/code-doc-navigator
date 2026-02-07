"""
Code ingestion module.

- Clones a GitHub repo
- Recursively reads source files (.py, .java, .js)
- Ignores .git, node_modules, build, dist
- Returns list of {"file_path": "...", "raw_code": "..."}
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Set
import json
import sys


DEFAULT_EXTENSIONS: Set[str] = {".py", ".java", ".js"}
SKIP_DIRS: Set[str] = {".git", "node_modules", "build", "dist"}


def clone_repo(repo_url: str, to_path: Path) -> None:
    """
    Clone the given repository URL into to_path.
    Raises subprocess.CalledProcessError on failure.
    """
    to_path.mkdir(parents=True, exist_ok=True)
    # Use shallow clone for speed
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(to_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def scan_source_files(root_path: Path, extensions: Set[str] = DEFAULT_EXTENSIONS) -> List[Dict]:
    """
    Walk root_path and collect files with given extensions, skipping SKIP_DIRS.
    Returns list of dicts with "file_path" and "raw_code".
    """
    results: List[Dict] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune directories we want to skip
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in extensions:
                full_path = Path(dirpath) / fname
                try:
                    raw = full_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    # Fallback to binary read decoded with replace
                    raw = full_path.read_bytes().decode("utf-8", errors="replace")
                results.append({"file_path": str(full_path), "raw_code": raw})
    return results


def ingest_repo(repo_url: str) -> List[Dict]:
    """
    Clone repo to a temporary directory, scan for source files, and return their contents.
    The temporary clone is removed after scanning.
    """
    with tempfile.TemporaryDirectory(prefix="repo_clone_") as tmp:
        tmp_path = Path(tmp)
        clone_repo(repo_url, tmp_path)
        return scan_source_files(tmp_path)


if __name__ == "__main__":
    # Simple CLI: python ingest.py <repo_url>
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <git_repo_url>", file=sys.stderr)
        sys.exit(2)
    repo = sys.argv[1]
    try:
        files = ingest_repo(repo)
        print(json.dumps(files, ensure_ascii=False, indent=2))
    except subprocess.CalledProcessError as e:
        print(f"Git clone failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)