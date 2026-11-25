// Daily Bread Online → Bible Brain (Faith Comes By Hearing's Digital Bible Platform v4), Supabase Edge Function "bible-text"
//
// Bible Brain keys must not be shared, so the reader asks this function and the function asks Bible Brain with the key.
// Only a few read-only requests are passed on (ALLOWED); everything else is refused.
//   GET ?path=/bibles/filesets/SWESFB/GEN/1        the verses of a chapter (text filesets)
//   GET ?path=/bibles/filesets/SWESFB/copyright    the copyright lines for a fileset
//   GET ?path=/bibles&language_code=swe            the Bibles (and their filesets) in a language — for setting up
//
// Secret (Supabase → Edge Functions → Secrets):  BIBLE_BRAIN_KEY   the API key from 4.dbt.io
// Deploy with "Verify JWT" turned off: the reader calls it without signing in.

const ORIGINS = ["https://dailybread.study", "https://www.dailybread.study", "https://dailybreadstudies.github.io",
  "http://localhost:8765", "http://127.0.0.1:8765"];
const KEY = Deno.env.get("BIBLE_BRAIN_KEY") || "";
const ALLOWED = [
  /^\/bibles\/filesets\/[A-Za-z0-9_-]{6,24}\/[1-3A-Z]{3}\/\d{1,3}$/,
  /^\/bibles\/filesets\/[A-Za-z0-9_-]{6,24}\/copyright$/,
  /^\/bibles$/,
  /^\/bibles\/[A-Za-z0-9_-]{6,12}$/,
];
const PASS = ["language_code", "media", "page", "limit"];   // query parameters passed on for /bibles

function cors(origin: string | null) {
  return {
    "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
    "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Vary": "Origin",
  };
}

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  if (req.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
  if (req.method !== "GET") return new Response("Only GET", { status: 405, headers: cors(origin) });
  if (!KEY) return new Response(JSON.stringify({ error: "BIBLE_BRAIN_KEY is not set" }), { status: 503, headers: { ...cors(origin), "Content-Type": "application/json" } });

  const url = new URL(req.url);
  const path = url.searchParams.get("path") || "";
  if (!ALLOWED.some((re) => re.test(path))) {
    return new Response(JSON.stringify({ error: "Not allowed" }), { status: 400, headers: { ...cors(origin), "Content-Type": "application/json" } });
  }
  const up = new URL("https://4.dbt.io/api" + path);
  up.searchParams.set("v", "4");
  up.searchParams.set("key", KEY);
  for (const p of PASS) { const v = url.searchParams.get(p); if (v) up.searchParams.set(p, v); }

  const r = await fetch(up.toString(), { headers: { Accept: "application/json" } });
  const body = await r.text();
  return new Response(body, {
    status: r.status,
    headers: { ...cors(origin), "Content-Type": "application/json", "Cache-Control": r.ok ? "public, max-age=3600" : "no-store" },
  });
});
