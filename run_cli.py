"""Convenience launcher: `python run_cli.py ...` from the repo root.

Forwards to the package entry point. The installed console script
`tripplanner` (pyproject [project.scripts]) and `python -m tripplanner` are the
other two ways in; all three call the same `main()`.
"""

from tripplanner.cli import main

if __name__ == "__main__":
    main()
