# Release procedure

- Create a release branch from main.
- Update version in `VERSION`to the new version number, eg `'0.2.0'`.
- Commit with commit message `Bump version to 0.2.0` and push the release branch to origin.
- Create a pull request from release branch to `main` with the commit message as title.
- Squash merge the pull request into `main`.
- Wait for all GitHub actions to have run successfully.
- Go to GitHub releases page and publish the current draft release, setting the correct title and tag version from main branch. Do not use a `v` prefix for the tag.
