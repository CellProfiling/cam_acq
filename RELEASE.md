# Release procedure

- Create a release branch from develop, called `rc`.
It's important to name it correctly to allow the github release action to work.
- Merge `master` branch into the release branch `rc` to make the PR mergeable.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Update `CHANGELOG.md` by running `scripts/gen_changelog`.
- Commit and push the release branch.
- Create a pull request from release branch `rc` to `master` with the upcoming release number as the title. Put the changes for the new release from the updated changelog as the PR message.
- Merge the pull request into `master`, do not squash.
- Fetch and checkout the `master` branch.
- Fetch and checkout the `develop` branch.
- Checkout a new branch to bump version, eg `bump-version` from `develop`.
- Merge `master` into the new branch `bump-version`.
- Update version in `VERSION` to the new develop version number, eg `'0.3.0.dev0'`
- Commit with commit message `Bump version to 0.3.0.dev0` and push the `bump-version` branch.
- Create a pull request from branch `bump-version` to `develop`.
- Squash merge the pull request into `develop`.
