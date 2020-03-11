# Release procedure

- Create a release branch from master.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Commit and push the release branch.
- Create a pull request from release branch to `master` with the upcoming release number as the title.
- Squash merge the pull request into `master`.
- Wait for all GitHub actions to have run successfully.
- Go to GitHub releases page and publish the current draft release, setting the correct title and tag version from master branch. Do not use a `v` prefix for the tag.
