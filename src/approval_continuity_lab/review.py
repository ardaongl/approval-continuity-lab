"""Complete, escaped rendering of stored review values."""
from .canonical import canonical
from .validation import pointer


def leaves(value, path=""):
    if isinstance(value, dict):
        if not value:
            yield path or "/", {}
        for key in sorted(value):
            yield from leaves(value[key], pointer(path, key))
    elif isinstance(value, list):
        yield (path or "/") + "#length", len(value)
        for i, item in enumerate(value):
            yield from leaves(item, pointer(path, i))
    else:
        yield path or "/", value


def render(review, description):
    return "".join("REVIEW " + p + ": " + canonical(v) + "\n" for p, v in leaves(review)) + "UNTRUSTED DESCRIPTION: " + canonical(description) + "\n"
