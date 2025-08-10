from typing import Callable, Any


def _ask_field(
    input_text: str,
    convert_value: Callable[[Any], Any] | None = None,
    default: Any | None = None,
    error_message: str | None = None,
):
    ask_again = True
    while ask_again:
        result = input(input_text)
        try:
            if default is not None and len(result) == 0:
                return default
            return convert_value(result) if convert_value is not None else result
        except Exception:
            if error_message is not None:
                print(error_message)


def _convert_yes_no_to_bool(value: str) -> bool:
    return {"yes": True, "no": False}[value.lower()]
