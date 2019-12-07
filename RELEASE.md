# Release procedure

- Create a release branch from develop, called the same as the release number.
- Merge master into the release branch to make the PR mergeable.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Update `CHANGELOG.md` by running `scripts/gen_changelog`.
- Commit and push the release branch.
- Create a pull request from release branch to master with the upcoming release number as the title. Put the changes for the new release from the updated changelog as the PR message.
- Merge the pull request into master, do not squash.
- Go to github releases and tag a new release on the master branch. Use the description from the merged PR.
- Fetch and checkout the master branch.
- Fetch and checkout the develop branch.
- Merge master into develop.
- Update version in `VERSION`to the new develop version number, eg `'0.3.0.dev0'`
- Commit the version bump and push to develop branch.
