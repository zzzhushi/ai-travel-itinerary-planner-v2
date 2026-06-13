"""Command-line entry point. Thin: parse args, delegate to application use-cases.

M0 ships `--version`; subcommands arrive as later milestones add use-cases.
"""

from __future__ import annotations

import argparse

from tripplanner import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tripplanner", description="AI travel itinerary planner")
    parser.add_argument("--version", action="version", version=f"tripplanner {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    parser.parse_args(argv)
    # No subcommands yet (M0); later milestones dispatch to use-cases here.
    parser.print_help()
