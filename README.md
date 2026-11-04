# FOR-CAST fork of Extension-Dynamic-Fire-System

This branch, `forcast/ci`, is the fork's default branch only so that GitHub offers its workflows to run by hand. It holds no extension code. The extension is on `master`, which is kept identical to [LANDIS-II-Foundation/Extension-Dynamic-Fire-System](https://github.com/LANDIS-II-Foundation/Extension-Dynamic-Fire-System) `master`; pull requests to upstream are made from branches off `master`.

To sync `master` with upstream, name the branch: `gh repo sync FOR-CAST/Extension-Dynamic-Fire-System --source LANDIS-II-Foundation/Extension-Dynamic-Fire-System --branch master`.

## Build an installer for upstream pull requests

Actions, "Build Windows installer", "Run workflow". Enter the upstream pull request numbers to merge onto upstream `master`, in order (e.g. `18, 19, 20`), or leave the list empty to build `master` alone. From the command line:

```sh
gh workflow run build-installer.yml -R FOR-CAST/Extension-Dynamic-Fire-System -f prs="18, 19, 20"
```

The run's artifact `dynamic-fire-installer-<prs>-<commit>` holds the installer, the DLLs it bundles, their checksums and `BUILD-INFO.txt` (the commits it was built from). The workflow file is the same one proposed upstream; there it also runs on every pull request.
