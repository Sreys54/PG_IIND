"""
Vocabulary-discipline check (Gurobi policy, rule 3 -- see 00_lab_log.md
2026-08-12 entry / thesis_docs/chapters/02_model_validation.md).

Until a row with algorithm_family == "optimal" exists in
results/master_results.csv, the words "optimal", "near-optimal", and
"optimality gap" may not appear in thesis_docs/chapters/*.md. The permitted
phrasing is "best-performing among the strategies tested". This enforces
the project's own rule against reporting a comparison that was never run.

Usage: python scripts/check_claims.py
Exit code 0 = clean, 1 = forbidden term(s) found while no optimal rows exist.
"""
import csv
import glob
import os
import re
import sys

REGISTRY_PATH = "results/master_results.csv"
CHAPTERS_GLOB = "thesis_docs/chapters/*.md"

FORBIDDEN_PATTERNS = [
    re.compile(r"\bnear-optimal\b", re.IGNORECASE),
    re.compile(r"\boptimality gap\b", re.IGNORECASE),
    re.compile(r"\boptimal\b", re.IGNORECASE),
]


def has_optimal_rows() -> bool:
    if not os.path.exists(REGISTRY_PATH):
        return False
    with open(REGISTRY_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return any(row.get("algorithm_family") == "optimal" for row in reader)


def find_violations() -> list:
    violations = []
    for path in sorted(glob.glob(CHAPTERS_GLOB)):
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        violations.append((path, line_no, pattern.pattern, line.strip()))
    return violations


if __name__ == "__main__":
    if has_optimal_rows():
        print("Registry contains algorithm_family=='optimal' rows -- vocabulary "
              "restriction lifted, skipping check.")
        sys.exit(0)

    violations = find_violations()
    if not violations:
        print("OK: no forbidden optimality language found, and no optimal rows "
              "exist yet -- consistent.")
        sys.exit(0)

    print("FAIL: forbidden optimality language found while no "
          "algorithm_family=='optimal' row exists in the registry:\n")
    for path, line_no, pattern, line in violations:
        print(f"  {path}:{line_no}  [{pattern}]  {line}")
    print("\nPermitted phrasing: \"best-performing among the strategies tested\".")
    sys.exit(1)
