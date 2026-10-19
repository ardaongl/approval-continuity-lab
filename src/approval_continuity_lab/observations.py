"""Independent read-only SQL oracles for the educational scenario coordinator.

These queries do not call the mediator, store validation or report assertions.
They observe durable rows using a fresh connection, including while a worker holds
the writer lock. No authority decision is made from these observations.
"""
import sqlite3
from contextlib import closing


def snapshot(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        return {name: [dict(row) for row in connection.execute("SELECT * FROM " + name + " ORDER BY 1")]
                for name in ("meta", "services", "proposals", "decisions", "executions", "transitions")}


def check(condition):
    if not condition:
        raise RuntimeError("Scenario assertion failed")
