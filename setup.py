"""Preserve the source documentation layout inside built package resources."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


def sync():
    root = Path(__file__).parent
    destination = root / "src/approval_continuity_lab/documentation"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "DISCOVERY.md", "AGENTS.md", "GOAL.md"):
        shutil.copy2(root / name, destination / name)
    shutil.copytree(root / "docs", destination / "docs", dirs_exist_ok=True)


class Build(build_py):
    def run(self):
        sync()
        super().run()


class Source(sdist):
    def run(self):
        sync()
        super().run()


setup(cmdclass={"build_py": Build, "sdist": Source})
