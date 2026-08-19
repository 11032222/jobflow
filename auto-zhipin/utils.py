import re


def remove_json_fences(raw: str):
    return re.sub(r"`{3}(json)?\n?", "", raw)
