"""Setup file for camacq package."""
import io

from setuptools import find_packages, setup

from camacq.const import __version__

GITHUB_URL = 'https://github.com/CellProfiling/cam_acq'


def read(*filenames, **kwargs):
    """Return joined content of *filenames.

    Parameters
    ----------
    *filenames : list
        Variable length filename list.
    **kwargs
        Arbitrary keyword arguments.
    encoding : codec, optional
        Encoding to use to open filename. See
        https://docs.python.org/2/library/codecs.html#standard-encodings
        for supported encodings.
    sep : str, optional
        Separator to use between joined content of filenames.

    Returns
    -------
    string
        Return joined content of *filenames.
    """
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as file_open:
            buf.append(file_open.read())
    return sep.join(buf)


LONG_DESCR = read('README.rst')
DOWNLOAD_URL = '{}/archive/master.zip'.format(GITHUB_URL)
CLASSIFIERS = [
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Science/Research',
    'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 2.7',
]

CONFIG = {
    'description': 'Control microscope through client server program.',
    'long_description': LONG_DESCR,
    'author': 'Martin Hjelmare',
    'url': GITHUB_URL,
    'download_url': DOWNLOAD_URL,
    'license': 'GPLv3',
    'author_email': 'marhje52@kth.se',
    'version': __version__,
    'install_requires': [
        'colorlog',
        'jinja2',
        'matrixscreener',
        'numpy',
        'Pillow',
        'PyYAML',
        'ruamel.yaml',
        'tifffile',
        'zope.event',
    ],
    'packages': find_packages(exclude=['contrib', 'docs', 'tests*']),
    'include_package_data': True,
    'entry_points': {
        'console_scripts': ['camacq = camacq.__main__:main']},
    'name': 'camacq',
    'zip_safe': False,
    'classifiers': CLASSIFIERS,
}

setup(**CONFIG)
