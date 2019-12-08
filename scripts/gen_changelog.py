#!/usr/bin/env python3
"""Generate changelog."""
import os
from pathlib import Path

from pygcgen.main import ChangelogGenerator

GITHUB_PROJECT = "cam_acq"
GITHUB_USER = "CellProfiling"
HISTORY_FILE = "HISTORY.md"
# Change this to 0.4.0 after changelog is generated when releasing 0.4.0.
TAG_SINCE = "0.4.0"


def validate_version():
    """Validate version before release."""
    import camacq  # pylint: disable=import-outside-toplevel

    version_string = camacq.__version__
    versions = version_string.split(".", 3)
    try:
        for ver in versions:
            int(ver)
    except ValueError:
        print(
            "Only integers are allowed in release version, "
            "please adjust current version {}".format(version_string)
        )
        return None
    return version_string


def generate():
    """Generate changelog."""
    old_dir = Path.cwd()
    proj_dir = Path(__file__).parent.parent
    os.chdir(proj_dir)
    version = validate_version()
    if not version:
        os.chdir(old_dir)
        return
    print("Generating changelog for version {}".format(version))
    options = [
        "--user",
        GITHUB_USER,
        "--project",
        GITHUB_PROJECT,
        "-v",
        "--with-unreleased",
        "--future-release",
        version,
        "--section",
        "**Breaking Changes:**",
        "breaking change",
        "--since-tag",
        TAG_SINCE,
        "--base",
        HISTORY_FILE,
    ]
    generator = ChangelogGenerator(options)
    generator.run()
    os.chdir(old_dir)


if __name__ == "__main__":
    generate()
