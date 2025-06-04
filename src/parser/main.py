import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Parse input repo and cache directory.")

    parser.add_argument(
        '--repo_root',
        type=str,
        required=True,
        help='The path to the input repo being parsed.'
    )

    parser.add_argument(
        '--cache_dir',
        type=str,
        required=False,
        default=None,
        help='The path where the parsed representation is cached (optional).'
    )

    return parser.parse_args()

def main():
    args = parse_args()
    print(f"Repo root: {args.repo_root}")
    print(f"Cache dir: {args.cache_dir}")

if __name__ == '__main__':
    main()
