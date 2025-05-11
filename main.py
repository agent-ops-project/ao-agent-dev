
import logging

def setup_logging():
    # Clear out any old handlers (especially in REPL or interactive walks)
    root = logging.getLogger()
    if root.handlers:
        root.handlers.clear()

    # This attaches a default StreamHandler to stderr
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(message)s",
    )

    return root

def main():
    setup_logging()

    # Now every module can just get its logger
    logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()