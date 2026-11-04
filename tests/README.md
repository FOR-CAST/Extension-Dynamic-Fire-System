# Test cases

Each case is a small LANDIS-II scenario that runs Dynamic Fire System, with Dynamic Fuel System and ForC Succession. It runs inside the LANDIS-II Docker image, with a freshly built Dynamic Fire DLL mounted over the image's copy. For each run, `check.py` does two things.

It checks the run against the user guide, in every time step:

- every event's `DamagedSites` equals its `SitesChecked`, and their sums equal the burned cells on the severity map (sections 3.1, 3.2);
- the events' `MeanSeverity` x `SitesChecked` sum to the severities on the map (1.9);
- the summary log's `NumberFires` equals the events in the event log, `TotalSitesBurned` the burned cells on the map, and each `EcoMaps_` column the burned cells in its fire region (3.3);
- every cohort on a severity-5 cell dies, and the events' `CohortsKilled` sum to the cohorts that died on burned cells (1.9). This uses ForC Succession's `log_BiomassC.csv`, so it runs only when ForC logs biomass every year.

It also writes a digest:

- `fire.csv`: per time step, the events, burned cells by severity, `CohortsKilled`, the cohorts that died, and the summary log's columns;
- `sha256sums.txt`: checksums of the fire logs, the severity maps and the ForC logs.

A case passes when every check holds and both digest files match its `expected/` copies.

The workflow `.github/workflows/test-cases.yml` runs every case on pull requests that change `src/` or `tests/`, and on pushes to `master`.

## Run locally

Needs Docker and Python 3.

```
tests/build.sh <landis image@sha256:...> build                 # build the DLL into build/
tests/run-cases.sh build/Landis.Extension.DynamicFire-v4.dll <landis image@sha256:...>
```

The image digest the workflow uses is `LANDIS_IMAGE` in `.github/workflows/test-cases.yml`. Each case runs in `tests/work/<name>/`, which keeps the outputs, `console.log`, `check.log`, and the diffs of a failing case.

## A change that is meant to change results

Run with `--update` to rewrite `expected/`, then commit the new files with the change. The diff of `fire.csv` shows the effect in review. A run that fails a check is never written.

```
tests/run-cases.sh --update build/Landis.Extension.DynamicFire-v4.dll <landis image@sha256:...>
```

Changing the image can also change the expected files (through ForC Succession or the libraries), so update them in the same commit as `LANDIS_IMAGE`.

## Adding a case

Create `tests/cases/<name>/` with either:

- `inputs/`, holding the scenario file and every input it reads; or
- a file `source`, holding one line that names an input directory relative to the repository root.

The scenario file is `scenario.txt` unless a file `scenario` in the case names another. Set `RandomNumberSeed` so the run repeats.

Keep cases small: a few cells, a few years, with ForC output every year (`ForCSOutput` `1 1 1 1`) so the mortality check runs. Then run with `--update` to write `expected/`.

## Cases

All are 6 x 6 cells of 100 m, with western hemlock (Hw, age 310) on columns 1-3 and subalpine fir (Bl, age 230) on columns 4-6, fire tolerance 1, and one weather row for every bin (FFMC 95, BUI 150, wind 40 km/h).

| Case | What it exercises |
|---|---|
| `severity5` | one fire burns all 36 cells in one year, 17 at severity 4 and 19 at severity 5 (#14, #15) |
| `two-regions` | as `severity5`, with columns 1-3 and 4-6 in two fire regions; the fire starts in the first and burns into the second (#17) |
| `one-cell-fires` | 10 years; every fire stops after its ignition cell (#15) |
| `four-regions` | 100 years; four fire regions of 9 cells with `NumFires` 0.5, 0.99, 1 and 2; every fire burns one cell (#17) |
