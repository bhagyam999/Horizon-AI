# Horizon AI — Netlify bridge

The website does **not** call Gemini directly.

Browser → Netlify Function → Railway Horizon API → Horizon AIProvider → Gemini

## Netlify variables

Set these server-side environment variables:

- `HORIZON_BOT_API_URL` — Railway public service URL, for example `https://your-service.up.railway.app`
- `HORIZON_BOT_API_TOKEN` — the same secret as Railway `HORIZON_API_TOKEN`
- `HORIZON_BOT_HTTP_TIMEOUT` — optional, defaults to `20000`

Do not set `GEMINI_API_KEY` for the website.

## Railway variables

The Railway Horizon service keeps:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional)
- `HORIZON_API_TOKEN`
- `PORT` (Railway normally supplies this)

The shared API token is never sent to the browser. The Netlify function adds it when calling Railway.

## API flow

- `GET /.netlify/functions/horizon-ai` checks the Railway Horizon health signal.
- `POST /.netlify/functions/horizon-ai` forwards the conversation to Railway `/api/ai`.
- Railway authenticates the request with `X-Horizon-API-Key` and uses its existing Horizon AI provider.


## Troubleshooting the Railway bridge

The browser never calls Railway directly. It calls `/.netlify/functions/horizon-ai`, and that Netlify function adds `X-Horizon-API-Key` server-side before calling Railway `/health` or `/api/ai`. `HORIZON_BOT_API_TOKEN` must exactly match Railway's `HORIZON_API_TOKEN`. The Gemini key remains only on Railway.

The function has the current Railway URL as a fallback, but `HORIZON_BOT_API_URL` can override it if the Railway service URL changes.
