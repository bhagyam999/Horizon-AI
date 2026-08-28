# Horizon AI — Gemini Discord Bot v1.6.1

This build fixes duplicate slash-command registration, improves `/ask` timeout handling, and keeps the local dashboard from crashing when its port is busy.

## Install
1. Install Python 3.11+ (your Python 3.14 setup is supported by this package).
2. Run `setup.bat`.
3. Open `.env`.
4. Put your Discord bot token in `DISCORD_TOKEN`.
5. Put your Google Gemini API key in `GEMINI_API_KEY`.
6. Keep `GEMINI_MODEL=gemini-2.5-flash-lite` initially.
7. Optionally set `DISCORD_GUILD_ID` to your server ID for fast slash-command syncing.
8. Run `start.bat`.

## v1.6.1 critical fix
- Fixed the `ImportError: cannot import name 'AIProvider'` that prevented the bot from starting.
- Added the `AIProvider` wrapper expected by `bot.py`, including `.generate()`, `.status()`, `.gemini.model_names()`, `.model`, `.enabled`, and `.provider_name`.
- `/ask` now performs automatic Gemini model failover using the models visible to your API key.
- `GEMINI_HTTP_TIMEOUT` and the older `GEMINI_TIMEOUT` setting are both accepted.

## Important fixes
- `/ask` no longer waits for Gemini model discovery before every request.
- Gemini requests use a direct HTTPS call with a 12-second default timeout. If the first model stalls, Horizon tries one alternate model instead of hanging indefinitely.
- The Gemini SDK is not required; this avoids SDK/import-version problems and keeps installation smaller.
- Model names automatically strip a mistaken `models/` prefix.
- If the configured model is unavailable, Horizon tries known Gemini models.
- Gemini API errors are returned to Discord instead of leaving the interaction stuck.
- If dashboard port 8765 is already occupied, Horizon automatically tries the next ports instead of crashing.
- `.env` is intentionally not included in this ZIP, so your API keys are not exposed.

## Commands
Use `/help` in Discord to see the available commands.



## v1.4 fixes
- `/ask` calls the configured Gemini model immediately instead of waiting for model discovery.
- Model fallback happens only for an explicit model-not-found response.
- Gemini timeouts and API errors return promptly to Discord.
- When `DISCORD_GUILD_ID` is set, Horizon syncs guild commands and removes stale global copies to prevent duplicate slash commands.

## v1.5 fixes
- Clears stale global and guild slash-command registrations before syncing the current command set, preventing duplicate `/ai_models`, `/ai_status`, etc.
- Uses the `x-goog-api-key` header for Gemini requests.
- `/ask` tries one alternate Gemini model after a timeout, then returns a clear error.
- Default Gemini request timeout reduced to 12 seconds.

## GitHub setup

This project is GitHub-ready. **Do not upload your `.env` file or any API keys.**
The repository includes a `.gitignore` that excludes `.env`, local databases, caches,
and virtual environments.

### Push it to GitHub

Create an empty repository on GitHub, then from this folder run:

```bash
git init
git add .
git commit -m "Horizon AI v1.6.1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

The included GitHub Actions workflow checks that the Python files compile and that
the dependencies install successfully.

### Important: GitHub is not the bot host

GitHub stores the source code; it does not keep a Discord bot running 24/7.
For continuous uptime, the repository can later be connected to a suitable hosting
service. Keep `DISCORD_TOKEN` and `GEMINI_API_KEY` in that host's secret/environment
settings rather than committing them.
