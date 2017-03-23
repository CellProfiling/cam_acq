# How to contribute

Bug reports in the issue tracker and pull requests are welcome.

## Pull request
1. Fork the repository at github.
2. Clone your fork.

  ```
  $ git clone https://github.com/YOUR_GIT_USERNAME/cam_acq.git
  $ cd cam_acq
  ```
3. Add the main repository as upstream.

  ```
  $ git remote add upstream https://github.com/CellProfiling/cam_acq.git
  ```
4. Fetch dev branch from upstream and checkout to a local branch.

  ```
  $ git fetch upstream dev
  $ git checkout dev
  ```
5. Create a topic branch based off dev branch.

  ```
  $ git checkout -b cool_new_feature dev
  ```
6. Make your changes in the new topic branch. New features should preferably be accompanied with new tests. [PEP8](https://www.python.org/dev/peps/pep-0008/) and [PEP257](https://www.python.org/dev/peps/pep-0257/) style should be followed. We use [pylint](https://www.pylint.org/) and [flake8](http://flake8.pycqa.org/en/latest/) as code linters.
7. Test with tox and make sure existing tests don't fail. Linting will also be checked when tox is run.

  ```
  $ pip install tox
  $ tox
  ```
8. Add and commit your work and describe the additions and or changes in the commit message. Use an editor for the commit message, not the command line. Try to keep the header of the commit message within 50 characters and the body within 72 characters per line. A blank line should separate the header from the body of the commit message. Markdown is cool.

  ```
  $ git add -A
  $ git commit
  ```
9. Push you local changes to your fork.

  ```
  $ git push origin HEAD
  ```
10. Create a pull request at github to the main cam_acq repository and target the dev branch with your changes. The master branch should only be targeted when a new version of cam_acq is ready. Changes in the dev branch is then merged with the master branch.
11. Watch Travis builds turn green :white_check_mark:, and get the :thumbsup: in the code review.
