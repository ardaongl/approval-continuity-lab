"""Offline approval continuity experiments. Importing performs no application IO."""

__version__ = "0.1.0"


def __getattr__(name):
    if name == "Lab":
        from .mediator import Lab
        return Lab
    raise AttributeError(name)
