import os
import inspect

def abs_path(rel_path):
    frame = inspect.stack()[1]
    caller_file = frame.filename
    caller_dir = os.path.dirname(os.path.abspath(caller_file))
    return os.path.abspath(os.path.join(caller_dir, rel_path))