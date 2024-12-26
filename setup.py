"""Set up file for camacq package."""

from pathlib import Path

from setuptools import find_packages, setup

PROJECT_DIR = Path(__file__).parent.resolve()
VERSION = (PROJECT_DIR / "camacq" / "VERSION").read_text(encoding="utf-8").strip()

GITHUB_URL = "https://github.com/CellProfiling/cam_acq"
REQUIRES = [
    "async_timeout",
    "colorlog",
    "jinja2",
    "leicacam>=0.4.0",
    "leicaimage",
    "numpy",
    "ruamel.yaml>=0.15",
    "tifffile",
    "voluptuous",
    "xmltodict",
]

README_FILE = PROJECT_DIR / "README.md"
LONG_DESCRIPTION = README_FILE.read_text(encoding="utf-8")

DOWNLOAD_URL = f"{GITHUB_URL}/archive/master.zip"
CLASSIFIERS = [
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    "Development Status :: 3 - Alpha",
    # Indicate who your project is intended for
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
    # Pick your license as you wish (should match "license" above)
    "License :: OSI Approved :: Apache Software License",
    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

CONFIG = {
    "description": "Control microscope through client server program.",
    "long_description": LONG_DESCRIPTION,
    "long_description_content_type": "text/markdown",
    "author": "Martin Hjelmare",
    "url": GITHUB_URL,
    "download_url": DOWNLOAD_URL,
    "license": "Apache-2.0",
    "author_email": "marhje52@gmail.com",
    "version": VERSION,
    "python_requires": ">=3.10",
    "install_requires": REQUIRES,
    "packages": find_packages(exclude=["contrib", "docs", "tests*"]),
    "include_package_data": True,
    "entry_points": {
        "console_scripts": ["camacq = camacq.__main__:main"],
        "camacq.plugins": [
            "api = camacq.plugins.api",
            "automations = camacq.plugins.automations",
            "leica = camacq.plugins.leica",
            "rename_image = camacq.plugins.rename_image",
            "sample = camacq.plugins.sample",
        ],
    },
    "name": "camacq",
    "zip_safe": False,
    "classifiers": CLASSIFIERS,
}

setup(**CONFIG)
