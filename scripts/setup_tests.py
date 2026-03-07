#!/usr/bin/env python3
"""Make sure fixtures are in place before running tests."""

import gzip
from pathlib import Path
import shutil
from typing import Annotated

import typer

IMAGE_DATA_DIR = Path(__file__).parent.parent / "tests/fixtures/image_data"
cli = typer.Typer()


def pack_image_fixture(root_dir: str | None = None) -> None:
    """Gunzip tif images for image tests."""
    if root_dir is None:
        root_dir = str(IMAGE_DATA_DIR)
    matches = Path(root_dir).glob("**/*.tif")
    print("Gzipping the images, this will take some time...")
    for path in matches:
        gz_path = f"{path}.gz"
        with open(path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        path.unlink()


def unpack_image_fixture(root_dir: str | None = None) -> None:
    """Unzip gunzipped tif images for image tests."""
    if root_dir is None:
        root_dir = str(IMAGE_DATA_DIR)
    matches = Path(root_dir).glob("**/*.gz")
    for gz_path in matches:
        path = gz_path.parent / gz_path.stem
        with gzip.open(gz_path, "rb") as f_in:
            with open(path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)


@cli.command()
def main(pack: Annotated[bool, typer.Option("--pack/--unpack")] = False) -> None:
    """Pack or unpack the images for test fixtures."""
    if pack:
        pack_image_fixture()
    else:
        unpack_image_fixture()


if __name__ == "__main__":
    main()
