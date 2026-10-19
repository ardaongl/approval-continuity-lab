"""Copy authored documentation into package resources; never regenerate goldens."""
from pathlib import Path
import shutil


def sync(root):
    destination = root / "src/approval_continuity_lab/documentation"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "DISCOVERY.md", "AGENTS.md", "GOAL.md"):
        shutil.copy2(root / name, destination / name)
    shutil.copytree(root / "docs", destination / "docs", dirs_exist_ok=True)


if __name__ == "__main__":
    sync(Path(__file__).resolve().parents[1])
