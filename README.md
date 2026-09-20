# Log Horizon Website

This is the complete React/Vite website bundled with Horizon AI. The preferred deployment is the combined Railway service: Railway builds this Vite app and the Python dashboard serves `dist` from the same domain.

The original Netlify Functions are retained under `netlify/functions/` for reference/standalone Netlify deployment, but the combined Railway deployment uses same-origin `/api/site/*` endpoints.
