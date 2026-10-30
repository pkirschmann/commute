"""Build schedule.json for the commute page from Madison Metro's GTFS schedule.

Run by the GitHub Action in .github/workflows/schedule.yml (weekly, or on demand).
Locally: python build_schedule.py  (or pass a path to an already-downloaded mmt_gtfs.zip)
"""
import csv
import io
import json
import sys
import urllib.request
import zipfile

GTFS_URL = "https://transitdata.cityofmadison.com/GTFS/mmt_gtfs.zip"

# route + direction_id -> stops to keep, in travel order (first = board, last = alight).
# Stop IDs are GTFS stop_id values (not the 4-digit numbers on stop signs).
STOPS_BY_DIR = {
    # Toward campus: Commercial & North -> Fourth Street -> Capitol Square (Mifflin) -> East Campus (Chazen)
    "B0": ["218", "2857", "2847", "2844"],
    "D0": ["581", "2083", "2810"],          # E Johnson at North -> W Gorham at Wisconsin -> University at N Mills
    "A0": ["2857", "2847", "2864"],         # Fourth Street -> Capitol Square (Mifflin) -> Orchard
    # Toward the east/north side: Orchard (Johnson St side) -> Capitol Square (Main & MLK) -> Fourth Street
    "A1": ["2865", "2848", "2858"],
    "B1": ["1301", "2848", "2858", "211"],  # Park & Dayton -> Capitol Square -> Fourth Street -> Commercial & North
    "D1": ["2896", "239"],                  # W Johnson at N Orchard -> North at E Johnson
}
ROUTES = sorted({k[0] for k in STOPS_BY_DIR})


def to_sec(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def read(z, name):
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))


def build(zip_bytes):
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    trips = {t["trip_id"]: t for t in read(z, "trips.txt") if t["route_id"] in ROUTES}
    wanted = {}
    for tid, t in trips.items():
        key = t["route_id"] + t["direction_id"]
        if key in STOPS_BY_DIR:
            wanted[tid] = key

    times = {}
    with z.open("stop_times.txt") as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
            key = wanted.get(r["trip_id"])
            if not key:
                continue
            stops = STOPS_BY_DIR[key]
            if r["stop_id"] not in stops:
                continue
            is_last = r["stop_id"] == stops[-1]
            t = r["arrival_time"] if is_last else r["departure_time"]
            times.setdefault(r["trip_id"], {})[r["stop_id"]] = to_sec(t)

    out = {k: [] for k in STOPS_BY_DIR}
    services = set()
    for tid, m in times.items():
        if len(m) < 2:
            continue
        key = wanted[tid]
        row = [m.get(s) for s in STOPS_BY_DIR[key]]
        sid = trips[tid]["service_id"]
        services.add(sid)
        out[key].append([tid, sid] + row)
    for rows in out.values():
        rows.sort(key=lambda r: next(x for x in r[2:] if x is not None))

    calendar = [
        [c["service_id"],
         "".join(c[d] for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]),
         c["start_date"], c["end_date"]]
        for c in read(z, "calendar.txt") if c["service_id"] in services
    ]
    dates = [[d["service_id"], d["date"], d["exception_type"]]
             for d in read(z, "calendar_dates.txt") if d["service_id"] in services]
    info = read(z, "feed_info.txt")[0]
    keep = {s for v in STOPS_BY_DIR.values() for s in v}
    stops = {s["stop_id"]: {"name": s["stop_name"], "code": s["stop_code"],
                            "lat": float(s["stop_lat"]), "lon": float(s["stop_lon"])}
             for s in read(z, "stops.txt") if s["stop_id"] in keep}
    colors = {r["route_id"]: "#" + (r.get("route_color") or "777777")
              for r in read(z, "routes.txt") if r["route_id"] in ROUTES}
    return {
        "feedVersion": info.get("feed_version"),
        "feedStart": info.get("feed_start_date"),
        "feedEnd": info.get("feed_end_date"),
        "stopsByDir": STOPS_BY_DIR,
        "stops": stops,
        "colors": colors,
        "trips": out,
        "calendar": calendar,
        "dates": dates,
    }


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            data = f.read()
    else:
        req = urllib.request.Request(GTFS_URL, headers={"User-Agent": "commute-page-schedule-builder"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    sched = build(data)
    with open("schedule.json", "w") as f:
        json.dump(sched, f, separators=(",", ":"))
    counts = {k: len(v) for k, v in sched["trips"].items()}
    print("feed", sched["feedVersion"], "valid until", sched["feedEnd"], "trips", counts)
    if sum(counts.values()) == 0:
        sys.exit("No trips found: stop or route IDs may have changed in Metro's schedule.")


if __name__ == "__main__":
    main()
