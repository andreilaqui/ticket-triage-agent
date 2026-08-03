"""
Validates that every file mentioned in a '## See Also' section actually
exists in knowledge_base/, and that no doc references itself.

This catches the structural half of "is this cross-reference still
accurate" automatically - e.g. someone renames a doc and forgets to
update the docs pointing to it. It cannot catch the semantic half (is the
*claim* still true, like "this policy is stricter than X") - that part
stays a human responsibility. See README's "Known limitations" section
for the full reasoning on this split.

Usage: python check_references.py
Exits 1 with details if any reference is broken; exits 0 if clean.
"""

import re
import sys
from pathlib import Path

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"

# Matches `some-file.md`-style references inside backticks
REFERENCE_PATTERN = re.compile(r"`([\w-]+\.md)`")


def find_see_also_references(text: str) -> list[str]:
    """Return every .md filename referenced within a doc's See Also section."""
    marker = "## See Also"
    idx = text.find(marker)
    if idx == -1:
        return []
    return REFERENCE_PATTERN.findall(text[idx:])


def check_all_references() -> list[str]:
    """Check every KB doc's See Also section. Returns a list of
    human-readable error strings; an empty list means everything's clean.
    """
    errors: list[str] = []
    existing_files = {p.name for p in KNOWLEDGE_BASE_DIR.glob("*.md")}

    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for ref in find_see_also_references(text):
            if ref == path.name:
                errors.append(f"{path.name}: references itself in See Also")
            elif ref not in existing_files:
                errors.append(f"{path.name}: references '{ref}', which does not exist")
    return errors


if __name__ == "__main__":
    errors = check_all_references()
    if errors:
        print("Broken references found:\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"All See Also references are valid ({len(list(KNOWLEDGE_BASE_DIR.glob('*.md')))} docs checked).")
    sys.exit(0)
