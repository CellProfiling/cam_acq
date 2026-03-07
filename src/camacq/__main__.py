"""Make the CLI runnable using python -m camacq."""

import argparse
import asyncio
import logging
from pathlib import Path
import sys
from typing import Any

from camacq import bootstrap
import camacq.config as config_util
from camacq.const import CONFIG_DIR, LOG_LEVEL


def check_dir_arg(path: str) -> Path:
    """Check that argument is a directory."""
    # remove if not needed
    p = Path(path)
    if p.is_dir():
        return p.resolve()
    raise argparse.ArgumentTypeError(f"String {path} is not a path to a directory")


def check_log_level(loglevel: str) -> int:
    """Validate log level and return it if valid."""
    # assuming loglevel is bound to the string value obtained from the
    # command line argument. Convert to upper case to allow the user to
    # specify --log=DEBUG or --log=debug
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise argparse.ArgumentTypeError(f"String {loglevel} is not a valid log level")
    return numeric_level


def parse_command_line(args: list[str] | None = None) -> dict[str, Any]:
    """Parse the provided command line."""
    parser = argparse.ArgumentParser(
        description="Control microscope through client-server program."
    )
    parser.add_argument(
        "--log-level",
        dest=LOG_LEVEL,
        type=check_log_level,
        help="an option to specify lowest log level to log",
    )
    parser.add_argument(
        "-C",
        "--config",
        dest=CONFIG_DIR,
        type=check_dir_arg,
        default=config_util.get_default_config_dir(),
        help="the path to camacq configuration directory",
    )
    parsed_args = parser.parse_args(args=args)
    cmd_args_dict = vars(parsed_args)
    cmd_args_dict = {key: val for key, val in cmd_args_dict.items() if val}

    return cmd_args_dict


def ensure_config_path(config_dir: Path) -> None:
    """Validate the configuration directory."""
    # Test if configuration directory exists
    if config_dir.is_dir():
        return
    try:
        config_dir.mkdir()
    except OSError:
        print(
            "Fatal Error: Unable to create default configuration "
            f"directory: {config_dir}"
        )
        sys.exit(1)


def ensure_config_file(config_dir: Path) -> Path:
    """Ensure configuration file exists."""
    config_path = config_util.ensure_config_exists(config_dir)

    if config_path is None:
        print("Error getting configuration path")
        sys.exit(1)

    return config_path


async def setup_and_start(config_file: Path, cmd_args: dict[str, Any]) -> int:
    """Set up app and start."""
    try:
        center = await bootstrap.setup_file(config_file, cmd_args)
    except Exception as exc:
        print("An error occurred during setup:", exc)
        return 1
    return await center.start()


def main(args: list[str] | None = None) -> int:
    """Run main function."""
    # Parse command line arguments
    cmd_args = parse_command_line(args=args)
    config_dir = cmd_args[CONFIG_DIR]
    ensure_config_path(config_dir)
    config_file = ensure_config_file(config_dir)
    exit_code = asyncio.run(setup_and_start(config_file, cmd_args))
    return exit_code


if __name__ == "__main__":
    main()
