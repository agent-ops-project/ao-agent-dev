from types import ModuleType
import sys
import inspect
import functools
from importlib import reload, import_module
from importlib.machinery import (
    FileFinder,
    PathFinder,
    SourceFileLoader,
    BuiltinImporter,
    SOURCE_SUFFIXES,
)
from importlib.util import spec_from_loader
from forbiddenfruit import curse

from runner.taint_wrappers import get_taint_origins, taint_wrap, untaint_if_needed
from common.logger import logger

import threading
from contextlib import contextmanager

_thread_local = threading.local()


@contextmanager
def disable_taint_propagation():
    old_value = getattr(_thread_local, "disable_taint", False)
    _thread_local.disable_taint = True
    try:
        yield
    finally:
        _thread_local.disable_taint = old_value


def _is_taint_disabled():
    return getattr(_thread_local, "disable_taint", False)


# these modules are definitely patched.
# we make sure of that by reloading them
# after our loader (hook) is inserted into the
# sys meta path.
MODULE_WHITELIST = ["json", "re"]

MODULE_BLACKLIST = [
    "__future__",
    "__main__",
    "_thread",
    "_tkinter",
    "_io",
    "_pyio",
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "dill._dill",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "ensurepip",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "graphlib",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "msilib",
    "msvcrt",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "typing_extensions",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
    # not builtin
    "six",
    "pydantic",
]

MODULE_ATTR_BLACKLIST = [
    "json.load",
    "json.dump",
    "json.encoder",
    "json.decoder",
    "json.detect_encoding",
]

CLS_ATTR_BLACKLIST = [
    "JSONEncoder.default",
    "JSONEncoder.decode",
    "JSONDecoder.raw_decode",
    "JSONEncoder.encode",
    "JSONEncoder.iterencode",
    "JSONDecodeError.add_note",
    "JSONDecodeError.with_traceback",
    "JSONDecoder.decode",
]

_original_functions = {}


def get_all_taint(*args, **kwargs):
    """TODO"""
    args_taint_origins = get_taint_origins(args)
    kwargs_taint_origins = get_taint_origins(kwargs)
    taints = set(args_taint_origins) | set(kwargs_taint_origins)
    return taints


def remove_taint(*args, **kwargs):
    """TODO"""
    args = untaint_if_needed(args)
    kwargs = untaint_if_needed(kwargs)
    return args, kwargs


def apply_taint(output, taint_origin: set):
    """TODO"""
    return taint_wrap(output, taint_origin=taint_origin)


def create_taint_wrapper(original_func):
    if getattr(original_func, "_is_taint_wrapped", False):
        return original_func

    key = id(original_func)
    if hasattr(original_func, "__name__") and not isinstance(original_func.__name__, str):
        return original_func  # this will break wraps()

    if key in _original_functions:
        # logger.info(f"{key} already in _original_functions. returning...")
        return _original_functions[key]

    @functools.wraps(original_func)
    def patched_function(*args, **kwargs):
        if _is_taint_disabled():
            return original_func(*args, **kwargs)

        with disable_taint_propagation():
            # TODO, the orig func could also return taint. if that is the case,
            # we should ignore the high-level taint because the sub-func is more precise
            taint = get_all_taint(*args, **kwargs)
            output = original_func(*args, **kwargs)
            # it could be that the returned function is also patched. this can lead to unforeseen side-effects
            # so we recursively unwrap it
            if hasattr(output, "__name__") and output.__name__ == "patched_function":
                output = inspect.unwrap(output)
            tainted_output = apply_taint(output, taint)
            return tainted_output

    patched_function._is_taint_wrapped = True
    _original_functions[key] = patched_function

    return patched_function


def patch_module_callables(module, visited=None):
    if isinstance(module, ModuleType):
        module_name = module.__name__
        parent_name = module_name.lstrip(".").split(".")[0]
        any_under = any(sub.startswith("_") for sub in module_name.split("."))
        # is_under = module_name.startswith("_")
        if (
            module_name in MODULE_BLACKLIST or parent_name in MODULE_BLACKLIST or any_under
        ):  # or any_under:
            # logger.info(f"{module_name} is under or in MODULE_BLACKLIST. Skipped.")
            return

    if visited is None:
        visited = set()

    if id(module) in visited:
        return
    visited.add(id(module))

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        if f"{module_name}.{attr_name}" in MODULE_ATTR_BLACKLIST:
            # logger.info(f"{module_name}.{attr_name} in MODULE_ATTR_BLACKLIST. Skipped.")
            continue

        attr = getattr(module, attr_name)

        if inspect.isfunction(attr):
            # Patch functions
            if hasattr(attr, "__wrapped__"):  # already patched
                continue

            logger.info(f"Patched {module_name}.{attr_name}")
            setattr(module, attr_name, create_taint_wrapper(attr))
        elif inspect.isclass(attr):
            if any(
                mro.__module__ in MODULE_BLACKLIST
                for mro in attr.__mro__
                if mro.__name__ != "object"
            ):
                continue

            if attr.__module__.lstrip(".").split(".")[0] in MODULE_BLACKLIST:
                continue

            # Patch class methods
            patch_class_methods(attr)
        elif inspect.ismodule(attr):
            # Recurse into submodules
            patch_module_callables(attr, visited)
        elif callable(attr):
            if attr.__module__ in MODULE_BLACKLIST:
                continue
            # Other callables
            logger.info(f"Patched {module}.{attr_name}")
            setattr(module, attr_name, create_taint_wrapper(attr))


def patch_class_methods(cls):
    if not cls.__class__.__name__ == "type":
        return

    for method_name in dir(cls):
        if method_name.startswith("_"):
            continue
        try:
            # Check the original descriptor type in __dict__
            original_descriptor = None
            if hasattr(cls, "__dict__") and method_name in cls.__dict__:
                original_descriptor = cls.__dict__[method_name]

            method = getattr(cls, method_name)
        except AttributeError:
            continue

        if inspect.ismethod(method) or inspect.isfunction(method):
            if f"{cls.__name__}.{method_name}" in CLS_ATTR_BLACKLIST:
                continue

            # Get the unbound function for special method types
            if isinstance(original_descriptor, staticmethod):
                # For staticmethod, get the wrapped function
                unbound_func = original_descriptor.__func__
                wrapped_method = create_taint_wrapper(unbound_func)
                curse(cls, method_name, staticmethod(wrapped_method))
            elif isinstance(original_descriptor, classmethod):
                # For classmethod, get the wrapped function
                unbound_func = original_descriptor.__func__
                wrapped_method = create_taint_wrapper(unbound_func)
                curse(cls, method_name, classmethod(wrapped_method))
            else:
                # Regular instance method
                wrapped_method = create_taint_wrapper(method)
                curse(cls, method_name, wrapped_method)


class TaintModuleLoader(SourceFileLoader):
    def exec_module(self, module):
        """Execute the module."""
        super().exec_module(module)
        patch_module_callables(module=module)


class TaintBuiltinLoader(BuiltinImporter):
    def exec_module(self, module):
        """Execute the module."""
        super().exec_module(module)
        patch_module_callables(module=module)


class TaintImportHook:
    def find_spec(self, fullname: str, path, target=None):

        if fullname.startswith("_"):
            # logger.debug(f"Skipping attaching TaintImportHook to: {fullname}")
            return None

        if path is None:
            path = sys.path

        builtin_importer = BuiltinImporter()
        spec = builtin_importer.find_spec(fullname=fullname)
        if spec and spec.origin:
            return spec_from_loader(fullname, TaintBuiltinLoader())

        finder = PathFinder()
        # Try to find the module in this directory
        spec = finder.find_spec(fullname, path=path)
        # return spec
        if spec and spec.origin and isinstance(spec.loader, SourceFileLoader):
            return spec_from_loader(fullname, TaintModuleLoader(fullname, spec.origin))

        # for search_path in path:
        #     # Create a FileFinder for this directory
        #     finder = FileFinder(search_path, (SourceFileLoader, SOURCE_SUFFIXES))

        #     # Try to find the module in this directory
        #     spec = finder.find_spec(fullname)
        #     # return spec
        #     if spec and spec.origin and isinstance(spec.loader, SourceFileLoader):
        #         return spec_from_loader(fullname, TaintModuleLoader(fullname, spec.origin))

        return None


# How do integrate the f-string re-writer:
# install the FStringFinder at first position in meta sys
# let it find only for modules in project root
# re-write the AST etc.
# execute the module and then patch the module


def install_patch_hook():
    if not any(isinstance(mod, TaintImportHook) for mod in sys.meta_path):
        sys.meta_path.insert(0, TaintImportHook())

    for module_name in MODULE_WHITELIST:
        mod = import_module(module_name)
        reload(mod)
