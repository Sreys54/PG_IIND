"""
Extracts source regions marked with a paired begin/end comment tag (see
BEGIN_RE/END_RE below for the exact syntax) so the hand-back document
(Deliverable 7) can quote code by reference instead of by hand-pasting it.
Regenerating the document after a code change is then just re-running this
extraction -- it can never quote code that no longer exists, because it
re-reads the actual file every time.

Usage as a library (used by scripts/make_week2_handback.py):
    from scripts.build_week_doc import extract_all_snippets, get_snippet
    snippets = extract_all_snippets()
    snippets["registry_schema"] -> {"file": ..., "start_line": ..., "end_line": ..., "code": ...}

Usage standalone (sanity check / listing):
    PYTHONPATH=. python scripts/build_week_doc.py
"""
import glob
import re

BEGIN_RE = re.compile(r"#\s*doc:begin\s+(\S+)")
END_RE = re.compile(r"#\s*doc:end\s+(\S+)")

SOURCE_GLOBS = [
    "ev2gym_thesis/*.py",
    "ev2gym_thesis/rl/*.py",  # Week 3: RL subpackage, added here so its doc:begin/doc:end tags are discoverable
    "ev2gym_thesis/oracle/*.py",  # Week 4: oracle subpackage, same reason
    "ev2gym_thesis/tests/*.py",
    "scripts/*.py",
]


def extract_snippets_from_file(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    snippets = {}
    open_tag = None
    open_start = None
    buffer = []

    for i, line in enumerate(lines, start=1):
        begin_match = BEGIN_RE.search(line)
        end_match = END_RE.search(line)

        if begin_match:
            if open_tag is not None:
                raise ValueError(
                    f"{path}:{i}: doc:begin {begin_match.group(1)!r} found while "
                    f"tag {open_tag!r} (opened at line {open_start}) is still open -- "
                    f"nested/unclosed doc tags are not supported."
                )
            open_tag = begin_match.group(1)
            open_start = i
            buffer = []
            continue

        if end_match:
            tag = end_match.group(1)
            if open_tag is None:
                raise ValueError(f"{path}:{i}: doc:end {tag!r} found with no matching doc:begin.")
            if tag != open_tag:
                raise ValueError(
                    f"{path}:{i}: doc:end {tag!r} does not match currently open tag {open_tag!r} "
                    f"(opened at line {open_start})."
                )
            if tag in snippets:
                raise ValueError(f"Duplicate doc tag {tag!r}: also defined in {snippets[tag]['file']}")
            snippets[tag] = {
                "file": path,
                "start_line": open_start + 1,
                "end_line": i - 1,
                "code": "".join(buffer).rstrip("\n"),
            }
            open_tag = None
            continue

        if open_tag is not None:
            buffer.append(line)

    if open_tag is not None:
        raise ValueError(f"{path}: doc:begin {open_tag!r} (line {open_start}) was never closed with a matching doc:end.")

    return snippets


def extract_all_snippets() -> dict:
    all_snippets = {}
    for pattern in SOURCE_GLOBS:
        for path in sorted(glob.glob(pattern)):
            path = path.replace("\\", "/")  # normalize for display/citation, Windows or not
            file_snippets = extract_snippets_from_file(path)
            for tag, data in file_snippets.items():
                if tag in all_snippets:
                    raise ValueError(
                        f"Duplicate doc tag {tag!r}: in both {all_snippets[tag]['file']} and {data['file']}"
                    )
                all_snippets[tag] = data
    return all_snippets


def get_snippet(tag: str) -> dict:
    snippets = extract_all_snippets()
    if tag not in snippets:
        raise KeyError(f"No doc:begin/doc:end tag {tag!r} found across {SOURCE_GLOBS}. "
                        f"Available tags: {sorted(snippets)}")
    return snippets[tag]


if __name__ == "__main__":
    snippets = extract_all_snippets()
    print(f"Found {len(snippets)} tagged snippets:\n")
    for tag, data in sorted(snippets.items()):
        n_lines = data["end_line"] - data["start_line"] + 1
        print(f"  {tag:25s} {data['file']}:{data['start_line']}-{data['end_line']} ({n_lines} lines)")
        if n_lines > 40:
            print(f"    ! WARNING: exceeds the ~40-line guideline for hand-back document excerpts")
