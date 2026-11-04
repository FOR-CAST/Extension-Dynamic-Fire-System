#!/usr/bin/env python3
"""Check a Dynamic Fire test run against the user guide, and write its digest.

Usage: check.py <run_dir> <digest_dir>

Python 3 standard library only. Finds the Dynamic Fire input file through the scenario file
(scenario.txt, or the name in $SCENARIO), and from it the event log, the summary log, the
severity maps and the initial fire-region map. For every time step with a severity map it checks:

  events     each event's DamagedSites equals its SitesChecked, and their sums equal the burned
             cells on the severity map (user guide 3.1 and 3.2);
  severity   the events' MeanSeverity x SitesChecked sum to the severities on the map (1.9);
  summary    NumberFires equals the events in the event log, TotalSitesBurned the burned cells
             on the map, and EcoMaps_<k> the burned cells in the k-th fire region of the fire
             region table (3.3);
  mortality  if the succession extension is ForC Succession and it logs biomass every year: every
             cohort on a severity-5 cell dies (1.9), and the events' CohortsKilled sum to the
             cohorts that died on burned cells.

The mortality check counts a cohort as dead if it is in log_BiomassC.csv one fire time step
earlier and not at this time. ForC writes no rows for a year without cohorts, so the check runs
only when its Biomass output interval (ForCSOutput) is 1, which makes a year without rows a year
without cohorts. A case should not let cohorts die of other causes on burned cells. Region counts
are checked only while the initial fire-region map applies (no DynamicEcoregionTable rows), and
only if that map is ESRI ASCII or an uncompressed 8-bit GeoTIFF.

Writes <digest_dir>/fire.csv, one row per time step (events, burned cells by severity,
CohortsKilled, the summary log's columns), and <digest_dir>/sha256sums.txt, the checksums of the
fire logs, the severity maps and any ForC Succession logs. Exits 1 if any check fails.
"""
import csv, glob, hashlib, os, re, struct, sys

def read_tiff(path):
    b = open(path, "rb").read()
    e = {b"II": "<", b"MM": ">"}[b[:2]]
    ifd = struct.unpack(e + "I", b[4:8])[0]
    n = struct.unpack(e + "H", b[ifd:ifd + 2])[0]
    tags = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack(e + "HHII", b[ifd + 2 + 12 * i: ifd + 14 + 12 * i])
        if typ == 3 and cnt == 1:
            val = struct.unpack(e + "H", b[ifd + 10 + 12 * i: ifd + 12 + 12 * i])[0]
        tags[tag] = (typ, cnt, val)
    w, h = tags[256][2], tags[257][2]
    if tags.get(259, (0, 0, 1))[2] != 1 or tags.get(258, (0, 0, 8))[2] != 8:
        raise ValueError("%s: only uncompressed 8-bit GeoTIFFs are read" % path)
    typ, cnt, val = tags[273 if 273 in tags else 324]
    if cnt != 1:
        raise ValueError("%s: multi-strip GeoTIFFs are not read" % path)
    return [list(b[val + r * w: val + (r + 1) * w]) for r in range(h)]

def read_asc(path):
    return [[int(float(v)) for v in line.split()] for line in open(path)
            if line.split() and not re.match(r"[A-Za-z]", line.split()[0])]

def read_grid(path):
    return read_asc(path) if path.lower().endswith(".asc") else read_tiff(path)

def read_log(path):
    with open(path, newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in r.items() if k and k.strip()}
                for r in csv.DictReader(f)]

def strip_comments(text):
    lines = []
    for line in text.splitlines():
        line = line.split("<<")[0]
        if not line.lstrip().startswith(">>"):
            lines.append(line.rstrip())
    return lines

def extension_file(run_dir, name):
    scen = os.environ.get("SCENARIO", "scenario.txt")
    m = re.search(r'^\s*"%s"\s+(\S+)' % re.escape(name), open(os.path.join(run_dir, scen)).read(), re.M)
    return os.path.join(run_dir, m.group(1)) if m else None

def forc_biomass_interval(run_dir):
    path = extension_file(run_dir, "ForC Succession")
    if path is None:
        return None
    lines = [l for l in strip_comments(open(path).read()) if l.split()]
    i = next((i for i, l in enumerate(lines) if l.split()[0] == "ForCSOutput"), None)
    return None if i is None else int(lines[i + 1].split()[0])

def fire_inputs(run_dir):
    path = extension_file(run_dir, "Dynamic Fire System")
    if path is None:
        raise ValueError("the scenario file names no Dynamic Fire System input file")
    lines = strip_comments(open(path).read())
    value = {}
    for line in lines:
        f = line.split()
        if len(f) >= 2 and f[0] in ("Timestep", "MapNames", "LogFile", "SummaryLogFile", "InitialFireEcoregionsMap"):
            value[f[0]] = f[1]
    # the fire region table: rows of 16 values between EventSizeType and InitialFireEcoregionsMap
    start = next(i for i, l in enumerate(lines) if l.split()[:1] == ["EventSizeType"])
    stop = next(i for i, l in enumerate(lines) if l.split()[:1] == ["InitialFireEcoregionsMap"])
    regions = [int(l.split()[0]) for l in lines[start:stop] if len(l.split()) == 16 and l.split()[0].isdigit()]
    # rows of the DynamicEcoregionTable, before the next keyword
    i = next(i for i, l in enumerate(lines) if l.split()[:1] == ["DynamicEcoregionTable"])
    dynamic = []
    for l in lines[i + 1:]:
        f = l.split()
        if not f:
            continue
        if not f[0].isdigit():
            break
        dynamic.append(f)
    return value, regions, dynamic

def main(run_dir, digest_dir):
    failures, checks = [], 0
    def check(ok, kind, msg):
        nonlocal checks
        checks += 1
        if not ok:
            failures.append((kind, msg))

    value, regions, dynamic = fire_inputs(run_dir)
    ev = read_log(os.path.join(run_dir, value["LogFile"]))
    sm = {int(r["Time"]): r for r in read_log(os.path.join(run_dir, value["SummaryLogFile"]))}
    pattern = os.path.join(run_dir, value["MapNames"])
    rx = re.compile(re.escape(pattern).replace(re.escape("{timestep}"), r"(\d+)") + "$")
    maps = {}
    for p in glob.glob(pattern.replace("{timestep}", "*")):
        m = rx.match(p)
        if m:
            maps[int(m.group(1))] = p
    if not maps:
        raise ValueError("no severity maps match %s" % value["MapNames"])

    region_grid, region_note = None, ""
    if dynamic:
        region_note = "region counts not checked: DynamicEcoregionTable has rows"
    else:
        try:
            region_grid = read_grid(os.path.join(run_dir, value["InitialFireEcoregionsMap"]))
        except (ValueError, OSError) as e:
            region_note = "region counts not checked: %s" % e

    cohorts, mortality_note = None, ""
    interval = forc_biomass_interval(run_dir)
    if interval is None:
        mortality_note = "mortality not checked: the succession extension is not ForC Succession"
    elif interval != 1:
        mortality_note = "mortality not checked: ForC logs biomass every %d years, not every year" % interval
    else:
        cohorts = {}
        for r in read_log(os.path.join(run_dir, "log_BiomassC.csv")):
            t = int(r["Time"])
            cohorts.setdefault(t, set()).add((int(r["row"]), int(r["column"]), r["species"], int(r["Age"]) - t))

    step = int(value["Timestep"])
    rows = []
    for t in sorted(maps):
        g = read_grid(maps[t])
        e = [r for r in ev if int(r["Time"]) == t]
        burned = {(r + 1, c + 1): v - 2 for r, row in enumerate(g) for c, v in enumerate(row) if v >= 2}
        sc = sum(int(r["SitesChecked"]) for r in e)
        ds = sum(int(r["DamagedSites"]) for r in e)
        killed = sum(int(r["CohortsKilled"]) for r in e)
        for r in e:
            check(r["DamagedSites"] == r["SitesChecked"], "events", "t %d, event at (%s, %s): DamagedSites %s != SitesChecked %s"
                  % (t, r["InitSiteRow"], r["InitSiteColumn"], r["DamagedSites"], r["SitesChecked"]))
        check(sc == len(burned), "events", "t %d: events' SitesChecked sum to %d, map has %d burned cells" % (t, sc, len(burned)))
        check(ds == len(burned), "events", "t %d: events' DamagedSites sum to %d, map has %d burned cells" % (t, ds, len(burned)))
        sev_events = sum(float(r["MeanSeverity"]) * int(r["SitesChecked"]) for r in e)
        sev_map = sum(burned.values())
        check(abs(sev_events - sev_map) < 1e-6 * max(1, len(e)), "severity",
              "t %d: events' MeanSeverity x SitesChecked sum to %.6f, map severities to %d" % (t, sev_events, sev_map))

        s = sm.get(t)
        check(s is not None, "summary", "t %d: no summary log row" % t)
        eco = []
        if s is not None:
            check(int(s["NumberFires"]) == len(e), "summary", "t %d: NumberFires %s, event log has %d events" % (t, s["NumberFires"], len(e)))
            check(int(s["TotalSitesBurned"]) == len(burned), "summary", "t %d: TotalSitesBurned %s, map has %d burned cells"
                  % (t, s["TotalSitesBurned"], len(burned)))
            eco = [int(float(s["EcoMaps_%d" % (k + 1)])) for k in range(len(regions))]
            if region_grid is not None:
                for k, code in enumerate(regions):
                    n = sum(1 for (r, c) in burned if region_grid[r - 1][c - 1] == code)
                    check(eco[k] == n, "regions", "t %d: EcoMaps_%d %d, map has %d burned cells in fire region %d" % (t, k + 1, eco[k], n, code))

        died = None
        if cohorts is not None:
            before = [x for x in cohorts.get(t - step, set()) if (x[0], x[1]) in burned]
            after = cohorts.get(t, set())
            died = sum(1 for x in before if x not in after)
            survivors = [x for x in before if burned[(x[0], x[1])] == 5 and x in after]
            check(not survivors, "mortality", "t %d: %d cohorts survive on severity-5 cells, e.g. %s" % (t, len(survivors), survivors[:3]))
            check(killed == died, "mortality", "t %d: events' CohortsKilled sum to %d, %d cohorts died on burned cells" % (t, killed, died))

        counts = [sum(1 for v in burned.values() if v == k) for k in range(6)]
        rows.append([t, len(e), len(burned)] + counts + [sc, ds, killed, "" if died is None else died] +
                    ([s["NumberFires"], s["TotalSitesBurned"]] if s else ["", ""]) + eco)

    os.makedirs(digest_dir, exist_ok=True)
    with open(os.path.join(digest_dir, "fire.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Time", "Events", "BurnedCells"] + ["Severity%d" % k for k in range(6)] +
                   ["SitesChecked", "DamagedSites", "CohortsKilled", "CohortsDied", "NumberFires", "TotalSitesBurned"] +
                   ["EcoMaps_%d" % (k + 1) for k in range(len(regions))])
        w.writerows(rows)
    files = [value["LogFile"], value["SummaryLogFile"]] + [os.path.relpath(maps[t], run_dir) for t in sorted(maps)]
    files += sorted(os.path.basename(p) for p in glob.glob(os.path.join(run_dir, "log_*.csv")))
    with open(os.path.join(digest_dir, "sha256sums.txt"), "w") as f:
        for name in files:
            f.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(run_dir, name), "rb").read()).hexdigest(), name))

    print("check.py: %d time steps, %d events, %d checks, %d failed" % (len(maps), len(ev), checks, len(failures)))
    for note in (region_note, mortality_note):
        if note:
            print("check.py: " + note)
    if failures:
        kinds = {}
        for kind, _ in failures:
            kinds[kind] = kinds.get(kind, 0) + 1
        print("check.py: failed by check: " + ", ".join("%s %d" % kv for kv in sorted(kinds.items())))
    for _, msg in failures[:20]:
        print("  FAIL " + msg)
    if len(failures) > 20:
        print("  ... and %d more" % (len(failures) - 20))
    return 1 if failures else 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
