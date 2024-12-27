"""Provide config options for Sphinx documentation."""

import datetime
from pathlib import Path

# Project information
now = datetime.datetime.now()
project = "camacq"
project_copyright = f"{now.year}, Martin Hjelmare"
author = "Martin Hjelmare"

project_dir = Path(__file__).parent.parent.resolve()
release = (project_dir / "camacq" / "VERSION").read_text(encoding="utf-8").strip()
version = ".".join(release.split(".")[:2])

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
]

autodoc_default_options = {
    "members": None,
    "inherited-members": True,
    "show-inheritance": True,
}

# The suffix of source filenames.
source_suffix = ".rst"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# Options for HTML output
html_theme = "sphinx_rtd_theme"
