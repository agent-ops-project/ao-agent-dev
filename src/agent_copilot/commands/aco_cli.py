from argparse import ArgumentParser
from agent_copilot.commands.config import get_config_parser
from agent_copilot.commands.launch import launch_command_parser, launch_command


def main():
    parser = ArgumentParser("Agent Copilot CLI tool", usage="aco <command> [<args>]", allow_abbrev=False)
    subparsers = parser.add_subparsers(help="aco command helpers")

    # Register commands
    get_config_parser(subparsers=subparsers)
    launch_command_parser(subparsers=subparsers)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        exit(1)

    args.func(args)


if __name__ == "__main__":
    main()