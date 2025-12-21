# Lazy imports to avoid circular import issues with ast_helpers
# (aco_server.py needs to load ast_helpers before package imports)


def __getattr__(name):
    """Lazy import of submodules to avoid circular imports."""
    if name == "launch":
        from aco.runner.context_manager import aco_launch

        return aco_launch
    elif name == "log":
        from aco.runner.context_manager import log

        return log
    elif name == "untaint_if_needed":
        from aco.server.ast_helpers import untaint_if_needed

        return untaint_if_needed
    elif name == "get_taint_origins":
        from aco.server.ast_helpers import get_taint_origins

        return get_taint_origins
    elif name == "taint_wrap":
        from aco.server.ast_helpers import taint_wrap

        return taint_wrap
    raise AttributeError(f"module 'aco' has no attribute {name!r}")


__all__ = ["launch", "log", "untaint_if_needed", "get_taint_origins", "taint_wrap"]
