import os
from common.utils import get_project_root

# server-related constants
HOST = '127.0.0.1'
PORT = 5959
SOCKET_TIMEOUT = 1
SHUTDOWN_WAIT = 2


# default home directory for configs and temporary/cached files
default_home: str = os.path.join(os.path.expanduser("~"), ".cache")
ACO_HOME: str = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "ACO_HOME",
            os.path.join(os.getenv("XDG_CACHE_HOME", default_home), "agent-copilot"),
        )
    )
)


# Path to config.yaml. This config file includes the possible
# command line args. Must be generated with `aco config`.
# > Note: This does not need to be set. You can also just pass
# the relevant command line args when you run `aco develop`.
default_config_path = os.path.join(ACO_HOME, "config.yaml")
ACO_CONFIG = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "ACO_CONFIG",
            default_config_path,
        )
    )
)


# Anything cache-related should be stored here
default_cache_path = os.path.join(ACO_HOME, "cache")
ACO_CACHE = os.path.expandvars(
    os.path.expanduser(
        os.getenv(
            "ACO_CACHE",
            default_cache_path,
        )
    )
)


# project root is only inferred once at import-time
ACO_PROJECT_ROOT = get_project_root()