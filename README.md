# Bus commute page

A phone page that answers "when should I leave, and which bus?" for trips between four places, using Madison Metro's live predictions on top of the timetable. Pick where you're starting from (Home, Daycare, Campus, Downtown) and where you're going. Home and Daycare pair with Campus and Downtown.

| Trip | Options shown |
|---|---|
| Home → Campus | B at Commercial & North (off at East Campus), D at Johnson & North (off at University & Mills) |
| Home → Downtown | B at Commercial & North (off at Capitol Square), D at Johnson & North (off at Gorham & Wisconsin) |
| Daycare → Campus | A or B at Fourth Street |
| Daycare → Downtown | A or B at Fourth Street (off at Capitol Square) |
| Campus → Home | B at Park & Dayton, D at Johnson & Orchard, A at Orchard then B at Fourth Street |
| Campus → Daycare | A at Orchard or B at Park & Dayton (off at Fourth Street) |
| Downtown → Home | B at Capitol Square (Main & MLK) |
| Downtown → Daycare | A or B at Capitol Square (off at Fourth Street) |

## What's in this folder

| File | What it does |
|---|---|
| `index.html` | The page you open on your phone. |
| `schedule.json` | Your buses' timetable. Created by the GitHub Action below; you don't edit it. |
| `build_schedule.py` | Builds `schedule.json` from Metro's published schedule. |
| `.github/workflows/schedule.yml` | Runs the builder every Monday, or whenever you click "Run workflow". |
| `worker.js` | The relay that lets the page read Metro's live feed. Lives on Cloudflare, not GitHub. |

## Setup (about 20 minutes)

### 1. Put the files on GitHub

1. On GitHub, create a new **public** repository, for example `commute`.
2. Unzip the download, then drag the whole folder's contents onto the repo's "uploading an existing file" page. Make sure `.github/workflows/schedule.yml` keeps its folder path. If the `.github` folder doesn't come through (hidden folders sometimes don't), use **Add file → Create new file**, type `.github/workflows/schedule.yml` as the name, and paste the file's contents.
3. Commit.

### 2. Build the timetable

1. Open the repo's **Actions** tab. If asked, enable workflows.
2. Click **Update bus schedule → Run workflow**.
3. After about a minute, `schedule.json` appears in the repo.

If it fails with a permissions error: **Settings → Actions → General → Workflow permissions → Read and write permissions**, save, and run it again.

### 3. Turn on GitHub Pages

**Settings → Pages → Build and deployment**: Source "Deploy from a branch", branch `main`, folder `/ (root)`. Save. The page will be at `https://YOUR-USERNAME.github.io/commute/` in a minute or two. It works now, using the timetable only.

### 4. Create the live-data relay on Cloudflare

1. Sign up for a free account at dash.cloudflare.com.
2. Go to **Workers & Pages → Create → Create Worker**. Name it `commute-relay` and click **Deploy**.
3. Click **Edit code**, delete the sample code, paste all of `worker.js`, and click **Deploy**.
4. Copy the worker's address, e.g. `https://commute-relay.yourname.workers.dev`.
5. Check it: open that address plus `/trips` in a browser. A small file should download. That's Metro's live data.

### 5. Connect the page to the relay

In `index.html` on GitHub, click the pencil icon and change this line near the top of the script:

```js
const DEFAULT_RELAY = "";
```

to your worker address:

```js
const DEFAULT_RELAY = "https://commute-relay.yourname.workers.dev";
```

Commit. (You can also paste the address in the page's Settings instead, but that only saves it on one device.)

### 6. Put it on your phone

Open the GitHub Pages address on your phone. On iPhone: **Share → Add to Home Screen**. On Android: **⋮ → Add to Home screen**.

## Adjusting it

- **Walking times:** tap the gear icon. Walking minutes are listed by place and stop, and each number is used in both directions. The defaults are estimates from the stop locations, so time yourself once and update them. Settings are saved per phone, so each person can set their own.
- **Your usual trip:** the page remembers the last trip you picked, separately for mornings and afternoons, so it opens on your usual trip.
- **Buffer:** minutes you want to be at the stop before the bus (default 1). Raise it in winter.
- **Transfer time:** minimum minutes to change from the A to the B at Fourth Street (default 1). Both stop at the same eastbound platform.

## Things to double-check

- **Where you get off near home.** The B ends at Commercial & North and the D at North & Johnson, assumed from where you board in the morning.
- **The evening D stop on campus.** Set to Johnson & Orchard. Other D stops nearby are Johnson & Mills (GTFS stop 1757) and Randall & Dayton by Union South (stop 2628).
- **Downtown walking times.** The two Capitol Square platforms are on opposite sides of the square: buses toward campus stop on Mifflin at Wisconsin (about 6 minutes from the City County Building), and buses toward the east side stop on Main at MLK (about 2 minutes).

To change a stop, edit the `ROUTES` list in `index.html` and the matching list in `STOPS_BY_DIR` in `build_schedule.py`. Committing `build_schedule.py` rebuilds the timetable automatically.

## How it works

- Both directions work at any time of day, including late-night buses that run past midnight.
- Metro's live feed refreshes about every 30 seconds. The page checks every 30 seconds while it's open and pauses when the phone is locked.
- Each timetable trip is matched to its live prediction by trip ID. If a bus has a live prediction, its time is "Live". If not, the page uses the timetable and says so. Canceled trips are shown crossed out.
- The "Best" option is the one that gets you there earliest. If two tie (for example, the A-to-B transfer catches the same B you'd get by walking to Park & Dayton), it picks the one that lets you leave later.
- Metro's schedule changes a few times a year. The current one runs through December 5, 2026. The weekly Action picks up new schedules automatically, and the page footer warns you if the timetable has expired.

Data provided under license granted by City of Madison, WI, Metro Transit.
