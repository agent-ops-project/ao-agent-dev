from .config import config_command_parser


def get_config_parser(subparsers=None):
    # The main config parser
    config_parser = config_command_parser(subparsers)
    return config_parser


def main():
    config_parser = get_config_parser()
    args = config_parser.parse_args()

    if not hasattr(args, "func"):
        config_parser.print_help()
        exit(1)

    # Run
    args.func(args)


if __name__ == "__main__":
    main()