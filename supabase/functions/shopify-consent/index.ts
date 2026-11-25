// Daily Bread Online → Ariel Media Shopify list (Supabase Edge Function "shopify-consent")
//
// The site calls this after a reader's email-list choice is saved in the "consent" table. It reads that
// reader's latest choice (never trusting the browser for it) and updates their Shopify customer:
//   • opted in  → create the customer, or update an existing one, as subscribed (confirmed opt-in: the
//                 address was proven by the sign-in code), with the tags daily-bread-online + dbo-us-preticked
//                 or dbo-opted-in
//   • switched off in the account panel → unsubscribed in Shopify
//   • left unticked at sign-in → nothing changes in Shopify (an existing subscriber is never unsubscribed
//                 just because a box was left empty)
//
// Secrets (Supabase → Edge Functions → Secrets):
//   SHOPIFY_SHOP           the store's myshopify subdomain, e.g. "ariel-media" for ariel-media.myshopify.com
//   SHOPIFY_CLIENT_ID      the Dev Dashboard app's client ID
//   SHOPIFY_CLIENT_SECRET  the Dev Dashboard app's client secret
// SUPABASE_URL and the server key (SUPABASE_SECRET_KEYS or SUPABASE_SERVICE_ROLE_KEY) are provided by Supabase automatically.
// Deploy with "Verify JWT" turned off: the function checks the reader's sign-in itself.

const API_VERSION = "2026-10";
const ORIGINS = ["https://dailybread.study", "https://www.dailybread.study", "https://dailybreadstudies.github.io"];

const SB_URL = Deno.env.get("SUPABASE_URL")!;
// The server key: the newer "sb_secret_…" style (SUPABASE_SECRET_KEYS) or the older service-role JWT
function serverKey(): string {
  try { const k = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}"); if (k.default) return k.default; } catch (_) { /* fall back */ }
  return Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
}
const SB_KEY = serverKey();
const SB_AUTH: Record<string, string> = SB_KEY.startsWith("sb_") ? { apikey: SB_KEY } : { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };
const SHOP = (Deno.env.get("SHOPIFY_SHOP") || "").replace(/\.myshopify\.com$/, "");
const CLIENT_ID = Deno.env.get("SHOPIFY_CLIENT_ID") || "";
const CLIENT_SECRET = Deno.env.get("SHOPIFY_CLIENT_SECRET") || "";

function cors(origin: string | null) {
  return {
    "Access-Control-Allow-Origin": origin && ORIGINS.includes(origin) ? origin : ORIGINS[0],
    "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}
function reply(body: unknown, status: number, origin: string | null) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors(origin), "Content-Type": "application/json" } });
}

// ── Shopify: a 24-hour token from the client credentials grant, kept while the function stays warm ──
let token = "", tokenUntil = 0;
async function shopifyToken(): Promise<string> {
  if (token && Date.now() < tokenUntil) return token;
  const r = await fetch(`https://${SHOP}.myshopify.com/admin/oauth/access_token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "client_credentials", client_id: CLIENT_ID, client_secret: CLIENT_SECRET }),
  });
  if (!r.ok) throw new Error(`Shopify token request failed: ${r.status} ${await r.text()}`);
  const j = await r.json();
  token = j.access_token;
  tokenUntil = Date.now() + ((j.expires_in || 86399) - 300) * 1000;
  return token;
}
async function gql(query: string, variables: Record<string, unknown>) {
  const r = await fetch(`https://${SHOP}.myshopify.com/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Shopify-Access-Token": await shopifyToken() },
    body: JSON.stringify({ query, variables }),
  });
  if (!r.ok) throw new Error(`Shopify request failed: ${r.status}`);
  const j = await r.json();
  if (j.errors?.length) throw new Error(`Shopify: ${JSON.stringify(j.errors)}`);
  return j.data;
}
function userErrors(d: Record<string, { userErrors?: { message: string }[] }>) {
  const e = Object.values(d)[0]?.userErrors || [];
  if (e.length) throw new Error("Shopify: " + e.map((x) => x.message).join("; "));
}

// ── Supabase REST with the service key ──
async function sb(path: string, init: RequestInit = {}) {
  const r = await fetch(SB_URL + path, {
    ...init,
    headers: { ...SB_AUTH, "Content-Type": "application/json", ...(init.headers || {}) },
  });
  if (!r.ok) throw new Error(`Supabase ${path}: ${r.status} ${await r.text()}`);
  const t = await r.text();
  return t ? JSON.parse(t) : null;
}

Deno.serve(async (req) => {
  const origin = req.headers.get("Origin");
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors(origin) });
  if (req.method !== "POST") return reply({ error: "POST only" }, 405, origin);
  if (!SHOP || !CLIENT_ID || !CLIENT_SECRET) return reply({ error: "Shopify is not set up yet" }, 503, origin);

  // 1. Who is asking: the reader's own sign-in token
  const auth = req.headers.get("Authorization") || "";
  const ur = await fetch(SB_URL + "/auth/v1/user", { headers: { apikey: SB_KEY, Authorization: auth } });
  if (!ur.ok) return reply({ error: "Not signed in" }, 401, origin);
  const user = await ur.json();
  if (!user?.id || !user?.email) return reply({ error: "Not signed in" }, 401, origin);

  try {
    // 2. Their latest saved choice
    const rows = await sb(`/rest/v1/consent?user_id=eq.${user.id}&select=id,opted_in,variant,method,created_at,shopify_synced_at&order=created_at.desc&limit=1`);
    const c = rows?.[0];
    if (!c) return reply({ ok: true, note: "no choice saved" }, 200, origin);
    if (c.shopify_synced_at) return reply({ ok: true, note: "already in step" }, 200, origin);

    // 3. Their Shopify customer, if they already are one (a journal buyer, say)
    const found = await gql(
      `query($email: String!) { customerByIdentifier(identifier: { emailAddress: $email }) { id emailMarketingConsent { marketingState } } }`,
      { email: user.email },
    );
    const customer = found.customerByIdentifier;
    const state = customer?.emailMarketingConsent?.marketingState;
    const tags = ["daily-bread-online", c.variant === "us-preticked" ? "dbo-us-preticked" : "dbo-opted-in"];
    let action = "none";

    if (c.opted_in) {
      const consent = { marketingState: "SUBSCRIBED", marketingOptInLevel: "CONFIRMED_OPT_IN", consentUpdatedAt: c.created_at };
      if (!customer) {
        const d = await gql(
          `mutation($input: CustomerInput!) { customerCreate(input: $input) { customer { id } userErrors { field message } } }`,
          { input: { email: user.email, tags, emailMarketingConsent: consent } },
        );
        userErrors(d);
        action = "created";
      } else {
        userErrors(await gql(
          `mutation($id: ID!, $tags: [String!]!) { tagsAdd(id: $id, tags: $tags) { userErrors { field message } } }`,
          { id: customer.id, tags },
        ));
        if (state !== "SUBSCRIBED") {
          userErrors(await gql(
            `mutation($input: CustomerEmailMarketingConsentUpdateInput!) { customerEmailMarketingConsentUpdate(input: $input) { userErrors { field message } } }`,
            { input: { customerId: customer.id, emailMarketingConsent: consent } },
          ));
          action = "subscribed";
        } else action = "tagged";
      }
    } else if (c.method === "account" && customer && state === "SUBSCRIBED") {
      // Switched off in the account panel: a clear "stop emailing me"
      userErrors(await gql(
        `mutation($input: CustomerEmailMarketingConsentUpdateInput!) { customerEmailMarketingConsentUpdate(input: $input) { userErrors { field message } } }`,
        { input: { customerId: customer.id, emailMarketingConsent: { marketingState: "UNSUBSCRIBED", consentUpdatedAt: c.created_at } } },
      ));
      action = "unsubscribed";
    }

    // 4. Mark this choice as done
    await sb(`/rest/v1/consent?id=eq.${c.id}`, { method: "PATCH", body: JSON.stringify({ shopify_synced_at: new Date().toISOString() }) });
    return reply({ ok: true, action }, 200, origin);
  } catch (e) {
    console.error(e);
    return reply({ error: "Could not update the list just now" }, 502, origin);
  }
});
