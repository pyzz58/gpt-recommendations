"""Prepare the W12 E2E database without predefined business records.

The test creates the first project and sites through the browser product path.
Keeping this command side-effect free preserves UX-A01: a developer seed must
not create the study, site, subject or monitoring visit being accepted.
"""
from __future__ import annotations


def main() -> None:
    print("no business records seeded; browser creates the blank project path")


if __name__ == "__main__":
    main()
