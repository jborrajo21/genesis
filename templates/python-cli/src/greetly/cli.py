import argparse
from importlib.metadata import version
from greetly.core import greet


def main(argv=None):
    parser = argparse.ArgumentParser(prog="greetly", description="greet user")
    parser.add_argument("--version", action="version", version=version("greetly"))

    subparsers = parser.add_subparsers(dest="command", required=True)
    greet_parser = subparsers.add_parser("greet", help="Say hello to said user")
    greet_parser.add_argument("name")

    args = parser.parse_args(argv)

    if args.command == "greet":
        print(greet(args.name))
        return 0

    return 0
