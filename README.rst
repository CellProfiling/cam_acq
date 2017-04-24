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

- Run camcaq with 63x objective.
  - You need to know the ip address of the microscope computer, ie host option.
    In this example we assume it is 127.0.0.1.
  - You need to know the directory where images are exported from the microscope, ie  --imaging-dir option.
    In this example we assume it is /image_export.
  - You need to know the number and format of the fields in the wells, ie --x-fields and --y-fields.
    In this example we assume it's two fields in x and three fields in y.
  - You need to know the integer representing the order of the experiment job in the imaging pattern, ie --first-job option.
    In this example we assume it's 1.
  - You need to know the path to the csv template file, that you want to use, ie --template-file option.
    In this example we assume it's `/template.csv`
  - You need to decide what objective to use for the experiment.
    In this example we use the 63x objective, ie --end-63x option.
  - You can set the log level to use when running the program with --log-level option.
    In this example we set DEBUG level.
  - You can set the path to the configuration directory with the --config option.
    If you don't set a path, the program will try to use the .camacq directory in the home directory of the user that runs the program.
    If that directory doesn't exist, the program will try to create the directory. In this example we'll set a path to /config

::

  camacq 127.0.0.1 --imaging-dir /image_export --x-fields 2 --y-fields 3 \
    --first-job 1 --template-file /template.csv --end-63x \
    --log-level DEBUG --config /config

.. |license-badge| image:: http://img.shields.io/badge/license-GPLv3-blue.svg
   :target: https://www.gnu.org/copyleft/gpl.html

.. |Build Status| image:: https://travis-ci.org/CellProfiling/cam_acq.svg?branch=develop
   :target: https://travis-ci.org/CellProfiling/cam_acq
