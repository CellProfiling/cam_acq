#!/usr/bin/env python3
"""Generate changelog."""
import os
from pathlib import Path

from pygcgen.main import ChangelogGenerator


def validate_version():
    """Validate version before release."""
    import camacq
    version_string = camacq.__version__
    versions = version_string.split('.', 3)
    try:
        for ver in versions:
            int(ver)
    except ValueError:
        print(
            'Only integers are allowed in release version, '
            'please adjust current version {}'.format(version_string))
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
    print('Generating changelog for version {}'.format(version))
    options = [
        '--user', 'CellProfiling', '--project', 'cam_acq',
        '-v', '--with-unreleased', '--future-release', version]
    generator = ChangelogGenerator(options)
    generator.run()
    os.chdir(old_dir)


if __name__ == '__main__':
    generate()
