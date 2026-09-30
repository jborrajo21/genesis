import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from greetly.core import AppError, run


def _version() -> str:
    """The installed version, or a placeholder when running from a source tree."""
    try:
        return version("greetly")
    except PackageNotFoundError:
        return "0.0.0+unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="greetly")
    parser.add_argument("--version", action="version", version=_version())

    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run the tool")
    run_parser.add_argument("target", nargs="?", default=None, help="what to run against")

    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            print(run(args.target))
        return 0
    except AppError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130
