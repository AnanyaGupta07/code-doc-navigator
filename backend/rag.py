from pathlib import Path
import re
from typing import List, Dict, Union, Optional


def _strip_python_comments(code: str) -> str:
    # remove shebang
    code = re.sub(r"^\s*#!.*\n", "", code)
    # remove module-level triple-quote docstring at top
    code = re.sub(r'^\s*(?P<q>"""|\'\'\')(?:.*?)(?P=q)\s*\n', "", code, flags=re.S)
    out_lines = []
    in_triple = False
    triple_delim = None
    for line in code.splitlines():
        # very simple triple-quoted detection to avoid stripping inside strings
        if not in_triple and re.search(r'("""|\'\'\')', line):
            # toggle into triple mode if starts a block (approximate)
            parts = re.split(r'("""|\'\'\')', line)
            # if there are an odd number of triple quotes, enter/exit mode
            if line.count('"""') + line.count("'''") == 1:
                in_triple = True
                triple_delim = '"""' if '"""' in line else "'''"
                # drop the part after the triple start (approx)
                line = line.split(triple_delim)[0]
        elif in_triple:
            if triple_delim in line:
                in_triple = False
                # keep text after closing delimiter
                line = line.split(triple_delim, 1)[1]
            else:
                continue
        # remove full-line comments
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        # remove inline comment if it's not inside quotes (heuristic)
        new_line = []
        in_single = in_double = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == "'" and not in_double:
                in_single = not in_single
                new_line.append(c)
            elif c == '"' and not in_single:
                in_double = not in_double
                new_line.append(c)
            elif c == "#" and not in_single and not in_double:
                # stop at inline comment
                break
            else:
                new_line.append(c)
            i += 1
        res_line = "".join(new_line).rstrip()
        if res_line:
            out_lines.append(res_line)
    return "\n".join(out_lines)


def _strip_js_java_comments(code: str) -> str:
    # remove shebang if any
    code = re.sub(r"^\s*#!.*\n", "", code)
    # remove /* ... */ block comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    # remove // comments but avoid those inside strings (heuristic)
    out_lines = []
    for line in code.splitlines():
        line_stripped = line.lstrip()
        # skip full-line // comments
        if line_stripped.startswith("//"):
            continue
        new_line = []
        in_single = in_double = in_back = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == "'" and not in_double and not in_back:
                in_single = not in_single
                new_line.append(c)
            elif c == '"' and not in_single and not in_back:
                in_double = not in_double
                new_line.append(c)
            elif c == "`" and not in_single and not in_double:
                in_back = not in_back
                new_line.append(c)
            elif c == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_single and not in_double and not in_back:
                break
            else:
                new_line.append(c)
            i += 1
        res_line = "".join(new_line).rstrip()
        if res_line:
            out_lines.append(res_line)
    return "\n".join(out_lines)


def _remove_boilerplate(code: str, lang: str) -> str:
    # common boilerplate patterns to drop
    patterns = [
        r"^\s*//\s*#.*$",  # weird comment lines
    ]
    # drop python main block
    if lang == "py":
        code = re.sub(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*\n(?:\s+.*\n?)*', "", code, flags=re.S)
        # keep import and defs, so nothing more aggressive here
    else:
        # drop Java main methods
        code = re.sub(r'public\s+static\s+void\s+main\s*\([^)]*\)\s*\{\s*(?:[^{}]*|\{[^}]*\})*\}', "", code, flags=re.S)
        # drop console.log lines and module.exports / export default in JS
        code = re.sub(r'^\s*console\.log\(.*\)\s*;?\s*$', "", code, flags=re.M)
        code = re.sub(r'^\s*(module\.exports|export\s+default|export\s+\{).*$', "", code, flags=re.M)
    for p in patterns:
        code = re.sub(p, "", code, flags=re.M)
    return code


def _detect_lang(snippet: str, file_path: Union[str, None]) -> str:
    if file_path:
        suf = Path(file_path).suffix.lower()
        if suf == ".py":
            return "py"
        if suf in (".js", ".jsx", ".ts", ".tsx"):
            return "js"
        if suf in (".java",):
            return "java"
    # fallback heuristics
    if re.search(r"^\s*def\s+\w+\s*\(", snippet, flags=re.M):
        return "py"
    if re.search(r"\bfunction\b|\bconsole\.log\b|=>", snippet):
        return "js"
    if re.search(r"\bpublic\b\s+\bclass\b|\bpublic\b\s+static\s+void\s+main\b", snippet):
        return "java"
    return "py"


def compress_code_snippets(
    snippets: List[Union[str, Dict]],
) -> str:
    """
    Compress multiple code snippets into a single text block.

    Heuristics:
    - Remove comments (line and block) for Python / JS / Java (best-effort)
    - Remove common boilerplate (if __name__ == '__main__', main methods, console.log, exports)
    - Preserve import lines and function/class signatures and bodies (non-comment lines)
    - Aggregate and deduplicate imports at top

    Input items can be either raw strings (code) or dicts containing "code_snippet" and optional "file_path".
    Returns a single compressed text block.
    """
    imports = []
    bodies = []

    for item in snippets:
        if isinstance(item, dict):
            code = item.get("code_snippet", "") or ""
            fp = item.get("file_path")
        else:
            code = item or ""
            fp = None
        lang = _detect_lang(code, fp)
        if lang == "py":
            code = _strip_python_comments(code)
        else:
            code = _strip_js_java_comments(code)
        code = _remove_boilerplate(code, lang)

        # extract import lines to keep at top
        if lang == "py":
            im_lines = [ln for ln in code.splitlines() if re.match(r'^\s*(from\s+\S+\s+import|import\s+\S+)', ln)]
        else:
            im_lines = [ln for ln in code.splitlines() if re.match(r'^\s*import\s+[\w\{\}\s,]+|^\s*const\s+\w+\s*=\s*require\(', ln)]
        # remove import lines from code body
        if im_lines:
            imports.extend([ln.strip() for ln in im_lines])
            # remove them from body text
            for ln in im_lines:
                code = code.replace(ln, "")

        # keep only meaningful non-empty lines
        meaningful_lines = []
        for ln in code.splitlines():
            s = ln.strip()
            if not s:
                continue
            # keep class/function signatures and other logic lines but drop trivial braces-only lines
            if s in ("{", "}", ";"):
                continue
            meaningful_lines.append(ln.rstrip())
        if meaningful_lines:
            bodies.append("\n".join(meaningful_lines))

    # deduplicate imports preserving order
    seen = set()
    dedup_imports = []
    for im in imports:
        if im not in seen:
            seen.add(im)
            dedup_imports.append(im)

    parts = []
    if dedup_imports:
        parts.append("\n".join(dedup_imports))
    if bodies:
        parts.append("\n\n".join(bodies))
    return "\n\n".join(parts).strip()


PROMPT_TEMPLATES = {
    "beginner": """You are a friendly assistant. Explain the code below in simple, non-technical terms so a beginner can understand.

Context:
{compressed_code}

Question:
{question}

Instructions:
- Use plain language; avoid jargon.
- Explain what the code does, why it might matter, and one short example of how it is used.
- Mention any obvious risks or things to watch out for in one short sentence.
- Keep the answer under ~150 words.
""",
    "developer": """You are a knowledgeable developer assistant. Provide a clear, technical explanation of the code below.

Context:
{compressed_code}

Question:
{question}

Instructions:
- Summarize the responsibilities of the code and important functions/classes.
- Point out where the key logic lives (refer to function/class names).
- List potential breakages or edge cases (short bullets).
- If relevant, suggest one concrete fix or improvement and link it to the affected symbol(s).
- Keep the answer focused and actionable (200-350 words).
""",
    "architect": """You are a senior architect. Provide a high-level, design-focused assessment of the code below.

Context:
{compressed_code}

Question:
{question}

Instructions:
- Describe how this code fits into a larger system and what modules/components it touches.
- Discuss design trade-offs, coupling, and maintainability concerns.
- Highlight risks, data flow implications, and migration/rollback strategies if this component changes.
- Recommend higher-level alternatives or refactoring approaches (brief).
- Keep the response concise and structured (250-400 words).
"""
}


def build_explanation_prompt(
    level: str,
    snippets: List[Union[str, Dict]],
    question: Optional[str] = "Explain the code and its potential impacts.",
) -> str:
    """
    Build a prompt string for the RAG pipeline.

    level: "beginner" | "developer" | "architect"
    snippets: list of raw code strings or dicts with "code_snippet" and optional "file_path"
    question: specific user question to guide the explanation

    Returns a filled prompt using compress_code_snippets to reduce payload size.
    """
    lvl = (level or "developer").lower()
    template = PROMPT_TEMPLATES.get(lvl, PROMPT_TEMPLATES["developer"])
    compressed = compress_code_snippets(snippets)
    return template.format(compressed_code=compressed, question=question)