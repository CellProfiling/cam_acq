try:
    from setuptools import setup, find_packages

    def readme():
        with open('README.md') as f:
            return f.read()
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Control microscope through client server program.',
    'long_description': readme(),
    'author': 'Martin Hjelmare',
    'url': 'https://github.com/MartinHjelmare/cam_acq',
    'download_url': 'https://github.com/MartinHjelmare/cam_acq/archive/master.zip',
    'license': 'GPLv3',
    'author_email': 'marhje52@kth.se',
    'version': '0.1.0',
    'install_requires': [
        'nose',
    ],
    'packages': find_packages(exclude=['contrib', 'docs', 'tests*']),
    'include_package_data': True,
    'scripts': ['scripts/path/to/script'],
    'name': 'cam_acq',
    'zip_safe': False,
    'classifiers': [
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
    ],
}

setup(**config)
