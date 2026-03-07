"""Test the CLI."""

import subprocess
import sys


def test_can_run_as_python_module():
    """Run the CLI as a Python module."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "camacq", "--help"],
        check=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert b"usage: __main__.py [-h]" in result.stdout
