# Log Horizon Website

This is the complete React/Vite website used by the unified Railway project. It is built by the root Dockerfile and served by Horizon's aiohttp web server.

The website talks to the same Railway process through same-origin endpoints:

- `/api/auth/login`
- `/api/auth/callback`
- `/api/auth/me`
- `/api/auth/logout`
- `/api/ai`
- `/health`

No Gemini or Discord bot secret is shipped to the browser.
