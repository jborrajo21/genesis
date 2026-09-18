import argparse
from importlib.metadata import version

from genesis.core import cmd_create, cmd_plan, cmd_scaffold_file
from genesis.interface import print_error


def main(argv=None):
    parser = argparse.ArgumentParser(prog="genesis", description="Project scaffolding agent")
    parser.add_argument("--version", action="version", version=version("genesis-agent"))

    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="create a structured plan from an idea")
    plan_parser.add_argument("idea", nargs="?", default=None, help="project idea")
    plan_parser.add_argument("--adapter", default=None, help="Adapter to use (anthropic or ollama)")
    plan_parser.add_argument("--model", default=None, help="Model name")
    plan_parser.add_argument("--output", type=str, help="path to save plan JSON")
    plan_parser.add_argument("--max-rounds", type=int, default=6, help="max planning rounds")
    plan_parser.add_argument("--max-tokens", type=int, default=10000, help="max tokens per call")

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="create a structured and tested repo from a plan"
    )
    scaffold_parser.add_argument("plan_json", nargs="?", default=None, help="path to plan JSON")
    scaffold_parser.add_argument(
        "output_dir", nargs="?", default=None, help="directory to scaffold into"
    )
    scaffold_parser.add_argument(
        "--force", action="store_true", help="overwrite the output directory if it exists"
    )

    create_parser = subparsers.add_parser(
        "create", help="create a structured and tested repo and a structured plan from an idea"
    )
    create_parser.add_argument("idea", nargs="?", default=None, help="project idea")
    create_parser.add_argument(
        "output_dir", nargs="?", default=None, help="directory to scaffold into"
    )
    create_parser.add_argument(
        "--adapter", default=None, help="Adapter to use (anthropic or ollama)"
    )
    create_parser.add_argument("--model", default=None, help="Model name")
    create_parser.add_argument("--output", type=str, help="path to save plan JSON")
    create_parser.add_argument(
        "--force", action="store_true", help="overwrite the output directory if it exists"
    )
    create_parser.add_argument("--max-rounds", type=int, default=6, help="max planning rounds")
    create_parser.add_argument("--max-tokens", type=int, default=10000, help="max tokens per call")

    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            return cmd_plan(
                args.idea,
                args.adapter,
                args.model,
                args.output,
                args.max_rounds,
                args.max_tokens,
            )

        if args.command == "scaffold":
            return cmd_scaffold_file(args.plan_json, args.output_dir, args.force)

        if args.command == "create":
            return cmd_create(
                args.idea,
                args.output_dir,
                args.adapter,
                args.model,
                args.output,
                args.force,
                args.max_rounds,
                args.max_tokens,
            )

        return 0
    except KeyboardInterrupt:
        print_error("Cancelled.")
        return 130
