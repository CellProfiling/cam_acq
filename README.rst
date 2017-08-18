cam-acq |Build Status| |license-badge|
======================================

Python project to control microscope through client-server program.

Install prerequisites
---------------------
- Make sure R is available on system and specifically `Rscript` command.
- On a debian system you can run:

::

  apt-get install r-base
  Rscript --version

Install
-------
- Install the camacq package. It requires python2.7.

::

  # Check python version.
  python --version
  # Clone the repo.
  git clone https://github.com/CellProfiling/cam_acq.git
  # Enter directory.
  cd camacq
  # Checkout master branch.
  git checkout master
  # Install package using requirements file.
  pip install -r requirements.txt
  # Test that program is callable and show help.
  camacq -h

Run
---
- Run camcaq with 63x objective.

  - Set the directory where images are exported from the microscope. This is the positional argument without option. In this example we assume it is /image_export.
  - Set the ip address or DNS address of the microscope computer, ie --host option. In this example we assume it is 127.0.0.1. The default value is localhost.
  - Set the number and format of the fields in the wells, ie --x-fields and --y-fields. In this example we assume it's two fields in x and three fields in y. The default value is 2 for both x and y.
  - Set the integer representing the order of the experiment job in the imaging pattern, ie --first-job option. In this example we assume it's 1. The default value is 2.
  - Set the path to the csv template file, that you want to use, ie --template-file option. In this example we assume it's `/template.csv`. The default value is no template file.
  - Set the objective to use for the experiment, ie --objective option. In this example we use the 63x objective. ie end_63x. You can chose between: end_10x, end_40x or end_63x.
  - Set the log level to use when running the program with --log-level option. In this example we set DEBUG level.
  - Set the path to the configuration directory with the --config option.
    If you don't set a path, the program will try to use the .camacq directory in the home directory of the user that runs the program.
    If that directory doesn't exist, the program will try to create the directory. In this example we'll set a path to /config.

::

  camacq /image_export --host 127.0.0.1 --x-fields 2 --y-fields 3 \
    --first-job 1 --template-file /template.csv --objective end_63x \
    --log-level DEBUG --config /config

Configure
---------
All options are configurable from the config file and overridable from the command line. See below for example options to set in the configuration file config.yml.

::

  host: localhost
  port: 8895
  last_well: 'U11--V07'
  fields_x: 2
  fields_y: 2
  first_job: 2
  objective: end_63x
  gain_only: false
  config_dir: '/path/to/config/directory/'
  coord_file: '/path/to/coordinate/file.csv'
  init_gain: '/path/to/inital/gain/file.csv'
  input_gain: '/path/to/input/gain/file.csv'
  template_file: '/path/to/template/file.csv'


.. |license-badge| image:: http://img.shields.io/badge/license-GPLv3-blue.svg
   :target: https://www.gnu.org/copyleft/gpl.html

.. |Build Status| image:: https://travis-ci.org/CellProfiling/cam_acq.svg?branch=develop
   :target: https://travis-ci.org/CellProfiling/cam_acq
