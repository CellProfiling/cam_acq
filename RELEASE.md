# Release procedure

- Create a release branch from develop.
- Merge `master` branch into the release branch to make the PR mergeable.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Commit and push the release branch.
- Create a pull request from release branch to `master` with the upcoming release number as the title.
- Merge the pull request into `master`, do not squash.
- Wait for all GitHub actions to have run successfully.
- Go to GitHub releases page and publish the current draft release, setting the correct title and tag version from master branch. Do not use a `v` prefix for the tag.
- Fetch and checkout the `master` branch.
- Fetch and checkout the `develop` branch.
- Merge `master` into branch `develop`.
- Update version in `VERSION` to the new develop version number, eg `'0.3.0.dev0'`
- Commit with commit message `Bump version to 0.3.0.dev0` and push the `develop` branch to origin.
