import re
import json
from forbiddenfruit import curse, patchable_builtin
from runner.taint_wrappers import (
    TaintStr,
    TaintInt,
    TaintFloat,
    get_taint_origins,
    shift_position_taints,
    get_random_positions,
    inject_random_marker,
    remove_random_marker,
    Position,
    taint_wrap,
    untaint_if_needed,
)


def str_patch():
    """Patches related to inbuilt str class."""
    curse(str, "join", _cursed_join)


def re_patch():
    """Patches related to re module for taint propagation."""
    # Store original methods first to avoid recursion
    _store_original_methods()

    # Patch Match object methods
    curse(re.Match, "group", _cursed_match_group)
    curse(re.Match, "groups", _cursed_match_groups)
    curse(re.Match, "groupdict", _cursed_match_groupdict)
    curse(re.Match, "expand", _cursed_match_expand)

    # Patch Pattern object methods
    curse(re.Pattern, "search", _cursed_pattern_search)
    curse(re.Pattern, "match", _cursed_pattern_match)
    curse(re.Pattern, "fullmatch", _cursed_pattern_fullmatch)
    curse(re.Pattern, "split", _cursed_pattern_split)
    curse(re.Pattern, "findall", _cursed_pattern_findall)
    curse(re.Pattern, "finditer", _cursed_pattern_finditer)
    curse(re.Pattern, "sub", _cursed_pattern_sub)
    curse(re.Pattern, "subn", _cursed_pattern_subn)

    # Replace module-level functions directly
    re.search = _cursed_re_search
    re.match = _cursed_re_match
    re.fullmatch = _cursed_re_fullmatch
    re.split = _cursed_re_split
    re.findall = _cursed_re_findall
    re.finditer = _cursed_re_finditer
    re.sub = _cursed_re_sub
    re.subn = _cursed_re_subn


def _cursed_join(sep: str, elements: list[str]) -> str:
    """
    Join string elements with a separator while preserving taint tracking.

    This function joins a list of strings with a separator, similar to str.join(),
    but maintains taint information and random position tracking throughout the
    operation. It uses byte-level joining for performance and handles taint
    propagation from both the separator and all elements.

    Args:
        sep (str): The separator string to join elements with
        elements (list[str]): List of string elements to join

    Returns:
        str | TaintStr: The joined string, returned as TaintStr if any element
                        or separator has taint information, otherwise regular str
    """
    joined_bytes = _bytes_join(sep.encode(), [elem.encode() for elem in elements])
    final_string = joined_bytes.decode()

    nodes = set(get_taint_origins(sep))
    curr_offs = 0
    random_positions = []
    for value in elements:
        shift_position_taints(value, curr_offs)
        curr_offs += len(value) + len(sep)
        random_positions.extend(get_random_positions(value))
        nodes.update(get_taint_origins(value))

    if len(nodes) > 0:
        return TaintStr(final_string, taint_origin=nodes, random_pos=random_positions)
    return final_string


def _bytes_join(sep: bytes, elements: list[bytes]) -> bytes:
    """
    Efficiently join byte sequences with a separator using a pre-allocated buffer.

    This function performs byte-level joining of elements with a separator,
    providing better performance than repeated concatenation by pre-allocating
    a buffer of the exact required size and copying data directly.

    Args:
        sep (bytes): The separator bytes to join elements with
        elements (list[bytes]): List of byte sequences to join

    Returns:
        bytes: The joined byte sequence, or empty bytes if total length is 0 or negative
    """
    # create a mutable buffer that is long enough to hold the result
    total_length = sum(len(elem) for elem in elements)
    total_length += (len(elements) - 1) * len(sep)
    if total_length <= 0:
        return bytearray(0)
    result = bytearray(total_length)
    # copy all characters from the inputs to the result
    insert_idx = 0
    for elem in elements:
        result[insert_idx : insert_idx + len(elem)] = elem
        insert_idx += len(elem)
        if insert_idx < total_length:
            result[insert_idx : insert_idx + len(sep)] = sep
            insert_idx += len(sep)
    return bytes(result)


# Global variable to store taint context for Match objects
_match_taint_context = {}

# Store original methods to avoid recursion
_original_methods = {}


def _store_original_methods():
    """Store original methods before patching to avoid recursion."""
    if not _original_methods:
        _original_methods.update(
            {
                "match_group": patchable_builtin(re.Match)["group"],
                "match_groups": patchable_builtin(re.Match)["groups"],
                "match_groupdict": patchable_builtin(re.Match)["groupdict"],
                "match_expand": patchable_builtin(re.Match)["expand"],
                "pattern_search": patchable_builtin(re.Pattern)["search"],
                "pattern_match": patchable_builtin(re.Pattern)["match"],
                "pattern_fullmatch": patchable_builtin(re.Pattern)["fullmatch"],
                "pattern_split": patchable_builtin(re.Pattern)["split"],
                "pattern_findall": patchable_builtin(re.Pattern)["findall"],
                "pattern_finditer": patchable_builtin(re.Pattern)["finditer"],
                "pattern_sub": patchable_builtin(re.Pattern)["sub"],
                "pattern_subn": patchable_builtin(re.Pattern)["subn"],
                "re_search": re.search,
                "re_match": re.match,
                "re_fullmatch": re.fullmatch,
                "re_split": re.split,
                "re_findall": re.findall,
                "re_finditer": re.finditer,
                "re_sub": re.sub,
                "re_subn": re.subn,
            }
        )


# Match object method patches
def _cursed_match_group(self, *args):
    """Tainted version of Match.group()."""
    original_method = _original_methods["match_group"]
    # original_method = patchable_builtin(re.Match)["_c_group"]
    result = original_method(self, *args)

    # Get taint context for this match object
    match_id = id(self)
    if match_id in _match_taint_context:
        taint_origins = _match_taint_context[match_id]
        if isinstance(result, str) and taint_origins:
            # Calculate position within original string for this group
            start_pos = self.start() if not args or args[0] == 0 else self.start(args[0])
            end_pos = self.end() if not args or args[0] == 0 else self.end(args[0])
            positions = [Position(0, len(result))] if start_pos != -1 else []
            return TaintStr(result, taint_origin=taint_origins, random_pos=positions)

    return result


def _cursed_match_groups(self, default=None):
    """Tainted version of Match.groups()."""
    original_method = _original_methods["match_groups"]
    result = original_method(self, default)

    match_id = id(self)
    if match_id in _match_taint_context:
        taint_origins = _match_taint_context[match_id]
        if taint_origins:
            tainted_groups = []
            for i, group in enumerate(result):
                if group is not None and isinstance(group, str):
                    try:
                        start_pos = self.start(i + 1)
                        end_pos = self.end(i + 1)
                        positions = [Position(0, len(group))] if start_pos != -1 else []
                        tainted_groups.append(
                            TaintStr(group, taint_origin=taint_origins, random_pos=positions)
                        )
                    except:
                        tainted_groups.append(group)
                else:
                    tainted_groups.append(group)
            return tuple(tainted_groups)

    return result


def _cursed_match_groupdict(self, default=None):
    """Tainted version of Match.groupdict()."""
    original_method = _original_methods["match_groupdict"]
    result = original_method(self, default)

    match_id = id(self)
    if match_id in _match_taint_context:
        taint_origins = _match_taint_context[match_id]
        if taint_origins:
            tainted_dict = {}
            for name, group in result.items():
                if group is not None and isinstance(group, str):
                    try:
                        start_pos = self.start(name)
                        end_pos = self.end(name)
                        positions = [Position(0, len(group))] if start_pos != -1 else []
                        tainted_dict[name] = TaintStr(
                            group, taint_origin=taint_origins, random_pos=positions
                        )
                    except:
                        tainted_dict[name] = group
                else:
                    tainted_dict[name] = group
            return tainted_dict

    return result


def _cursed_match_expand(self, template):
    """Tainted version of Match.expand()."""
    original_method = _original_methods["match_expand"]

    # Use marker injection for template expansion
    marked_template = (
        inject_random_marker(template) if isinstance(template, (str, TaintStr)) else template
    )
    result = original_method(self, marked_template)

    # Extract positions and combine taint origins
    result, positions = remove_random_marker(result)

    match_id = id(self)
    taint_origins = set()
    if match_id in _match_taint_context:
        taint_origins.update(_match_taint_context[match_id])
    taint_origins.update(get_taint_origins(template))

    if taint_origins:
        return TaintStr(result, taint_origin=list(taint_origins), random_pos=positions)
    return result


# Pattern object method patches
def _cursed_pattern_search(self, string, pos=0, endpos=None):
    """Tainted version of Pattern.search()."""
    original_method = _original_methods["pattern_search"]
    if endpos is None:
        result = original_method(self, string, pos)
    else:
        result = original_method(self, string, pos, endpos)

    if result is not None:
        # Store taint context for this match object
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_pattern_match(self, string, pos=0, endpos=None):
    """Tainted version of Pattern.match()."""
    original_method = _original_methods["pattern_match"]
    if endpos is None:
        result = original_method(self, string, pos)
    else:
        result = original_method(self, string, pos, endpos)

    if result is not None:
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_pattern_fullmatch(self, string, pos=0, endpos=None):
    """Tainted version of Pattern.fullmatch()."""
    original_method = _original_methods["pattern_fullmatch"]
    if endpos is None:
        result = original_method(self, string, pos)
    else:
        result = original_method(self, string, pos, endpos)

    if result is not None:
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_pattern_split(self, string, maxsplit=0):
    """Tainted version of Pattern.split()."""
    original_method = _original_methods["pattern_split"]

    # Use marker injection to track positions through split
    marked_string = inject_random_marker(string, level="char")
    result = original_method(self, marked_string, maxsplit=maxsplit)

    taint_origins = get_taint_origins(string)
    if not taint_origins:
        return result

    # Process each split part
    tainted_result = []
    for part in result:
        if isinstance(part, str):
            clean_part, positions = remove_random_marker(part, level="char")
            if positions or taint_origins:
                tainted_result.append(
                    TaintStr(clean_part, taint_origin=taint_origins, random_pos=positions)
                )
            else:
                tainted_result.append(clean_part)
        else:
            tainted_result.append(part)

    return tainted_result


def _cursed_pattern_findall(self, string, pos=0, endpos=None):
    """Tainted version of Pattern.findall()."""
    original_method = _original_methods["pattern_findall"]
    if endpos is None:
        result = original_method(self, string, pos)
    else:
        result = original_method(self, string, pos, endpos)

    taint_origins = get_taint_origins(string)
    if not taint_origins:
        return result

    # Taint all found strings
    tainted_result = []
    for item in result:
        if isinstance(item, str):
            tainted_result.append(
                TaintStr(item, taint_origin=taint_origins, random_pos=[Position(0, len(item))])
            )
        elif isinstance(item, tuple):
            # Multiple groups case
            tainted_groups = []
            for group in item:
                if isinstance(group, str):
                    tainted_groups.append(
                        TaintStr(
                            group, taint_origin=taint_origins, random_pos=[Position(0, len(group))]
                        )
                    )
                else:
                    tainted_groups.append(group)
            tainted_result.append(tuple(tainted_groups))
        else:
            tainted_result.append(item)

    return tainted_result


def _cursed_pattern_finditer(self, string, pos=0, endpos=None):
    """Tainted version of Pattern.finditer()."""
    original_method = _original_methods["pattern_finditer"]
    if endpos is None:
        iterator = original_method(self, string, pos)
    else:
        iterator = original_method(self, string, pos, endpos)

    taint_origins = get_taint_origins(string)

    # Store taint context for each match as we iterate
    for match in iterator:
        if taint_origins:
            _match_taint_context[id(match)] = taint_origins
        yield match


def _cursed_pattern_sub(self, repl, string, count=0):
    """Tainted version of Pattern.sub()."""
    original_method = _original_methods["pattern_sub"]

    if callable(repl):
        # Handle function callbacks - need to wrap the callback to ensure match objects are tainted
        def wrapped_callback(match):
            # Store taint context for this match before calling user function
            _match_taint_context[id(match)] = get_taint_origins(string)
            return repl(match)

        result = original_method(self, wrapped_callback, string, count)

        # Combine taint from string and callback result
        taint_origins = set(get_taint_origins(string))
        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins))
        return result
    else:
        # Use marker injection to track position changes for string replacements
        marked_string = inject_random_marker(string)
        marked_repl = inject_random_marker(repl) if isinstance(repl, (str, TaintStr)) else repl

        result = original_method(self, marked_repl, marked_string, count)
        result, positions = remove_random_marker(result)

        # Combine taint origins from string and replacement
        taint_origins = set(get_taint_origins(string))
        taint_origins.update(get_taint_origins(repl))

        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins), random_pos=positions)
        return result


def _cursed_pattern_subn(self, repl, string, count=0):
    """Tainted version of Pattern.subn()."""
    original_method = _original_methods["pattern_subn"]

    if callable(repl):
        # Handle function callbacks
        def wrapped_callback(match):
            _match_taint_context[id(match)] = get_taint_origins(string)
            return repl(match)

        result, num_subs = original_method(self, wrapped_callback, string, count)

        # Combine taint from string
        taint_origins = set(get_taint_origins(string))
        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins)), num_subs
        return result, num_subs
    else:
        # Use marker injection to track position changes for string replacements
        marked_string = inject_random_marker(string)
        marked_repl = inject_random_marker(repl) if isinstance(repl, (str, TaintStr)) else repl

        result, num_subs = original_method(self, marked_repl, marked_string, count)
        result, positions = remove_random_marker(result)

        # Combine taint origins from string and replacement
        taint_origins = set(get_taint_origins(string))
        taint_origins.update(get_taint_origins(repl))

        if taint_origins:
            return (
                TaintStr(result, taint_origin=list(taint_origins), random_pos=positions),
                num_subs,
            )
        return result, num_subs


# Module-level function patches
def _cursed_re_search(pattern, string, flags=0):
    """Tainted version of re.search()."""
    original_func = _original_methods["re_search"]
    result = original_func(pattern, string, flags)

    if result is not None:
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_re_match(pattern, string, flags=0):
    """Tainted version of re.match()."""
    original_func = _original_methods["re_match"]
    result = original_func(pattern, string, flags)

    if result is not None:
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_re_fullmatch(pattern, string, flags=0):
    """Tainted version of re.fullmatch()."""
    original_func = _original_methods["re_fullmatch"]
    result = original_func(pattern, string, flags)

    if result is not None:
        _match_taint_context[id(result)] = get_taint_origins(string)

    return result


def _cursed_re_split(pattern, string, maxsplit=0, flags=0):
    """Tainted version of re.split()."""
    original_func = _original_methods["re_split"]

    marked_string = inject_random_marker(string, level="char")
    result = original_func(pattern, marked_string, maxsplit=maxsplit, flags=flags)

    taint_origins = get_taint_origins(string)
    if not taint_origins:
        return result

    tainted_result = []
    for part in result:
        if isinstance(part, str):
            clean_part, positions = remove_random_marker(part, level="char")
            if positions or taint_origins:
                tainted_result.append(
                    TaintStr(clean_part, taint_origin=taint_origins, random_pos=positions)
                )
            else:
                tainted_result.append(clean_part)
        else:
            tainted_result.append(part)

    return tainted_result


def _cursed_re_findall(pattern, string, flags=0):
    """Tainted version of re.findall()."""
    original_func = _original_methods["re_findall"]
    result = original_func(pattern, string, flags)

    taint_origins = get_taint_origins(string)
    if not taint_origins:
        return result

    tainted_result = []
    for item in result:
        if isinstance(item, str):
            tainted_result.append(
                TaintStr(item, taint_origin=taint_origins, random_pos=[Position(0, len(item))])
            )
        elif isinstance(item, tuple):
            tainted_groups = []
            for group in item:
                if isinstance(group, str):
                    tainted_groups.append(
                        TaintStr(
                            group, taint_origin=taint_origins, random_pos=[Position(0, len(group))]
                        )
                    )
                else:
                    tainted_groups.append(group)
            tainted_result.append(tuple(tainted_groups))
        else:
            tainted_result.append(item)

    return tainted_result


def _cursed_re_finditer(pattern, string, flags=0):
    """Tainted version of re.finditer()."""
    original_func = _original_methods["re_finditer"]
    iterator = original_func(pattern, string, flags=flags)

    taint_origins = get_taint_origins(string)

    for match in iterator:
        if taint_origins:
            _match_taint_context[id(match)] = taint_origins
        yield match


def _cursed_re_sub(pattern, repl, string, count=0, flags=0):
    """Tainted version of re.sub()."""
    original_func = _original_methods["re_sub"]

    if callable(repl):
        # Handle function callbacks
        def wrapped_callback(match):
            _match_taint_context[id(match)] = get_taint_origins(string)
            return repl(match)

        result = original_func(pattern, wrapped_callback, string, count=count, flags=flags)

        # Combine taint from string
        taint_origins = set(get_taint_origins(string))
        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins))
        return result
    else:
        # Use marker injection for string replacements
        marked_string = inject_random_marker(string)
        marked_repl = inject_random_marker(repl) if isinstance(repl, (str, TaintStr)) else repl

        result = original_func(pattern, marked_repl, marked_string, count=count, flags=flags)
        result, positions = remove_random_marker(result)

        taint_origins = set(get_taint_origins(string))
        taint_origins.update(get_taint_origins(repl))

        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins), random_pos=positions)
        return result


def _cursed_re_subn(pattern, repl, string, count=0, flags=0):
    """Tainted version of re.subn()."""
    original_func = _original_methods["re_subn"]

    if callable(repl):
        # Handle function callbacks
        def wrapped_callback(match):
            _match_taint_context[id(match)] = get_taint_origins(string)
            return repl(match)

        result, num_subs = original_func(
            pattern, wrapped_callback, string, count=count, flags=flags
        )

        # Combine taint from string
        taint_origins = set(get_taint_origins(string))
        if taint_origins:
            return TaintStr(result, taint_origin=list(taint_origins)), num_subs
        return result, num_subs
    else:
        # Use marker injection for string replacements
        marked_string = inject_random_marker(string)
        marked_repl = inject_random_marker(repl) if isinstance(repl, (str, TaintStr)) else repl

        result, num_subs = original_func(
            pattern, marked_repl, marked_string, count=count, flags=flags
        )
        result, positions = remove_random_marker(result)

        taint_origins = set(get_taint_origins(string))
        taint_origins.update(get_taint_origins(repl))

        if taint_origins:
            return (
                TaintStr(result, taint_origin=list(taint_origins), random_pos=positions),
                num_subs,
            )
        return result, num_subs


def json_patch():
    """Patches related to json module for taint propagation."""
    _store_json_original_methods()

    # Replace module-level functions
    json.loads = _cursed_json_loads
    json.dumps = _cursed_json_dumps


def _store_json_original_methods():
    """Store original JSON methods before patching to avoid recursion."""
    if "json_loads" not in _original_methods:
        _original_methods.update(
            {
                "json_loads": json.loads,
                "json_dumps": json.dumps,
            }
        )


def _cursed_json_loads(
    s,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    **kw,
):
    """Tainted version of json.loads()."""
    original_func = _original_methods["json_loads"]

    # Get taint origins from input string
    taint_origins = get_taint_origins(s)

    if not taint_origins:
        # No taint, use original function
        return original_func(
            s,
            cls=cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )

    # Check if input has position tracking
    random_positions = get_random_positions(s)

    if random_positions:
        # Inject markers into the JSON string before parsing
        marked_json = inject_random_marker(s)

        # Parse the marked JSON
        result = original_func(
            marked_json,
            cls=cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )

        # Traverse result and remove markers from strings, extracting positions
        result = _remove_markers_from_parsed_json(result)
    else:
        # No position tracking, parse normally
        result = original_func(
            s,
            cls=cls,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            object_pairs_hook=object_pairs_hook,
            **kw,
        )

    # Use taint_wrap to recursively wrap the entire result with taint
    return taint_wrap(result, taint_origin=taint_origins)


def _remove_markers_from_parsed_json(obj):
    """Traverse parsed JSON result and remove markers from strings, extracting positions."""

    def _process_value(value):
        if isinstance(value, str):
            # Check if this string contains markers
            if ">>" in value and "<<" in value:
                # Extract positions and clean the string
                clean_value, extracted_positions = remove_random_marker(value)
                if extracted_positions:
                    return TaintStr(clean_value, taint_origin=[], random_pos=extracted_positions)
            return value
        elif isinstance(value, dict):
            return {k: _process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_process_value(item) for item in value]
        else:
            return value

    return _process_value(obj)


def _collect_taint_from_object(obj):
    """Recursively collect all taint origins from nested objects."""
    # Use existing get_taint_origins which handles nested structures and circular references
    return get_taint_origins(obj)


def _inject_markers_in_object(obj, _seen=None):
    """Recursively inject random markers into TaintStr values in nested objects."""
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    _seen.add(obj_id)

    if isinstance(obj, TaintStr):
        # Only inject markers if there are random positions to track
        if get_random_positions(obj):
            return inject_random_marker(obj)
        else:
            # For TaintStr without random positions, add full-string position and inject
            marked_str = TaintStr(
                obj.get_raw(), taint_origin=obj._taint_origin, random_pos=[Position(0, len(obj))]
            )
            return inject_random_marker(marked_str)
    elif isinstance(obj, (TaintInt, TaintFloat, int, float, bool)):
        # Don't inject markers into numeric/boolean types, return as-is
        return obj
    elif isinstance(obj, dict):
        return {k: _inject_markers_in_object(v, _seen) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        result = [_inject_markers_in_object(item, _seen) for item in obj]
        return tuple(result) if isinstance(obj, tuple) else result
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        # Handle custom objects with attributes
        new_obj = obj.__class__.__new__(obj.__class__)
        for attr, value in obj.__dict__.items():
            setattr(new_obj, attr, _inject_markers_in_object(value, _seen))
        return new_obj
    else:
        return obj


def _cursed_json_dumps(
    obj,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    """Tainted version of json.dumps()."""
    original_func = _original_methods["json_dumps"]

    # Collect all taint origins from the input object
    taint_origins = _collect_taint_from_object(obj)

    if not taint_origins:
        # No taint, use original function
        return original_func(
            obj,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            cls=cls,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )

    # Inject markers into tainted strings before serialization
    marked_obj = _inject_markers_in_object(obj)

    # Serialize with markers
    result = original_func(
        marked_obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )

    # Extract positions from the serialized result
    clean_result, positions = remove_random_marker(result)

    # Return TaintStr with combined taint origins and position tracking
    return TaintStr(clean_result, taint_origin=taint_origins, random_pos=positions)
