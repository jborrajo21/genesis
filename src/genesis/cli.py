import argparse
from importlib.metadata import version

from genesis.core import cmd_create, cmd_plan, cmd_scaffold


def main(argv=None):
    parser = argparse.ArgumentParser(prog="genesis", description="Project scaffolding agent")
    parser.add_argument("--version", action="version", version=version("genesis"))

    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="create a structured plan from an idea")
    plan_parser.add_argument("idea", help="project idea")
    plan_parser.add_argument("--adapter", choices=["anthropic", "ollama"], default="anthropic")
    plan_parser.add_argument("--model", type=str, default="haiku")
    plan_parser.add_argument(
        "--no-interactive", action="store_false", dest="interactive", default=True
    )
    plan_parser.add_argument("--output", type=str, help="path to save plan JSON")

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="create a structured and tested repo from a plan"
    )
    scaffold_parser.add_argument("plan_json", help="path to plan JSON")
    scaffold_parser.add_argument("output_dir", help="directory to scaffold into")
    scaffold_parser.add_argument("--force", action="store_true")

    create_parser = subparsers.add_parser(
        "create", help="create a structured and tested repo and a structured plan from an idea"
    )
    create_parser.add_argument("idea", help="project idea")
    create_parser.add_argument("output_dir", help="directory to scaffold into")
    create_parser.add_argument("--adapter", choices=["anthropic", "ollama"], default="anthropic")
    create_parser.add_argument("--model", type=str, default="haiku")
    create_parser.add_argument(
        "--no-interactive", action="store_false", dest="interactive", default=True
    )
    create_parser.add_argument("--output", type=str, help="path to save plan JSON")
    create_parser.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "plan":
        return cmd_plan(args.idea, args.adapter, args.model, args.interactive, args.output)

    if args.command == "scaffold":
        return cmd_scaffold(args.plan_json, args.output_dir, args.force)

    if args.command == "create":
        return cmd_create(
            args.idea,
            args.output_dir,
            args.adapter,
            args.model,
            args.interactive,
            args.output,
            args.force,
        )

    return 0
