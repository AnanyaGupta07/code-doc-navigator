"""
Simple code chunker.

- Takes raw source code and file path
- Attempts to extract functions and classes
- If parsing/extraction fails, falls back to approximate chunking every ~400 tokens

Each chunk is a dict:
{
  "chunk_id": "...",
  "file_path": "...",
  "code_snippet": "...",
  "chunk_type": "function" | "class" | "other"
}
"""

from pathlib import Path
import ast
import re
import uuid
from typing import List, Dict, Tuple


def _make_id() -> str:
    return uuid.uuid4().hex


def _lines_slice(source: str, start_lineno: int, end_lineno: int) -> str:
    lines = source.splitlines(keepends=True)
    # lineno are 1-based
    start = max(0, start_lineno - 1)
    end = min(len(lines), end_lineno)
    return "".join(lines[start:end])


def _extract_python_nodes(source: str) -> List[Dict]:
    chunks: List[Dict] = []
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                snippet = ast.get_source_segment(source, node) or _lines_slice(source, node.lineno, node.end_lineno)  # type: ignore[attr-defined]
            except Exception:
                # fallback if end_lineno missing
                snippet = _lines_slice(source, getattr(node, "lineno", 1), getattr(node, "end_lineno", 1))
            chunks.append(
                {
                    "chunk_id": _make_id(),
                    "file_path": "",
                    "code_snippet": snippet,
                    "chunk_type": "function",
                }
            )
        elif isinstance(node, ast.ClassDef):
            try:
                snippet = ast.get_source_segment(source, node) or _lines_slice(source, node.lineno, node.end_lineno)  # type: ignore[attr-defined]
            except Exception:
                snippet = _lines_slice(source, getattr(node, "lineno", 1), getattr(node, "end_lineno", 1))
            chunks.append(
                {
                    "chunk_id": _make_id(),
                    "file_path": "",
                    "code_snippet": snippet,
                    "chunk_type": "class",
                }
            )
    return chunks


def _find_matching_brace(text: str, start: int, open_char: str = "{", close_char: str = "}") -> int:
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _extract_blocks_by_regex(source: str) -> List[Dict]:
    chunks: List[Dict] = []
    taken_spans: List[Tuple[int, int]] = []

    # class blocks (JS/Java/C-like): class Name { ... }
    for m in re.finditer(r"\bclass\s+\w+\s*(?:extends\s+\w+\s*)?\{", source):
        start = m.start()
        brace_start = source.find("{", m.end() - 1)
        if brace_start == -1:
            continue
        end = _find_matching_brace(source, brace_start)
        snippet = source[start:end]
        chunks.append(
            {"chunk_id": _make_id(), "file_path": "", "code_snippet": snippet, "chunk_type": "class"}
        )
        taken_spans.append((start, end))

    # function blocks: function name(...) { ... } or name(...) { ... } (heuristic)
    # avoid common control structures by negative lookbehind is limited; we'll filter short signatures
    for m in re.finditer(r"(?:function\s+\w+|\w+\s*\([^)]*\))\s*\{", source):
        start = m.start()
        brace_start = source.find("{", m.end() - 1)
        if brace_start == -1:
            continue
        # rudimentary filter: skip "if", "for", "while", "switch", "catch"
        prefix = source[max(0, start - 10):start].lower()
        if any(k in prefix for k in ("if", "for", "while", "switch", "catch")):
            continue
        end = _find_matching_brace(source, brace_start)
        snippet = source[start:end]
        # avoid overlapping extractions
        overlap = False
        for a, b in taken_spans:
            if not (end <= a or start >= b):
                overlap = True
                break
        if overlap:
            continue
        chunks.append(
            {"chunk_id": _make_id(), "file_path": "", "code_snippet": snippet, "chunk_type": "function"}
        )
        taken_spans.append((start, end))

    return chunks


def _approx_token_chunks(source: str, approx_tokens: int = 400) -> List[Dict]:
    # approximate token -> characters heuristic (avg 4 chars/token)
    chars_per_token = 4
    chunk_chars = approx_tokens * chars_per_token
    chunks: List[Dict] = []
    i = 0
    n = len(source)
    while i < n:
        j = min(n, i + chunk_chars)
        snippet = source[i:j]
        chunks.append(
            {"chunk_id": _make_id(), "file_path": "", "code_snippet": snippet, "chunk_type": "other"}
        )
        i = j
    return chunks


def chunk_code(file_path: str, raw_code: str) -> List[Dict]:
    """
    Main entry.

    Returns list of chunks. Each chunk contains file_path.
    """
    results: List[Dict] = []
    ext = Path(file_path).suffix.lower()

    # Try strong parser for Python
    if ext == ".py":
        py_chunks = _extract_python_nodes(raw_code)
        if py_chunks:
            for c in py_chunks:
                c["file_path"] = file_path
            return py_chunks

    # Try regex-based extraction for other languages or as fallback
    try:
        regex_chunks = _extract_blocks_by_regex(raw_code)
        if regex_chunks:
            for c in regex_chunks:
                c["file_path"] = file_path
            # also include leftover top-level other code if it's meaningful
            covered = []
            for c in regex_chunks:
                start = raw_code.find(c["code_snippet"])
                if start >= 0:
                    covered.append((start, start + len(c["code_snippet"])))
            covered.sort()
            # find gaps larger than small threshold and add as "other"
            last = 0
            for a, b in covered:
                if a - last > 200:  # arbitrary threshold for meaningful leftover
                    snippet = raw_code[last:a]
                    results.append(
                        {"chunk_id": _make_id(), "file_path": file_path, "code_snippet": snippet, "chunk_type": "other"}
                    )
                last = b
            if last < len(raw_code):
                snippet = raw_code[last:]
                if len(snippet.strip()) > 0:
                    results.append(
                        {"chunk_id": _make_id(), "file_path": file_path, "code_snippet": snippet, "chunk_type": "other"}
                    )
            # attach class/function chunks
            for c in regex_chunks:
                results.append(c)
            return results
    except Exception:
        pass

    # As a final fallback chunk by approximate token size (300-500 tokens ~= 400 default)
    return [
        {**c, "file_path": file_path}
        for c in _approx_token_chunks(raw_code, approx_tokens=400)
    ]


# Simple helper for module usage
def chunk_file_entry(entry: Dict) -> List[Dict]:
    """
    entry: {"file_path": "...", "raw_code": "..."}
    """
    return chunk_code(entry.get("file_path", ""), entry.get("raw_code", ""))