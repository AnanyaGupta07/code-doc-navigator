"""
Simple impact analysis helper.

- analyze_impact(name, ingested_files)
  ingested_files: List[{"file_path": str, "raw_code": str}]
- Searches for definitions, imports and references (best-effort)
- Returns {
    "impacted_files": [...],
    "explanation": "plain English explanation",
    "details": { file_path: [reasons...] }
  }

Designed for accuracy-over-completeness and readability.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any


def _analyze_python(name: str, code: str) -> List[str]:
    reasons = []
    try:
        tree = ast.parse(code)
    except Exception:
        # fallback: regex search
        if re.search(r"\b" + re.escape(name) + r"\b", code):
            reasons.append("possible_reference_regex")
        return reasons

    # look for definition
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if getattr(node, "name", None) == name:
                reasons.append("definition")

    # imports
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == name or (alias.asname and alias.asname == name):
                    reasons.append("imported_via_from")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                # conservative: if top-level module matches the name or alias used as name
                if alias.asname == name or alias.name.split(".")[-1] == name:
                    reasons.append("imported")

    # simple usage detections: Name and Attribute
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            reasons.append("name_usage")
        if isinstance(node, ast.Attribute) and getattr(node, "attr", None) == name:
            reasons.append("attribute_usage")
        # calls where function is attribute or name
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == name:
                reasons.append("called")
            if isinstance(func, ast.Attribute) and getattr(func, "attr", None) == name:
                reasons.append("called_via_attribute")

    # dedupe reasons
    return list(dict.fromkeys(reasons))


def _analyze_js_java(name: str, code: str) -> List[str]:
    reasons = []
    # definition heuristics
    if re.search(r"\bclass\s+" + re.escape(name) + r"\b", code):
        reasons.append("definition")
    # function definition e.g., function name(  OR name = (params) => OR name(param)
    if re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", code) or re.search(
        re.escape(name) + r"\s*[:=]\s*function\b", code
    ) or re.search(re.escape(name) + r"\s*=\s*\(.*?\)\s*=>", code):
        reasons.append("definition")

    # imports / requires / exports
    if re.search(r"\bimport\b[^;]*\b" + re.escape(name) + r"\b", code) or re.search(
        r"\brequire\([^)]*['\"]" + re.escape(name) + r"['\"]\)", code
    ) or re.search(r"\bexports\." + re.escape(name) + r"\b", code) or re.search(
        r"\bmodule\.exports\b.*\b" + re.escape(name) + r"\b", code
    ):
        reasons.append("imported_or_exported")

    # instantiation or usage: new Name(  or Name(  or Name.
    if re.search(r"\bnew\s+" + re.escape(name) + r"\s*\(", code):
        reasons.append("instantiated")
    if re.search(r"\b" + re.escape(name) + r"\s*\(", code):
        reasons.append("called")
    if re.search(r"\b" + re.escape(name) + r"\.", code):
        reasons.append("attribute_usage")

    # conservative regex for any bare reference
    if re.search(r"\b" + re.escape(name) + r"\b", code):
        reasons.append("possible_reference_regex")

    # dedupe
    return list(dict.fromkeys(reasons))


def analyze_impact(name: str, ingested_files: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyze impact of changing/removing a function or class named `name`.

    Returns:
      {
        "impacted_files": [file_path, ...],
        "explanation": "plain English explanation",
        "details": { file_path: [reason1, reason2, ...] }
      }
    """
    details: Dict[str, List[str]] = {}
    definition_files = set()
    reference_files = set()

    for entry in ingested_files:
        file_path = entry.get("file_path", "<unknown>")
        code = entry.get("raw_code", "") or ""
        suf = Path(file_path).suffix.lower()

        reasons: List[str] = []
        try:
            if suf == ".py":
                reasons = _analyze_python(name, code)
            elif suf in (".js", ".jsx", ".ts", ".tsx", ".java"):
                reasons = _analyze_js_java(name, code)
            else:
                # fallback: simple regex
                if re.search(r"\b" + re.escape(name) + r"\b", code):
                    reasons = ["possible_reference_regex"]
        except Exception:
            # on any parsing error, try conservative regex
            if re.search(r"\b" + re.escape(name) + r"\b", code):
                reasons = ["possible_reference_regex"]

        if reasons:
            details[file_path] = reasons
            if "definition" in reasons:
                definition_files.add(file_path)
            # treat imports, calls, usage, attribute, instantiated as references
            if any(r in reasons for r in ("imported", "imported_via_from", "imported_or_exported", "called", "called_via_attribute", "name_usage", "attribute_usage", "instantiated", "possible_reference_regex")):
                reference_files.add(file_path)

    impacted = sorted(set(definition_files) | set(reference_files))

    # Build explanation (plain English)
    if not impacted:
        explanation = (
            f"No uses or definitions of '{name}' were found in the ingested files. "
            "Changing it is unlikely to break the scanned code, but other unscanned consumers may be affected."
        )
    else:
        parts = []
        if definition_files:
            parts.append(
                f"Found definition(s) of '{name}' in: {', '.join(sorted(definition_files))}."
            )
            # files that reference but are not defining
            non_defs = sorted(reference_files - definition_files)
            if non_defs:
                parts.append(
                    f"The following files reference or import it and may break if the definition changes: {', '.join(non_defs)}."
                )
        else:
            parts.append(
                f"No definition of '{name}' was found, but references were detected in: {', '.join(sorted(reference_files))}."
            )
        # short note about types of references
        examples = []
        # gather examples from details for first few files
        for fp in sorted(impacted)[:5]:
            examples.append(f"{fp} ({', '.join(details.get(fp, [])[:3])})")
        if examples:
            parts.append("Sample detections: " + "; ".join(examples) + ".")
        explanation = " ".join(parts)

    return {"impacted_files": impacted, "explanation": explanation, "details": details}


if __name__ == "__main__":
    # simple CLI for manual testing:
    import json
    import sys

    if len(sys.argv) < 3:
        print("Usage: python impact_analysis.py <NAME> <ingested_json_file>", file=sys.stderr)
        sys.exit(2)

    name_arg = sys.argv[1]
    ingested_path = sys.argv[2]
    with open(ingested_path, "r", encoding="utf-8") as f:
        ingested = json.load(f)

    out = analyze_impact(name_arg, ingested)
    print(json.dumps(out, indent=2, ensure_ascii=False))