"""D006: build a throwaway git repo to practise recovery commands on.

    uv run python d006_git_drills/setup_sandbox.py

Creates a sandbox in the SYSTEM TEMP directory - never inside fde-plan,
so your real learning history is never at risk.
Delete the sandbox and re-run this script to start over.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed: {' '.join(args)}\n{result.stderr}")
    return result.stdout.strip()


def main() -> None:
    sandbox = Path(tempfile.gettempdir()) / "fde-git-sandbox"

    if sandbox.exists():
        print(f"sandbox already exists: {sandbox}")
        print("delete it and re-run to start fresh:")
        print(f"  Remove-Item -Recurse -Force {sandbox}")
        return

    sandbox.mkdir(parents=True)
    print(f"creating sandbox at {sandbox}\n")

    # Fully isolated identity, independent of the user's global config.
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Sandbox User",
            "GIT_AUTHOR_EMAIL": "sandbox@example.com",
            "GIT_COMMITTER_NAME": "Sandbox User",
            "GIT_COMMITTER_EMAIL": "sandbox@example.com",
        }
    )

    # Disable signing and hooks so nothing in the user's setup interferes.
    run(["git", "init", "-b", "main"], sandbox, env)
    run(["git", "config", "commit.gpgsign", "false"], sandbox, env)
    run(["git", "config", "core.hooksPath", os.devnull], sandbox, env)

    # --- a deliberately messy history ------------------------------------ #
    commits = [
        ("main.py", "print('v1')\n", "feat: add main entry"),
        ("main.py", "print('v1')\nprint('helper')\n", "fix"),
        ("main.py", "print('v1')\nprint('helper v2')\n", "fix again"),
        ("README.md", "# sandbox\n", "add readme"),
        ("main.py", "print('v1')\nprint('helper v3')\n", "真的好了"),
        ("utils.py", "def add(a, b):\n    return a + b\n", "feat: add utils"),
    ]

    for filename, content, message in commits:
        (sandbox / filename).write_text(content, encoding="utf-8")
        run(["git", "add", "."], sandbox, env)
        run(["git", "commit", "-m", message], sandbox, env)

    # a second branch, for the "wrong branch" and "stash" drills
    run(["git", "checkout", "-b", "feature/experiment"], sandbox, env)
    (sandbox / "exp.py").write_text("# experiment\n", encoding="utf-8")
    run(["git", "add", "."], sandbox, env)
    run(["git", "commit", "-m", "wip: experiment"], sandbox, env)
    run(["git", "checkout", "main"], sandbox, env)

    # leave one uncommitted change behind, for the stash drill
    (sandbox / "main.py").write_text(
        "print('v1')\nprint('WIP: half-finished edit')\n", encoding="utf-8"
    )

    print("=== git log (main) ===")
    print(run(["git", "log", "--oneline"], sandbox, env))
    print("\n=== branches ===")
    print(run(["git", "branch"], sandbox, env))
    print("\n=== git status (note the uncommitted change) ===")
    print(run(["git", "status", "-s"], sandbox, env))

    print(f"\n{'=' * 60}")
    print("sandbox ready. Open a terminal there:")
    print(f"  cd {sandbox}")
    print("\nThen follow d006_git_drills/README.md, scenarios 1-5.")
    print("This repo lives in temp - nothing here can touch fde-plan.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
