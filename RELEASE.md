# Release Process

This project follows semantic versioning and ships releases from the `main` branch.

## Versioning policy

- `MAJOR`: breaking API/CLI changes
- `MINOR`: new features, backwards compatible
- `PATCH`: fixes and maintenance

## Cut a release

1. Ensure the working tree is clean and CI is green.
2. Bump the version in `pyproject.toml`.
3. Update `CHANGELOG.md` with the release notes.
4. Run tests locally:
   ```bash
   pytest
   cd web && npm test && npm run build
   ```
5. Tag and push:
   ```bash
   git tag -a vX.Y.Z -m "xAI-Forge vX.Y.Z"
   git push origin vX.Y.Z
   ```
6. Create the GitHub release from the tag and attach release notes.

## Artifacts

- Python package is distributed via `pip install -e .` for local usage
- Web UI is built with `npm run build`
- Docker image builds from the root `Dockerfile`
