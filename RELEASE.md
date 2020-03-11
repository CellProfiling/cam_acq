# Release procedure

- Create a release branch from develop.
- Merge `master` branch into the release branch to make the PR mergeable.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Commit and push the release branch.
- Create a pull request from release branch to `master` with the upcoming release number as the title. Put the changes for the new release from the updated changelog as the PR message.
- Merge the pull request into `master`, do not squash.
- Fetch and checkout the `master` branch.
- Fetch and checkout the `develop` branch.
- Merge `master` into branch `develop`.
- Update version in `VERSION` to the new develop version number, eg `'0.3.0.dev0'`
- Commit with commit message `Bump version to 0.3.0.dev0` and push the `develop` branch to origin.
