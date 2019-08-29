#!/usr/bin/env python
"""Make sure fixtures are in place before running tests."""
import fnmatch
import gzip
import os
import shutil

import click

GAIN_DATA_DIR = os.path.join(os.path.dirname(__file__), "../tests/fixtures/gain_data")


def _find_files(root_dir, search):
    """Search for files in root directory."""
    matches = []
    for root, _, filenames in os.walk(os.path.normpath(root_dir)):
        for filename in fnmatch.filter(filenames, search):
            matches.append(os.path.join(root, filename))
    return matches


def pack_gain_fixture(root_dir=None):
    """Gunzip tif images for gain tests."""
    if root_dir is None:
        root_dir = GAIN_DATA_DIR
    matches = _find_files(root_dir, "*.tif")
    print("Gzipping the images, this will take some time...")
    for path in matches:
        gz_path = "{}.gz".format(path)
        with open(path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(path)


def unpack_gain_fixture(root_dir=None):
    """Unzip gunzipped tif images for gain tests."""
    if root_dir is None:
        root_dir = GAIN_DATA_DIR
    matches = _find_files(root_dir, "*.gz")
    for gz_path in matches:
        path, _ = os.path.splitext(gz_path)
        with gzip.open(gz_path, "rb") as f_in:
            with open(path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)


@click.command()
@click.option("--pack/--unpack", default=False)
def main(pack):
    """Pack or unpack the images for test fixtures."""
    if pack:
        pack_gain_fixture()
    else:
        unpack_gain_fixture()


if __name__ == "__main__":
    main()  # pylint:disable=no-value-for-parameter
