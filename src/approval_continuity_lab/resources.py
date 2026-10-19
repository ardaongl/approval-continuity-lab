"""Bundled immutable data, loaded only when explicitly requested."""
import importlib.resources
import json


def bytes_asset(name):
    # Only fixed names chosen by package code, never arbitrary user paths.
    if name not in ("base-config.json", "submission.json", "proposal.expected.json", "review.expected.json", "decision-input.json", "decision.expected.json", "execution-input.json", "canonical-vectors.json", "duplicate-key.input.txt", "d01-report.golden.json", "d08-report.golden.json", "digests.expected.json", "review-leaves.expected.json", "review-suffix.golden.txt"):
        raise ValueError("Unknown built-in asset")
    return importlib.resources.files("approval_continuity_lab").joinpath("documentation", "docs", "fixtures", name).read_bytes()


def asset(name):
    return json.loads(bytes_asset(name))
