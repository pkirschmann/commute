// Cloudflare Worker: relays Madison Metro's live GTFS-Realtime feeds so a web page
// on another site (like GitHub Pages) is allowed to read them.
//
//   https://<your-worker>.workers.dev/trips     -> predicted arrival times
//   https://<your-worker>.workers.dev/vehicles  -> bus positions
//   https://<your-worker>.workers.dev/alerts    -> detours and notices
//
// Data provided under license granted by City of Madison, WI, Metro Transit.

const FEEDS = {
  trips: "https://metromap.cityofmadison.com/gtfsrt/trips",
  vehicles: "https://metromap.cityofmadison.com/gtfsrt/vehicles",
  alerts: "https://metromap.cityofmadison.com/gtfsrt/alerts",
};

// Which websites may read from this relay. "*" means any site.
// To lock it to your page, use e.g. ["https://yourname.github.io"].
const ALLOWED_ORIGINS = ["*"];

// Metro updates its feed about every 30 seconds, so a short cache spares
// Metro's server without making the data noticeably staler.
const CACHE_SECONDS = 15;
const memo = {}; // name -> { at, body }

function corsHeaders(req) {
  const origin = req.headers.get("Origin") || "";
  const allow = ALLOWED_ORIGINS.includes("*") ? "*" : (ALLOWED_ORIGINS.includes(origin) ? origin : "");
  const h = {
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Expose-Headers": "X-Relay-Age, X-Relay-Stale",
    "Vary": "Origin",
  };
  if (allow) h["Access-Control-Allow-Origin"] = allow;
  return h;
}

export default {
  async fetch(req) {
    const cors = corsHeaders(req);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (req.method !== "GET") return new Response("Use GET", { status: 405, headers: cors });

    const name = new URL(req.url).pathname.replace(/^\/+|\/+$/g, "");
    const upstream = FEEDS[name];
    if (!upstream) {
      return new Response("Try /trips, /vehicles or /alerts", { status: 404, headers: cors });
    }

    const now = Date.now();
    let hit = memo[name];
    if (!hit || now - hit.at > CACHE_SECONDS * 1000) {
      const res = await fetch(upstream, { headers: { "User-Agent": "commute-page-relay" } });
      if (!res.ok) {
        if (hit) return send(hit, cors, true); // serve the last good copy
        return new Response("Metro's feed returned " + res.status, { status: 502, headers: cors });
      }
      hit = memo[name] = { at: now, body: await res.arrayBuffer() };
    }
    return send(hit, cors, false);
  },
};

function send(hit, cors, stale) {
  return new Response(hit.body, {
    headers: {
      ...cors,
      "Content-Type": "application/x-protobuf",
      "Cache-Control": "no-store",
      "X-Relay-Age": String(Math.round((Date.now() - hit.at) / 1000)),
      ...(stale ? { "X-Relay-Stale": "1" } : {}),
    },
  });
}
