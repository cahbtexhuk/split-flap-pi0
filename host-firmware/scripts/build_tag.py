Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

import datetime
import os
import subprocess

project_dir = env["PROJECT_DIR"]  # noqa: F821


def git(*args):
    try:
        return subprocess.check_output(
            ["git", *args], cwd=project_dir, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return ""


commit = git("rev-parse", "--short", "HEAD") or "nogit"
if git("status", "--porcelain", "--", "."):
    commit += "-dirty"
stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# A generated header, instead of a -D flag, so only the files including it rebuild.
include_dir = os.path.join(project_dir, "include")
os.makedirs(include_dir, exist_ok=True)
with open(os.path.join(include_dir, "build_tag.h"), "w") as f:
    f.write('#pragma once\n#define BUILD_TAG "%s %s"\n' % (commit, stamp))
