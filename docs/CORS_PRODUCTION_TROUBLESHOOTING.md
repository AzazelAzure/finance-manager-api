# CORS in production (browser + `https://api.thehivemanager.com`)

## Symptom

- Vite/JS on **`https://jsdevtesting...`** or **`https://api-jsdevtesting...`** shows **ERR_NETWORK** or generic login failure.
- `curl` from a laptop to **`https://api.thehivemanager.com/api/token/`** with an `Origin:` header may show **no** `access-control-*` headers, while the **same** OPTIONS to **`https://127.0.0.1:8443`** (or the container) on the VPS **does** return `access-control-allow-origin`.

That means **Django + nginx for the app are not the weak link**; the path **Cloudflare (or another edge) → origin** is dropping CORS, caching a bad preflight, or a different service is responding on the public name.

## What to do on Cloudflare

1. **Cache Rules** (or **Page Rules**): for hostname **`api.thehivemanager.com`**, set **Cache eligibility** to **Bypass cache** (all paths, all methods) so preflight/POST responses are not a stale cached 200.
2. **Purge** cache for **`api.thehivemanager.com`**, especially if OPTIONS previously returned empty.
3. Review **Transform Rules** / **Workers** on that hostname — do not remove `Access-Control-*` on responses.
4. Re-test from the browser; DevTools **Network** → `token` / `preflight` → Response headers must include `access-control-allow-origin` for your `https://jsdev…` Origin.

## Code (already in repo)

- `corsheaders` in `INSTALLED_APPS` and `CorsMiddleware` in `MIDDLEWARE` (early in the stack).
- Default `CORS_ALLOWED_ORIGINS` in `settings.py` includes the `jsdev*` and Vite local origins; production can override with env — ensure deploy env is not a **narrower** list that omits the tunnel hostnames.

## One-shot checks

**Public (through Cloudflare):**

```bash
curl -sI -X OPTIONS "https://api.thehivemanager.com/api/token/" \
  -H "Origin: https://jsdevtesting.thehivemanager.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
# Expect: access-control-allow-origin, access-control-allow-credentials (if used), not text/html 0-byte body
```

**Direct to TLS listener on the box (should match a healthy app):**

```bash
curl -skI -X OPTIONS "https://127.0.0.1:8443/api/token/" \
  -H "Origin: https://jsdevtesting.thehivemanager.com" \
  -H "Access-Control-Request-Method: POST"
```

If the second has CORS and the first does not, fix the **edge** in front of the public API, not the JS bundle.
